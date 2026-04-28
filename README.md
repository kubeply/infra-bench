# infrabench

`infra-bench` is an open benchmark of realistic infrastructure tasks for evaluating AI agents.

## Datasets

| Dataset | 🟢 Easy | 🟡 Medium | 🔴 Hard | Status |
| --- | ---: | ---: | ---: | --- |
| [`kubeply/kubernetes-core`](datasets/kubernetes-core) | 22 | 23 | 13 | 🛠️ Working |
| [`kubeply/terraform-core`](datasets/terraform-core) | 0 | 0 | 0 | 🛠️ Working |
| `kubeply/observability-core` | 0 | 0 | 0 | ⏳ Not started yet |

## Quickstart

Tasks are compatible with [Harbor](https://www.harborframework.com/) and can be
run through `uvx`.

Run a local Kubernetes benchmark task with Harbor:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-local-smoke \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=high \
  -e docker \
  -n 1 \
  -y \
  --max-retries 0 \
  -i fix-crashloop-env-var
```

For repeated local `kubernetes-core` runs, configure k3s registry
authentication first so the ephemeral clusters can authenticate their own Docker
Hub pulls. See [k3s registry authentication](docs/k3s-registry-auth.md).

## Citation

If you use `infra-bench` in academic work, please cite it using the "Cite this
repository" button on GitHub or the following BibTeX entry:

```bibtex
@software{Infra_Bench,
  author = {{Kubeply}},
  month = apr,
  title = {{infra-bench: Open benchmark tasks for evaluating AI agents on real infrastructure work}},
  url = {https://github.com/kubeply/infra-bench},
  year = {2026}
}
```

## License

Apache License 2.0. See [LICENSE](LICENSE).
