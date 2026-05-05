#!/usr/bin/env python3
"""Fixture tests for scripts/normalize-benchmark-run.py."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / "scripts" / "normalize-benchmark-run.py"


def write_json(path: Path, data: dict) -> None:
    """Write fixture JSON data to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_fixture_dataset(root: Path) -> Path:
    """Create a minimal fixture dataset."""

    dataset = root / "datasets" / "kubernetes-core"
    dataset.mkdir(parents=True)
    (dataset / "dataset.toml").write_text(
        """
[dataset]
name = "kubeply/kubernetes-core"
description = "Fixture dataset"
keywords = ["kubernetes"]
""".lstrip()
    )
    task = dataset / "restore-multi-hop-checkout-route"
    task.mkdir()
    (task / "task.toml").write_text(
        """
schema_version = "1.1"

[task]
name = "kubeply/restore-multi-hop-checkout-route"
description = "Fixture task"
category = "service-connectivity"
keywords = ["kubernetes", "service-routing"]

[metadata]
difficulty = "hard"
""".lstrip()
    )
    return dataset


def write_fixture_job(root: Path) -> Path:
    """Create a minimal fixture Harbor job directory."""

    job = root / "jobs" / "job-openai"
    write_json(
        job / "result.json",
        {
            "started_at": "2026-04-26T12:00:00Z",
            "finished_at": "2026-04-26T12:05:00Z",
        },
    )
    trial = job / "restore-multi-hop-checkout-route"
    write_json(
        trial / "config.json",
        {"task_name": "kubeply/restore-multi-hop-checkout-route"},
    )
    write_json(
        trial / "result.json",
        {
            "passed": True,
            "reward": 1,
            "started_at": "2026-04-26T12:00:00Z",
            "finished_at": "2026-04-26T12:05:00Z",
            "agent_execution": {
                "started_at": "2026-04-26T12:01:00Z",
                "finished_at": "2026-04-26T12:03:00Z",
            },
            "verifier": {
                "started_at": "2026-04-26T12:04:00Z",
                "finished_at": "2026-04-26T12:04:15Z",
            },
            "agent_result": {
                "n_input_tokens": 1234,
                "n_cache_tokens": 1000,
                "n_output_tokens": 56,
                "cost_usd": None,
            },
            "status": "completed",
        },
    )
    write_json(
        trial / "agent" / "trajectory.json",
        {
            "schema_version": "ATIF-v1.5",
            "steps": [{"source": "agent", "message": "fixed it"}],
        },
    )
    (trial / "agent" / "codex.txt").write_text("agent transcript\n")
    (trial / "verifier").mkdir()
    (trial / "verifier" / "reward.txt").write_text("1\n")
    (trial / "verifier" / "test.log").write_text("verifier test log\n")
    (trial / "verifier" / "test-stdout.txt").write_text("verifier stdout\n")
    return job


def run_normalizer(dataset: Path, job: Path, output: Path) -> None:
    """Run the normalizer against fixture inputs."""

    command = [
        str(NORMALIZER),
        "--job-dir",
        str(job),
        "--dataset-path",
        str(dataset),
        "--model-provider",
        "openai",
        "--model-name",
        "o4-mini",
        "--model-version",
        "2026-04-26",
        "--model-reasoning",
        "high",
        "--infra-bench-commit",
        "9fe586c000000000000000000000000000000000",
        "--run-id",
        "fixture-run",
        "--output-dir",
        str(output),
    ]
    subprocess.run(command, check=True, cwd=ROOT)


def run_dry_run(dataset: Path, job: Path) -> dict:
    """Run the normalizer in dry-run mode."""

    command = [
        str(NORMALIZER),
        "--job-dir",
        str(job),
        "--dataset-path",
        str(dataset),
        "--model-provider",
        "openai",
        "--model-name",
        "o4-mini",
        "--infra-bench-commit",
        "9fe586c000000000000000000000000000000000",
        "--run-id",
        "fixture-run",
        "--dry-run",
    ]
    result = subprocess.run(
        command, check=True, cwd=ROOT, capture_output=True, text=True
    )
    return json.loads(result.stdout)


def test_normalizer_writes_public_contract() -> None:
    """Verify file output follows the public benchmark contract."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dataset = write_fixture_dataset(root)
        job = write_fixture_job(root)
        output = root / "out"
        run_normalizer(dataset, job, output)

        run = json.loads((output / "run.json").read_text())
        results = json.loads((output / "results.json").read_text())
        assert run["run_id"] == "fixture-run"
        assert run["summary"]["task_count"] == 1
        assert run["summary"]["passed"] == 1
        assert run["summary"]["score"] == 1
        assert run["agent_tool"] == "codex"
        assert run["model"] == {
            "provider": "openai",
            "name": "o4-mini",
            "version": "2026-04-26",
            "reasoning": "high",
        }

        [result] = results["results"]
        assert result["task_name"] == "kubeply/restore-multi-hop-checkout-route"
        assert result["difficulty"] == "hard"
        assert result["passed"] is True
        assert result["duration_sec"] == 120
        assert result["input_tokens"] == 1234
        assert result["cache_tokens"] == 1000
        assert result["output_tokens"] == 56
        assert result["total_tokens"] == 1290
        assert result["started_at"] == "2026-04-26T12:01:00Z"
        assert result["finished_at"] == "2026-04-26T12:03:00Z"
        assert run["summary"]["duration_sec"] == 120
        assert run["summary"]["input_tokens"] == 1234
        assert run["summary"]["cache_tokens"] == 1000
        assert run["summary"]["output_tokens"] == 56
        assert run["summary"]["total_tokens"] == 1290
        assert run["artifacts"]["summary"].endswith("/summary.json")
        assert "/public/" in result["agent_artifact_key"]
        assert result["agent_artifact_key"].endswith("agent-summary.json")
        agent_summary = json.loads(
            (output / "public" / result["task_slug"] / "agent-summary.json").read_text()
        )
        verifier_summary = json.loads(
            (
                output / "public" / result["task_slug"] / "verifier-summary.json"
            ).read_text()
        )
        assert agent_summary["raw_transcript_public"] is True
        assert agent_summary["agent_log_name"] == "codex.txt"
        assert agent_summary["agent_log"] == "agent transcript\n"
        assert agent_summary["codex_log"] == "agent transcript\n"
        assert agent_summary["input_tokens"] == 1234
        assert agent_summary["cache_tokens"] == 1000
        assert agent_summary["output_tokens"] == 56
        assert agent_summary["total_tokens"] == 1290
        assert agent_summary["trajectory"]["schema_version"] == "ATIF-v1.5"
        assert verifier_summary["duration_sec"] == 15
        assert verifier_summary["test_log"] == "verifier test log\n"
        assert verifier_summary["test_stdout"] == "verifier stdout\n"
        assert (
            "INSERT OR REPLACE INTO benchmark_runs"
            in (output / "d1-upsert.sql").read_text()
        )
        assert "agent_tool" in (output / "d1-upsert.sql").read_text()
        assert "model_reasoning" in (output / "d1-upsert.sql").read_text()
        assert "input_tokens" in (output / "d1-upsert.sql").read_text()
        assert "BEGIN TRANSACTION" not in (output / "d1-upsert.sql").read_text()
        assert "COMMIT" not in (output / "d1-upsert.sql").read_text()
        assert not (output / "public" / result["task_slug"] / "agent.log").exists()


def test_normalizer_dry_run_writes_no_files() -> None:
    """Verify dry-run mode emits JSON without writing output files."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dataset = write_fixture_dataset(root)
        job = write_fixture_job(root)
        normalized = run_dry_run(dataset, job)

        assert normalized["run"]["run_id"] == "fixture-run"
        assert normalized["results"]["results"][0]["passed"] is True
        assert normalized["results"]["results"][0]["total_tokens"] == 1290
        assert not (root / "out").exists()


def test_normalizer_keeps_missing_usage_null() -> None:
    """Verify missing agent usage remains null for agents that do not report it."""

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dataset = write_fixture_dataset(root)
        job = write_fixture_job(root)
        trial_result = job / "restore-multi-hop-checkout-route" / "result.json"
        data = json.loads(trial_result.read_text())
        data["agent_result"] = {
            "n_input_tokens": None,
            "n_cache_tokens": None,
            "n_output_tokens": None,
            "cost_usd": None,
        }
        write_json(trial_result, data)
        normalized = run_dry_run(dataset, job)

        result = normalized["results"]["results"][0]
        assert result["input_tokens"] is None
        assert result["cache_tokens"] is None
        assert result["output_tokens"] is None
        assert result["total_tokens"] is None
        assert normalized["run"]["summary"]["input_tokens"] is None
        assert normalized["run"]["summary"]["cache_tokens"] is None
        assert normalized["run"]["summary"]["output_tokens"] is None
        assert normalized["run"]["summary"]["total_tokens"] is None


def main() -> int:
    """Run fixture tests without a test framework."""

    test_normalizer_writes_public_contract()
    test_normalizer_dry_run_writes_no_files()
    test_normalizer_keeps_missing_usage_null()
    print("benchmark result normalizer tests ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
