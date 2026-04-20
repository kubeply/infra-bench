#!/usr/bin/env bash
set -euo pipefail

prepare-kubeconfig

namespace="TODO_NAMESPACE"

# TODO: verify semantic live-cluster state and reject shortcut fixes.
kubectl -n "$namespace" get all
