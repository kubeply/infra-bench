#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="processing-team"

kubectl -n "$namespace" patch deployment worker \
  --type json \
  --patch '[{"op":"add","path":"/spec/template/spec/containers/0/resources/requests/cpu","value":"100m"}]'

kubectl -n "$namespace" patch hpa worker \
  --type json \
  --patch '[{"op":"replace","path":"/spec/scaleTargetRef/name","value":"worker"}]'

kubectl -n "$namespace" rollout status deployment/worker --timeout=180s

for _ in $(seq 1 90); do
  scaling_active="$(
    kubectl -n "$namespace" get hpa worker \
      -o jsonpath='{.status.conditions[?(@.type=="ScalingActive")].status}' 2>/dev/null || true
  )"
  able_to_scale="$(
    kubectl -n "$namespace" get hpa worker \
      -o jsonpath='{.status.conditions[?(@.type=="AbleToScale")].status}' 2>/dev/null || true
  )"
  current_metric="$(
    kubectl -n "$namespace" get hpa worker \
      -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization}' 2>/dev/null || true
  )"
  desired_replicas="$(
    kubectl -n "$namespace" get hpa worker \
      -o jsonpath='{.status.desiredReplicas}' 2>/dev/null || true
  )"
  ready_replicas="$(
    kubectl -n "$namespace" get deployment worker \
      -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true
  )"

  if [[ "$scaling_active" == "True" && "$able_to_scale" == "True" && -n "$current_metric" && "${desired_replicas:-0}" -ge 3 && "${ready_replicas:-0}" -ge 3 ]]; then
    exit 0
  fi

  sleep 2
done

kubectl -n "$namespace" describe hpa worker >&2 || true
kubectl -n "$namespace" get deployment worker -o yaml >&2 || true
exit 1
