# Datasets

Datasets are the public benchmark units. Each dataset should be small enough to
understand, run, and version deliberately.

## Current Datasets

| Dataset | Path | Purpose |
| --- | --- | --- |
| `kubeply/kubernetes-core` | `datasets/kubernetes-core` | Initial Kubernetes benchmark tasks. |

## Adding a Task

1. Create or initialize a task inside the dataset directory:

   ```bash
   uvx --from harbor harbor init \
     --task kubeply/<task-name> \
     --output-dir datasets/kubernetes-core \
     --include-standard-metadata
   ```

2. Implement `instruction.md`, `environment/`, `solution/solve.sh`, and
   `tests/test.sh`.

3. Add or refresh the task in the dataset manifest:

   ```bash
   cd datasets/kubernetes-core
   uvx --from harbor harbor add ./<task-name>
   uvx --from harbor harbor sync
   ```

4. Run the oracle solution when feasible:

   ```bash
   uvx --from harbor harbor run -p datasets/kubernetes-core/<task-name> -a oracle
   ```

## Versioning

Publish dataset versions intentionally. A task behavior change should produce a
new dataset tag so prior evaluation results remain interpretable.

Suggested early tags:

- `v0.1`: first public seed dataset.
- `v0.2`: next compatible expansion.

Avoid publishing moving benchmark definitions as if they were stable releases.
