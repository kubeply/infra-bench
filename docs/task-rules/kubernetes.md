# Kubernetes Task Rules

Kubernetes is the first benchmark domain for `infra-bench`.

## Task Shape

- Prefer realistic, bounded operator work: manifest repair, rollout debugging,
  policy fixes, service discovery, storage, RBAC, scheduling, and upgrade
  hygiene.
- Keep each task focused on one operator outcome.
- Include broken starting state in `environment/`, not in tests.
- The verifier should check behavior or externally observable state, not just
  exact file diffs.
- Avoid tasks that require privileged host access unless the dataset explicitly
  documents that environment class.

## Scenario Classes

- Manifest repair: fix invalid or semantically wrong Kubernetes YAML.
- Rollout debugging: repair workloads that cannot become ready.
- Service discovery: fix selectors, ports, DNS assumptions, or endpoints.
- Config and secret wiring: correct projected config, env vars, and mounts.
- RBAC and policy: fix least-privilege access or admission failures.
- Scheduling: resolve node selectors, taints, tolerations, resources, and
  topology constraints.
- Storage: fix PVC, volume, and mount issues.

## Environment Classes

Use the smallest environment that still tests the operator skill.

| Class | Description | Use When |
| --- | --- | --- |
| `static_manifest` | Agent edits manifests; verifier parses resources. | Testing Kubernetes object semantics without a cluster. |
| `local_cluster` | Task starts a local Kubernetes cluster. | Runtime behavior matters. |
| `remote_sandbox` | Task targets a pre-provisioned cluster. | Cloud or managed-platform behavior matters. |

Use `static_manifest` for the first lightweight baseline tasks.

## Verifier Expectations

Kubernetes verifiers should prefer semantic checks:

- Resource kind, name, namespace, labels, selectors, and references.
- Rollout-critical relationships such as Deployment selector to pod labels.
- Service selectors and target ports.
- RBAC subject, role, and verb coverage.
- Storage class, PVC, and mount relationships.

Avoid checking YAML formatting unless formatting is the task.
