# Datasets

Datasets are the public benchmark units. Each dataset should be small enough to
understand, run, and version deliberately.

## Current Datasets

| Dataset | Path | Purpose |
| --- | --- | --- |
| `kubeply/kubernetes-core` | `datasets/kubernetes-core` | Kubernetes operator benchmark tasks. |
| `kubeply/terraform-core` | `datasets/terraform-core` | Terraform infrastructure-as-code benchmark tasks. |

## Planning Tasks

Before implementing a new task, decide how it fits the dataset plan.

1. Confirm the dataset release or difficulty plan already has room for the
   scenario and that the intended outcome does not duplicate another task.
2. Write a task design brief before implementation starts. The design brief
   should capture the operator story, broken starting state, hidden diagnosis,
   expected solution shape, verifier strategy, oracle strategy, metadata, and
   validation commands.
3. Track the scenario in its own issue and connect it to the relevant planning
   issue as a GitHub sub-issue.
4. Label the scenario issue with:
   - the release label, such as `v1`
   - the difficulty label, such as `easy`, `medium`, or `hard`
   - one dataset-specific coverage-area label, such as `area:service-routing`

Implementation should follow the issue-backed design brief, not invent the task
shape on the fly.

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
