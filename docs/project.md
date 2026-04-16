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
