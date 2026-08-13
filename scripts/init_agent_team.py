#!/usr/bin/env python3
"""Initialize a confirmed agent-team workflow without overwriting project files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
INTEGRATION_MODES = {"fragment", "create", "none"}
SECRET_REFERENCE_PREFIXES = (
    "env:",
    "keyring:",
    "secret:",
    "vault:",
    "aws-secretsmanager:",
    "gcp-secretmanager:",
    "azure-keyvault:",
)
SENSITIVE_KEYS = {
    "password",
    "passwd",
    "token",
    "access_token",
    "api_key",
    "secret",
    "secret_value",
    "private_key",
    "credentials",
}
RAW_SECRET_PATTERNS = (
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)


class ConfigError(ValueError):
    pass


def load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ConfigError(
                "YAML input requires PyYAML; provide the same answers as JSON instead"
            ) from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ConfigError("configuration root must be a mapping")
    return data


def require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"{key} must be a mapping")
    return value


def require_text(parent: dict[str, Any], key: str, scope: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{scope}.{key} must be a non-empty string")
    return value.strip()


def safe_relative_path(value: str, field: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path == Path(".") or ".." in path.parts:
        raise ConfigError(f"{field} must be a non-empty repository-relative path")
    return path


def validate_secret_references(manifest: dict[str, Any]) -> None:
    secrets = manifest.get("secrets", [])
    if secrets in (None, "unknown"):
        return
    if not isinstance(secrets, list):
        raise ConfigError("resources.manifest.secrets must be a list")
    for index, entry in enumerate(secrets):
        if not isinstance(entry, dict):
            raise ConfigError(f"resources.manifest.secrets[{index}] must be a mapping")
        reference = entry.get("reference")
        if reference == "unknown":
            continue
        if not isinstance(reference, str) or not reference.startswith(
            SECRET_REFERENCE_PREFIXES
        ):
            raise ConfigError(
                "secret entries must contain references such as env:NAME, "
                "keyring:ENTRY, or secret-manager URIs; values are forbidden"
            )


def validate_no_raw_secrets(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            child_path = f"{path}.{key}"
            if normalized in SENSITIVE_KEYS:
                if not (
                    isinstance(child, str)
                    and (
                        child == "unknown"
                        or child.startswith(SECRET_REFERENCE_PREFIXES)
                    )
                ):
                    raise ConfigError(
                        f"{child_path} looks credential-bearing; "
                        "store only a secret reference"
                    )
            validate_no_raw_secrets(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_raw_secrets(child, f"{path}[{index}]")
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in RAW_SECRET_PATTERNS):
            raise ConfigError(f"{path} contains a secret-like value")


def validate_config(
    data: dict[str, Any], repo: Path, docs_override: str | None
) -> tuple[dict[str, Any], Path, str, dict[str, Any]]:
    project = require_mapping(data, "project")
    workflow = require_mapping(data, "workflow")
    resources = require_mapping(data, "resources")
    documentation = require_mapping(data, "documentation")
    confirmation = require_mapping(data, "confirmation")

    project_name = require_text(project, "name", "project")
    require_text(project, "objective", "project")
    configured_repo = Path(require_text(project, "repository", "project")).expanduser()
    if configured_repo.resolve() != repo.resolve():
        raise ConfigError(
            f"project.repository resolves to {configured_repo.resolve()}, not {repo.resolve()}"
        )

    required_workflow_text = (
        "formal_task_trigger",
        "commit_policy",
        "push_policy",
        "destructive_action_policy",
        "external_action_policy",
        "agents_integration",
    )
    for key in required_workflow_text:
        require_text(workflow, key, "workflow")

    for key in ("status_cadence_minutes", "max_agents"):
        value = workflow.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ConfigError(f"workflow.{key} must be a positive integer")

    integration = workflow["agents_integration"]
    if integration not in INTEGRATION_MODES:
        raise ConfigError(
            "workflow.agents_integration must be fragment, create, or none"
        )

    docs_value = docs_override or require_text(workflow, "docs_dir", "workflow")
    docs_dir = safe_relative_path(docs_value, "workflow.docs_dir")
    workflow["docs_dir"] = docs_dir.as_posix()
    safe_relative_path(
        require_text(documentation, "task_dir", "documentation"),
        "documentation.task_dir",
    )
    safe_relative_path(
        require_text(documentation, "progress_dir", "documentation"),
        "documentation.progress_dir",
    )

    confirmed_by = require_text(confirmation, "confirmed_by", "confirmation")
    confirmed_at = require_text(confirmation, "confirmed_at", "confirmation")
    if confirmed_by.lower() in {"unknown", "unconfirmed", "pending"}:
        raise ConfigError("confirmation.confirmed_by must record explicit confirmation")
    if confirmed_at.lower() in {"unknown", "unconfirmed", "pending"}:
        raise ConfigError("confirmation.confirmed_at must record confirmation time")

    manifest_value = resources.get("manifest", {})
    if not isinstance(manifest_value, dict):
        raise ConfigError("resources.manifest must be a mapping when provided")
    manifest = dict(manifest_value)
    manifest.setdefault("schema_version", 1)
    manifest.setdefault("project", project_name)
    manifest.setdefault(
        "repositories",
        [
            {
                "id": "main",
                "role": "implementation",
                "local_path": str(repo.resolve()),
                "canonical_branch": "unknown",
                "worktree_root": "unknown",
                "integration_branch": "unknown",
            }
        ],
    )
    for key, default in (
        ("environments", []),
        ("hosts", []),
        ("compute_pools", []),
        ("storage", []),
        ("network", {"default": "unknown", "allowed_operations": []}),
        ("secrets", []),
        ("tools", []),
        (
            "approval_boundaries",
            {
                "terminate_process": workflow["destructive_action_policy"],
                "push": workflow["push_policy"],
                "deploy": workflow["external_action_policy"],
                "external_message": workflow["external_action_policy"],
                "destructive_filesystem": workflow["destructive_action_policy"],
            },
        ),
        ("budgets", {}),
    ):
        manifest.setdefault(key, default)
    manifest.setdefault("validated_at", confirmed_at)
    manifest.setdefault("validated_by", confirmed_by)
    validate_secret_references(manifest)
    return data, docs_dir, integration, manifest


def render(text: str, replacements: dict[str, str], source: Path) -> str:
    for token, value in replacements.items():
        text = text.replace("{{" + token + "}}", value)
    unresolved = sorted(set(TOKEN_RE.findall(text)))
    if unresolved:
        raise ConfigError(f"{source} has unresolved tokens: {', '.join(unresolved)}")
    return text


def build_plan(
    template_root: Path,
    repo: Path,
    docs_dir: Path,
    integration: str,
    replacements: dict[str, str],
) -> list[tuple[Path, str]]:
    plan: list[tuple[Path, str]] = []
    source_docs = template_root / "agent_team"
    if not source_docs.is_dir():
        raise ConfigError(f"missing template directory: {source_docs}")

    for source in sorted(path for path in source_docs.rglob("*") if path.is_file()):
        target = repo / docs_dir / source.relative_to(source_docs)
        plan.append(
            (
                target,
                render(source.read_text(encoding="utf-8"), replacements, source),
            )
        )

    fragment_source = template_root / "AGENTS.md.fragment"
    if integration == "fragment":
        target = repo / "AGENTS.md.agent-team.fragment"
        plan.append(
            (
                target,
                render(
                    fragment_source.read_text(encoding="utf-8"),
                    replacements,
                    fragment_source,
                ),
            )
        )
    elif integration == "create":
        target = repo / "AGENTS.md"
        plan.append(
            (
                target,
                render(
                    fragment_source.read_text(encoding="utf-8"),
                    replacements,
                    fragment_source,
                ),
            )
        )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize a confirmed, collision-safe agent-team workflow"
    )
    parser.add_argument("--repo", required=True, help="Target repository root")
    parser.add_argument("--config", required=True, help="Confirmed YAML or JSON answers")
    parser.add_argument(
        "--docs-dir",
        help="Override the confirmed repository-relative documentation directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the exact create plan without writing",
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser()
    config_path = Path(args.config).expanduser()
    if not repo.is_dir():
        print(f"ERROR: repository directory does not exist: {repo}", file=sys.stderr)
        return 2
    if not config_path.is_file():
        print(f"ERROR: configuration file does not exist: {config_path}", file=sys.stderr)
        return 2

    try:
        data = load_mapping(config_path)
        validate_no_raw_secrets(data)
        data, docs_dir, integration, manifest = validate_config(
            data, repo, args.docs_dir
        )
        project = data["project"]
        workflow = data["workflow"]
        confirmation = data["confirmation"]
        replacements = {
            "PROJECT_NAME": str(project["name"]),
            "PROJECT_OBJECTIVE": str(project["objective"]),
            "REPOSITORY_PATH": str(repo.resolve()),
            "DOCS_DIR": docs_dir.as_posix(),
            "FORMAL_TASK_TRIGGER": str(workflow["formal_task_trigger"]),
            "STATUS_CADENCE_MINUTES": str(workflow["status_cadence_minutes"]),
            "MAX_AGENTS": str(workflow["max_agents"]),
            "COMMIT_POLICY": str(workflow["commit_policy"]),
            "PUSH_POLICY": str(workflow["push_policy"]),
            "DESTRUCTIVE_ACTION_POLICY": str(workflow["destructive_action_policy"]),
            "EXTERNAL_ACTION_POLICY": str(workflow["external_action_policy"]),
            "CONFIRMED_BY": str(confirmation["confirmed_by"]),
            "CONFIRMED_AT": str(confirmation["confirmed_at"]),
            "SETUP_ANSWERS_JSON": json.dumps(data, indent=2, sort_keys=True),
            "RESOURCE_MANIFEST_JSON": json.dumps(manifest, indent=2, sort_keys=True),
        }
        template_root = Path(__file__).resolve().parents[1] / "assets" / "repo-template"
        plan = build_plan(
            template_root, repo.resolve(), docs_dir, integration, replacements
        )
    except (ConfigError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    collisions = [target for target, _ in plan if target.exists()]
    mode = "DRY-RUN" if args.dry_run else "INITIALIZE"
    print(f"MODE: {mode}")
    print(f"REPOSITORY: {repo.resolve()}")
    print(f"DOCS_DIR: {docs_dir.as_posix()}")
    print(f"AGENTS_INTEGRATION: {integration}")
    for target, _ in plan:
        label = "COLLISION" if target in collisions else "CREATE"
        print(f"{label}: {target.relative_to(repo.resolve())}")

    if collisions:
        print(
            "ERROR: refusing to overwrite existing files; "
            "reconcile or choose another destination",
            file=sys.stderr,
        )
        return 3
    if args.dry_run:
        print(f"PASS: {len(plan)} files planned; no files written")
        return 0

    try:
        for target, text in plan:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
    except FileExistsError as exc:
        print(
            f"ERROR: concurrent collision; no overwrite performed: {exc}",
            file=sys.stderr,
        )
        return 3
    except OSError as exc:
        print(f"ERROR: initialization failed: {exc}", file=sys.stderr)
        return 2

    print(f"PASS: created {len(plan)} files; no existing files modified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
