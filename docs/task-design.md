# Task Design

Use this workflow when adding a new scenario.

## 1. Define the Operator Story

Write one sentence:

> A platform engineer needs to ... because ...

The task should be realistic without requiring a long backstory.

## 2. Choose the Environment Class

Start with the smallest viable class:

- `static_manifest` for manifest semantics.
- `local_cluster` for runtime Kubernetes behavior.
- `remote_sandbox` only when external platform behavior is central.

Document the class in `task.toml` metadata.

## 3. Create the Broken Starting State

Place all starting files under `environment/`. The agent should only need files
available in the runtime environment.

For Docker environments, the Dockerfile should copy starting assets into `/app`.

## 4. Write the Instruction

Keep the prompt direct:

- Current working directory.
- Desired end state.
- Constraints.
- What the agent may edit.
- What not to do.

Do not describe exact verifier assertions.

## 5. Write the Verifier

The verifier should answer: did the operator outcome happen?

For most tasks, `tests/test.sh` can run a Python script and map exit code to
`/logs/verifier/reward.txt`.

## 6. Write the Oracle Solution

`solution/solve.sh` should pass the verifier from a clean task environment.
Keep it deterministic and short.

## 7. Refresh the Dataset

Run:

```bash
./scripts/validate-structure.sh
cd datasets/kubernetes-core
uvx --from harbor harbor add ./<task-name>
uvx --from harbor harbor sync
```
