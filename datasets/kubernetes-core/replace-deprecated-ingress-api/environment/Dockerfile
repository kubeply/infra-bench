FROM debian:bookworm-slim

ARG KUBECTL_VERSION=v1.30.6

RUN apt-get update \
  && apt-get install -y --no-install-recommends bash ca-certificates curl \
  && arch="$(dpkg --print-architecture)" \
  && curl -fsSLo /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/${arch}/kubectl" \
  && chmod +x /usr/local/bin/kubectl \
  && rm -rf /var/lib/apt/lists/*

ENV KUBECONFIG=/kube/kubeconfig.yaml

WORKDIR /app
COPY workspace/app/ /app/
COPY scripts/ /usr/local/bin/
RUN chmod +x /usr/local/bin/prepare-kubeconfig /usr/local/bin/bootstrap-cluster
