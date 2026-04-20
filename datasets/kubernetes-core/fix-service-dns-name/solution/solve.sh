#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="checkout-team"
deployment="checkout-client"

kubectl -n "$namespace" set env deployment/"$deployment" \
  BACKEND_URL=http://orders-api.orders-team.svc.cluster.local

kubectl -n "$namespace" rollout status deployment/"$deployment" --timeout=180s
