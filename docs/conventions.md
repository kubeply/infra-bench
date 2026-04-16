# Conventions

## Naming

- Dataset directories use kebab case: `kubernetes-core`.
- Task directories use action-oriented kebab case:
  `repair-workload-rollout`.
- Harbor task names use the `kubeply/<task-name>` namespace.
- Dataset names use `kubeply/<dataset-name>`.

## Metadata

Every `task.toml` should include:

- `canary`: same full string as the first line of `instruction.md`, formatted
  as `<infra-bench-canary: UUID>`.
- `difficulty`: one of `easy`, `medium`, `hard`.
- `category`: broad area, starting with `kubernetes`.
- `tags`: focused labels such as `manifests`, `service`, `rbac`, `storage`.
- `expert_time_estimate_min` and `junior_time_estimate_min`.

Prefer task-specific metadata when it clarifies evaluation:

- `scenario_type`: `manifest_repair`, `live_cluster_debug`,
  `policy_authoring`, `incident_response`, or similar.
- `requires_cluster`: `true` or `false`.
- `kubernetes_focus`: short topic name.

## Difficulty

Use difficulty to describe expected operator complexity, not line count.

- `easy`: one concept, clear failure mode, low ambiguity.
- `medium`: multiple related concepts or moderate diagnosis.
- `hard`: layered failure, ambiguous symptoms, or multi-step validation.

## Instructions

The first line of `instruction.md` must be the task canary:

```md
<infra-bench-canary: UUID>
```

Generate it with:

```bash
python3 -c 'import uuid; print(f"<infra-bench-canary: {uuid.uuid4()}>")'
```

After the canary, `instruction.md` should tell the agent:

- The working directory.
- The user-visible goal.
- Explicit constraints.
- What is out of scope.
- How success will be evaluated at a high level.

Do not reveal verifier internals or exact assertions.

## Environment

- Put starting state under `environment/`.
- Keep the Docker build context minimal.
- Do not copy tests, solutions, or hidden answers into the environment image.
- Prefer deterministic local assets over network calls at verification time.

## Verification

- `tests/test.sh` must write a Harbor reward file.
- Verifiers should check behavior or resource semantics, not exact formatting.
- Use absolute paths in verifier scripts.
- Store useful logs under `/logs/verifier`.
- A passing task should score `1`; a failing task should score `0`.

## Solutions

`solution/solve.sh` should be boring and deterministic. It exists to sanity
check the task, not to demonstrate the best human workflow.

## Documentation Updates

- Update this file when adding a new repository-wide task convention.
- Update `docs/task-rules/<domain>.md` when adding or changing rules for a
  specific task domain.
- Update the relevant dataset documentation and manifest when adding tasks to a
  dataset.
