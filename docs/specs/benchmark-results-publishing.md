# Benchmark Results Publishing

## Status

Proposed.

## Context

`infra-bench` tasks are executed with Harbor. Harbor writes local job output,
including task results, logs, verifier output, and run metadata. Kubeply needs a
repeatable way to turn those local job folders into benchmark data that can be
shown on the public marketing website.

The marketing site is deployed on Cloudflare Workers. The publishing path should
therefore fit Cloudflare-hosted reads, but `infra-bench` should remain focused
on benchmark datasets and result artifacts rather than becoming a hosted
benchmark platform.

## Goals

- Preserve raw benchmark evidence from Harbor runs.
- Publish compact, stable result summaries that the marketing site can render.
- Make each public result traceable to the exact `infra-bench` commit and
  dataset/task definitions used during the run.
- Support model comparisons by dataset, task, difficulty, provider, run date,
  score, duration, and cost when available.
- Keep the first implementation simple enough to run after local or CI Harbor
  jobs.

## Non-Goals

- Do not build a hosted benchmark runner in `infra-bench`.
- Do not add a product dashboard or API service to this repository.
- Do not store raw logs, traces, or job archives in a SQL database.
- Do not publish secret-bearing prompts, credentials, provider request payloads,
  or private environment details.

## Proposed Architecture

Use Cloudflare R2 as durable artifact storage and Cloudflare D1 as a queryable
metadata index.

```text
Harbor runner
  -> local jobs/
  -> result normalizer
  -> R2 raw artifacts and JSON summaries
  -> D1 run, task, model, and score rows
  -> marketing site benchmark page
```

R2 stores immutable evidence:

- original Harbor job archive
- normalized `run.json`
- normalized `results.json`
- verifier outputs
- selected logs that are safe to publish
- precomputed `summary.json` files for static or cached reads

D1 stores compact query data:

- run identity and timestamps
- dataset and task identity
- model and agent harness identity
- pass/fail, reward, and score
- duration and cost metrics when available
- R2 object keys for evidence and summaries

The marketing site should query D1 for tables, filters, and comparisons. It may
read summary JSON from R2 for simple initial pages or cached aggregate payloads.

## Result Identity

Every uploaded run must have a stable `run_id`. The recommended format is:

```text
<utc-timestamp>-<dataset>-<model-slug>-<short-commit>
```

Example:

```text
2026-04-26T120000Z-kubernetes-core-openai-o4-mini-9fe586c
```

Each task result inside a run is identified by:

```text
<run_id>/<task_name>
```

Task names must use the Harbor task name, such as
`kubeply/restore-multi-hop-checkout-route`.

## R2 Object Layout

Use immutable run-scoped paths for evidence and mutable alias paths only for
latest summaries.

```text
benchmarks/runs/<run_id>/run.json
benchmarks/runs/<run_id>/results.json
benchmarks/runs/<run_id>/artifacts.tar.zst
benchmarks/runs/<run_id>/logs/<task-slug>/verifier.log
benchmarks/runs/<run_id>/logs/<task-slug>/agent.log
benchmarks/latest/<dataset>.json
benchmarks/latest/<dataset>/<model-slug>.json
```

Mutable `latest` objects must be derived from immutable run objects. They are a
cache and must not be treated as the source of truth.

## Normalized Run Schema

`run.json` describes the benchmark run as a whole.

```json
{
  "schema_version": "1.0",
  "run_id": "2026-04-26T120000Z-kubernetes-core-openai-o4-mini-9fe586c",
  "dataset": "kubeply/kubernetes-core",
  "dataset_path": "datasets/kubernetes-core",
  "infra_bench_commit": "9fe586c...",
  "harbor_version": "x.y.z",
  "agent_harness": "harbor",
  "model": {
    "provider": "openai",
    "name": "o4-mini",
    "version": null
  },
  "started_at": "2026-04-26T12:00:00Z",
  "finished_at": "2026-04-26T13:10:00Z",
  "summary": {
    "task_count": 58,
    "passed": 41,
    "failed": 17,
    "score": 0.7069,
    "duration_sec": 4200,
    "cost_usd": null
  },
  "artifacts": {
    "run": "benchmarks/runs/<run_id>/run.json",
    "results": "benchmarks/runs/<run_id>/results.json",
    "archive": "benchmarks/runs/<run_id>/artifacts.tar.zst"
  }
}
```

`results.json` contains one row per task.

```json
{
  "schema_version": "1.0",
  "run_id": "2026-04-26T120000Z-kubernetes-core-openai-o4-mini-9fe586c",
  "results": [
    {
      "task_name": "kubeply/restore-multi-hop-checkout-route",
      "task_slug": "restore-multi-hop-checkout-route",
      "difficulty": "hard",
      "category": "kubernetes",
      "keywords": ["service-routing", "ingress", "networking"],
      "passed": true,
      "reward": 1.0,
      "score": 1.0,
      "duration_sec": 312,
      "cost_usd": null,
      "started_at": "2026-04-26T12:04:00Z",
      "finished_at": "2026-04-26T12:09:12Z",
      "verifier_artifact_key": "benchmarks/runs/<run_id>/logs/restore-multi-hop-checkout-route/verifier.log",
      "agent_artifact_key": "benchmarks/runs/<run_id>/logs/restore-multi-hop-checkout-route/agent.log"
    }
  ]
}
```

Missing optional values should be represented as `null`, not omitted.

## D1 Data Model

The initial D1 schema should stay intentionally small.

```sql
CREATE TABLE benchmark_runs (
  run_id TEXT PRIMARY KEY,
  dataset TEXT NOT NULL,
  infra_bench_commit TEXT NOT NULL,
  harbor_version TEXT,
  agent_harness TEXT NOT NULL,
  model_provider TEXT NOT NULL,
  model_name TEXT NOT NULL,
  model_version TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  task_count INTEGER NOT NULL,
  passed INTEGER NOT NULL,
  failed INTEGER NOT NULL,
  score REAL NOT NULL,
  duration_sec REAL,
  cost_usd REAL,
  run_artifact_key TEXT NOT NULL,
  results_artifact_key TEXT NOT NULL,
  archive_artifact_key TEXT
);

CREATE TABLE benchmark_task_results (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES benchmark_runs(run_id),
  task_name TEXT NOT NULL,
  task_slug TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  category TEXT NOT NULL,
  passed INTEGER NOT NULL,
  reward REAL NOT NULL,
  score REAL NOT NULL,
  duration_sec REAL,
  cost_usd REAL,
  started_at TEXT,
  finished_at TEXT,
  verifier_artifact_key TEXT,
  agent_artifact_key TEXT
);

CREATE INDEX idx_benchmark_task_results_run_id
  ON benchmark_task_results(run_id);

CREATE INDEX idx_benchmark_task_results_task_name
  ON benchmark_task_results(task_name);

CREATE INDEX idx_benchmark_task_results_difficulty
  ON benchmark_task_results(difficulty);

CREATE INDEX idx_benchmark_runs_model
  ON benchmark_runs(model_provider, model_name);
```

Task keywords may remain in R2 JSON for the first implementation. Add a separate
keyword table only when the marketing page needs keyword filtering.

## Uploader Contract

The uploader should be a small script or command that runs after Harbor
completes. It should:

1. Accept a Harbor job directory path.
2. Accept required run metadata that Harbor may not know, including model
   provider, model name, model version, and cost if available.
3. Read task metadata from the checked-out dataset files.
4. Produce `run.json` and `results.json`.
5. Validate the normalized JSON against the schema version.
6. Upload immutable artifacts to R2.
7. Insert or upsert compact rows into D1.
8. Recompute the relevant `benchmarks/latest/*.json` summaries.

The uploader must fail closed if required metadata is missing. It should never
guess the model, dataset commit, or task difficulty from artifact names alone.

## Public Data Rules

Before upload, the normalizer must redact or exclude:

- provider API keys and credentials
- kubeconfigs or cluster tokens
- environment variables that are not explicitly allowlisted
- private request/response payloads
- unrelated local filesystem paths
- unpublished solution files or verifier internals that would weaken future
  benchmark integrity

Public artifacts should favor verifier summaries and high-level logs over raw
agent transcripts until transcript publication rules are defined.

## Marketing Site Contract

The marketing website owns presentation. `infra-bench` owns benchmark data
contracts.

The first `/benchmarks` page should be able to render:

- latest run per model and dataset
- pass rate by difficulty
- task-level table for a selected model/run
- run metadata with commit SHA and timestamp
- links to safe public artifacts

The page should not need to know Harbor's original local job folder layout. It
should consume only normalized D1 rows and R2 JSON summaries.

## Implementation Plan

1. Add normalized JSON schema files for benchmark runs and task results.
2. Add a local normalizer that reads Harbor job folders and emits JSON without
   uploading.
3. Add fixture-based tests for normalizer behavior.
4. Add an R2 upload mode gated by explicit Cloudflare credentials.
5. Add a D1 write mode gated by explicit Cloudflare credentials.
6. Add a dry-run command for CI validation.
7. Add marketing repository bindings and a `/benchmarks` page that reads the
   normalized data contract.

## Acceptance Criteria

- A Harbor job folder can be converted into `run.json` and `results.json`.
- The normalized output records `infra_bench_commit`, dataset, task, difficulty,
  model, score, duration, and artifact keys.
- Raw bulky artifacts are stored in R2, not D1.
- D1 stores only compact queryable metadata and per-task result rows.
- The marketing site can render benchmark tables without parsing Harbor job
  directories.
- Publishing can be run locally in dry-run mode without Cloudflare credentials.
- Upload mode refuses to publish when required metadata is missing.
