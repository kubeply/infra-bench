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

Use the benchmark result normalizer uv script to turn a local Harbor job
directory into the public JSON contract:

```bash
scripts/normalize-benchmark-run.py \
  --job-dir jobs/<job-name> \
  --dataset-path datasets/kubernetes-core \
  --model-provider openai \
  --model-name o4-mini \
  --output-dir build/benchmark-results/<run-id>
```

Use `--dry-run` to validate and print the normalized JSON without writing files.

The normalizer writes `run.json`, `results.json`, `summary.json`, public
per-task summaries, and `d1-upsert.sql`. Apply
`schemas/benchmark-results/d1.sql` before loading generated D1 upsert files.

## Publish Benchmark Results

Use this workflow after Harbor jobs finish and the normalized results should be
published to Cloudflare D1 and Cloudflare R2.

Set publish variables from the `infra-bench` repository root:

```bash
export D1_DB="<cloudflare-d1-database-name>"
export R2_BUCKET="<cloudflare-r2-bucket-name>"
export RUN_ID="<stable-run-id>"
export JOB_DIR="jobs/<harbor-job-name>"
export DATASET_PATH="datasets/<dataset-name>"
```

Normalize the Harbor job:

```bash
scripts/normalize-benchmark-run.py \
  --job-dir "$JOB_DIR" \
  --dataset-path "$DATASET_PATH" \
  --model-provider "<provider>" \
  --model-name "<model-name>" \
  --model-version "<model-version>" \
  --model-reasoning "<reasoning-effort>" \
  --agent-tool "<agent-tool>" \
  --run-id "$RUN_ID" \
  --output-dir "build/benchmark-results/$RUN_ID"
```

Upsert the compact query rows into remote D1:

```bash
wrangler d1 execute "$D1_DB" --remote --file "build/benchmark-results/$RUN_ID/d1-upsert.sql"
```

Upload the normalized JSON artifacts to remote R2:

```bash
scripts/upload-benchmark-r2.py \
  --output-dir "build/benchmark-results/$RUN_ID" \
  --bucket "$R2_BUCKET" \
  --remote
```

The D1 upserts use stable run ids, so rerunning this workflow replaces existing
rows for the same runs. R2 uploads use the same immutable run-scoped object keys
and are safe to rerun when normalized artifacts are corrected.
