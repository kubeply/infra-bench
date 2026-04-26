#!/usr/bin/env python3
"""Normalize a Harbor job directory into InfraBench benchmark result JSON."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from typing import Any


SCHEMA_VERSION = "1.0"
UTC_FORMAT = "%Y-%m-%dT%H%M%SZ"


@dataclass(frozen=True)
class TaskMetadata:
    name: str
    slug: str
    difficulty: str
    category: str
    keywords: list[str]


@dataclass(frozen=True)
class TrialResult:
    task_name: str
    task_slug: str
    difficulty: str
    category: str
    keywords: list[str]
    passed: bool
    reward: float
    score: float
    duration_sec: float | None
    cost_usd: float | None
    started_at: str | None
    finished_at: str | None
    verifier_artifact_key: str
    agent_artifact_key: str
    verifier_summary: dict[str, Any]
    agent_summary: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a Harbor job folder into public InfraBench JSON."
    )
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--model-provider", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version")
    parser.add_argument("--agent-harness", default="harbor")
    parser.add_argument("--harbor-version")
    parser.add_argument("--infra-bench-commit")
    parser.add_argument("--run-id")
    parser.add_argument("--started-at")
    parser.add_argument("--finished-at")
    parser.add_argument("--cost-usd", type=float)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--r2-prefix", default="benchmarks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print JSON without writing output files.",
    )
    parser.add_argument(
        "--include-archive",
        action="store_true",
        help="Write artifacts.tar.zst containing the Harbor job directory.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


def load_dataset_name(dataset_path: Path) -> str:
    manifest = dataset_path / "dataset.toml"
    if not manifest.exists():
        raise SystemExit(f"{manifest}: dataset manifest not found")
    data = tomllib.loads(manifest.read_text())
    dataset = data.get("dataset", {})
    name = dataset.get("name")
    if not isinstance(name, str) or not name:
        raise SystemExit(f"{manifest}: missing dataset.name")
    return name


def load_task_metadata(dataset_path: Path) -> dict[str, TaskMetadata]:
    tasks: dict[str, TaskMetadata] = {}
    for task_toml in sorted(dataset_path.glob("*/task.toml")):
        data = tomllib.loads(task_toml.read_text())
        task = data.get("task", {})
        metadata = data.get("metadata", {})
        name = task.get("name")
        difficulty = metadata.get("difficulty")
        category = task.get("category")
        keywords = task.get("keywords")
        if not isinstance(name, str) or not name:
            raise SystemExit(f"{task_toml}: missing task.name")
        if difficulty not in {"easy", "medium", "hard"}:
            raise SystemExit(f"{task_toml}: invalid metadata.difficulty")
        if not isinstance(category, str) or not category:
            raise SystemExit(f"{task_toml}: missing task.category")
        if not isinstance(keywords, list) or not all(
            isinstance(item, str) for item in keywords
        ):
            raise SystemExit(f"{task_toml}: invalid task.keywords")
        slug = name.split("/", 1)[-1]
        tasks[name] = TaskMetadata(
            name=name,
            slug=slug,
            difficulty=difficulty,
            category=category,
            keywords=keywords,
        )
    if not tasks:
        raise SystemExit(f"{dataset_path}: no task.toml files found")
    return tasks


def recursive_values(data: Any, keys: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                found.append(value)
            found.extend(recursive_values(value, keys))
    elif isinstance(data, list):
        for item in data:
            found.extend(recursive_values(item, keys))
    return found


def first_string(data: Any, keys: set[str]) -> str | None:
    for value in recursive_values(data, keys):
        if isinstance(value, str) and value:
            return value
    return None


def first_number(data: Any, keys: set[str]) -> float | None:
    for value in recursive_values(data, keys):
        number = coerce_float(value)
        if number is not None:
            return number
    return None


def first_bool(data: Any, keys: set[str]) -> bool | None:
    for value in recursive_values(data, keys):
        if isinstance(value, bool):
            return value
    return None


def first_present(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def normalize_timestamp(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def current_timestamp() -> str:
    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def git_commit() -> str:
    command = ["git", "rev-parse", "HEAD"]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit("could not determine git commit; pass --infra-bench-commit")
    return result.stdout.strip()


def infer_task_name(
    trial_dir: Path,
    trial_config: dict[str, Any],
    trial_result: dict[str, Any],
    tasks: dict[str, TaskMetadata],
) -> str:
    candidates: list[str] = []
    for data in (trial_result, trial_config):
        candidates.extend(
            str(value)
            for value in recursive_values(
                data,
                {
                    "task_name",
                    "task_id",
                    "task",
                    "name",
                    "taskName",
                    "taskId",
                },
            )
            if isinstance(value, str)
        )
    for candidate in candidates:
        if candidate in tasks:
            return candidate
        if candidate.startswith("kubeply/") and candidate in tasks:
            return candidate
        if "/" not in candidate:
            namespaced = f"kubeply/{candidate}"
            if namespaced in tasks:
                return namespaced

    path_text = trial_dir.name
    for task_name, task in tasks.items():
        if task.slug == path_text or task.slug in path_text:
            return task_name

    raise SystemExit(f"{trial_dir}: could not infer task name from trial config/result")


def read_reward_from_verifier(trial_dir: Path) -> float | None:
    reward_txt = trial_dir / "verifier" / "reward.txt"
    if reward_txt.exists():
        return coerce_float(reward_txt.read_text().strip())

    reward_json = trial_dir / "verifier" / "reward.json"
    if reward_json.exists():
        data = load_json(reward_json)
        return first_number(data, {"reward", "score"})

    return None


def find_trial_dirs(job_dir: Path) -> list[Path]:
    trial_dirs: list[Path] = []
    for result_path in sorted(job_dir.rglob("result.json")):
        if result_path.parent == job_dir:
            continue
        if "public" in result_path.parts:
            continue
        trial_dirs.append(result_path.parent)
    return trial_dirs


def artifact_key(prefix: str, run_id: str, task_slug: str, filename: str) -> str:
    return f"{prefix}/runs/{run_id}/public/{task_slug}/{filename}"


def normalize_trial(
    trial_dir: Path,
    tasks: dict[str, TaskMetadata],
    run_id: str,
    r2_prefix: str,
    cost_usd: float | None,
) -> TrialResult:
    trial_config = read_json_if_present(trial_dir / "config.json")
    trial_result = read_json_if_present(trial_dir / "result.json")
    combined = {"config": trial_config, "result": trial_result}

    task_name = infer_task_name(trial_dir, trial_config, trial_result, tasks)
    task = tasks[task_name]
    reward = first_present(
        first_number(combined, {"reward", "score", "score_raw"}),
        read_reward_from_verifier(trial_dir),
        0.0,
    )
    passed = first_bool(combined, {"passed", "success", "succeeded"})
    if passed is None:
        passed = reward >= 1.0

    duration = first_number(
        combined,
        {"duration_sec", "duration_seconds", "duration", "elapsed_sec"},
    )
    started = normalize_timestamp(
        first_string(combined, {"started_at", "start_time", "startedAt"})
    )
    finished = normalize_timestamp(
        first_string(combined, {"finished_at", "end_time", "finishedAt"})
    )
    score = max(0.0, min(1.0, reward))

    verifier_key = artifact_key(r2_prefix, run_id, task.slug, "verifier-summary.json")
    agent_key = artifact_key(r2_prefix, run_id, task.slug, "agent-summary.json")
    verifier_summary = {
        "schema_version": SCHEMA_VERSION,
        "task_name": task.name,
        "passed": passed,
        "reward": reward,
        "score": score,
        "has_reward_txt": (trial_dir / "verifier" / "reward.txt").exists(),
        "has_reward_json": (trial_dir / "verifier" / "reward.json").exists(),
    }
    agent_summary = {
        "schema_version": SCHEMA_VERSION,
        "task_name": task.name,
        "status": first_string(combined, {"status", "state"}),
        "raw_transcript_public": False,
    }

    return TrialResult(
        task_name=task.name,
        task_slug=task.slug,
        difficulty=task.difficulty,
        category=task.category,
        keywords=task.keywords,
        passed=passed,
        reward=reward,
        score=score,
        duration_sec=duration,
        cost_usd=cost_usd,
        started_at=started,
        finished_at=finished,
        verifier_artifact_key=verifier_key,
        agent_artifact_key=agent_key,
        verifier_summary=verifier_summary,
        agent_summary=agent_summary,
    )


def make_run_id(
    explicit_run_id: str | None,
    started_at: str | None,
    dataset_name: str,
    model_provider: str,
    model_name: str,
    commit: str,
) -> str:
    if explicit_run_id:
        return explicit_run_id
    timestamp = normalize_timestamp(started_at) or current_timestamp()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        compact_time = parsed.astimezone(UTC).strftime(UTC_FORMAT)
    except ValueError:
        compact_time = datetime.now(tz=UTC).strftime(UTC_FORMAT)
    dataset_slug = slugify(dataset_name.split("/", 1)[-1])
    model_slug = slugify(f"{model_provider}-{model_name}")
    return f"{compact_time}-{dataset_slug}-{model_slug}-{commit[:7]}"


def result_to_json(result: TrialResult) -> dict[str, Any]:
    return {
        "task_name": result.task_name,
        "task_slug": result.task_slug,
        "difficulty": result.difficulty,
        "category": result.category,
        "keywords": result.keywords,
        "passed": result.passed,
        "reward": result.reward,
        "score": result.score,
        "duration_sec": result.duration_sec,
        "cost_usd": result.cost_usd,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "verifier_artifact_key": result.verifier_artifact_key,
        "agent_artifact_key": result.agent_artifact_key,
    }


def build_documents(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any], list[TrialResult]]:
    job_dir = args.job_dir.resolve()
    dataset_path = args.dataset_path.resolve()
    if not job_dir.is_dir():
        raise SystemExit(f"{job_dir}: job directory not found")
    if not dataset_path.is_dir():
        raise SystemExit(f"{dataset_path}: dataset directory not found")

    dataset_name = load_dataset_name(dataset_path)
    tasks = load_task_metadata(dataset_path)
    commit = args.infra_bench_commit or git_commit()
    started_at = args.started_at
    job_result = read_json_if_present(job_dir / "result.json")
    if not started_at:
        started_at = first_string(job_result, {"started_at", "start_time", "startedAt"})
    finished_at = args.finished_at or first_string(
        job_result, {"finished_at", "end_time", "finishedAt"}
    )
    started_at = normalize_timestamp(started_at) or current_timestamp()
    finished_at = normalize_timestamp(finished_at)
    run_id = make_run_id(
        args.run_id,
        started_at,
        dataset_name,
        args.model_provider,
        args.model_name,
        commit,
    )

    trial_dirs = find_trial_dirs(job_dir)
    if not trial_dirs:
        raise SystemExit(f"{job_dir}: no Harbor trial result.json files found")

    trial_results = [
        normalize_trial(
            trial_dir=trial_dir,
            tasks=tasks,
            run_id=run_id,
            r2_prefix=args.r2_prefix.strip("/"),
            cost_usd=None,
        )
        for trial_dir in trial_dirs
    ]

    passed = sum(1 for result in trial_results if result.passed)
    failed = len(trial_results) - passed
    durations = [
        result.duration_sec
        for result in trial_results
        if result.duration_sec is not None
    ]
    total_duration = sum(durations) if durations else None
    run_cost = args.cost_usd
    if run_cost is not None:
        per_task_cost = run_cost / len(trial_results)
        trial_results = [
            replace(result, cost_usd=per_task_cost) for result in trial_results
        ]

    archive_key = None
    if args.include_archive:
        archive_key = f"{args.r2_prefix.strip('/')}/runs/{run_id}/artifacts.tar.zst"
    run_doc = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "dataset": dataset_name,
        "dataset_path": str(args.dataset_path),
        "infra_bench_commit": commit,
        "harbor_version": args.harbor_version,
        "agent_harness": args.agent_harness,
        "model": {
            "provider": args.model_provider,
            "name": args.model_name,
            "version": args.model_version,
        },
        "started_at": started_at,
        "finished_at": finished_at,
        "summary": {
            "task_count": len(trial_results),
            "passed": passed,
            "failed": failed,
            "score": passed / len(trial_results),
            "duration_sec": total_duration,
            "cost_usd": run_cost,
        },
        "artifacts": {
            "run": f"{args.r2_prefix.strip('/')}/runs/{run_id}/run.json",
            "results": f"{args.r2_prefix.strip('/')}/runs/{run_id}/results.json",
            "archive": archive_key,
        },
    }
    results_doc = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "results": [result_to_json(result) for result in trial_results],
    }
    validate_documents(run_doc, results_doc)
    return run_doc, results_doc, trial_results


def validate_documents(run_doc: dict[str, Any], results_doc: dict[str, Any]) -> None:
    required_run_keys = {
        "schema_version",
        "run_id",
        "dataset",
        "dataset_path",
        "infra_bench_commit",
        "harbor_version",
        "agent_harness",
        "model",
        "started_at",
        "finished_at",
        "summary",
        "artifacts",
    }
    missing_run = required_run_keys - run_doc.keys()
    if missing_run:
        raise SystemExit(f"run.json missing keys: {sorted(missing_run)}")
    if run_doc["schema_version"] != SCHEMA_VERSION:
        raise SystemExit("run.json has unsupported schema_version")
    model = run_doc["model"]
    for key in ("provider", "name", "version"):
        if key not in model:
            raise SystemExit(f"run.json model missing {key}")
    if not model["provider"] or not model["name"]:
        raise SystemExit("model provider and name are required")

    if results_doc.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("results.json has unsupported schema_version")
    if results_doc.get("run_id") != run_doc["run_id"]:
        raise SystemExit("run.json and results.json run_id mismatch")
    results = results_doc.get("results")
    if not isinstance(results, list) or not results:
        raise SystemExit("results.json must contain at least one result")
    for index, result in enumerate(results):
        for key in (
            "task_name",
            "task_slug",
            "difficulty",
            "category",
            "keywords",
            "passed",
            "reward",
            "score",
            "duration_sec",
            "cost_usd",
            "started_at",
            "finished_at",
            "verifier_artifact_key",
            "agent_artifact_key",
        ):
            if key not in result:
                raise SystemExit(f"results[{index}] missing {key}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def sql_values(values: list[Any]) -> str:
    return ", ".join(sql_literal(value) for value in values)


def write_d1_sql(
    output_dir: Path,
    run_doc: dict[str, Any],
    results_doc: dict[str, Any],
) -> None:
    summary = run_doc["summary"]
    model = run_doc["model"]
    artifacts = run_doc["artifacts"]
    statements = [
        "-- Generated by scripts/normalize-benchmark-run.py",
        "BEGIN TRANSACTION;",
        (
            "INSERT OR REPLACE INTO benchmark_runs "
            "(run_id, dataset, infra_bench_commit, harbor_version, agent_harness, "
            "model_provider, model_name, model_version, started_at, finished_at, "
            "task_count, passed, failed, score, duration_sec, cost_usd, "
            "run_artifact_key, results_artifact_key, archive_artifact_key) VALUES "
            f"({sql_values([run_doc['run_id'], run_doc['dataset'], run_doc['infra_bench_commit'], run_doc['harbor_version'], run_doc['agent_harness'], model['provider'], model['name'], model['version'], run_doc['started_at'], run_doc['finished_at'], summary['task_count'], summary['passed'], summary['failed'], summary['score'], summary['duration_sec'], summary['cost_usd'], artifacts['run'], artifacts['results'], artifacts['archive']])});"
        ),
    ]
    for result in results_doc["results"]:
        row_id = f"{run_doc['run_id']}/{result['task_name']}"
        statements.append(
            "INSERT OR REPLACE INTO benchmark_task_results "
            "(id, run_id, task_name, task_slug, difficulty, category, passed, "
            "reward, score, duration_sec, cost_usd, started_at, finished_at, "
            "verifier_artifact_key, agent_artifact_key) VALUES "
            f"({sql_values([row_id, run_doc['run_id'], result['task_name'], result['task_slug'], result['difficulty'], result['category'], result['passed'], result['reward'], result['score'], result['duration_sec'], result['cost_usd'], result['started_at'], result['finished_at'], result['verifier_artifact_key'], result['agent_artifact_key']])});"
        )
    statements.append("COMMIT;")
    (output_dir / "d1-upsert.sql").write_text("\n".join(statements) + "\n")


def write_archive(job_dir: Path, output_dir: Path) -> None:
    archive_path = output_dir / "artifacts.tar.zst"
    command = [
        "tar",
        "--zstd",
        "-cf",
        str(archive_path),
        "-C",
        str(job_dir.parent),
        job_dir.name,
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            "could not create artifacts.tar.zst; install tar with zstd support "
            "or omit --include-archive"
        )


def write_outputs(
    output_dir: Path,
    run_doc: dict[str, Any],
    results_doc: dict[str, Any],
    trial_results: list[TrialResult],
    include_archive: bool,
    job_dir: Path,
) -> None:
    write_json(output_dir / "run.json", run_doc)
    write_json(output_dir / "results.json", results_doc)
    write_d1_sql(output_dir, run_doc, results_doc)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_doc["run_id"],
        "dataset": run_doc["dataset"],
        "model": run_doc["model"],
        "summary": run_doc["summary"],
    }
    write_json(output_dir / "summary.json", summary)
    for result in trial_results:
        public_dir = output_dir / "public" / result.task_slug
        write_json(public_dir / "verifier-summary.json", result.verifier_summary)
        write_json(public_dir / "agent-summary.json", result.agent_summary)
    if include_archive:
        write_archive(job_dir, output_dir)


def main() -> int:
    args = parse_args()
    if not args.dry_run and args.output_dir is None:
        raise SystemExit("--output-dir is required unless --dry-run is set")
    run_doc, results_doc, trial_results = build_documents(args)
    if args.dry_run:
        print(json.dumps({"run": run_doc, "results": results_doc}, indent=2))
        return 0
    assert args.output_dir is not None
    write_outputs(
        output_dir=args.output_dir,
        run_doc=run_doc,
        results_doc=results_doc,
        trial_results=trial_results,
        include_archive=args.include_archive,
        job_dir=args.job_dir.resolve(),
    )
    print(f"wrote benchmark results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
