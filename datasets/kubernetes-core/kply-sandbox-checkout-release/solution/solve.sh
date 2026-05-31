#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

kply app inspect checkout
kply session plan checkout --release v2
kply session apply checkout --release v2
kubectl -n commerce-prod get deployment checkout-api checkout-api-checkout-candidate
