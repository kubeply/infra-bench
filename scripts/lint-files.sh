#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

fail() {
  echo "error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 is required"
}

collect_files() {
  find . \
    -path "./.git" -prune -o \
    -path "./jobs" -prune -o \
    "$@"
}

require_command bunx
require_command jq
require_command shellcheck
require_command uvx

# renovate: datasource=npm depName=@taplo/cli
TAPLO_VERSION="0.7.0"
# renovate: datasource=npm depName=prettier
PRETTIER_VERSION="3.8.3"
# renovate: datasource=pypi depName=ruff
RUFF_VERSION="0.15.11"

toml_files=()
while IFS= read -r -d "" path; do
  toml_files+=("$path")
done < <(collect_files -type f -name "*.toml" -print0)
if [[ "${#toml_files[@]}" -gt 0 ]]; then
  bunx "@taplo/cli@${TAPLO_VERSION}" fmt --check "${toml_files[@]}"
  bunx "@taplo/cli@${TAPLO_VERSION}" lint "${toml_files[@]}"
fi

yaml_json_files=()
while IFS= read -r -d "" path; do
  yaml_json_files+=("$path")
done < <(
  collect_files -type f \( -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) -print0
)
if [[ "${#yaml_json_files[@]}" -gt 0 ]]; then
  bunx "prettier@${PRETTIER_VERSION}" --check "${yaml_json_files[@]}"
fi

json_files=()
while IFS= read -r -d "" path; do
  json_files+=("$path")
done < <(collect_files -type f -name "*.json" -print0)
if [[ "${#json_files[@]}" -gt 0 ]]; then
  for json_file in "${json_files[@]}"; do
    jq empty "$json_file" >/dev/null
  done
fi

shell_files=()
while IFS= read -r -d "" path; do
  shell_files+=("$path")
done < <(
  while IFS= read -r -d "" path; do
    if head -n 1 "$path" | grep -Eq '^#!.*(ba)?sh'; then
      printf "%s\0" "$path"
    fi
  done < <(collect_files -type f \( -name "*.sh" -o -perm -111 \) -print0)
)
if [[ "${#shell_files[@]}" -gt 0 ]]; then
  shellcheck -x "${shell_files[@]}"
fi

uvx --from "ruff==${RUFF_VERSION}" ruff check .
uvx --from "ruff==${RUFF_VERSION}" ruff format --check .

echo "file lint ok"
