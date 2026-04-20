#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

kubectl -n web-platform patch service web \
  --type merge \
  --patch '{"spec":{"selector":{"app":"web"}}}'

kubectl -n web-platform rollout status deployment/web --timeout=120s

for _ in $(seq 1 60); do
  endpoints="$(kubectl -n web-platform get endpoints web -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
  if [[ -n "$endpoints" ]]; then
    exit 0
  fi
  sleep 1
done

echo "Service web did not receive endpoints" >&2
exit 1
