# Harbor Compatibility

This repository follows the Harbor task and dataset format.

Reference docs:

- [Harbor task structure](https://www.harborframework.com/docs/tasks)
- [Harbor task differences from Terminal-Bench](https://www.harborframework.com/docs/tasks/task-difference)
- [Harbor dataset publishing](https://www.harborframework.com/docs/datasets/publishing)
- [Harbor dataset metrics](https://www.harborframework.com/docs/datasets/metrics)

## Task Shape

A task directory must include:

```text
instruction.md
task.toml
environment/
solution/solve.sh
tests/test.sh
```

Harbor copies `solution/` to `/solution` for the oracle agent and `tests/` to
`/tests` for verification. The verifier must write a reward file under
`/logs/verifier`.

Accepted reward outputs:

- `/logs/verifier/reward.txt` with a numeric value such as `1` or `0`.
- `/logs/verifier/reward.json` with numeric metrics.

## `task.toml`

Harbor task configuration is stored in `task.toml`. Harbor marks most config
properties as optional, but published `infra-bench` tasks should include the
standard sections below so task behavior is explicit.

Required top-level content:

| Field | Value |
| --- | --- |
| `schema_version` | Current Harbor task schema version, such as `"1.1"`. |
| `[task]` | Task identity and public description. |
| `[metadata]` | Arbitrary metadata used for filtering and comparison. |
| `[verifier]` | Verifier runtime configuration. |
| `[agent]` | Agent runtime configuration. |
| `[solution]` | Oracle solution runtime configuration. |
| `[environment]` | Task environment resources and runtime options. |
| `source` | Optional source URL or source identifier. |

### Task Fields

| Field | Type | Notes |
| --- | --- | --- |
| `task.name` | string | Globally unique Harbor task name, using `kubeply/<task-name>`. |
| `task.description` | string | Short public description of the task. |
| `task.keywords` | list of strings | Search and discovery keywords. |
| `task.authors` | list of tables | Each author includes `name` and, when available, `email`. |

Example:

```toml
[task]
name = "kubeply/<task-name>"
description = "Repair a focused infrastructure problem."
keywords = ["kubernetes", "manifests"]

[[task.authors]]
name = "Kubeply"
email = "thomas@kubeply.com"
```

### Runtime Fields

| Section | Field | Type | Notes |
| --- | --- | --- | --- |
| `verifier` | `timeout_sec` | number | Maximum verifier runtime. |
| `verifier` | `env` | object | Environment variables for verifier execution. |
| `verifier` | `user` | string, integer, or null | Optional OS user for verifier execution. |
| `agent` | `timeout_sec` | number | Maximum agent runtime. |
| `agent` | `user` | string, integer, or null | Optional OS user for agent execution. |
| `solution` | `env` | object | Environment variables for oracle solution execution. |
| `environment` | `build_timeout_sec` | number | Maximum environment build time. |
| `environment` | `docker_image` | string or null | Optional prebuilt image reference. |
| `environment` | `cpus` | number | CPU allocation. |
| `environment` | `memory_mb` | integer | Memory allocation in MiB. |
| `environment` | `storage_mb` | integer | Storage allocation in MiB. |
| `environment` | `gpus` | integer | GPU allocation. Use `0` unless a task explicitly requires GPU access. |
| `environment` | `gpu_types` | list of strings or null | Optional allowed GPU types, such as `H100` or `A100`. |
| `environment` | `allow_internet` | boolean | Whether the task environment may access the internet. Prefer `false`. |
| `environment` | `env` | object | Environment variables for the task environment. |
| `environment` | `mcp_servers` | list of MCP server configs | MCP servers exposed to the task environment. Use `[]` unless required. |
| `environment` | `skills_dir` | string or null | Optional skills directory exposed to the task environment. |
| `environment.healthcheck` | `command` | string | Optional healthcheck command. |
| `environment.healthcheck` | `interval_sec` | number | Optional interval between healthcheck attempts. |
| `environment.healthcheck` | `timeout_sec` | number | Optional healthcheck timeout. |
| `environment.healthcheck` | `start_period_sec` | number | Optional healthcheck start period. |
| `environment.healthcheck` | `start_interval_sec` | number | Optional start-period interval. |
| `environment.healthcheck` | `retries` | integer | Optional retry count. |
| top level | `source` | string or null | Optional source URL or identifier. |

Recommended baseline:

```toml
source = null

[verifier]
timeout_sec = 600.0
env = {}
user = null

[agent]
timeout_sec = 600.0
user = null

[solution]
env = {}

[environment]
build_timeout_sec = 600.0
docker_image = null
cpus = 1
memory_mb = 2048
storage_mb = 10240
gpus = 0
gpu_types = null
allow_internet = false
mcp_servers = []
skills_dir = null
env = {}
```

Healthchecks are optional and should be used only when the task environment
starts a service that must become ready before the agent begins:

```toml
[environment.healthcheck]
command = "curl -f http://localhost:8080/health"
interval_sec = 5.0
timeout_sec = 30.0
retries = 3
```

MCP server configs are optional. When used, follow Harbor's MCP server shape:

```toml
[[environment.mcp_servers]]
name = "mcp-server"
transport = "streamable-http"
url = "http://mcp-server:8000/mcp"
```

## Metadata

Harbor allows arbitrary metadata under `[metadata]`. `infra-bench` uses a small
Terminal-Bench-style metadata set so tasks remain searchable and comparable.

Common fields:

| Field | Type | Values |
| --- | --- | --- |
| `author_name` | string | Usually `"Kubeply"`. |
| `author_email` | string | Usually `"thomas@kubeply.com"`. |
| `canary` | string | Same value as the first line of `instruction.md`, using `<infra-bench-canary: UUID>`. |
| `difficulty` | string | `easy`, `medium`, or `hard`. |
| `difficulty_explanation` | string | Short reason for the chosen difficulty. |
| `category` | string | Dataset domain, such as `kubernetes`, `terraform`, or `observability`. |
| `tags` | list of strings | Focused labels such as `manifests`, `service`, `rbac`, `storage`, `modules`, `state`, `alerts`, or `metrics`. |
| `expert_time_estimate_min` | number | Expected expert completion time in minutes. |
| `junior_time_estimate_min` | number | Expected junior engineer completion time in minutes. |

Domain-specific fields should be added only when they improve evaluation or
filtering:

| Field | Type | Example values |
| --- | --- | --- |
| `scenario_type` | string | `manifest_repair`, `rollout_debugging`, `plan_repair`, `policy_authoring`, `incident_response`. |
| `requires_cluster` | boolean | `true` or `false`. |
| `kubernetes_focus` | string | `"Deployment, Service, and ConfigMap references"`. |
| `terraform_focus` | string | `"module inputs and resource references"`. |
| `observability_focus` | string | `"alert rule thresholds and label matching"`. |

## Instruction Preambles

Every published `infra-bench` task must include a canary UUID. The canary is a
contamination marker: it does not prevent training, but it gives the project a
stable string to search for if task prompts appear in model outputs or training
corpora.

Generate the canary with:

```bash
python3 -c 'import uuid; print(f"<infra-bench-canary: {uuid.uuid4()}>")'
```

Add the generated line as the first line of `instruction.md`:

```md
<infra-bench-canary: 7f7e9f1e-8e4e-4d47-a42f-2a5a5f2b7c11>

You are working in /app...
```

Store the same full string in `task.toml` metadata:

```toml
[metadata]
canary = "<infra-bench-canary: 7f7e9f1e-8e4e-4d47-a42f-2a5a5f2b7c11>"
```

The value in `instruction.md` and `task.toml` must match exactly. Do not reuse
canaries across tasks.

`infra-bench` has not adopted a training-data disclaimer yet. Do not add
task-specific disclaimers ad hoc. If this project adopts one, it should be a
repository-wide convention documented here and applied consistently before the
task prompt content.

## Dataset Shape

Datasets live under `datasets/<dataset-name>/` and contain a `dataset.toml`
manifest. Local tasks can live next to that manifest so Harbor can refresh their
digests during publish.

Current datasets:

```text
datasets/
|-- kubernetes-core/
|   |-- dataset.toml
|   `-- metric.py
`-- terraform-core/
    |-- dataset.toml
    `-- metric.py
```

## Common Commands

Run a local dataset with the oracle solution:

```bash
uvx --from harbor harbor run -p datasets/kubernetes-core -a oracle
```

Run a single local task once tasks exist:

```bash
uvx --from harbor harbor run \
  -p datasets/<dataset-name>/<task-name> \
  -a oracle
```

Refresh dataset digests:

```bash
uvx --from harbor harbor sync datasets/<dataset-name>
```

Publish publicly when ready:

```bash
uvx --from harbor harbor publish datasets/<dataset-name> --public -t v0.1
```
