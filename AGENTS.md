# AGENTS.md

Guidance for AI agents and contributors working in this repository.

## Mission

Keep `infra-bench` focused on infrastructure and platform engineering
benchmarks for AI agents. The first task scope is Kubernetes, but the repository
should stay open to other infrastructure domains when they fit the same
benchmark shape.

Optimize for realistic task design, reproducible evaluation, and compatibility
with Kubeply benchmark conventions and Harbor task formats over framework
growth.

## Non-Goals

- Do not add a benchmark platform, service, dashboard, or product CLI.
- Do not turn this into a generic DevOps benchmark zoo.
- Do not add broad framework abstractions before multiple tasks prove the need.
- Do not hide task-specific verifier logic in shared code unless duplication is
  already meaningful.

## Harbor Task Rules

Every published task must keep the Harbor task shape:

```text
task-name/
|-- instruction.md
|-- task.toml
|-- environment/
|-- solution/
|   `-- solve.sh
`-- tests/
    `-- test.sh
```

Rules:

- `instruction.md` is the only task prompt shown to the agent.
- `task.toml` must include `[task]` with a globally unique `kubeply/<name>`.
- `environment/` is the build context. Do not copy `tests/`, `solution/`, or
  answer material into the image.
- `solution/solve.sh` must solve the task for the Harbor oracle agent.
- `tests/test.sh` must write `/logs/verifier/reward.txt` or
  `/logs/verifier/reward.json`.
- Tests should use absolute paths such as `/app`, `/tests`, and
  `/logs/verifier`.

## Domain Task Rules

Keep documentation updates in `docs/` instead of expanding this file with
domain-specific guidance.

Current docs:

```text
docs/
|-- conventions.md
|-- datasets.md
|-- harbor.md
|-- project.md
|-- specs/
|   |-- README.md
|   `-- benchmark-results-publishing.md
|-- task-design.md
`-- task-rules/
    |-- README.md
    `-- kubernetes.md
```

## Commit Messages

Use Conventional Commits for all commits. Prefer scopes that match the area
being changed, such as `feat(kubernetes-core): ...`, `fix(kubernetes-core): ...`,
`chore(deps): ...`, or `docs: ...`.

## Validation

Before considering a change complete:

```bash
./scripts/validate-structure.sh
uvx --from harbor harbor sync datasets/kubernetes-core
uvx --from harbor harbor sync datasets/terraform-core
```

When feasible, run the changed task with the oracle agent:

```bash
uvx --from harbor harbor run -p datasets/<dataset>/<task> -a oracle
```
