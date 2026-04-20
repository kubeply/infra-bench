---
name: implement-infra-task
description: Implement one approved infra-bench task issue into a Harbor-compatible dataset task. Use when asked to implement a Kubernetes Core, Terraform Core, or future infra-bench task from a GitHub issue or planning backlog, including reading the issue and repo docs, creating the task directory, writing environment, instruction, verifier, oracle solution, running validation, and updating the issue or PR status.
---

# Implement Infra Task

Use this skill to implement exactly one approved `infra-bench` task at a
time. The source of truth is the task issue; do not broaden, merge, or redesign
the scenario unless the user explicitly asks for a planning change first.

## Inputs

- A GitHub issue number or URL, such as `#21`.
- A target dataset only when the issue does not make it clear.

If the issue is ambiguous or not approved for implementation, ask one concise
question before editing files.

## Read First

1. Read the task issue and any linked parent planning issues.
2. Read the required repo docs:
   - `datasets/<dataset-name>/dataset.toml`
   - `docs/conventions.md`
   - `docs/harbor.md`
   - `docs/task-design.md`
   - `docs/task-rules/<domain>.md`
3. Inspect existing tasks in `datasets/<dataset-name>/`, especially tasks with
   the same difficulty or environment class.
4. For Kubernetes Core v1 easy tasks, inspect
   `datasets/kubernetes-core/debug-service-endpoints` as the current local
   cluster reference pattern.

Derive `<domain>` from the dataset name:

- `kubernetes-core` -> `kubernetes`
- `terraform-core` -> `terraform`
- `observability-core` -> `observability`

If `docs/task-rules/<domain>.md` does not exist, stop and report that the
domain rules must be written before implementation.

## Implementation Contract

Before editing files, restate the contract in a short plan:

- Dataset and task directory.
- Harbor task name.
- Difficulty and primary coverage keyword.
- Environment class.
- Broken starting state.
- Intended operator outcome.
- Shortcut fixes the verifier must reject.
- Validation commands that will be run.

## Workflow

1. Work on one task issue only.
   - Use a dedicated branch or worktree when practical.
   - Do not include unrelated cleanup or framework work.

2. Create the Harbor task shape:

   ```text
   datasets/<dataset-name>/<task-name>/
   |-- instruction.md
   |-- task.toml
   |-- environment/
   |-- solution/
   |   `-- solve.sh
   `-- tests/
       `-- test.sh
   ```

3. Generate a fresh canary:

   ```bash
   python3 -c 'import uuid; print(f"<infra-bench-canary: {uuid.uuid4()}>")'
   ```

   Put the same full string in the first line of `instruction.md` and in
   `[metadata].canary` in `task.toml`.

4. Implement the broken starting state under `environment/`.
   - Do not copy `tests/`, `solution/`, or answer material into the image.
   - Use deterministic local assets instead of network fetches during
     verification.
   - Keep task-specific bootstrap and verifier logic task-local unless several
     implemented tasks prove shared code is worth adding.
   - For live-cluster tasks, do not copy bootstrap scripts or bootstrap
     manifests that reveal the answer into the agent image or `/app`; keep them
     in the bootstrap image and bootstrap-only mounts.

5. Write `instruction.md`.
   - State the working directory.
   - State the live outcome the operator must achieve.
   - State constraints and out-of-scope changes.
   - Do not reveal exact verifier assertions.

6. Write the verifier before tuning the oracle.
   - Verify behavior or semantic state, not formatting.
   - Write `/logs/verifier/reward.txt` or `/logs/verifier/reward.json`.
   - Dump useful debug output under `/logs/verifier` on failure.
   - Reject shortcut fixes described in the issue or implementation contract.

7. Write `solution/solve.sh`.
   - Keep it deterministic and boring.
   - It should prove the task is solvable from a clean environment.
   - It should not rely on hidden files or verifier internals.

8. Refresh the dataset manifest only after the task works locally.

9. Update the GitHub issue or PR with the actual validation results. Do not
   mark the issue complete until oracle validation passes.

## Kubernetes Core v1 Easy Rules

For easy Kubernetes tasks, prefer `local_cluster` unless the issue explicitly
requires otherwise. The task should prove a live `kubectl` diagnosis of one
clear broken relationship.

Local-cluster tasks should use separate cluster credentials:

- Keep the admin kubeconfig available only to bootstrap and verifier paths.
- Generate a least-privilege ServiceAccount kubeconfig for the agent.
- Mount the agent kubeconfig read-only into the main agent container.
- Grant only the read verbs needed for diagnosis and the write verbs needed for
  the intended fix.
- Do not let the agent mutate verifier-trusted baseline data, such as a
  ConfigMap that stores original resource UIDs.
- Use separate task-local images: `environment/Dockerfile` for the agent,
  solution, and verifier runtime, and `environment/Dockerfile.bootstrap` for the
  bootstrap service. Do not copy `bootstrap-cluster` into the agent image.

The verifier should usually check:

- Original resource UIDs for resources that must not be replaced.
- Runtime behavior, such as ready pods, endpoints, successful requests, or
  authorization success.
- Critical fields that must not change, such as images, ports, selectors,
  replica counts, ServiceAccounts, and policy boundaries.
- Absence of replacement workloads, replacement Services, cluster restarts, or
  broad privilege/policy bypasses.
- Unexpected workload kinds beyond Deployments, including StatefulSets,
  DaemonSets, Jobs, CronJobs, standalone Pods, and stray ReplicaSets.
- Ownership relationships, such as Pods owned by ReplicaSets and ReplicaSets
  owned by the intended Deployment.

Use the smallest local-cluster structure that fits the task:

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

Keep Docker Compose focused on orchestration. Put cluster bootstrap logic in
`environment/scripts/` and syntax-check those scripts.

Run a bypass review before final validation:

- Can the agent mutate verifier baseline data?
- Can the agent delete and recreate the target resource and still pass?
- Can the agent create alternate workloads, Services, or standalone Pods?
- Can the agent read bootstrap scripts or assets that reveal the answer?
- Does the verifier check ownership relationships, not just counts?

For current k3s sidecar tasks, keep `allow_internet = true` unless an oracle run
proves the agent can still reach the cluster with it disabled. This is a Harbor
Docker networking constraint, not permission to rely on external services.

## Guardrails

- Do not redesign the approved scenario while implementing it.
- Do not implement multiple task issues in one change.
- Do not make Kubernetes Core v1 easy tasks static-only unless the issue says
  so.
- Do not weaken verifier assertions just to make the oracle pass.
- Do not put tests, solutions, or hidden answer material in `environment/`.
- Do not delete and recreate resources when the task is meant to preserve
  identity.
- Do not add shared frameworks, dashboards, services, or CLIs for task
  implementation.

## Validation

Run checks in this order when the relevant files exist:

```bash
bash -n datasets/<dataset-name>/<task-name>/environment/scripts/*
bash -n datasets/<dataset-name>/<task-name>/tests/*.sh
bash -n datasets/<dataset-name>/<task-name>/solution/solve.sh
./scripts/validate-structure.sh
uvx --from harbor harbor sync datasets/<dataset-name>
uvx --from harbor harbor run -p datasets/<dataset-name>/<task-name> -a oracle
```

For live Kubernetes tasks, run at least one real-agent trial before publishing
when feasible:

```bash
uvx --from harbor harbor run \
  -p datasets/<dataset-name>/<task-name> \
  -a codex \
  -m gpt-5.3-codex
```

If a command cannot be run, report the reason and the remaining risk.
