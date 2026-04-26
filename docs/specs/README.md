# Specs

Specs capture planned repository-level changes before implementation starts.
They are lighter than task design briefs and should focus on behavior,
contracts, storage shape, and rollout steps that affect more than one benchmark
task.

Use specs when a change introduces a new workflow, public contract, or
cross-repository integration. Keep implementation details concrete enough that
future issues and pull requests can be reviewed against the same expected
behavior.

Current specs:

| Spec | Purpose |
| --- | --- |
| [Benchmark Results Publishing](benchmark-results-publishing.md) | Defines how Harbor benchmark runs become durable public benchmark data for the marketing site. |

## Local Normalization

Use the benchmark result normalizer to turn a local Harbor job directory into
the public JSON contract:

```bash
scripts/normalize-benchmark-run.py \
  --job-dir jobs/<job-name> \
  --dataset-path datasets/kubernetes-core \
  --model-provider openai \
  --model-name o4-mini \
  --output-dir build/benchmark-results/<run-id>
```

Use `--dry-run` to validate and print the normalized JSON without writing files.
