# Project

`infra-bench` is an open benchmark repository for real-world infrastructure and
platform engineering tasks for AI agents.

## Goals

- Publish realistic infrastructure and platform engineering tasks.
- Compare agent and model performance on the same task set.
- Learn which platform tasks are actually hard for agents.
- Keep task definitions compatible with Kubeply benchmark conventions and
  Harbor task formats.

## Initial Scope

- Kubernetes is the first task scope.
- Harbor-compatible.
- Small and opinionated.
- Task and evaluation focused.
- Open source under Apache License 2.0.

## Non-Goals

- A full benchmark platform.
- A productized CLI.
- A hosted leaderboard.
- A giant generic DevOps benchmark zoo.
- A wrapper around every possible infrastructure tool.

## Design Bias

Tasks should feel like real platform work: diagnose a broken state, make a
minimal change, and leave the system in a verifiably correct condition.

Prefer a small number of high-signal tasks over a large catalog of shallow
examples.

## Planning Workflow

Plan dataset releases deliberately instead of adding benchmark tasks ad hoc.

- Define scenario sets before implementation starts, especially when planning a
  new dataset version or a new difficulty tier.
- Use one planning issue per dataset release and difficulty tier so the intended
  task matrix is visible before implementation begins.
- Track each approved scenario in its own issue with a task design brief before
  opening implementation PRs.
- Label task-planning issues with the release label, the difficulty label, and
  one dataset-specific coverage-area label such as `area:service-routing`.
- Attach scenario issues as sub-issues of the relevant planning issue so GitHub
  reflects the intended hierarchy.

Keep this planning workflow repository-wide. Domain-specific difficulty
calibration and authoring rules still belong in `docs/task-rules/<domain>.md`.

Use `docs/specs/` for repository-level workflow changes and cross-repository
contracts that are broader than one benchmark task design brief.
