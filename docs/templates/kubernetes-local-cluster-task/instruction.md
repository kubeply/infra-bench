<infra-bench-canary: TODO_UUID>

You are working in `/app`; the problem to fix is in the live Kubernetes
cluster.

A Kubernetes cluster is already running and `kubectl` is configured through
`KUBECONFIG`.

TODO_DESCRIBE_THE_OPERATOR_PROBLEM.

Constraints:

- Use `kubectl` to inspect the live resources before changing anything.
- Preserve TODO_IDENTITY_AND_INVARIANTS.
- Do not create replacement workloads or bypass resources.
- Do not patch status or write verifier artifacts directly.

Success means TODO_DESCRIBE_LIVE_SUCCESS_STATE.
