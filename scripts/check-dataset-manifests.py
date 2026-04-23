#!/usr/bin/env python3
"""Verify dataset manifest digests without installing Harbor.

This mirrors Harbor's local `harbor sync` behavior for the task layout used in
this repository. It checks dataset-level file digests and local task digests,
then exits non-zero when a manifest is stale.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
from pathlib import Path
import sys
import tomllib


DEFAULT_IGNORES = [
    "__pycache__/",
    "*.pyc",
    ".DS_Store",
    "*.swp",
    "*.swo",
    "*~",
]

SINGLE_FILES = ("task.toml", "instruction.md", "README.md")
RECURSIVE_DIRS = ("environment", "tests", "solution")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that dataset.toml digests are synchronized."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Dataset directories or dataset.toml files. Defaults to all datasets.",
    )
    return parser.parse_args()


def resolve_manifests(paths: list[Path]) -> list[Path]:
    if not paths:
        return sorted(Path("datasets").glob("*/dataset.toml"))

    manifests: list[Path] = []
    for raw_path in paths:
        path = raw_path.resolve()
        if path.is_dir():
            manifest = path / "dataset.toml"
        else:
            manifest = path
        if manifest.name != "dataset.toml" or not manifest.exists():
            raise SystemExit(f"{raw_path}: dataset.toml not found")
        manifests.append(manifest)
    return sorted(manifests)


def compute_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def should_ignore(relative_path: str) -> bool:
    for pattern in DEFAULT_IGNORES:
        if pattern.endswith("/"):
            if relative_path == pattern[:-1] or relative_path.startswith(pattern):
                return True
            continue
        if fnmatch.fnmatch(relative_path, pattern):
            return True
    return False


def collect_task_files(task_dir: Path) -> list[Path]:
    gitignore_path = task_dir / ".gitignore"
    if gitignore_path.exists():
        raise SystemExit(
            f"{gitignore_path}: task-level .gitignore is not supported by "
            "scripts/check-dataset-manifests.py yet; use Harbor sync locally "
            "or extend the checker first"
        )

    files: list[Path] = []

    for name in SINGLE_FILES:
        candidate = task_dir / name
        if candidate.exists():
            files.append(candidate)

    for directory_name in RECURSIVE_DIRS:
        directory = task_dir / directory_name
        if not directory.exists():
            continue
        for child in directory.rglob("*"):
            if child.is_file():
                files.append(child)

    filtered = [
        path
        for path in files
        if not should_ignore(path.relative_to(task_dir).as_posix())
    ]
    return sorted(filtered, key=lambda path: path.relative_to(task_dir).as_posix())


def compute_task_hash(task_dir: Path) -> str:
    outer = hashlib.sha256()
    for path in collect_task_files(task_dir):
        rel = path.relative_to(task_dir).as_posix()
        file_hash = compute_file_hash(path)
        outer.update(f"{rel}\0{file_hash}\n".encode())
    return outer.hexdigest()


def load_toml(path: Path) -> dict:
    return tomllib.loads(path.read_text())


def local_task_index(dataset_dir: Path) -> dict[str, Path]:
    tasks: dict[str, Path] = {}
    for child in sorted(dataset_dir.iterdir()):
        if not child.is_dir():
            continue
        config_path = child / "task.toml"
        if not config_path.exists():
            continue

        try:
            data = load_toml(config_path)
            task_name = data["task"]["name"]
        except Exception:
            continue

        if isinstance(task_name, str) and task_name:
            tasks[task_name] = child

    return tasks


def verify_manifest(manifest_path: Path) -> list[str]:
    dataset_dir = manifest_path.parent
    data = load_toml(manifest_path)
    errors: list[str] = []

    for file_ref in data.get("files", []):
        file_path = dataset_dir / file_ref["path"]
        if not file_path.exists():
            errors.append(
                f"{manifest_path}: missing referenced file {file_ref['path']}"
            )
            continue

        actual = f"sha256:{compute_file_hash(file_path)}"
        expected = file_ref.get("digest", "")
        if expected != actual:
            errors.append(
                f"{manifest_path}: file {file_ref['path']} digest mismatch "
                f"(expected {expected}, actual {actual})"
            )

    local_tasks = local_task_index(dataset_dir)
    seen_names: set[str] = set()
    for task_ref in data.get("tasks", []):
        task_name = task_ref["name"]
        if task_name in seen_names:
            continue
        seen_names.add(task_name)

        task_dir = local_tasks.get(task_name)
        if task_dir is None:
            continue

        actual = f"sha256:{compute_task_hash(task_dir)}"
        expected = task_ref.get("digest", "")
        if expected != actual:
            rel_task_dir = task_dir.relative_to(dataset_dir)
            errors.append(
                f"{manifest_path}: task {task_name} ({rel_task_dir}) digest mismatch "
                f"(expected {expected}, actual {actual})"
            )

    return errors


def main() -> int:
    args = parse_args()
    manifests = resolve_manifests(args.paths)
    if not manifests:
        raise SystemExit("No dataset manifests found.")

    failures: list[str] = []
    for manifest in manifests:
        failures.extend(verify_manifest(manifest))

    if failures:
        for failure in failures:
            print(f"error: {failure}", file=sys.stderr)
        print(
            "\nRun `uvx --from harbor harbor sync datasets/<dataset-name>` to refresh "
            "the affected manifest.",
            file=sys.stderr,
        )
        return 1

    for manifest in manifests:
        print(f"{manifest}: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
