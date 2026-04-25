#!/usr/bin/env python3
"""Lint Kubernetes task agent RBAC for shortcut-prone privileges."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
import sys


WRITE_VERBS = {"create", "delete", "deletecollection", "patch", "update", "*"}
MUTATING_VERBS = {"delete", "deletecollection", "patch", "update", "*"}
CREATE_GUARDED_RESOURCES = {
    "pods",
    "services",
    "deployments",
    "daemonsets",
    "statefulsets",
    "jobs",
    "cronjobs",
}

ALLOW_BROAD_WRITES = {
    ("fix-job-command-argument", "batch", "jobs"),
    ("repair-cross-namespace-service-discovery", "", "configmaps"),
    ("repair-plugin-driven-app-startup", "", "configmaps"),
    ("replace-deprecated-ingress-api", "networking.k8s.io", "ingresses"),
    ("restore-alert-signal-after-telemetry-split", "", "configmaps"),
    ("restore-order-pipeline-after-queue-migration", "", "configmaps"),
    ("restore-missing-configmap", "", "configmaps"),
}


@dataclass(frozen=True)
class Rule:
    api_groups: tuple[str, ...]
    resources: tuple[str, ...]
    resource_names: tuple[str, ...]
    verbs: tuple[str, ...]
    line: int


@dataclass(frozen=True)
class RbacDoc:
    path: Path
    task: str
    kind: str
    name: str
    namespace: str
    rules: tuple[Rule, ...]


def parse_scalar_list(value: str) -> tuple[str, ...]:
    value = value.strip()
    if not value:
        return ()
    if value.startswith("["):
        parsed = ast.literal_eval(value)
        return tuple(str(item) for item in parsed)
    if value.startswith("- "):
        return (value[2:].strip().strip('"'),)
    return (value.strip('"'),)


def field_value(lines: list[str], index: int) -> tuple[tuple[str, ...], int]:
    line = lines[index]
    _, raw_value = line.split(":", 1)
    raw_value = raw_value.strip()
    if raw_value:
        return parse_scalar_list(raw_value), index

    next_index = index + 1
    values: list[str] = []
    while next_index < len(lines):
        next_line = lines[next_index]
        stripped = next_line.strip()
        if not stripped:
            next_index += 1
            continue
        if re.match(r"^[a-zA-Z][a-zA-Z0-9]*:", stripped) or stripped.startswith(
            "- apiGroups:"
        ):
            break
        if stripped.startswith("[") and not stripped.endswith("]"):
            parts = [stripped]
            while next_index + 1 < len(lines) and not parts[-1].strip().endswith("]"):
                next_index += 1
                parts.append(lines[next_index].strip())
            values.extend(parse_scalar_list(" ".join(parts)))
            next_index += 1
            continue
        values.extend(parse_scalar_list(stripped))
        next_index += 1
    return tuple(values), next_index - 1


def simple_metadata_value(lines: list[str], field: str) -> str:
    in_metadata = False
    for line in lines:
        if line == "metadata:":
            in_metadata = True
            continue
        if in_metadata:
            if line and not line.startswith(" "):
                return ""
            stripped = line.strip()
            if stripped.startswith(f"{field}:"):
                return stripped.split(":", 1)[1].strip().strip('"')
    return ""


def simple_top_value(lines: list[str], field: str) -> str:
    for line in lines:
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def parse_rules(lines: list[str]) -> tuple[Rule, ...]:
    rules: list[Rule] = []
    current: dict[str, tuple[str, ...] | int] | None = None

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("- apiGroups:"):
            if current:
                rules.append(make_rule(current))
            current = {"line": index + 1}
            current["apiGroups"], index = field_value(lines, index)
        elif current and any(
            stripped.startswith(f"{field}:")
            for field in ("resources", "resourceNames", "verbs")
        ):
            field = stripped.split(":", 1)[0]
            current[field], index = field_value(lines, index)
        index += 1

    if current:
        rules.append(make_rule(current))

    return tuple(rules)


def make_rule(data: dict[str, tuple[str, ...] | int]) -> Rule:
    def values(field: str) -> tuple[str, ...]:
        value = data.get(field, ())
        if isinstance(value, tuple):
            return value
        return ()

    return Rule(
        api_groups=values("apiGroups"),
        resources=values("resources"),
        resource_names=values("resourceNames"),
        verbs=values("verbs"),
        line=int(data.get("line", 1)),
    )


def parse_docs(path: Path) -> list[RbacDoc]:
    docs: list[RbacDoc] = []
    task = path.parts[2]

    for raw_doc in re.split(r"(?m)^---\s*$", path.read_text()):
        lines = [line.rstrip() for line in raw_doc.splitlines() if line.strip()]
        kind = simple_top_value(lines, "kind")
        if kind not in {"Role", "ClusterRole"}:
            continue

        name = simple_metadata_value(lines, "name")
        namespace = simple_metadata_value(lines, "namespace")
        if not name.startswith("infra-bench"):
            continue

        docs.append(
            RbacDoc(
                path=path,
                task=task,
                kind=kind,
                name=name,
                namespace=namespace,
                rules=parse_rules(lines),
            )
        )

    return docs


def is_allowed_broad_write(task: str, group: str, resource: str) -> bool:
    return (task, group, resource) in ALLOW_BROAD_WRITES


def lint_doc(doc: RbacDoc) -> list[str]:
    errors: list[str] = []

    for rule in doc.rules:
        write_verbs = WRITE_VERBS.intersection(rule.verbs)
        if not write_verbs:
            continue

        for group in rule.api_groups:
            for resource in rule.resources:
                location = f"{doc.path}:{rule.line}"
                allowed = is_allowed_broad_write(doc.task, group, resource)

                if doc.kind == "ClusterRole":
                    errors.append(
                        f"{location}: {doc.name} grants cluster-scope write "
                        f"verbs {sorted(write_verbs)} on {group or 'core'}/{resource}"
                    )

                if resource == "configmaps" and not allowed:
                    errors.append(
                        f"{location}: agent RBAC must not grant ConfigMap writes "
                        f"without an explicit task exception"
                    )

                if (
                    "create" in write_verbs
                    and resource in CREATE_GUARDED_RESOURCES
                    and not allowed
                ):
                    errors.append(
                        f"{location}: agent RBAC grants create on shortcut-prone "
                        f"resource {group or 'core'}/{resource}"
                    )

                if (
                    MUTATING_VERBS.intersection(write_verbs)
                    and not rule.resource_names
                    and not allowed
                ):
                    errors.append(
                        f"{location}: mutating agent RBAC on {group or 'core'}/{resource} "
                        "must use resourceNames or an explicit exception"
                    )

    return errors


def main() -> int:
    root = Path("datasets/kubernetes-core")
    errors: list[str] = []

    for path in sorted(root.glob("*/environment/workspace/bootstrap/*.yaml")):
        for doc in parse_docs(path):
            errors.extend(lint_doc(doc))

    if errors:
        print("Kubernetes RBAC lint failed:", file=sys.stderr)
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("kubernetes rbac lint ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
