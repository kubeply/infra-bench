# Datasets

Datasets are the public benchmark units. Each dataset should be small enough to
understand, run, and version deliberately.

## Current Datasets

| Dataset | Path | Purpose |
| --- | --- | --- |
| `kubeply/kubernetes-core` | `datasets/kubernetes-core` | Kubernetes operator benchmark tasks. |
| `kubeply/terraform-core` | `datasets/terraform-core` | Terraform infrastructure-as-code benchmark tasks. |

## Adding a Task

1. Choose the target dataset directory:

   ```text
   datasets/<dataset-name>
   ```

2. Create or initialize a task inside the dataset directory:

   ```bash
   uvx --from harbor harbor init \
     --task kubeply/<task-name> \
     --output-dir datasets/<dataset-name> \
     --include-standard-metadata
   ```

3. Implement `instruction.md`, `environment/`, `solution/solve.sh`, and
   `tests/test.sh`.

4. Add or refresh the task in the dataset manifest:

   ```bash
   cd datasets/<dataset-name>
   uvx --from harbor harbor add ./<task-name>
   uvx --from harbor harbor sync
   ```

5. Run the oracle solution when feasible:

   ```bash
   uvx --from harbor harbor run -p datasets/<dataset-name>/<task-name> -a oracle
   ```

## Versioning

Publish dataset versions intentionally. A task behavior change should produce a
new dataset tag so prior evaluation results remain interpretable.

Suggested early tags:

- `v0.1`: first public seed dataset.
- `v0.2`: next compatible expansion.

Avoid publishing moving benchmark definitions as if they were stable releases.
