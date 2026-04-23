#!/usr/bin/env bash
set -euo pipefail

namespace="product-observability"
mkdir -p /logs/verifier

prepare-kubeconfig

dump_debug() {
  {
    echo "### namespace resources"
    kubectl -n "$namespace" get all,configmap,secret,role,rolebinding,endpoints -o wide || true
    echo
    echo "### observability-ui deployment"
    kubectl -n "$namespace" get deployment observability-ui -o yaml || true
    echo
    echo "### datasource secret"
    kubectl -n "$namespace" get secret observability-datasources -o yaml || true
    echo
    echo "### observability-ui logs"
    kubectl -n "$namespace" logs deployment/observability-ui --tail=120 || true
    echo
    echo "### recent events"
    kubectl -n "$namespace" get events --sort-by=.lastTimestamp || true
  } > /logs/verifier/debug.log 2>&1
}

fail() {
  echo "$1" >&2
  dump_debug
  exit 1
}

baseline() {
  kubectl -n "$namespace" get configmap infra-bench-baseline \
    -o "jsonpath={.data.$1}"
}

uid_for() {
  kubectl -n "$namespace" get "$1" "$2" -o jsonpath='{.metadata.uid}'
}

expect_uid() {
  local kind="$1"
  local name="$2"
  local key="$3"
  local expected
  local actual
  expected="$(baseline "$key")"
  actual="$(uid_for "$kind" "$name")"
  [[ -n "$expected" ]] || fail "missing baseline UID for $key"
  [[ "$actual" == "$expected" ]] || fail "$kind/$name was deleted and recreated"
}

secret_file() {
  kubectl -n "$namespace" get secret "$1" -o "jsonpath={.data.$2}" | base64 --decode
}

expect_uid deployment observability-ui ui_deployment_uid
expect_uid service observability-ui ui_service_uid
expect_uid deployment incident-monitor incident_monitor_deployment_uid
expect_uid deployment logs-backend logs_backend_deployment_uid
expect_uid service logs-backend logs_backend_service_uid
expect_uid deployment docs docs_deployment_uid
expect_uid service docs docs_service_uid
expect_uid deployment demo-api demo_deployment_uid
expect_uid service demo-api demo_service_uid
expect_uid deployment metrics-backend metrics_backend_deployment_uid
expect_uid service metrics-backend metrics_backend_service_uid
expect_uid secret observability-datasources datasource_secret_uid
expect_uid configmap logs-backend-content logs_backend_content_uid
expect_uid configmap metrics-backend-content metrics_backend_content_uid
expect_uid serviceaccount observability-ui ui_serviceaccount_uid

deployments="$(kubectl -n "$namespace" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort | tr '\n' ' ')"
[[ "$deployments" == "demo-api docs incident-monitor logs-backend metrics-backend observability-ui " ]] || fail "unexpected Deployments: $deployments"

services="$(kubectl -n "$namespace" get services -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort | tr '\n' ' ')"
[[ "$services" == "demo-api docs logs-backend metrics-backend observability-ui " ]] || fail "unexpected Services: $services"

configmaps="$(kubectl -n "$namespace" get configmaps -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort | tr '\n' ' ')"
[[ "$configmaps" == "infra-bench-baseline kube-root-ca.crt logs-backend-content metrics-backend-content " ]] || fail "unexpected ConfigMaps: $configmaps"

secrets="$(kubectl -n "$namespace" get secrets -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort | tr '\n' ' ')"
[[ "$secrets" == "infra-bench-agent-token observability-datasources " ]] || fail "unexpected Secrets: $secrets"

for resource in statefulsets daemonsets jobs cronjobs; do
  count="$(kubectl -n "$namespace" get "$resource" -o name | wc -l | tr -d ' ')"
  [[ "$count" == "0" ]] || fail "unexpected $resource were created"
done

bare_pods="$(kubectl -n "$namespace" get pods -o jsonpath='{range .items[?(@.metadata.ownerReferences[0].kind!="ReplicaSet")]}{.metadata.name}{"\n"}{end}')"
[[ -z "$bare_pods" ]] || fail "standalone pods are not allowed: $bare_pods"

for deployment in observability-ui incident-monitor logs-backend metrics-backend docs demo-api; do
  kubectl -n "$namespace" rollout status "deployment/${deployment}" --timeout=120s \
    || fail "deployment/${deployment} did not complete rollout"
done

for service in observability-ui logs-backend metrics-backend docs demo-api; do
  endpoints="$(kubectl -n "$namespace" get endpoints "$service" -o jsonpath='{.subsets[*].addresses[*].ip}')"
  [[ -n "$endpoints" ]] || fail "service/$service has no ready endpoints"
done

datasource="$(secret_file observability-datasources datasource\\.yaml)"
expected_url="http://logs-backend.product-observability.svc.cluster.local:3100/ready"
expected_metrics_url="http://metrics-backend.product-observability.svc.cluster.local:9090/ready"

grep -q "name: cluster-logs" <<< "$datasource" || fail "datasource name changed or disappeared"
grep -q "type: loki" <<< "$datasource" || fail "datasource type changed"
grep -q "access: proxy" <<< "$datasource" || fail "datasource access mode changed"
grep -q "url: ${expected_url}" <<< "$datasource" || fail "datasource URL does not point at the in-cluster logging backend"
grep -q "name: cluster-metrics" <<< "$datasource" || fail "metrics datasource disappeared"
grep -q "type: prometheus" <<< "$datasource" || fail "metrics datasource type changed"
grep -q "url: ${expected_metrics_url}" <<< "$datasource" || fail "metrics datasource URL changed"

if grep -Eq 'https?://(localhost|127\.0\.0\.1|host\.docker\.internal|[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+|[^. ]+\.com)' <<< "$datasource"; then
  fail "datasource uses an external or host-local endpoint"
fi

ui_image="$(kubectl -n "$namespace" get deployment observability-ui -o jsonpath='{.spec.template.spec.containers[0].image}')"
ui_sa="$(kubectl -n "$namespace" get deployment observability-ui -o jsonpath='{.spec.template.spec.serviceAccountName}')"
ui_port="$(kubectl -n "$namespace" get deployment observability-ui -o jsonpath='{.spec.template.spec.containers[0].ports[0].containerPort}')"
ui_secret="$(kubectl -n "$namespace" get deployment observability-ui -o jsonpath='{.spec.template.spec.volumes[0].secret.secretName}')"
ui_mount="$(kubectl -n "$namespace" get deployment observability-ui -o jsonpath='{.spec.template.spec.containers[0].volumeMounts[0].mountPath}')"
incident_monitor_image="$(kubectl -n "$namespace" get deployment incident-monitor -o jsonpath='{.spec.template.spec.containers[0].image}')"
incident_monitor_command="$(kubectl -n "$namespace" get deployment incident-monitor -o jsonpath='{.spec.template.spec.containers[0].command[*]}')"
logs_backend_image="$(kubectl -n "$namespace" get deployment logs-backend -o jsonpath='{.spec.template.spec.containers[0].image}')"
logs_backend_service_port="$(kubectl -n "$namespace" get service logs-backend -o jsonpath='{.spec.ports[0].port}')"
logs_backend_target_port="$(kubectl -n "$namespace" get service logs-backend -o jsonpath='{.spec.ports[0].targetPort}')"
metrics_backend_image="$(kubectl -n "$namespace" get deployment metrics-backend -o jsonpath='{.spec.template.spec.containers[0].image}')"
metrics_backend_service_port="$(kubectl -n "$namespace" get service metrics-backend -o jsonpath='{.spec.ports[0].port}')"
metrics_backend_target_port="$(kubectl -n "$namespace" get service metrics-backend -o jsonpath='{.spec.ports[0].targetPort}')"

[[ "$ui_image" == "busybox:1.36.1" ]] || fail "observability UI image changed"
[[ "$ui_sa" == "observability-ui" ]] || fail "observability UI ServiceAccount changed"
[[ "$ui_port" == "3000" ]] || fail "observability UI container port changed"
[[ "$ui_secret" == "observability-datasources" ]] || fail "observability UI datasource Secret mount changed"
[[ "$ui_mount" == "/etc/observability-ui/provisioning/datasources" ]] || fail "observability UI datasource mount path changed"
[[ "$incident_monitor_image" == "busybox:1.36.1" ]] || fail "incident monitor image changed"
grep -q 'observability-ui.product-observability.svc.cluster.local:3000/panels' <<< "$incident_monitor_command" \
  || fail "incident monitor dependency path changed"
[[ "$logs_backend_image" == "nginx:1.27" ]] || fail "logging backend image changed"
[[ "$logs_backend_service_port" == "3100" && "$logs_backend_target_port" == "http" ]] || fail "logging backend Service port changed"
[[ "$metrics_backend_image" == "nginx:1.27" ]] || fail "metrics backend image changed"
[[ "$metrics_backend_service_port" == "9090" && "$metrics_backend_target_port" == "http" ]] || fail "metrics backend Service port changed"

for service in docs demo-api; do
  selector="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.selector.app}')"
  target_port="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.ports[0].targetPort}')"
  image="$(kubectl -n "$namespace" get deployment "$service" -o jsonpath='{.spec.template.spec.containers[0].image}')"
  [[ "$selector" == "$service" && "$target_port" == "http" && "$image" == "busybox:1.36.1" ]] \
    || fail "$service app or Service changed unexpectedly"
done

for _ in $(seq 1 90); do
  if kubectl -n "$namespace" logs deployment/observability-ui --tail=80 2>/dev/null | grep -q "log panels ready via ${expected_url}" \
    && kubectl -n "$namespace" logs deployment/incident-monitor --tail=80 2>/dev/null | grep -q 'incident monitor confirmed log panels via http://observability-ui.product-observability.svc.cluster.local:3000/panels'; then
    echo "observability UI log panels recovered through the in-cluster datasource"
    exit 0
  fi
  sleep 1
done

fail "observability UI or downstream incident monitor logs do not show successful datasource recovery"
