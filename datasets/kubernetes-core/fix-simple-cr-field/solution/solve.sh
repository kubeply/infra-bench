#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="search-team"

kubectl -n "$namespace" patch widget search-index \
  --type merge \
  --patch '{"spec":{"mode":"active"}}'
