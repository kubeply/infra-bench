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

For Docker environments, the agent `Dockerfile` should copy only the files the
agent is meant to see into `/app`. For local-cluster Kubernetes tasks, keep
bootstrap-only assets and scripts out of the agent image; expose them through a
separate bootstrap image or bootstrap-only mounts.

## 4. Generate the Canary

Run:

```bash
python3 -c 'import uuid; print(f"<infra-bench-canary: {uuid.uuid4()}>")'
```

Add the generated canary as the first line of `instruction.md` and store the
same full string in `[metadata].canary` in `task.toml`.

## 5. Write the Instruction

Keep the prompt direct:

- Current working directory.
- Desired end state.
- Constraints.
- What the agent may edit.
- What not to do.

Do not describe exact verifier assertions.

## 6. Write the Verifier

The verifier should answer: did the operator outcome happen?

For most tasks, `tests/test.sh` can run a Python script and map exit code to
`/logs/verifier/reward.txt`.

## 7. Write the Oracle Solution

`solution/solve.sh` should pass the verifier from a clean task environment.
Keep it deterministic and short.

## 8. Refresh the Dataset

Run:

```bash
./scripts/validate-structure.sh
cd datasets/<dataset-name>
uvx --from harbor harbor add ./<task-name>
uvx --from harbor harbor sync
```
