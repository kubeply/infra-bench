#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="edge-team"
ingress="portal"

kubectl -n "$namespace" patch ingress "$ingress" \
  --type json \
  --patch '[{"op":"replace","path":"/spec/tls/0/secretName","value":"portal-tls"},{"op":"remove","path":"/spec/rules/0/http/paths/0/backend/service/port/name"},{"op":"add","path":"/spec/rules/0/http/paths/0/backend/service/port/number","value":80}]'
