# infrabench

`infra-bench` is an open benchmark of realistic infrastructure tasks for evaluating AI agents.

## Datasets

| Dataset | 🟢 Easy | 🟡 Medium | 🔴 Hard | Status |
| --- | ---: | ---: | ---: | --- |
| [`kubeply/kubernetes-core`](datasets/kubernetes-core) | 22 | 2 | 0 | 🛠️ Working |
| [`kubeply/terraform-core`](datasets/terraform-core) | 0 | 0 | 0 | 🛠️ Working |
| `kubeply/observability-core` | 0 | 0 | 0 | ⏳ Not started yet |

## Quickstart

Tasks are compatible with [Harbor](https://www.harborframework.com/) and can be
run through `uvx`.

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
