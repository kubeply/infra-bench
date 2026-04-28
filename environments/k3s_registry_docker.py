"""Harbor Docker environment for passing local registry auth into k3s tasks.

This keeps Kubernetes task definitions portable while allowing a runner to
provide Docker Hub credentials to each ephemeral k3s cluster through the local
K3S_REGISTRIES_PATH environment variable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from harbor.environments.docker.docker import DockerEnvironment


class K3SRegistryDockerEnvironment(DockerEnvironment):
    """Docker environment that can pass registry auth into k3s.

    Set K3S_REGISTRIES_PATH to a local k3s registries.yaml file. The file is
    mounted into the task's k3s service without changing task definitions or
    committing machine-specific paths.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Docker environment with optional k3s registry auth."""
        super().__init__(*args, **kwargs)
        self._k3s_registries_path: Path | None = self._resolve_k3s_registries_path()
        self._k3s_registries_compose_path: Path | None = None

    @staticmethod
    def _resolve_k3s_registries_path() -> Path | None:
        """Return the configured k3s registries file path, if one was provided."""
        raw_path: str | None = os.environ.get("K3S_REGISTRIES_PATH")
        if not raw_path:
            return None

        path: Path = Path(raw_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(
                f"K3S_REGISTRIES_PATH points to a missing file: {path}"
            )

        return path

    @property
    def _docker_compose_paths(self) -> list[Path]:
        """Return compose files, including the k3s registry override when enabled."""
        paths = list(super()._docker_compose_paths)
        if self._k3s_registries_compose_path:
            paths.append(self._k3s_registries_compose_path)
        return paths

    def _write_k3s_registries_compose_file(self) -> Path:
        """Write a compose override that mounts registries.yaml into k3s."""
        if not self._k3s_registries_path:
            raise RuntimeError("K3S registries path was not configured")

        compose = {
            "services": {
                "k3s": {
                    "volumes": [
                        f"{self._k3s_registries_path}:/etc/rancher/k3s/registries.yaml:ro"
                    ]
                }
            }
        }
        path = self.trial_paths.trial_dir / "docker-compose-k3s-registries.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(compose, indent=2))
        return path

    async def start(self, force_build: bool) -> None:
        """Start the Docker environment with the optional k3s registry override."""
        if self._k3s_registries_path:
            self._k3s_registries_compose_path = (
                self._write_k3s_registries_compose_file()
            )

        await super().start(force_build)
