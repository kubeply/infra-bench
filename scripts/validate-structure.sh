#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

fail() {
  echo "error: $*" >&2
  exit 1
}

[[ -f LICENSE ]] || fail "missing LICENSE"
[[ -f AGENTS.md ]] || fail "missing AGENTS.md"
[[ -d docs ]] || fail "missing docs/"
[[ -d datasets ]] || fail "missing datasets/"

while IFS= read -r task_toml; do
  task_dir="$(dirname "$task_toml")"

  [[ -f "$task_dir/instruction.md" ]] || fail "$task_dir missing instruction.md"
  [[ -d "$task_dir/environment" ]] || fail "$task_dir missing environment/"
  [[ -f "$task_dir/solution/solve.sh" ]] || fail "$task_dir missing solution/solve.sh"
  [[ -x "$task_dir/solution/solve.sh" ]] || fail "$task_dir solution/solve.sh is not executable"
  [[ -f "$task_dir/tests/test.sh" ]] || fail "$task_dir missing tests/test.sh"
  [[ -x "$task_dir/tests/test.sh" ]] || fail "$task_dir tests/test.sh is not executable"
done < <(find datasets -mindepth 3 -maxdepth 3 -name task.toml | sort)

python_bin="${PYTHON:-}"
if [[ -z "$python_bin" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    python_bin="python3"
  elif command -v python >/dev/null 2>&1; then
    python_bin="python"
  else
    fail "python3 or python is required for TOML validation"
  fi
fi

"$python_bin" - <<'PY'
from pathlib import Path
import tomllib

for path in sorted(Path("datasets").glob("*/dataset.toml")):
    data = tomllib.loads(path.read_text())
    dataset = data.get("dataset", {})
    if not dataset.get("name"):
        raise SystemExit(f"{path}: missing dataset.name")

for path in sorted(Path("datasets").glob("*/*/task.toml")):
    data = tomllib.loads(path.read_text())
    task = data.get("task", {})
    if not task.get("name"):
        raise SystemExit(f"{path}: missing task.name")
    if not data.get("schema_version"):
        raise SystemExit(f"{path}: missing schema_version")
PY

echo "structure ok"
