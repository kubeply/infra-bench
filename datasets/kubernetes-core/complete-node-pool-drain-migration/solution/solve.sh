#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="retail-ops"
retiring_node="$(
  kubectl get nodes -l infra-bench/drain-target=true \
    -o jsonpath='{.items[0].metadata.name}'
)"

kubectl -n "$namespace" patch deployment checkout-api \
  --type json \
  --patch '[
    {"op":"replace","path":"/spec/replicas","value":3},
    {"op":"replace","path":"/spec/template/spec/affinity/nodeAffinity/requiredDuringSchedulingIgnoredDuringExecution/nodeSelectorTerms/0/matchExpressions/0/values/0","value":"target"}
  ]'

kubectl -n "$namespace" rollout status deployment/checkout-api --timeout=300s

evict_non_daemon_pods_on_retiring_node() {
  local pod

  while IFS='|' read -r pod owner_kind node_name; do
    [[ -z "$pod" ]] && continue
    [[ "$node_name" == "$retiring_node" && "$owner_kind" != "DaemonSet" ]] || continue

    cat <<EOF | kubectl create --raw "/api/v1/namespaces/${namespace}/pods/${pod}/eviction" -f - >/dev/null
{"apiVersion":"policy/v1","kind":"Eviction","metadata":{"name":"${pod}","namespace":"${namespace}"}}
EOF
  done < <(
    kubectl -n "$namespace" get pods \
      -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.metadata.ownerReferences[0].kind}{"|"}{.spec.nodeName}{"\n"}{end}'
  )
}

remaining_retiring_pods() {
  kubectl -n "$namespace" get pods \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.metadata.ownerReferences[0].kind}{"|"}{.spec.nodeName}{"\n"}{end}' \
    | awk -F'|' -v node="$retiring_node" '$3 == node && $2 != "DaemonSet" {print $1}'
}

migrated="false"
for _ in $(seq 1 120); do
  checkout_ready="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true)"
  checkout_allowed="$(kubectl -n "$namespace" get pdb checkout-api -o jsonpath='{.status.disruptionsAllowed}' 2>/dev/null || true)"
  checkout_on_retiring="$(
    kubectl -n "$namespace" get pods -l app=checkout-api \
      -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' \
      | grep -c "^${retiring_node}$" || true
  )"

  if [[ "$checkout_ready" == "3" && "$checkout_allowed" -ge 1 && "$checkout_on_retiring" == "0" ]]; then
    evict_non_daemon_pods_on_retiring_node
    migrated="true"
    break
  fi

  sleep 2
done

[[ "$migrated" == "true" ]] || {
  kubectl get nodes -o wide >&2 || true
  kubectl -n "$namespace" get pods,pdb -o wide >&2 || true
  exit 1
}

for _ in $(seq 1 120); do
  if [[ -z "$(remaining_retiring_pods)" ]]; then
    exit 0
  fi

  sleep 2
done

kubectl get nodes -o wide >&2 || true
kubectl -n "$namespace" get pods,pdb -o wide >&2 || true
exit 1
