---
name: design-infra-task
description: Design a new infra-bench task for a specific dataset. Use when asked to propose, plan, outline, or prepare a Harbor-compatible benchmark task for datasets such as kubernetes-core, terraform-core, or future infra-bench datasets, especially when the task must follow dataset-specific rules from docs/task-rules.
---

# Design Infra Task

Use this skill to design, not implement, an `infra-bench` task unless the user
explicitly asks for file creation.

## Workflow

1. Identify the target dataset.
   - Accept names like `kubernetes-core`, `kubeply/kubernetes-core`, or
     `datasets/kubernetes-core`.
   - If the dataset is ambiguous, ask one concise question.

2. Read the required repo docs before proposing the task:
   - `datasets/<dataset-name>/dataset.toml`
   - `docs/conventions.md`
   - `docs/harbor.md`
   - `docs/task-design.md`
   - `docs/task-rules/<domain>.md`

3. Derive `<domain>` from the dataset name.
   - `kubernetes-core` -> `kubernetes`
   - `terraform-core` -> `terraform`
   - `observability-core` -> `observability`

4. If `docs/task-rules/<domain>.md` does not exist, stop and report the gap.
   Propose creating the domain rule document before designing tasks for that
   dataset. Do not invent undocumented task rules.

5. Inspect existing tasks in `datasets/<dataset-name>/` to avoid duplicate task
   names, repeated scenarios, or misleading difficulty counts.

6. Produce a task design brief.

## Task Design Brief

Include these fields:

- Dataset: `kubeply/<dataset-name>`
- Proposed task directory: `datasets/<dataset-name>/<task-name>`
- Harbor task name: `kubeply/<task-name>`
- Difficulty: `easy`, `medium`, or `hard`
- Task category and keywords
- Operator story: one sentence
- Scenario type
- Environment class
- Broken starting state
- Agent-facing instruction outline
- Expected solution approach
- Verifier strategy
- Oracle solution strategy
- Required metadata, including `canary`
- Validation commands

For Kubernetes `local_cluster` task designs, specify the two-image environment
shape: `environment/Dockerfile` for the agent, solution, and verifier runtime,
and `environment/Dockerfile.bootstrap` for bootstrap-only setup code and
fixtures. Bootstrap manifests and scripts must not be present in the agent
image unless they are intentionally part of the task.

For Kubernetes medium task designs, require a bounded diagnosis across at least
two related Kubernetes concepts, such as workload plus Service, ConfigMap,
Secret, RBAC, NetworkPolicy, storage, Job, or controller-generated state. Keep
the outcome focused on one operator goal and identify the shortcut fixes the
verifier must reject. Use `docs/templates/kubernetes-local-cluster-task/` as the
starting environment shape for live-cluster medium and hard tasks.

## Canary Requirement

Every published task must include the same canary string in two places:

- First line of `instruction.md`
- `[metadata].canary` in `task.toml`

Generate the canary with:

```bash
python3 -c 'import uuid; print(f"<infra-bench-canary: {uuid.uuid4()}>")'
```

Do not reuse canaries across tasks.

## Validation

For a designed task, list the checks that must pass once implemented:

```bash
./scripts/validate-structure.sh
python3 scripts/lint-kubernetes-rbac.py
uvx --from harbor harbor sync datasets/<dataset-name>
uvx --from harbor harbor run -p datasets/<dataset-name>/<task-name> -a oracle
```

Only include the oracle run when a task implementation exists.
