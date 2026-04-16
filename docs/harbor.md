# Harbor Compatibility

This repository follows the Harbor task and dataset format.

Reference docs:

- [Harbor task structure](https://www.harborframework.com/docs/tasks)
- [Harbor task differences from Terminal-Bench](https://www.harborframework.com/docs/tasks/task-difference)
- [Harbor dataset publishing](https://www.harborframework.com/docs/datasets/publishing)
- [Harbor dataset metrics](https://www.harborframework.com/docs/datasets/metrics)

## Task Shape

A task directory must include:

```text
instruction.md
task.toml
environment/
solution/solve.sh
tests/test.sh
```

Harbor copies `solution/` to `/solution` for the oracle agent and `tests/` to
`/tests` for verification. The verifier must write a reward file under
`/logs/verifier`.

Accepted reward outputs:

- `/logs/verifier/reward.txt` with a numeric value such as `1` or `0`.
- `/logs/verifier/reward.json` with numeric metrics.

## Dataset Shape

Datasets live under `datasets/<dataset-name>/` and contain a `dataset.toml`
manifest. Local tasks can live next to that manifest so Harbor can refresh their
digests during publish.

Current dataset:

```text
datasets/kubernetes-core/
|-- dataset.toml
`-- metric.py
```

## Common Commands

Run a local dataset with the oracle solution:

```bash
uvx --from harbor harbor run -p datasets/kubernetes-core -a oracle
```

Run a single local task once tasks exist:

```bash
uvx --from harbor harbor run \
  -p datasets/kubernetes-core/<task-name> \
  -a oracle
```

Refresh dataset digests:

```bash
uvx --from harbor harbor sync datasets/kubernetes-core
```

Publish publicly when ready:

```bash
uvx --from harbor harbor publish datasets/kubernetes-core --public -t v0.1
```
