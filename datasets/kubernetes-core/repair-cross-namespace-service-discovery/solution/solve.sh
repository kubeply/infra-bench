#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="orders-app"

kubectl -n "$namespace" patch configmap worker-settings \
  --type merge \
  --patch '{"data":{"DATABASE_URL":"http://database.shared-data.svc.cluster.local:8080/query"}}'

kubectl -n "$namespace" rollout restart deployment/order-worker
kubectl -n "$namespace" rollout status deployment/order-worker --timeout=180s
