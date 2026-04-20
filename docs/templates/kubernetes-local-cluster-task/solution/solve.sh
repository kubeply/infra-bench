#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="TODO_NEUTRAL_NAMESPACE"

# TODO: implement the minimal oracle repair.
kubectl -n "$namespace" get all
