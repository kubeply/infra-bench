#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="metrics-team"
deployment="metrics-adapter"
service="metrics-adapter"
values_configmap="metrics-adapter-values"
telemetry_deployment="telemetry-proxy"
telemetry_service="telemetry-proxy"
telemetry_values_configmap="telemetry-proxy-values"
dashboard_deployment="metrics-dashboard"
dashboard_service="metrics-dashboard"

dump_debug() {
  echo "--- namespace resources ---"
  kubectl -n "$namespace" get all,configmaps,endpoints -o wide || true
  echo "--- service yaml ---"
  kubectl -n "$namespace" get service "$service" -o yaml || true
  echo "--- endpoints yaml ---"
  kubectl -n "$namespace" get endpoints "$service" -o yaml || true
  echo "--- deployment yaml ---"
  kubectl -n "$namespace" get deployment "$deployment" -o yaml || true
  echo "--- dashboard logs ---"
  kubectl -n "$namespace" logs deployment/"$dashboard_deployment" --tail=120 || true
  echo "--- pod describe ---"
  kubectl -n "$namespace" describe pods || true
  echo "--- recent events ---"
  kubectl -n "$namespace" get events --sort-by=.lastTimestamp || true
}

for rollout_deployment in "$deployment" "$telemetry_deployment" "$dashboard_deployment"; do
  if kubectl -n "$namespace" rollout status deployment/"$rollout_deployment" --timeout=180s; then
    continue
  fi
  dump_debug
  exit 1
done

deployment_uid="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.metadata.uid}')"
service_uid="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.metadata.uid}')"
values_uid="$(kubectl -n "$namespace" get configmap "$values_configmap" -o jsonpath='{.metadata.uid}')"
telemetry_deployment_uid="$(kubectl -n "$namespace" get deployment "$telemetry_deployment" -o jsonpath='{.metadata.uid}')"
telemetry_service_uid="$(kubectl -n "$namespace" get service "$telemetry_service" -o jsonpath='{.metadata.uid}')"
telemetry_values_uid="$(kubectl -n "$namespace" get configmap "$telemetry_values_configmap" -o jsonpath='{.metadata.uid}')"
dashboard_deployment_uid="$(kubectl -n "$namespace" get deployment "$dashboard_deployment" -o jsonpath='{.metadata.uid}')"
dashboard_service_uid="$(kubectl -n "$namespace" get service "$dashboard_service" -o jsonpath='{.metadata.uid}')"
baseline_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.deployment_uid}')"
baseline_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.service_uid}')"
baseline_values_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.values_uid}')"
baseline_telemetry_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.telemetry_deployment_uid}')"
baseline_telemetry_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.telemetry_service_uid}')"
baseline_telemetry_values_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.telemetry_values_uid}')"
baseline_dashboard_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.dashboard_deployment_uid}')"
baseline_dashboard_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.dashboard_service_uid}')"

if [[ -z "$baseline_deployment_uid" \
  || -z "$baseline_service_uid" \
  || -z "$baseline_values_uid" \
  || -z "$baseline_dashboard_deployment_uid" \
  || -z "$baseline_dashboard_service_uid" \
  || -z "$baseline_telemetry_deployment_uid" \
  || -z "$baseline_telemetry_service_uid" \
  || -z "$baseline_telemetry_values_uid" ]]; then
  echo "Baseline ConfigMap is missing resource UIDs" >&2
  kubectl -n "$namespace" get configmap infra-bench-baseline -o yaml || true
  exit 1
fi

if [[ "$deployment_uid" != "$baseline_deployment_uid" \
  || "$service_uid" != "$baseline_service_uid" \
  || "$values_uid" != "$baseline_values_uid" \
  || "$dashboard_deployment_uid" != "$baseline_dashboard_deployment_uid" \
  || "$dashboard_service_uid" != "$baseline_dashboard_service_uid" \
  || "$telemetry_deployment_uid" != "$baseline_telemetry_deployment_uid" \
  || "$telemetry_service_uid" != "$baseline_telemetry_service_uid" \
  || "$telemetry_values_uid" != "$baseline_telemetry_values_uid" ]]; then
  echo "A preserved resource was replaced" >&2
  echo "deployment expected=${baseline_deployment_uid} got=${deployment_uid}" >&2
  echo "service expected=${baseline_service_uid} got=${service_uid}" >&2
  echo "values expected=${baseline_values_uid} got=${values_uid}" >&2
  echo "dashboard deployment expected=${baseline_dashboard_deployment_uid} got=${dashboard_deployment_uid}" >&2
  echo "dashboard service expected=${baseline_dashboard_service_uid} got=${dashboard_service_uid}" >&2
  echo "telemetry deployment expected=${baseline_telemetry_deployment_uid} got=${telemetry_deployment_uid}" >&2
  echo "telemetry service expected=${baseline_telemetry_service_uid} got=${telemetry_service_uid}" >&2
  echo "telemetry values expected=${baseline_telemetry_values_uid} got=${telemetry_values_uid}" >&2
  exit 1
fi

deployment_names="$(kubectl -n "$namespace" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
service_names="$(kubectl -n "$namespace" get services -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
configmap_names="$(kubectl -n "$namespace" get configmaps -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"

if [[ "$deployment_names" != $'metrics-adapter\nmetrics-dashboard\ntelemetry-proxy' || "$service_names" != $'metrics-adapter\nmetrics-dashboard\ntelemetry-proxy' ]]; then
  echo "Unexpected Deployment or Service set: deployments=${deployment_names} services=${service_names}" >&2
  exit 1
fi

if [[ "$configmap_names" != $'infra-bench-baseline\nkube-root-ca.crt\nmetrics-adapter-values\ntelemetry-proxy-values' ]]; then
  echo "Unexpected ConfigMap set in $namespace: $configmap_names" >&2
  exit 1
fi

unexpected_workloads="$(
  {
    kubectl -n "$namespace" get daemonsets.apps -o name
    kubectl -n "$namespace" get statefulsets.apps -o name
    kubectl -n "$namespace" get jobs.batch -o name
    kubectl -n "$namespace" get cronjobs.batch -o name
  } 2>/dev/null | sort
)"

if [[ -n "$unexpected_workloads" ]]; then
  echo "Unexpected replacement workload resources in $namespace:" >&2
  echo "$unexpected_workloads" >&2
  exit 1
fi

deployment_label_name="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.metadata.labels.app\.kubernetes\.io/name}')"
deployment_label_component="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.metadata.labels.app\.kubernetes\.io/component}')"
selector_name="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.selector.matchLabels.app\.kubernetes\.io/name}')"
selector_component="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.selector.matchLabels.app\.kubernetes\.io/component}')"
pod_label_name="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.metadata.labels.app\.kubernetes\.io/name}')"
pod_label_component="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.metadata.labels.app\.kubernetes\.io/component}')"
service_selector_name="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/name}')"
service_selector_component="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/component}')"
container_names="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.spec.containers[*].name}')"
container_image="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.spec.containers[0].image}')"
container_port_name="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.spec.containers[0].ports[0].name}')"
container_port="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.template.spec.containers[0].ports[0].containerPort}')"
service_port_name="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.ports[0].name}')"
service_port="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.ports[0].port}')"
service_target_port="$(kubectl -n "$namespace" get service "$service" -o jsonpath='{.spec.ports[0].targetPort}')"
replicas="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.spec.replicas}')"
ready_replicas="$(kubectl -n "$namespace" get deployment "$deployment" -o jsonpath='{.status.readyReplicas}')"

if [[ "$deployment_label_name" != "$deployment" || "$deployment_label_component" != "controller" || "$selector_name" != "$deployment" || "$selector_component" != "controller" ]]; then
  echo "Deployment labels/selectors changed" >&2
  exit 1
fi

if [[ "$pod_label_name" != "$deployment" || "$pod_label_component" != "controller" ]]; then
  echo "Pod labels changed; name=${pod_label_name} component=${pod_label_component}" >&2
  exit 1
fi

if [[ "$service_selector_name" != "$deployment" || "$service_selector_component" != "controller" ]]; then
  echo "Service selector should match controller pod labels, got name=${service_selector_name} component=${service_selector_component}" >&2
  exit 1
fi

if [[ "$container_names" != "$deployment" || "$container_image" != "busybox:1.36" || "$container_port_name" != "https" || "$container_port" != "8443" ]]; then
  echo "Controller container changed; names=${container_names} image=${container_image} port=${container_port_name}:${container_port}" >&2
  exit 1
fi

if [[ "$service_port_name" != "https" || "$service_port" != "443" || "$service_target_port" != "https" ]]; then
  echo "Service port changed; got ${service_port_name} ${service_port}->${service_target_port}" >&2
  exit 1
fi

if [[ "$replicas" != "2" || "$ready_replicas" != "2" ]]; then
  echo "Deployment replica count changed; expected 2 ready replicas, got spec=${replicas} ready=${ready_replicas}" >&2
  exit 1
fi

telemetry_selector_name="$(kubectl -n "$namespace" get service "$telemetry_service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/name}')"
telemetry_selector_component="$(kubectl -n "$namespace" get service "$telemetry_service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/component}')"
telemetry_image="$(kubectl -n "$namespace" get deployment "$telemetry_deployment" -o jsonpath='{.spec.template.spec.containers[0].image}')"
telemetry_replicas="$(kubectl -n "$namespace" get deployment "$telemetry_deployment" -o jsonpath='{.spec.replicas}')"
telemetry_ready_replicas="$(kubectl -n "$namespace" get deployment "$telemetry_deployment" -o jsonpath='{.status.readyReplicas}')"
telemetry_service_port="$(kubectl -n "$namespace" get service "$telemetry_service" -o jsonpath='{.spec.ports[0].port}')"
telemetry_target_port="$(kubectl -n "$namespace" get service "$telemetry_service" -o jsonpath='{.spec.ports[0].targetPort}')"
dashboard_selector_name="$(kubectl -n "$namespace" get service "$dashboard_service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/name}')"
dashboard_selector_component="$(kubectl -n "$namespace" get service "$dashboard_service" -o jsonpath='{.spec.selector.app\.kubernetes\.io/component}')"
dashboard_image="$(kubectl -n "$namespace" get deployment "$dashboard_deployment" -o jsonpath='{.spec.template.spec.containers[0].image}')"
dashboard_replicas="$(kubectl -n "$namespace" get deployment "$dashboard_deployment" -o jsonpath='{.spec.replicas}')"
dashboard_ready_replicas="$(kubectl -n "$namespace" get deployment "$dashboard_deployment" -o jsonpath='{.status.readyReplicas}')"
dashboard_url="$(kubectl -n "$namespace" get deployment "$dashboard_deployment" -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="METRICS_URL")].value}')"
dashboard_service_port="$(kubectl -n "$namespace" get service "$dashboard_service" -o jsonpath='{.spec.ports[0].port}')"
dashboard_target_port="$(kubectl -n "$namespace" get service "$dashboard_service" -o jsonpath='{.spec.ports[0].targetPort}')"
values_release="$(kubectl -n "$namespace" get configmap "$values_configmap" -o jsonpath='{.data.values\.yaml}' | grep -c 'release: platform-metrics' || true)"
telemetry_values_release="$(kubectl -n "$namespace" get configmap "$telemetry_values_configmap" -o jsonpath='{.data.values\.yaml}' | grep -c 'release: telemetry-stack' || true)"

if [[ "$telemetry_selector_name" != "$telemetry_deployment" || "$telemetry_selector_component" != "controller" ]]; then
  echo "Healthy telemetry Service selector changed" >&2
  exit 1
fi

if [[ "$telemetry_image" != "busybox:1.36" || "$telemetry_replicas" != "1" || "$telemetry_ready_replicas" != "1" ]]; then
  echo "Healthy telemetry Deployment changed; image=${telemetry_image} spec=${telemetry_replicas} ready=${telemetry_ready_replicas}" >&2
  exit 1
fi

if [[ "$telemetry_service_port" != "443" || "$telemetry_target_port" != "https" ]]; then
  echo "Healthy telemetry Service port changed" >&2
  exit 1
fi

if [[ "$dashboard_selector_name" != "$dashboard_deployment" || "$dashboard_selector_component" != "client" ]]; then
  echo "Metrics dashboard Service selector changed" >&2
  exit 1
fi

if [[ "$dashboard_image" != "busybox:1.36" || "$dashboard_replicas" != "1" || "$dashboard_ready_replicas" != "1" ]]; then
  echo "Metrics dashboard did not recover; image=${dashboard_image} spec=${dashboard_replicas} ready=${dashboard_ready_replicas}" >&2
  exit 1
fi

if [[ "$dashboard_url" != "http://metrics-adapter.metrics-team.svc.cluster.local:443/ready" ]]; then
  echo "Metrics dashboard dependency URL changed: ${dashboard_url}" >&2
  exit 1
fi

if [[ "$dashboard_service_port" != "80" || "$dashboard_target_port" != "http" ]]; then
  echo "Metrics dashboard Service port changed" >&2
  exit 1
fi

if [[ "$values_release" != "1" || "$telemetry_values_release" != "1" ]]; then
  echo "Chart-style values ConfigMaps were modified unexpectedly" >&2
  exit 1
fi

for _ in $(seq 1 60); do
  endpoint_ips="$(kubectl -n "$namespace" get endpoints "$service" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
  endpoint_port="$(kubectl -n "$namespace" get endpoints "$service" -o jsonpath='{.subsets[0].ports[0].port}' 2>/dev/null || true)"

  if [[ -n "$endpoint_ips" && "$endpoint_port" == "8443" ]]; then
    break
  fi

  sleep 1
done

if [[ -z "${endpoint_ips:-}" || "${endpoint_port:-}" != "8443" ]]; then
  echo "Service $service has no ready controller endpoints on port 8443" >&2
  dump_debug
  exit 1
fi

telemetry_endpoint_ips="$(kubectl -n "$namespace" get endpoints "$telemetry_service" -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
telemetry_endpoint_port="$(kubectl -n "$namespace" get endpoints "$telemetry_service" -o jsonpath='{.subsets[0].ports[0].port}' 2>/dev/null || true)"

if [[ -z "$telemetry_endpoint_ips" || "$telemetry_endpoint_port" != "8443" ]]; then
  echo "Healthy telemetry Service lost its endpoints" >&2
  dump_debug
  exit 1
fi

dashboard_log="$(kubectl -n "$namespace" logs deployment/"$dashboard_deployment" --tail=120 2>/dev/null || true)"
if ! grep -q "metrics dashboard reached metrics-adapter" <<< "$dashboard_log"; then
  echo "Metrics dashboard did not reach the repaired metrics-adapter Service" >&2
  dump_debug
  exit 1
fi

echo "Service $service has controller endpoints: $endpoint_ips"
