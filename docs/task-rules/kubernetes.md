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
| `local_cluster` | Task starts a local Kubernetes cluster, usually through Docker Compose with a k3s sidecar. | Runtime behavior matters and the agent should use `kubectl` against live resources. |
| `remote_sandbox` | Task targets a pre-provisioned cluster. | Cloud or managed-platform behavior matters. |

Use `local_cluster` when the benchmark outcome depends on live Kubernetes
state, such as pods becoming ready, Services receiving endpoints, or controllers
reconciling resources.

Local cluster tasks may require privileged Docker sidecars. Keep that
requirement task-local, document it through metadata such as
`requires_cluster = true`, and avoid privileged host assumptions outside the
task environment.

For `local_cluster` tasks, keep Docker Compose focused on orchestration:
services, volumes, dependencies, healthchecks, and commands that call scripts.
Put cluster bootstrap logic in executable scripts under `environment/scripts/`
instead of writing multi-line shell programs directly in `docker-compose.yaml`.
This avoids Docker Compose interpolating shell variables like `${deployment_uid}`
before the command runs inside the container, and keeps bootstrap behavior easier
to test with `bash -n`.

### Local Cluster Authoring Pattern

For Kubernetes tasks that use a local cluster, prefer this structure:

```text
environment/
|-- Dockerfile
|-- docker-compose.yaml
|-- scripts/
|   |-- bootstrap-cluster
|   `-- prepare-kubeconfig
`-- workspace/
    `-- <starting-assets>
```

Use `bootstrap-cluster` to:

- Wait for the cluster API to become reachable.
- Apply the broken starting state.
- Wait only for resources that should be healthy before the agent starts.
- Record immutable baseline facts needed by the verifier, such as Deployment
  and Service UIDs, in a task-local ConfigMap.

Use `prepare-kubeconfig` from the agent, solution, and verifier when the
cluster writes a kubeconfig with container-local addresses. Keep that helper
small and task-local until multiple Kubernetes tasks prove a shared helper is
worth maintaining.

The agent prompt should make the live-cluster expectation explicit. Tell the
agent to use `kubectl`, state that the cluster is already running, and describe
the desired live state without revealing verifier assertions.

## Verifier Expectations

Kubernetes verifiers should prefer semantic checks:

- Resource kind, name, namespace, labels, selectors, and references.
- Rollout-critical relationships such as Deployment selector to pod labels.
- Service selectors and target ports.
- RBAC subject, role, and verb coverage.
- Storage class, PVC, and mount relationships.

Avoid checking YAML formatting unless formatting is the task.

For `local_cluster` tasks, verifiers should also defend against common shortcut
solutions:

- Compare baseline UIDs for resources that must not be deleted and recreated.
- Check that replacement workloads or Services were not added.
- Check critical fields that the prompt forbids changing, such as images,
  container ports, Service ports, selectors, replica counts, and RBAC subjects.
- Verify the runtime behavior that matters, such as ready pods, populated
  Endpoints or EndpointSlices, successful rollout, DNS resolution, or a working
  request path.
- Dump enough Kubernetes state on failure to debug the next run: namespace
  resources, relevant YAML, `describe` output, and recent events.

Keep verifier waits bounded and targeted. Wait for controller reconciliation
where Kubernetes is eventually consistent, but fail with debug output instead of
sleeping blindly.

## Validation Workflow

Before adding a Kubernetes task to the dataset, run it in this order:

1. Syntax-check task shell scripts:

   ```bash
   bash -n datasets/kubernetes-core/<task>/environment/scripts/*
   bash -n datasets/kubernetes-core/<task>/tests/*.sh
   bash -n datasets/kubernetes-core/<task>/solution/solve.sh
   ```

2. Validate repository structure and refresh the dataset digest:

   ```bash
   ./scripts/validate-structure.sh
   uvx --from harbor harbor sync datasets/kubernetes-core
   ```

3. Run the oracle agent to prove the scripted solution passes:

   ```bash
   uvx --from harbor harbor run \
     -p datasets/kubernetes-core/<task> \
     -a oracle
   ```

4. Run at least one real agent before publishing when the task is meant to test
   live Kubernetes diagnosis:

   ```bash
   uvx --from harbor harbor run \
     -p datasets/kubernetes-core/<task> \
     -a codex \
     -m gpt-5.3-codex
   ```

Inspect the job logs after the real-agent run. A good first pass should show
the agent using `kubectl` to inspect live resources, applying a minimal fix, and
passing the verifier for the intended reason.
