#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="commerce-prod"

kubectl -n "$namespace" set env deployment/checkout-api RELEASE=v2
kubectl -n "$namespace" annotate deployment/checkout-api release.kubeply.io/id=v2 --overwrite
kubectl -n "$namespace" rollout status deployment/checkout-api --timeout=180s
