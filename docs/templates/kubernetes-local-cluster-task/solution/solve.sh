#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="TODO_NAMESPACE"

# TODO: implement the minimal oracle repair.
kubectl -n "$namespace" get all
