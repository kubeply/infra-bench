#!/usr/bin/env python3
"""Upload normalized benchmark JSON artifacts to Cloudflare R2."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

JSON_CONTENT_TYPE = "application/json; charset=utf-8"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the R2 uploader."""

    parser = argparse.ArgumentParser(
        description="Upload normalized benchmark JSON artifacts to R2."
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--r2-prefix", default="benchmarks")
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def load_run_id(output_dir: Path) -> str:
    """Read the run id from a normalized run.json file."""

    run_path = output_dir / "run.json"
    if not run_path.exists():
        raise SystemExit(f"{run_path}: missing run.json")
    data = json.loads(run_path.read_text())
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise SystemExit(f"{run_path}: missing run_id")
    return run_id


def iter_upload_files(output_dir: Path) -> list[Path]:
    """Return normalized JSON files that should be public R2 artifacts."""

    files = [
        output_dir / "run.json",
        output_dir / "results.json",
        output_dir / "summary.json",
    ]
    files.extend(sorted((output_dir / "public").glob("*/*.json")))
    missing = [path for path in files if not path.exists()]
    if missing:
        formatted = "\n".join(str(path) for path in missing)
        raise SystemExit(f"missing normalized artifact files:\n{formatted}")
    return files


def object_key(output_dir: Path, path: Path, r2_prefix: str, run_id: str) -> str:
    """Build the R2 object key for one normalized artifact file."""

    relative = path.relative_to(output_dir).as_posix()
    return f"{r2_prefix.strip('/')}/runs/{run_id}/{relative}"


def upload_file(
    bucket: str,
    key: str,
    path: Path,
    *,
    local: bool,
    remote: bool,
) -> None:
    """Upload one file to R2 with Wrangler."""

    command = [
        "wrangler",
        "r2",
        "object",
        "put",
        f"{bucket}/{key}",
        "--file",
        str(path),
        "--content-type",
        JSON_CONTENT_TYPE,
    ]
    if local:
        command.append("--local")
    if remote:
        command.append("--remote")
    subprocess.run(command, check=True)


def main() -> int:
    """Run the R2 upload workflow."""

    args = parse_args()
    output_dir = args.output_dir.resolve()
    run_id = load_run_id(output_dir)
    files = iter_upload_files(output_dir)

    for path in files:
        key = object_key(output_dir, path, args.r2_prefix, run_id)
        if args.dry_run:
            print(f"{path} -> r2://{args.bucket}/{key}")
        else:
            upload_file(args.bucket, key, path, local=args.local, remote=args.remote)

    action = "would upload" if args.dry_run else "uploaded"
    print(f"{action} {len(files)} benchmark artifacts to r2://{args.bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
