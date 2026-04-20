#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="web-platform"

dump_debug() {
  echo "--- namespace ---"
  kubectl get namespace "$namespace" -o wide || true
  echo "--- deployments ---"
  kubectl -n "$namespace" get deployments -o wide || true
  echo "--- pods ---"
  kubectl -n "$namespace" get pods -o wide || true
  echo "--- service ---"
  kubectl -n "$namespace" get service web -o yaml || true
  echo "--- endpoints ---"
  kubectl -n "$namespace" get endpoints web -o yaml || true
  echo "--- deployment describe ---"
  kubectl -n "$namespace" describe deployment web || true
  echo "--- pod describe ---"
  kubectl -n "$namespace" describe pods || true
  echo "--- recent events ---"
  kubectl -n "$namespace" get events --sort-by=.lastTimestamp || true
}

if ! kubectl -n "$namespace" rollout status deployment/web --timeout=120s; then
  dump_debug
  exit 1
fi

deployment_uid="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.metadata.uid}')"
service_uid="$(kubectl -n "$namespace" get service web -o jsonpath='{.metadata.uid}')"
baseline_deployment_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.deployment_uid}')"
baseline_service_uid="$(kubectl -n "$namespace" get configmap infra-bench-baseline -o jsonpath='{.data.service_uid}')"

if [[ -z "$baseline_deployment_uid" || -z "$baseline_service_uid" ]]; then
  echo "Baseline ConfigMap is missing resource UIDs" >&2
  kubectl -n "$namespace" get configmap infra-bench-baseline -o yaml || true
  exit 1
fi

if [[ "$deployment_uid" != "$baseline_deployment_uid" ]]; then
  echo "Deployment web was replaced; expected UID $baseline_deployment_uid, got $deployment_uid" >&2
  exit 1
fi

if [[ "$service_uid" != "$baseline_service_uid" ]]; then
  echo "Service web was replaced; expected UID $baseline_service_uid, got $service_uid" >&2
  exit 1
fi

deployment_names="$(kubectl -n "$namespace" get deployments -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"
service_names="$(kubectl -n "$namespace" get services -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort)"

if [[ "$deployment_names" != "web" ]]; then
  echo "Unexpected Deployment set in $namespace: $deployment_names" >&2
  exit 1
fi

if [[ "$service_names" != "web" ]]; then
  echo "Unexpected Service set in $namespace: $service_names" >&2
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

deployment_labels="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.template.metadata.labels.app}')"
service_selector="$(kubectl -n "$namespace" get service web -o jsonpath='{.spec.selector.app}')"
container_names="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.template.spec.containers[*].name}')"
container_image="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}')"
container_port_name="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.template.spec.containers[0].ports[0].name}')"
container_port="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.template.spec.containers[0].ports[0].containerPort}')"
service_port="$(kubectl -n "$namespace" get service web -o jsonpath='{.spec.ports[0].port}')"
service_target_port="$(kubectl -n "$namespace" get service web -o jsonpath='{.spec.ports[0].targetPort}')"
deployment_replicas="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.spec.replicas}')"
deployment_ready_replicas="$(kubectl -n "$namespace" get deployment web -o jsonpath='{.status.readyReplicas}')"
pod_count="$(kubectl -n "$namespace" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | grep -c . || true)"

if [[ "$deployment_labels" != "web" ]]; then
  echo "Deployment web pod label app is '$deployment_labels', expected 'web'" >&2
  exit 1
fi

if [[ "$deployment_replicas" != "2" || "$deployment_ready_replicas" != "2" ]]; then
  echo "Deployment web replica count changed; expected 2 ready replicas, got spec=${deployment_replicas} ready=${deployment_ready_replicas}" >&2
  exit 1
fi

if [[ "$container_names" != "web" ]]; then
  echo "Deployment web containers changed; expected only 'web', got '$container_names'" >&2
  exit 1
fi

if [[ "$container_image" != "nginx:1.27" ]]; then
  echo "Deployment web image changed; expected nginx:1.27, got '$container_image'" >&2
  exit 1
fi

if [[ "$container_port_name" != "http" || "$container_port" != "80" ]]; then
  echo "Deployment web container port changed; expected http:80, got ${container_port_name}:${container_port}" >&2
  exit 1
fi

if [[ "$service_port" != "80" || "$service_target_port" != "http" ]]; then
  echo "Service web port changed; expected port 80 targetPort http, got port ${service_port} targetPort ${service_target_port}" >&2
  exit 1
fi

if [[ "$service_selector" != "$deployment_labels" ]]; then
  echo "Service selector app='$service_selector' does not match pod label app='$deployment_labels'" >&2
  exit 1
fi

ready_pods="$(kubectl -n "$namespace" get pods -l app=web -o jsonpath='{range .items[*]}{range .status.conditions[?(@.type=="Ready")]}{.status}{"\n"}{end}{end}' | grep -c '^True$' || true)"
if [[ "$pod_count" != "2" ]]; then
  echo "Unexpected pod count in $namespace; expected 2 Deployment pods, got $pod_count" >&2
  exit 1
fi

if [[ "$ready_pods" != "2" ]]; then
  echo "Expected 2 ready pods for app=web, got $ready_pods" >&2
  exit 1
fi

while IFS='|' read -r pod_name pod_app owner_kind; do
  [[ -z "$pod_name" ]] && continue

  if [[ "$pod_app" != "web" || "$owner_kind" != "ReplicaSet" ]]; then
    echo "Unexpected pod ownership for ${pod_name}: app=${pod_app} ownerKind=${owner_kind}" >&2
    exit 1
  fi
done < <(
  kubectl -n "$namespace" get pods \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.metadata.labels.app}{"|"}{.metadata.ownerReferences[0].kind}{"\n"}{end}'
)

while IFS='|' read -r replicaset_name owner_kind owner_name; do
  [[ -z "$replicaset_name" ]] && continue

  if [[ "$owner_kind" != "Deployment" || "$owner_name" != "web" ]]; then
    echo "Unexpected ReplicaSet ownership for ${replicaset_name}: ownerKind=${owner_kind} ownerName=${owner_name}" >&2
    exit 1
  fi
done < <(
  kubectl -n "$namespace" get replicasets \
    -o jsonpath='{range .items[*]}{.metadata.name}{"|"}{.metadata.ownerReferences[0].kind}{"|"}{.metadata.ownerReferences[0].name}{"\n"}{end}'
)

for _ in $(seq 1 60); do
  endpoint_ips="$(kubectl -n "$namespace" get endpoints web -o jsonpath='{.subsets[*].addresses[*].ip}' 2>/dev/null || true)"
  if [[ -n "$endpoint_ips" ]]; then
    echo "Service web has endpoints: $endpoint_ips"
    exit 0
  fi
  sleep 1
done

echo "Service web has no endpoint addresses" >&2
exit 1
