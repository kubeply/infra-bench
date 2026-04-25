#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

kubectl -n plugin-lab patch configmap plugin-app-template \
  --type merge \
  --patch '{"data":{"plugin_name":"analytics","config_output":"/generated/app.conf"}}'

kubectl -n plugin-lab patch deployment plugin-catalog \
  --type json \
  --patch '[{"op":"replace","path":"/spec/template/spec/containers/1/volumeMounts/0/mountPath","value":"/generated"}]'

kubectl -n plugin-lab rollout status deployment/plugin-catalog --timeout=180s

for _ in $(seq 1 90); do
  ready="$(kubectl -n plugin-lab get pod -l app=plugin-catalog -o jsonpath='{.items[0].status.containerStatuses[?(@.name=="app")].ready}' 2>/dev/null || true)"
  if [[ "$ready" == "true" ]]; then
    exit 0
  fi
  sleep 2
done

echo "plugin-catalog did not become ready after patching plugin-app-template" >&2
exit 1
