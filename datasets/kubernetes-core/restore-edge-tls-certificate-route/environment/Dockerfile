# syntax=docker/dockerfile:1

FROM debian:bookworm-slim

ARG KUBECTL_VERSION=v1.30.6

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
  apt-get update \
  && apt-get install -y --no-install-recommends bash ca-certificates curl openssl \
  && arch="$(dpkg --print-architecture)" \
  && curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl" \
  && curl -fsSLo /tmp/kubectl.sha256 "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl.sha256" \
  && printf '%s  %s\n' "$(cat /tmp/kubectl.sha256)" "/usr/local/bin/kubectl" > /tmp/kubectl.sha256.check \
  && sha256sum -c /tmp/kubectl.sha256.check \
  && rm -f /tmp/kubectl.sha256 /tmp/kubectl.sha256.check \
  && chmod +x /usr/local/bin/kubectl

ENV KUBECONFIG=/kube/kubeconfig.yaml

WORKDIR /app
COPY scripts/prepare-kubeconfig /usr/local/bin/prepare-kubeconfig
RUN chmod +x /usr/local/bin/prepare-kubeconfig
