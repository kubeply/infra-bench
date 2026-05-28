#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="commerce-prod"
sandbox="checkout-api-checkout-candidate"
session="kply-session-checkout-candidate"

fail() {
  echo "$1" >&2
  kubectl -n "$namespace" get all,configmaps -o wide >&2 || true
  kubectl -n "$namespace" get deployments -o yaml >&2 || true
  exit 1
}

kubectl -n "$namespace" rollout status deployment/checkout-api --timeout=180s \
  || fail "production rollout is not healthy"
kubectl -n "$namespace" rollout status "deployment/${sandbox}" --timeout=180s \
  || fail "sandbox rollout did not complete"

deployment_uid="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.metadata.uid}')"
service_uid="$(kubectl -n "$namespace" get service checkout-api -o jsonpath='{.metadata.uid}')"
baseline_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.deployment_uid}')"
baseline_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.service_uid}')"

[[ "$deployment_uid" == "$baseline_deployment_uid" ]] || fail "production Deployment was replaced"
[[ "$service_uid" == "$baseline_service_uid" ]] || fail "production Service was replaced"

deployments="$(kubectl -n "$namespace" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
services="$(kubectl -n "$namespace" get services -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
configmaps="$(kubectl -n "$namespace" get configmaps -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"

[[ "$deployments" == $'checkout-api\ncheckout-api-checkout-candidate' ]] || fail "unexpected Deployments: $deployments"
[[ "$services" == $'checkout-api\ncheckout-api-checkout-candidate' ]] || fail "unexpected Services: $services"
[[ "$configmaps" == $'infra-bench-baseline\nkply-session-checkout-candidate\nkube-root-ca.crt' ]] || fail "unexpected ConfigMaps: $configmaps"

prod_release="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="RELEASE")].value}')"
prod_ready="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.status.readyReplicas}')"
prod_selector="$(kubectl -n "$namespace" get service checkout-api -o jsonpath='{.spec.selector.app}')"
sandbox_release="$(kubectl -n "$namespace" get deployment "$sandbox" -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="RELEASE")].value}')"
sandbox_ready="$(kubectl -n "$namespace" get deployment "$sandbox" -o jsonpath='{.status.readyReplicas}')"
sandbox_selector="$(kubectl -n "$namespace" get service "$sandbox" -o jsonpath='{.spec.selector.app}')"
prod_endpoints="$(kubectl -n "$namespace" get endpoints checkout-api -o jsonpath='{.subsets[*].addresses[*].ip}')"
sandbox_endpoints="$(kubectl -n "$namespace" get endpoints "$sandbox" -o jsonpath='{.subsets[*].addresses[*].ip}')"
session_status="$(kubectl -n "$namespace" get configmap "$session" -o jsonpath='{.data.status}')"
session_mutated="$(kubectl -n "$namespace" get configmap "$session" -o jsonpath='{.data.production_mutated}')"
session_release="$(kubectl -n "$namespace" get configmap "$session" -o jsonpath='{.data.candidate_release}')"

[[ "$prod_release" == "v1" && "$prod_ready" == "2" ]] || fail "production should stay on v1 with 2 ready replicas"
[[ "$prod_selector" == "checkout-api" ]] || fail "production Service selector changed"
[[ "$sandbox_release" == "v2" && "$sandbox_ready" == "1" ]] || fail "sandbox should serve candidate v2"
[[ "$sandbox_selector" == "$sandbox" ]] || fail "sandbox Service selector is $sandbox_selector"
[[ -n "$prod_endpoints" && -n "$sandbox_endpoints" ]] || fail "production and sandbox Services need endpoints"
[[ "$session_status" == "applied" && "$session_mutated" == "false" && "$session_release" == "v2" ]] \
  || fail "session metadata is incomplete"

prod_pod="$(kubectl -n "$namespace" get pod -l app=checkout-api -o jsonpath='{.items[0].metadata.name}')"
sandbox_pod="$(kubectl -n "$namespace" get pod -l app="$sandbox" -o jsonpath='{.items[0].metadata.name}')"
prod_body="$(kubectl -n "$namespace" exec "$prod_pod" -- cat /www/index.html 2>/dev/null || true)"
sandbox_body="$(kubectl -n "$namespace" exec "$sandbox_pod" -- cat /www/index.html 2>/dev/null || true)"

[[ "$prod_body" == "checkout v1" ]] || fail "production pod returned '$prod_body'"
[[ "$sandbox_body" == "checkout v2" ]] || fail "sandbox pod returned '$sandbox_body'"
