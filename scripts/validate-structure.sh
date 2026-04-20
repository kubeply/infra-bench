#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

fail() {
  echo "error: $*" >&2
  exit 1
}

service_block() {
  local compose_file="$1"
  local service="$2"

  awk -v service="$service" '
    $0 ~ "^  " service ":$" {
      in_service = 1
      print
      next
    }
    in_service && $0 ~ /^  [[:alnum:]_-]+:$/ {
      exit
    }
    in_service {
      print
    }
  ' "$compose_file"
}

[[ -f LICENSE ]] || fail "missing LICENSE"
[[ -f AGENTS.md ]] || fail "missing AGENTS.md"
[[ -d docs ]] || fail "missing docs/"
[[ -d datasets ]] || fail "missing datasets/"

while IFS= read -r task_toml; do
  task_dir="$(dirname "$task_toml")"

  [[ -f "$task_dir/instruction.md" ]] || fail "$task_dir missing instruction.md"
  [[ -d "$task_dir/environment" ]] || fail "$task_dir missing environment/"
  if [[ -f "$task_dir/environment/scripts/bootstrap-cluster" ]]; then
    [[ -f "$task_dir/environment/Dockerfile" ]] || fail "$task_dir missing environment/Dockerfile"
    [[ -f "$task_dir/environment/Dockerfile.bootstrap" ]] || fail "$task_dir missing environment/Dockerfile.bootstrap"
    [[ -f "$task_dir/environment/docker-compose.yaml" ]] || fail "$task_dir missing environment/docker-compose.yaml"
    if grep -q 'bootstrap-cluster' "$task_dir/environment/Dockerfile"; then
      fail "$task_dir agent Dockerfile must not copy bootstrap-cluster"
    fi
    if grep -Eq 'COPY[[:space:]]+scripts/[[:space:]]' "$task_dir/environment/Dockerfile"; then
      fail "$task_dir agent Dockerfile must copy only scripts/prepare-kubeconfig"
    fi
    if grep -Eq 'COPY[[:space:]]+.*workspace/bootstrap|ADD[[:space:]]+.*workspace/bootstrap' "$task_dir/environment/Dockerfile"; then
      fail "$task_dir agent Dockerfile must not copy workspace/bootstrap"
    fi
    grep -q 'bootstrap-cluster' "$task_dir/environment/Dockerfile.bootstrap" \
      || fail "$task_dir bootstrap Dockerfile must include bootstrap-cluster"
    grep -q 'Dockerfile.bootstrap' "$task_dir/environment/docker-compose.yaml" \
      || fail "$task_dir bootstrap service must build from Dockerfile.bootstrap"

    main_block="$(service_block "$task_dir/environment/docker-compose.yaml" main)"
    bootstrap_block="$(service_block "$task_dir/environment/docker-compose.yaml" bootstrap)"

    grep -q 'agent-kubeconfig:/kube:ro' <<<"$main_block" \
      || fail "$task_dir main service must mount agent kubeconfig read-only"
    if grep -q 'admin-kubeconfig:/admin-kube' <<<"$main_block"; then
      fail "$task_dir main service must not mount admin kubeconfig"
    fi
    if grep -q './workspace/bootstrap' <<<"$main_block"; then
      fail "$task_dir main service must not mount workspace/bootstrap"
    fi
    grep -q './workspace/bootstrap:/bootstrap:ro' <<<"$bootstrap_block" \
      || fail "$task_dir bootstrap service must mount workspace/bootstrap read-only"
  fi
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
import re
import tomllib

CANARY_RE = re.compile(
    r"^<infra-bench-canary: "
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    r">$"
)

for path in sorted(Path("datasets").glob("*/dataset.toml")):
    data = tomllib.loads(path.read_text())
    dataset = data.get("dataset", {})
    if not dataset.get("name"):
        raise SystemExit(f"{path}: missing dataset.name")

seen_canaries = {}

for path in sorted(Path("datasets").glob("*/*/task.toml")):
    data = tomllib.loads(path.read_text())
    task = data.get("task", {})
    if not task.get("name"):
        raise SystemExit(f"{path}: missing task.name")
    if not task.get("category"):
        raise SystemExit(f"{path}: missing task.category")
    if not isinstance(task.get("keywords"), list) or not task.get("keywords"):
        raise SystemExit(f"{path}: missing task.keywords")
    if not data.get("schema_version"):
        raise SystemExit(f"{path}: missing schema_version")

    metadata = data.get("metadata", {})
    for duplicate_field in ("author_name", "author_email", "category", "tags"):
        if duplicate_field in metadata:
            raise SystemExit(
                f"{path}: metadata.{duplicate_field} duplicates task fields"
            )

    canary = metadata.get("canary")
    if not isinstance(canary, str):
        raise SystemExit(f"{path}: missing metadata.canary")
    if not CANARY_RE.fullmatch(canary):
        raise SystemExit(
            f"{path}: metadata.canary must match '<infra-bench-canary: UUIDv4>'"
        )
    if canary in seen_canaries:
        raise SystemExit(
            f"{path}: metadata.canary duplicates {seen_canaries[canary]}"
        )
    seen_canaries[canary] = path

    instruction_path = path.parent / "instruction.md"
    instruction_lines = instruction_path.read_text().splitlines()
    if not instruction_lines:
        raise SystemExit(f"{instruction_path}: missing canary first line")

    instruction_canary = instruction_lines[0].strip()
    if instruction_canary != canary:
        raise SystemExit(
            f"{instruction_path}: first line must match metadata.canary in {path}"
        )
PY

echo "structure ok"
