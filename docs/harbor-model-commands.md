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

Common agent names:

| Agent | Harbor agent name |
| --- | --- |
| Codex | `codex` |
| Gemini CLI | `gemini-cli` |
| Claude Code | `claude-code` |
| OpenCode | `opencode` |
| Kimi CLI | `kimi-cli` |
| Mini SWE Agent | `mini-swe-agent` |

Recommended agents for non-default providers:

| Provider family | Recommended Harbor agent | Model format |
| --- | --- | --- |
| DeepSeek | `opencode` | `deepseek/<model-name>` |
| Mistral | `opencode` | `mistral/<model-name>` |
| Z.ai | `mini-swe-agent` | `zai/<model-name>` |
| Moonshot AI / Kimi K | `kimi-cli` | `moonshot/<model-name>` or `kimi/<model-name>` |

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

## Claude Code

Run Claude Code on the full Kubernetes dataset, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-claude-code-<model-name> \
  -p datasets/kubernetes-core \
  -a claude-code \
  -m <model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single Claude Code task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-claude-code-<model-name>-<task-name> \
  -p datasets/kubernetes-core \
  -a claude-code \
  -m <model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

## OpenCode

Use OpenCode for providers it supports directly, including DeepSeek and
Mistral.

Run the full Kubernetes dataset with OpenCode, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-opencode-<provider>-<model-name> \
  -p datasets/kubernetes-core \
  -a opencode \
  -m <provider>/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single OpenCode task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-opencode-<provider>-<model-name>-<task-name> \
  -p datasets/kubernetes-core \
  -a opencode \
  -m <provider>/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

## Kimi CLI

Use Kimi CLI for Moonshot AI and Kimi K models.

Run the full Kubernetes dataset with Kimi CLI, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-kimi-cli-<model-name> \
  -p datasets/kubernetes-core \
  -a kimi-cli \
  -m moonshot/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single Kimi CLI task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-kimi-cli-<model-name>-<task-name> \
  -p datasets/kubernetes-core \
  -a kimi-cli \
  -m moonshot/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

## Mini SWE Agent

Use Mini SWE Agent for LiteLLM-backed providers without a more specific Harbor
CLI adapter, including Z.ai.

Run the full Kubernetes dataset with Mini SWE Agent, one task at a time:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-mini-swe-agent-<provider>-<model-name> \
  -p datasets/kubernetes-core \
  -a mini-swe-agent \
  -m <provider>/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0
```

Run a single Mini SWE Agent task:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-mini-swe-agent-<provider>-<model-name>-<task-name> \
  -p datasets/kubernetes-core \
  -a mini-swe-agent \
  -m <provider>/<model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i <task-name>
```

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
