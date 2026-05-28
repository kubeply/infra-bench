#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="commerce-prod"

fail() {
  echo "$1" >&2
  kubectl -n "$namespace" get all,configmaps -o wide >&2 || true
  kubectl -n "$namespace" get deployment checkout-api -o yaml >&2 || true
  exit 1
}

kubectl -n "$namespace" rollout status deployment/checkout-api --timeout=180s \
  || fail "checkout-api rollout did not complete"

deployment_uid="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.metadata.uid}')"
service_uid="$(kubectl -n "$namespace" get service checkout-api -o jsonpath='{.metadata.uid}')"
baseline_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.deployment_uid}')"
baseline_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.service_uid}')"

[[ "$deployment_uid" == "$baseline_deployment_uid" ]] || fail "checkout-api Deployment was replaced"
[[ "$service_uid" == "$baseline_service_uid" ]] || fail "checkout-api Service was replaced"

deployments="$(kubectl -n "$namespace" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
services="$(kubectl -n "$namespace" get services -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
configmaps="$(kubectl -n "$namespace" get configmaps -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"

[[ "$deployments" == "checkout-api" ]] || fail "unexpected Deployments: $deployments"
[[ "$services" == "checkout-api" ]] || fail "unexpected Services: $services"
[[ "$configmaps" == $'infra-bench-baseline\nkube-root-ca.crt' ]] || fail "unexpected ConfigMaps: $configmaps"

release_env="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="RELEASE")].value}')"
release_annotation="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.metadata.annotations.release\.kubeply\.io/id}')"
replicas="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.spec.replicas}')"
ready="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.status.readyReplicas}')"
selector="$(kubectl -n "$namespace" get deployment checkout-api -o jsonpath='{.spec.selector.matchLabels.app}')"
service_selector="$(kubectl -n "$namespace" get service checkout-api -o jsonpath='{.spec.selector.app}')"
target_port="$(kubectl -n "$namespace" get service checkout-api -o jsonpath='{.spec.ports[0].targetPort}')"
endpoints="$(kubectl -n "$namespace" get endpoints checkout-api -o jsonpath='{.subsets[*].addresses[*].ip}')"

[[ "$release_env" == "v2" ]] || fail "production Deployment RELEASE is $release_env"
[[ "$release_annotation" == "v2" ]] || fail "release annotation is $release_annotation"
[[ "$replicas" == "2" && "$ready" == "2" ]] || fail "expected 2 ready production replicas"
[[ "$selector" == "checkout-api" && "$service_selector" == "checkout-api" ]] || fail "production selectors changed"
[[ "$target_port" == "http" ]] || fail "production Service targetPort changed"
[[ -n "$endpoints" ]] || fail "production Service has no endpoints"
