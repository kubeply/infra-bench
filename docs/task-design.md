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

For Kubernetes cluster state, choose neutral namespace names. Namespaces should
look like plausible team, tenant, or application boundaries, not the task slug,
failure mode, intended fix, or benchmark coverage area.

## 4. Generate the Canary

Run:

```bash
python3 -c 'import uuid; dataset="kubernetes-core"; print(f"<!-- {dataset} GUID {uuid.uuid4()} -->")'
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

For Kubernetes prompts, do not use namespace names that reveal the issue; keep
them consistent with the neutral names in the starting cluster.

For medium and hard tasks, keep the agent-facing symptom intentionally sparse.
The prompt may state the user-visible failure, but should not name the suspected
root cause, exact Kubernetes concept, useful evidence source, or unrelated
healthy services. For example, prefer "Users report that checkout records are
failing" over "The billing API stopped becoming ready after database credential
rotation." Do not tell the agent which resources are noise; add realistic
distractor resources to the environment and let the agent decide what matters.

Review constraints for answer leakage. A constraint that names the exact field
or resource to change can make a medium task behave like an easy task. Prefer
policy-level constraints, then let the verifier enforce the hidden relationships
that matter.

## 6. Write the Verifier

The verifier should answer: did the operator outcome happen?

For most tasks, `tests/test.sh` can run a Python script and map exit code to
`/logs/verifier/reward.txt`.

Verifier logic may know the hidden diagnosis, but the task prompt should not.
Use the verifier to reject bypasses such as replacement resources, broad
privilege grants, disabled policies, or edits to verifier-trusted baselines.

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
