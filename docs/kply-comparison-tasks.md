# kply Comparison Tasks

`kubernetes-core` includes a paired benchmark for comparing direct `kubectl`
production changes with a bounded `kply` sandbox workflow.

## Task Pair

- `kubeply/raw-rollout-checkout-release`: asks the agent to roll release `v2`
  directly onto the production `checkout-api` Deployment.
- `kubeply/kply-sandbox-checkout-release`: asks the agent to use the local
  benchmark `kply` shim to create a sandbox release session while production
  stays on release `v1`.

Both tasks use the same neutral namespace, app shape, and candidate release. The
verifiers measure different operational boundaries:

- the raw task succeeds only when production serves `v2` through the original
  Service without replacement resources;
- the bounded task succeeds only when the sandbox serves `v2`, the session
  metadata exists, and production still serves `v1`.

The `kply` command in the bounded task is a benchmark-local shim. It exists to
make the comparison runnable before the open-source CLI is distributed inside
Harbor task images.

## Example Runs

```bash
uvx --from harbor harbor run \
  --job-name raw-rollout-checkout-release \
  -p datasets/kubernetes-core \
  -a <agent-name> \
  -m <model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i raw-rollout-checkout-release
```

```bash
uvx --from harbor harbor run \
  --job-name kply-sandbox-checkout-release \
  -p datasets/kubernetes-core \
  -a <agent-name> \
  -m <model-name> \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i kply-sandbox-checkout-release
```
