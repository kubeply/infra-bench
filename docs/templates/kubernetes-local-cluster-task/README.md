# Kubernetes Local Cluster Task Template

Use this skeleton for Kubernetes tasks where the agent must repair live cluster
state through `kubectl`.

The template follows the two-image convention:

- `environment/Dockerfile` is the agent, solution, and verifier runtime.
- `environment/Dockerfile.bootstrap` is the bootstrap runtime.
- `environment/scripts/bootstrap-cluster` and `environment/workspace/bootstrap`
  are available only to the bootstrap service.
- `environment/scripts/prepare-kubeconfig` is available to agent, solution,
  verifier, and bootstrap.

Before copying this template into `datasets/kubernetes-core/<task-name>`,
replace all `TODO_*` placeholders, generate a fresh canary, and run the
validation workflow documented in `docs/task-rules/kubernetes.md`.
