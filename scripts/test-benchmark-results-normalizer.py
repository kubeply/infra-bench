#!/usr/bin/env python3
"""Fixture tests for scripts/normalize-benchmark-run.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
NORMALIZER = ROOT / "scripts" / "normalize-benchmark-run.py"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_fixture_dataset(root: Path) -> Path:
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
category = "kubernetes"
keywords = ["kubernetes", "service-routing"]

[metadata]
difficulty = "hard"
""".lstrip()
    )
    return dataset


def write_fixture_job(root: Path) -> Path:
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
            "duration_sec": 300,
            "status": "completed",
        },
    )
    (trial / "verifier").mkdir()
    (trial / "verifier" / "reward.txt").write_text("1\n")
    return job


def run_normalizer(dataset: Path, job: Path, output: Path) -> None:
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
        "--infra-bench-commit",
        "9fe586c000000000000000000000000000000000",
        "--run-id",
        "fixture-run",
        "--output-dir",
        str(output),
    ]
    subprocess.run(command, check=True, cwd=ROOT)


def run_dry_run(dataset: Path, job: Path) -> dict:
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

        [result] = results["results"]
        assert result["task_name"] == "kubeply/restore-multi-hop-checkout-route"
        assert result["difficulty"] == "hard"
        assert result["passed"] is True
        assert "/public/" in result["agent_artifact_key"]
        assert result["agent_artifact_key"].endswith("agent-summary.json")
        assert (
            "INSERT OR REPLACE INTO benchmark_runs"
            in (output / "d1-upsert.sql").read_text()
        )
        assert not (output / "public" / result["task_slug"] / "agent.log").exists()


def test_normalizer_dry_run_writes_no_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dataset = write_fixture_dataset(root)
        job = write_fixture_job(root)
        normalized = run_dry_run(dataset, job)

        assert normalized["run"]["run_id"] == "fixture-run"
        assert normalized["results"]["results"][0]["passed"] is True
        assert not (root / "out").exists()


def main() -> int:
    test_normalizer_writes_public_contract()
    test_normalizer_dry_run_writes_no_files()
    print("benchmark result normalizer tests ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
