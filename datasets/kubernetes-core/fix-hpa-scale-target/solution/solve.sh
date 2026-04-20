#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="catalog-team"
hpa="catalog-api"

kubectl -n "$namespace" patch hpa "$hpa" \
  --type json \
  --patch '[{"op":"replace","path":"/spec/scaleTargetRef/name","value":"catalog-api"}]'
