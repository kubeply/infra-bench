CREATE TABLE IF NOT EXISTS benchmark_runs (
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

CREATE TABLE IF NOT EXISTS benchmark_task_results (
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

CREATE INDEX IF NOT EXISTS idx_benchmark_task_results_run_id
  ON benchmark_task_results(run_id);

CREATE INDEX IF NOT EXISTS idx_benchmark_task_results_task_name
  ON benchmark_task_results(task_name);

CREATE INDEX IF NOT EXISTS idx_benchmark_task_results_difficulty
  ON benchmark_task_results(difficulty);

CREATE INDEX IF NOT EXISTS idx_benchmark_runs_model
  ON benchmark_runs(model_provider, model_name);
