#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "rich>=13.7",
# ]
# ///
"""Normalize a Harbor job directory into InfraBench benchmark result JSON."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
)

import tomllib

SCHEMA_VERSION = "1.0"
UTC_FORMAT = "%Y-%m-%dT%H%M%SZ"
CONSOLE = Console(stderr=True)
AGENT_LOG_FILENAMES = (
    "codex.txt",
    "gemini-cli.txt",
    "claude-code.txt",
    "opencode.txt",
    "kimi-cli.txt",
    "mini-swe-agent.txt",
)
AGENT_TOOL_NAMES = {
    "claude-code",
    "codex",
    "gemini-cli",
    "kimi-cli",
    "mini-swe-agent",
    "opencode",
}
REASONING_EFFORTS = {"low", "medium", "high", "xhigh"}


@dataclass(frozen=True)
class TaskMetadata:
    """Hold public metadata for one benchmark task."""

    name: str
    slug: str
    difficulty: str
    category: str
    keywords: list[str]


@dataclass(frozen=True)
class TrialResult:
    """Hold one normalized Harbor trial result."""

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
    input_tokens: int | None
    cache_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    started_at: str | None
    finished_at: str | None
    verifier_artifact_key: str
    agent_artifact_key: str
    verifier_summary: dict[str, Any]
    agent_summary: dict[str, Any]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the normalizer."""

    parser = argparse.ArgumentParser(
        description="Convert a Harbor job folder into public InfraBench JSON."
    )
    parser.add_argument("--job-dir", required=True, type=Path)
    parser.add_argument("--dataset-path", required=True, type=Path)
    parser.add_argument("--model-provider", required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-version")
    parser.add_argument("--model-reasoning")
    parser.add_argument("--agent-tool")
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


def make_progress() -> Progress:
    """Create the terminal progress display for normalizer work."""

    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=CONSOLE,
    )


def advance(progress: Progress | None, task_id: TaskID | None) -> None:
    """Advance a progress task when progress reporting is enabled."""

    if progress is not None and task_id is not None:
        progress.advance(task_id)


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected JSON object")
    return data


def read_json_if_present(path: Path) -> dict[str, Any]:
    """Return a JSON object from a path when it exists."""

    if not path.exists():
        return {}
    return load_json(path)


def read_text_if_present(path: Path) -> str | None:
    """Return text file contents when the file exists."""

    if not path.exists():
        return None
    return path.read_text(errors="replace")


def read_first_agent_log(trial_dir: Path) -> tuple[str | None, str | None]:
    """Read the first public text transcript emitted by known agent harnesses."""

    agent_dir = trial_dir / "agent"
    for name in AGENT_LOG_FILENAMES:
        content = read_text_if_present(agent_dir / name)
        if content is not None:
            return name, content

    return None, None


def load_dataset_name(dataset_path: Path) -> str:
    """Read the Harbor dataset name from dataset.toml."""

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
    """Read task metadata for every task in a dataset directory."""

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
    """Collect values for matching keys from nested JSON-like data."""

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
    """Return the first non-empty string for any matching key."""

    for value in recursive_values(data, keys):
        if isinstance(value, str) and value:
            return value
    return None


def first_number(data: Any, keys: set[str]) -> float | None:
    """Return the first numeric value for any matching key."""

    for value in recursive_values(data, keys):
        number = coerce_float(value)
        if number is not None:
            return number
    return None


def first_bool(data: Any, keys: set[str]) -> bool | None:
    """Return the first boolean value for any matching key."""

    for value in recursive_values(data, keys):
        if isinstance(value, bool):
            return value
    return None


def first_present(*values: Any) -> Any:
    """Return the first value that is not None."""

    for value in values:
        if value is not None:
            return value
    return None


def coerce_float(value: Any) -> float | None:
    """Convert a scalar value to float when possible."""

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


def coerce_int(value: Any) -> int | None:
    """Convert a scalar value to int when it is a whole number."""

    number = coerce_float(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def first_int(data: Any, keys: set[str]) -> int | None:
    """Return the first integer value for any matching key."""

    for value in recursive_values(data, keys):
        number = coerce_int(value)
        if number is not None:
            return number
    return None


def sum_optional_ints(*values: int | None) -> int | None:
    """Sum integers only when every provided value is known."""

    if any(value is None for value in values):
        return None
    return sum(value for value in values if value is not None)


def normalize_timestamp(value: str | None) -> str | None:
    """Normalize a timestamp string to UTC ISO-8601 when possible."""

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


def duration_between_timestamps(
    started_at: str | None,
    finished_at: str | None,
) -> float | None:
    """Compute elapsed seconds from normalized timestamps when possible."""

    if started_at is None or finished_at is None:
        return None

    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return None

    duration = (finished - started).total_seconds()
    if duration < 0:
        return None
    return duration


def phase_data(data: dict[str, Any], name: str) -> dict[str, Any]:
    """Return timing phase data when present in a Harbor result."""

    value = data.get(name)
    if isinstance(value, dict):
        return value
    return {}


def current_timestamp() -> str:
    """Return the current UTC timestamp without microseconds."""

    return (
        datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    """Convert arbitrary text into a stable lowercase slug."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def git_commit() -> str:
    """Return the current repository commit SHA."""

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
    """Infer the Harbor task name for one trial directory."""

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
    """Read verifier reward output from a trial directory."""

    reward_txt = trial_dir / "verifier" / "reward.txt"
    if reward_txt.exists():
        return coerce_float(reward_txt.read_text().strip())

    reward_json = trial_dir / "verifier" / "reward.json"
    if reward_json.exists():
        data = load_json(reward_json)
        return first_number(data, {"reward", "score"})

    return None


def find_trial_dirs(job_dir: Path) -> list[Path]:
    """Find Harbor trial directories below a job directory."""

    trial_dirs: list[Path] = []
    for result_path in sorted(job_dir.rglob("result.json")):
        if result_path.parent == job_dir:
            continue
        if "public" in result_path.parts:
            continue
        trial_dirs.append(result_path.parent)
    return trial_dirs


def artifact_key(prefix: str, run_id: str, task_slug: str, filename: str) -> str:
    """Build an R2 object key for a public task artifact."""

    return f"{prefix}/runs/{run_id}/public/{task_slug}/{filename}"


def public_file_key(prefix: str, run_id: str, filename: str) -> str:
    """Build an R2 object key for a public run artifact."""

    return f"{prefix}/runs/{run_id}/{filename}"


def normalize_trial(
    trial_dir: Path,
    tasks: dict[str, TaskMetadata],
    run_id: str,
    r2_prefix: str,
    cost_usd: float | None,
) -> TrialResult:
    """Normalize one Harbor trial into the public task result shape."""

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

    agent_execution = phase_data(trial_result, "agent_execution")
    verifier = phase_data(trial_result, "verifier")
    duration = first_present(
        first_number(
            agent_execution,
            {"duration_sec", "duration_seconds", "duration", "elapsed_sec"},
        ),
        first_number(
            combined,
            {"agent_duration_sec", "agent_duration_seconds"},
        ),
    )
    started = normalize_timestamp(
        first_string(agent_execution, {"started_at", "start_time", "startedAt"})
        or first_string(combined, {"started_at", "start_time", "startedAt"})
    )
    finished = normalize_timestamp(
        first_string(agent_execution, {"finished_at", "end_time", "finishedAt"})
        or first_string(combined, {"finished_at", "end_time", "finishedAt"})
    )
    if duration is None:
        duration = duration_between_timestamps(started, finished)
    score = max(0.0, min(1.0, reward))
    agent_result = phase_data(trial_result, "agent_result")
    input_tokens = first_int(
        agent_result,
        {"n_input_tokens", "input_tokens", "prompt_tokens"},
    )
    cache_tokens = first_int(
        agent_result,
        {"n_cache_tokens", "cache_tokens", "cached_tokens"},
    )
    output_tokens = first_int(
        agent_result,
        {"n_output_tokens", "output_tokens", "completion_tokens"},
    )
    total_tokens = first_present(
        first_int(agent_result, {"n_total_tokens", "total_tokens"}),
        sum_optional_ints(input_tokens, output_tokens),
    )

    verifier_key = artifact_key(r2_prefix, run_id, task.slug, "verifier-summary.json")
    agent_key = artifact_key(r2_prefix, run_id, task.slug, "agent-summary.json")
    verifier_started = normalize_timestamp(
        first_string(verifier, {"started_at", "start_time", "startedAt"})
    )
    verifier_finished = normalize_timestamp(
        first_string(verifier, {"finished_at", "end_time", "finishedAt"})
    )
    verifier_summary = {
        "schema_version": SCHEMA_VERSION,
        "task_name": task.name,
        "passed": passed,
        "reward": reward,
        "score": score,
        "started_at": verifier_started,
        "finished_at": verifier_finished,
        "duration_sec": duration_between_timestamps(
            verifier_started,
            verifier_finished,
        ),
        "has_reward_txt": (trial_dir / "verifier" / "reward.txt").exists(),
        "has_reward_json": (trial_dir / "verifier" / "reward.json").exists(),
        "reward_txt": read_text_if_present(trial_dir / "verifier" / "reward.txt"),
        "test_log": read_text_if_present(trial_dir / "verifier" / "test.log"),
        "test_stdout": read_text_if_present(trial_dir / "verifier" / "test-stdout.txt"),
        "debug_log": read_text_if_present(trial_dir / "verifier" / "debug.log"),
    }
    agent_log_name, agent_log = read_first_agent_log(trial_dir)
    agent_summary = {
        "schema_version": SCHEMA_VERSION,
        "task_name": task.name,
        "status": first_string(combined, {"status", "state"}),
        "started_at": started,
        "finished_at": finished,
        "duration_sec": duration,
        "input_tokens": input_tokens,
        "cache_tokens": cache_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "raw_transcript_public": True,
        "agent_log_name": agent_log_name,
        "agent_log": agent_log,
        "codex_log": read_text_if_present(trial_dir / "agent" / "codex.txt"),
        "trajectory": read_json_if_present(trial_dir / "agent" / "trajectory.json")
        or None,
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
        input_tokens=input_tokens,
        cache_tokens=cache_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
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
    """Build or return the stable benchmark run identifier."""

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
    """Convert a normalized trial result to JSON-compatible data."""

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
        "input_tokens": result.input_tokens,
        "cache_tokens": result.cache_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
        "verifier_artifact_key": result.verifier_artifact_key,
        "agent_artifact_key": result.agent_artifact_key,
    }


def build_documents(
    args: argparse.Namespace,
    progress: Progress | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[TrialResult]]:
    """Build run and results documents from CLI arguments."""

    metadata_task: TaskID | None = None
    if progress is not None:
        metadata_task = progress.add_task("Reading run metadata", total=5)

    job_dir = args.job_dir.resolve()
    dataset_path = args.dataset_path.resolve()
    if not job_dir.is_dir():
        raise SystemExit(f"{job_dir}: job directory not found")
    if not dataset_path.is_dir():
        raise SystemExit(f"{dataset_path}: dataset directory not found")
    advance(progress, metadata_task)

    dataset_name = load_dataset_name(dataset_path)
    advance(progress, metadata_task)
    tasks = load_task_metadata(dataset_path)
    advance(progress, metadata_task)
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
    advance(progress, metadata_task)

    trial_dirs = find_trial_dirs(job_dir)
    if not trial_dirs:
        raise SystemExit(f"{job_dir}: no Harbor trial result.json files found")
    advance(progress, metadata_task)

    normalize_task: TaskID | None = None
    if progress is not None:
        normalize_task = progress.add_task(
            "Normalizing trial results", total=len(trial_dirs)
        )

    trial_results = []
    for trial_dir in trial_dirs:
        trial_results.append(
            normalize_trial(
                trial_dir=trial_dir,
                tasks=tasks,
                run_id=run_id,
                r2_prefix=args.r2_prefix.strip("/"),
                cost_usd=None,
            )
        )
        advance(progress, normalize_task)

    passed = sum(1 for result in trial_results if result.passed)
    failed = len(trial_results) - passed
    durations = [
        result.duration_sec
        for result in trial_results
        if result.duration_sec is not None
    ]
    total_duration = sum(durations) if durations else None
    has_input_tokens = any(result.input_tokens is not None for result in trial_results)
    has_cache_tokens = any(result.cache_tokens is not None for result in trial_results)
    has_output_tokens = any(
        result.output_tokens is not None for result in trial_results
    )
    has_total_tokens = any(result.total_tokens is not None for result in trial_results)
    input_tokens = (
        sum(
            result.input_tokens
            for result in trial_results
            if result.input_tokens is not None
        )
        if has_input_tokens
        else None
    )
    cache_tokens = (
        sum(
            result.cache_tokens
            for result in trial_results
            if result.cache_tokens is not None
        )
        if has_cache_tokens
        else None
    )
    output_tokens = (
        sum(
            result.output_tokens
            for result in trial_results
            if result.output_tokens is not None
        )
        if has_output_tokens
        else None
    )
    total_tokens = (
        sum(
            result.total_tokens
            for result in trial_results
            if result.total_tokens is not None
        )
        if has_total_tokens
        else None
    )
    run_cost = args.cost_usd
    if run_cost is not None:
        per_task_cost = run_cost / len(trial_results)
        trial_results = [
            replace(result, cost_usd=per_task_cost) for result in trial_results
        ]

    model_version = args.model_version
    model_reasoning = args.model_reasoning
    agent_tool = args.agent_tool or infer_agent_tool(trial_results)
    normalized_version = normalize_cli_value(model_version)
    if normalized_version in AGENT_TOOL_NAMES:
        agent_tool = agent_tool or normalized_version
        model_version = None
    elif normalized_version in REASONING_EFFORTS:
        model_reasoning = model_reasoning or normalized_version
        model_version = None

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
        "agent_tool": agent_tool,
        "model": {
            "provider": args.model_provider,
            "name": args.model_name,
            "version": model_version,
            "reasoning": model_reasoning,
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
            "input_tokens": input_tokens,
            "cache_tokens": cache_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
        "artifacts": {
            "run": public_file_key(args.r2_prefix.strip("/"), run_id, "run.json"),
            "results": public_file_key(
                args.r2_prefix.strip("/"), run_id, "results.json"
            ),
            "summary": public_file_key(
                args.r2_prefix.strip("/"), run_id, "summary.json"
            ),
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
    """Validate the required fields in normalized documents."""

    required_run_keys = {
        "schema_version",
        "run_id",
        "dataset",
        "dataset_path",
        "infra_bench_commit",
        "harbor_version",
        "agent_harness",
        "agent_tool",
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
    for key in ("provider", "name", "version", "reasoning"):
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
            "input_tokens",
            "cache_tokens",
            "output_tokens",
            "total_tokens",
            "started_at",
            "finished_at",
            "verifier_artifact_key",
            "agent_artifact_key",
        ):
            if key not in result:
                raise SystemExit(f"results[{index}] missing {key}")


def write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON document with stable formatting."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def sql_literal(value: Any) -> str:
    """Convert a Python value into a SQLite SQL literal."""

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int | float):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def sql_values(values: list[Any]) -> str:
    """Convert a sequence of Python values into SQL values text."""

    return ", ".join(sql_literal(value) for value in values)


def normalize_cli_value(value: str | None) -> str | None:
    """Normalize optional CLI metadata for comparisons."""

    if value is None:
        return None
    return value.strip().lower().replace("_", "-")


def infer_agent_tool(trial_results: list[TrialResult]) -> str | None:
    """Infer the concrete agent tool from public trial artifacts."""

    for result in trial_results:
        trajectory = result.agent_summary.get("trajectory")
        if isinstance(trajectory, dict):
            agent = trajectory.get("agent")
            if isinstance(agent, dict) and isinstance(agent.get("name"), str):
                return agent["name"]
        agent_log_name = result.agent_summary.get("agent_log_name")
        if isinstance(agent_log_name, str) and agent_log_name.endswith(".txt"):
            return agent_log_name.removesuffix(".txt")
    return None


def write_d1_sql(
    output_dir: Path,
    run_doc: dict[str, Any],
    results_doc: dict[str, Any],
) -> None:
    """Write D1 upsert SQL for normalized benchmark results."""

    summary = run_doc["summary"]
    model = run_doc["model"]
    artifacts = run_doc["artifacts"]
    run_values = [
        run_doc["run_id"],
        run_doc["dataset"],
        run_doc["infra_bench_commit"],
        run_doc["harbor_version"],
        run_doc["agent_harness"],
        run_doc["agent_tool"],
        model["provider"],
        model["name"],
        model["version"],
        model["reasoning"],
        run_doc["started_at"],
        run_doc["finished_at"],
        summary["task_count"],
        summary["passed"],
        summary["failed"],
        summary["score"],
        summary["duration_sec"],
        summary["cost_usd"],
        summary["input_tokens"],
        summary["cache_tokens"],
        summary["output_tokens"],
        summary["total_tokens"],
        artifacts["run"],
        artifacts["results"],
        artifacts["archive"],
    ]
    statements = [
        "-- Generated by scripts/normalize-benchmark-run.py",
        (
            "INSERT OR REPLACE INTO benchmark_runs "
            "(run_id, dataset, infra_bench_commit, harbor_version, agent_harness, agent_tool, "
            "model_provider, model_name, model_version, model_reasoning, started_at, finished_at, "
            "task_count, passed, failed, score, duration_sec, cost_usd, "
            "input_tokens, cache_tokens, output_tokens, total_tokens, "
            "run_artifact_key, results_artifact_key, archive_artifact_key) VALUES "
            f"({sql_values(run_values)});"
        ),
    ]
    for result in results_doc["results"]:
        row_id = f"{run_doc['run_id']}/{result['task_name']}"
        result_values = [
            row_id,
            run_doc["run_id"],
            result["task_name"],
            result["task_slug"],
            result["difficulty"],
            result["category"],
            result["passed"],
            result["reward"],
            result["score"],
            result["duration_sec"],
            result["cost_usd"],
            result["input_tokens"],
            result["cache_tokens"],
            result["output_tokens"],
            result["total_tokens"],
            result["started_at"],
            result["finished_at"],
            result["verifier_artifact_key"],
            result["agent_artifact_key"],
        ]
        statements.append(
            "INSERT OR REPLACE INTO benchmark_task_results "
            "(id, run_id, task_name, task_slug, difficulty, category, passed, "
            "reward, score, duration_sec, cost_usd, "
            "input_tokens, cache_tokens, output_tokens, total_tokens, "
            "started_at, finished_at, "
            "verifier_artifact_key, agent_artifact_key) VALUES "
            f"({sql_values(result_values)});"
        )
    (output_dir / "d1-upsert.sql").write_text("\n".join(statements) + "\n")


def write_archive(job_dir: Path, output_dir: Path) -> None:
    """Write a zstd-compressed archive of the source Harbor job."""

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
    progress: Progress | None = None,
) -> None:
    """Write all normalized benchmark output files."""

    documents_task: TaskID | None = None
    if progress is not None:
        document_total = 4 + (len(trial_results) * 2)
        documents_task = progress.add_task(
            "Writing normalized artifacts", total=document_total
        )

    write_json(output_dir / "run.json", run_doc)
    advance(progress, documents_task)
    write_json(output_dir / "results.json", results_doc)
    advance(progress, documents_task)
    write_d1_sql(output_dir, run_doc, results_doc)
    advance(progress, documents_task)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_doc["run_id"],
        "dataset": run_doc["dataset"],
        "model": run_doc["model"],
        "summary": run_doc["summary"],
    }
    write_json(output_dir / "summary.json", summary)
    advance(progress, documents_task)
    for result in trial_results:
        public_dir = output_dir / "public" / result.task_slug
        write_json(public_dir / "verifier-summary.json", result.verifier_summary)
        advance(progress, documents_task)
        write_json(public_dir / "agent-summary.json", result.agent_summary)
        advance(progress, documents_task)
    if include_archive:
        archive_task: TaskID | None = None
        if progress is not None:
            archive_task = progress.add_task("Creating job archive", total=None)
        write_archive(job_dir, output_dir)
        if progress is not None and archive_task is not None:
            progress.update(archive_task, completed=1, total=1)


def main() -> int:
    """Run the benchmark normalizer CLI."""

    args = parse_args()
    if not args.dry_run and args.output_dir is None:
        raise SystemExit("--output-dir is required unless --dry-run is set")
    if args.dry_run:
        run_doc, results_doc, _trial_results = build_documents(args)
        print(json.dumps({"run": run_doc, "results": results_doc}, indent=2))
        return 0
    assert args.output_dir is not None
    with make_progress() as progress:
        run_doc, results_doc, trial_results = build_documents(args, progress=progress)
        write_outputs(
            output_dir=args.output_dir,
            run_doc=run_doc,
            results_doc=results_doc,
            trial_results=trial_results,
            include_archive=args.include_archive,
            job_dir=args.job_dir.resolve(),
            progress=progress,
        )
    print(f"wrote benchmark results to {args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
