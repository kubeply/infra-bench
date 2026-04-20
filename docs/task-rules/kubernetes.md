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

## Difficulty Progression

Use difficulty to describe Kubernetes operator complexity and bypass resistance,
not the number of files touched.

- `easy`: one broken relationship, one primary resource family, and direct
  symptoms. The intended fix should be reachable after a short `kubectl`
  inspection, and the verifier should still reject delete-and-recreate or
  alternate-resource shortcuts.
- `medium`: two or more related Kubernetes concepts, a moderate diagnosis path,
  or symptoms that require correlating resources. Good medium tasks may combine
  a workload with a Service, ConfigMap, Secret, RBAC rule, NetworkPolicy,
  storage object, Job, or controller-generated resource. The fix should still
  be bounded to one operator outcome and should not require guessing hidden
  verifier details.
- `hard`: layered or ambiguous failure modes, multi-step remediation, scarce
  capacity, migration or upgrade constraints, or validation that spans several
  controllers and runtime behaviors.

For medium and hard `local_cluster` tasks, start from the same two-image
environment pattern used by the easy tasks. Do not reintroduce a single image
that copies bootstrap-only scripts or manifests into the agent runtime.

## Coverage Area Keywords

Kubernetes tasks should include one primary coverage-area keyword in
`[task].keywords`. Area keywords are plain Harbor task keywords, not GitHub
label names: use `service-routing`, not `area:service-routing`.

Keep `task.category = "kubernetes"` for the dataset domain. Use
`metadata.scenario_type` for the task workflow shape, such as
`live_cluster_debug`, `upgrade_readiness`, `migration`, or `incident_response`.

| Area Keyword | Covers |
| --- | --- |
| `service-routing` | Services, selectors, named ports, endpoints, EndpointSlices, and request paths. |
| `rollout-readiness` | Deployment rollout state, probes, ReplicaSets, readiness gates, and rollout recovery. |
| `config-secrets` | ConfigMaps, Secrets, env refs, projected files, reload behavior, and rotation. |
| `rbac-access` | ServiceAccounts, Roles, RoleBindings, authorization checks, and least privilege. |
| `scheduling-capacity` | Pending pods, taints, tolerations, node selectors, affinity, and resource requests. |
| `cpu-operations` | CPU requests, limits, throttling, contention, and HPA inputs. |
| `gpu-operations` | GPU resource requests, node labels, taints, device plugin assumptions, and scarce capacity. |
| `storage-stateful` | PVCs, StorageClasses, mounts, StatefulSets, headless Services, and data preservation. |
| `network-policy` | NetworkPolicy, namespace selectors, ports, DNS assumptions, and allowed or denied paths. |
| `dns-cluster-services` | Service DNS, CoreDNS symptoms, namespace resolution, and cluster service dependencies. |
| `ingress-tls` | IngressClass, routes, TLS Secrets, certificate rotation, and ingress controller behavior. |
| `autoscaling` | HPA, metrics availability, requests, scale targets, flapping, and capacity. |
| `node-migration` | Cordon, drain, PDBs, node pools, single-node clusters, and server migration. |
| `kubernetes-upgrades` | Deprecated APIs, version compatibility, and control-plane dependency assumptions. |
| `controller-upgrades` | Helm values, CRDs, webhooks, and ingress, storage, or metrics controller upgrades. |
| `operators-crds` | Custom resources, generated resources, status conditions, finalizers, and controller logs. |
| `batch-scheduled-work` | Jobs, CronJobs, history, logs, retries, idempotency, and maintenance automation. |
| `observability-incident` | Events, logs, metrics, status fields, noisy symptoms, and root cause isolation. |
| `multi-app-dependencies` | Frontend, API, worker, database, namespace, queue, and background-job dependencies. |
| `backup-restore-migration` | Restore workflows, namespace migration, data movement, and validation after restore. |
| `security-posture` | Pod Security, securityContext, restricted workloads, permissions, and hardening without breakage. |
| `quirky-apps` | Nonstandard health endpoints, sidecars, generated config, unusual startup behavior, and unfamiliar apps. |

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
|-- Dockerfile.bootstrap
|-- docker-compose.yaml
|-- scripts/
|   |-- bootstrap-cluster
|   `-- prepare-kubeconfig
`-- workspace/
    `-- <starting-assets>
```

A copyable skeleton lives in
`docs/templates/kubernetes-local-cluster-task/`. Replace every `TODO_*`
placeholder before moving it into `datasets/kubernetes-core/<task-name>`.

Use `bootstrap-cluster` to:

- Wait for the cluster API to become reachable.
- Apply the broken starting state.
- Wait only for resources that should be healthy before the agent starts.
- Record immutable baseline facts needed by the verifier, such as Deployment
  and Service UIDs. If those facts are stored in Kubernetes resources, the agent
  must not be able to mutate those resources.

Use separate task-local images for local-cluster work:

- `environment/Dockerfile` is the agent, solution, and verifier runtime. It
  should include `kubectl`, `prepare-kubeconfig`, and only files intentionally
  exposed to the agent.
- `environment/Dockerfile.bootstrap` is the bootstrap runtime. It may include
  `bootstrap-cluster` and any setup-only helpers needed to prepare the cluster.

Use `prepare-kubeconfig` from the agent, solution, verifier, and bootstrap when
the cluster writes a kubeconfig with container-local addresses. Keep that helper
small and task-local until multiple Kubernetes tasks prove a shared helper is
worth maintaining.

### Local Cluster Access Boundaries

Local-cluster tasks should separate bootstrap/verifier authority from agent
authority.

- Keep an admin kubeconfig available only to bootstrap and verifier paths.
- Generate a least-privilege ServiceAccount kubeconfig for the agent.
- Mount the agent kubeconfig read-only into the main agent container.
- Grant the agent only the read verbs needed for diagnosis and the write verbs
  needed for the intended fix.
- Do not let the agent update verifier-trusted baseline objects, such as
  ConfigMaps that store original resource UIDs.
- Do not copy `bootstrap-cluster` into the agent runtime image. The bootstrap
  service should build from `Dockerfile.bootstrap` or otherwise receive
  bootstrap-only code outside the agent container.

Do not copy answer-bearing bootstrap assets into `/app` or the agent image. If
`environment/workspace/bootstrap/*.yaml` reveals the broken field or intended
fix, mount it only into the bootstrap service, for example at `/bootstrap:ro`.
The agent workspace should contain only files the task intentionally exposes.

Current Harbor Docker local-cluster tasks may need `allow_internet = true` so
the main container can reach the k3s sidecar network. Treat that as a documented
exception to the general preference for `allow_internet = false`; do not flip a
local-cluster task to `false` without proving the oracle can still reach the
cluster.

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

- Compare trusted baseline UIDs for resources that must not be deleted and
  recreated. A UID stored in an agent-writable ConfigMap is not trusted.
- Check that replacement workloads or Services were not added. Cover workload
  kinds beyond Deployments, including StatefulSets, DaemonSets, Jobs, CronJobs,
  standalone Pods, and stray ReplicaSets.
- Verify ownership relationships, not just counts. For Deployment tasks, check
  that Pods are owned by ReplicaSets and ReplicaSets are owned by the intended
  Deployment.
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
   python3 scripts/lint-kubernetes-rbac.py
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
