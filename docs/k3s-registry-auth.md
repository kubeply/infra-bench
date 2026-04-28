# k3s Registry Authentication

`kubernetes-core` tasks run an ephemeral k3s cluster inside Harbor's Docker
environment. The host Docker daemon may already be logged in to Docker Hub, but
k3s uses its own containerd image pull path inside the cluster. Without explicit
k3s registry credentials, repeated benchmark runs can fail during environment
setup with Docker Hub `429 Too Many Requests` errors.

Use a Docker Hub read-only access token and a local k3s `registries.yaml` file
to authenticate image pulls from inside each ephemeral k3s cluster.

## Create a Docker Hub Token

1. Open Docker Hub personal access tokens:
   <https://app.docker.com/settings/personal-access-tokens>
2. Generate a new token.
3. Use a clear name, such as `infra-bench-k3s-pulls`.
4. Select read-only access.
5. Copy the token once when Docker Hub shows it.

Use your Docker Hub username for `DOCKERHUB_USERNAME`. Do not use your email
address.

## Create `registries.yaml`

Choose any local path outside the repository. The path below follows the XDG
config convention and works on Linux and macOS:

```bash
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/infra-bench"

read -r DOCKERHUB_USERNAME
read -rs DOCKERHUB_TOKEN
echo

cat > "${XDG_CONFIG_HOME:-$HOME/.config}/infra-bench/k3s-registries.yaml" <<EOF
mirrors:
  docker.io:
    endpoint:
      - "https://registry-1.docker.io"
configs:
  "registry-1.docker.io":
    auth:
      username: "$DOCKERHUB_USERNAME"
      password: "$DOCKERHUB_TOKEN"
  "docker.io":
    auth:
      username: "$DOCKERHUB_USERNAME"
      password: "$DOCKERHUB_TOKEN"
EOF

chmod 600 "${XDG_CONFIG_HOME:-$HOME/.config}/infra-bench/k3s-registries.yaml"
export K3S_REGISTRIES_PATH="${XDG_CONFIG_HOME:-$HOME/.config}/infra-bench/k3s-registries.yaml"
```

Keep this file local. It contains registry credentials and must not be committed
to the repository.

## Run Harbor With k3s Auth

Use the custom Docker environment so Harbor mounts `K3S_REGISTRIES_PATH` into
the `k3s` service as `/etc/rancher/k3s/registries.yaml`:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-local \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=high \
  -e docker \
  --environment-import-path environments.k3s_registry_docker:K3SRegistryDockerEnvironment \
  -n 1 \
  -y
```

For local reliability, keep `-n 1` unless the runner has enough CPU, memory, and
Docker Hub pull budget for multiple concurrent k3s clusters.

## Verify the Setup

Run one task first:

```bash
uvx --from harbor harbor run \
  --job-name kubernetes-core-local-smoke \
  -p datasets/kubernetes-core \
  -a codex \
  -m gpt-5.5 \
  --ak reasoning_effort=high \
  -e docker \
  --environment-import-path environments.k3s_registry_docker:K3SRegistryDockerEnvironment \
  -n 1 \
  -y \
  --max-retries 0 \
  -i fix-crashloop-env-var
```

If the setup is working, environment setup should get past image pulls and the
trial should finish as a normal Harbor pass/fail result. A verifier failure with
reward `0.0` is different from an environment setup failure.
