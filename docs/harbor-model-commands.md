# Harbor Model Commands

Use these commands from the repository root. Replace the placeholder values
before running.

## Generic Task Run

```bash
uvx --from harbor harbor run \
  --job-name <job-name> \
  -p <dataset-path> \
  -a <agent-name> \
  -m <model-name> \
  -e docker \
  -n <parallel-task-count> \
  -y \
  --max-retries 0
```

Examples of common placeholders:

| Placeholder | Example |
| --- | --- |
| `<job-name>` | `kubernetes-core-codex-gpt-5-5-high` |
| `<dataset-path>` | `datasets/kubernetes-core` |
| `<agent-name>` | `codex` |
| `<model-name>` | `gpt-5.5` |
| `<parallel-task-count>` | `1` to run tasks one at a time |
| `<task-name>` | `fix-crashloop-env-var` |

Without `-i <task-name>`, Harbor runs the full dataset. Add `-i <task-name>` to
run only one selected task.

For repeated local `kubernetes-core` runs, configure Docker Hub registry
authentication first. See [k3s registry authentication](k3s-registry-auth.md).

## Codex

Run the full Kubernetes dataset with GPT-5.5 high reasoning, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-codex-gpt-5-5-high \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=high \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run the full Kubernetes dataset with GPT-5.5 medium reasoning, one task at a
time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-codex-gpt-5-5-medium \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=medium \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single Codex task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-codex-gpt-5-5-high-<task-name> \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=high \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

## Gemini CLI

Gemini CLI must be trusted and allowed to approve tool calls. Without these
agent settings, Harbor runs can fail with `NonZeroAgentExitCodeError`.

Run Gemini 3 Flash Preview on the full Kubernetes dataset, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-gemini-3-flash-preview \
  -p datasets/kubernetes-core \
  -a gemini-cli \
  -m google/gemini-3-flash-preview \
  --ae GEMINI_CLI_TRUST_WORKSPACE=true \
  --ak approval_mode=yolo \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single Gemini task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-gemini-3-flash-preview-<task-name> \
  -p datasets/kubernetes-core \
  -a gemini-cli \
  -m google/gemini-3-flash-preview \
  --ae GEMINI_CLI_TRUST_WORKSPACE=true \
  --ak approval_mode=yolo \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

If the installed Harbor/Gemini adapter expects a different approval key, use
`--ak yolo=true` instead of `--ak approval_mode=yolo`.

## Oracle

Use the oracle agent to sanity-check a task against its reference solution:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-oracle-<task-name> \
  -p datasets/kubernetes-core \
  -a oracle \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```
