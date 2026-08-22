#!/usr/bin/env python3
"""Read-only validation for an initialized agent-team workflow."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

PHASES = {"proposed", "ready", "active", "review", "evaluation", "accepted", "integrated"}
STATUSES = {"running", "waiting", "blocked", "completed", "archived", "superseded"}
AGENT_STATES = {
    "active",
    "waiting",
    "blocked",
    "awaiting_review",
    "completed",
    "superseded",
    "disconnected",
}
JOB_STATES = {
    "none",
    "planned",
    "starting",
    "running",
    "succeeded",
    "failed",
    "unknown",
    "stopped",
}
RESERVATION_STATES = {"planned", "reserved", "active", "released", "failed"}
TOKEN_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}")
TASK_SERIAL_RE = re.compile(r"-(\d+)$")
MARKDOWN_LINK_RE = re.compile(r"!?(?:\[[^\]]*\])\(([^)]+)\)")
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
    re.compile(r"\bhttps?://[^\s/:]+:[^\s/@]+@"),
)
DISALLOWED_SUFFIXES = {
    ".ckpt",
    ".pt",
    ".pth",
    ".npz",
    ".npy",
    ".tar",
    ".gz",
    ".zip",
    ".log",
    ".pid",
    ".status",
    ".orig",
    ".rej",
}
DISALLOWED_DIRS = {"__pycache__", ".cache", "wandb", "outputs"}
REQUIRED_FILES = (
    "agent_team_init.md",
    "setup_answers.yaml",
    "resources_manifest.yaml",
    "agent_team_scheme.md",
    "task_status.md",
    "resource_status.md",
    "artifact_retention.md",
    ".gitignore",
    "tasks/_template/goal_manifest.md",
    "tasks/_template/inspection_report.md",
    "progress_reports/index.md",
)


def load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise ValueError(f"{path}: YAML requires PyYAML") from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: root must be a mapping")
    return data


def table_value(text: str, field: str) -> str | None:
    pattern = re.compile(
        rf"^\|\s*{re.escape(field)}\s*\|\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def markdown_rows(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    section_match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not section_match:
        return [], []
    table_lines = [
        line.strip()
        for line in section_match.group(1).splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(table_lines) < 2:
        return [], []
    headers = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    rows: list[list[str]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(cells)
    return headers, rows


def validate_required_files(docs: Path, errors: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (docs / relative).is_file():
            errors.append(f"missing required file: {relative}")


def validate_placeholders_and_links(
    repo: Path, docs: Path, errors: list[str]
) -> None:
    for path in sorted(item for item in docs.rglob("*") if item.is_file()):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        tokens = sorted(set(TOKEN_RE.findall(text)))
        if tokens:
            errors.append(
                f"{path.relative_to(repo)}: unresolved placeholders "
                f"{', '.join(tokens)}"
            )
        for raw_target in MARKDOWN_LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if (
                not target
                or target.startswith(("#", "http://", "https://", "mailto:"))
                or "{{" in target
            ):
                continue
            target_path = Path(target.split("#", 1)[0])
            if target_path.is_absolute():
                errors.append(
                    f"{path.relative_to(repo)}: absolute local link {target_path}"
                )
                continue
            resolved = (path.parent / target_path).resolve()
            try:
                resolved.relative_to(repo)
            except ValueError:
                errors.append(
                    f"{path.relative_to(repo)}: link escapes repository {target_path}"
                )
                continue
            if target_path and not resolved.exists():
                errors.append(f"{path.relative_to(repo)}: broken relative link {target_path}")


def validate_secret_like_values(
    repo: Path, docs: Path, errors: list[str]
) -> None:
    for path in sorted(item for item in docs.rglob("*") if item.is_file()):
        if path.name == ".gitignore":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                errors.append(f"{path.relative_to(repo)}: secret-like value detected")
                break
        for line_number, line in enumerate(text.splitlines(), start=1):
            if re.search(
                r"\b(?:password|passwd|api[_-]?key|access[_-]?token)[\"']?\s*[:=]",
                line,
                re.IGNORECASE,
            ):
                lowered = line.lower()
                safe_prefixes = ("env:", "keyring:", "secret:", "unknown", "example")
                if not any(prefix in lowered for prefix in safe_prefixes):
                    errors.append(
                        f"{path.relative_to(repo)}:{line_number}: "
                        "credential-like assignment detected"
                    )
            for candidate in IPV4_RE.findall(line):
                octets = [int(part) for part in candidate.split(".")]
                if all(part <= 255 for part in octets):
                    errors.append(
                        f"{path.relative_to(repo)}:{line_number}: "
                        "tracked IPv4 address detected"
                    )


def validate_retention(repo: Path, docs: Path, errors: list[str]) -> None:
    for path in sorted(docs.rglob("*")):
        relative = path.relative_to(docs)
        if any(part in DISALLOWED_DIRS for part in relative.parts):
            errors.append(f"{path.relative_to(repo)}: disallowed runtime directory")
            continue
        if path.is_file() and path.suffix.lower() in DISALLOWED_SUFFIXES:
            errors.append(f"{path.relative_to(repo)}: disallowed bulk/runtime artifact")


def validate_setup_and_resources(
    docs: Path, errors: list[str]
) -> dict[str, Any] | None:
    try:
        setup = load_mapping(docs / "setup_answers.yaml")
        resources = load_mapping(docs / "resources_manifest.yaml")
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        return None

    for key in ("project", "workflow", "resources", "documentation", "confirmation"):
        if not isinstance(setup.get(key), dict):
            errors.append(f"setup_answers.yaml: {key} must be a mapping")
    workflow = setup.get("workflow", {})
    if isinstance(workflow, dict):
        status_cadence = workflow.get("status_cadence_minutes")
        if (
            not isinstance(status_cadence, int)
            or isinstance(status_cadence, bool)
            or status_cadence <= 0
        ):
            errors.append(
                "setup_answers.yaml: workflow.status_cadence_minutes "
                "must be a positive integer"
            )
        max_agents = workflow.get("max_agents")
        if max_agents != "unlimited" and (
            not isinstance(max_agents, int)
            or isinstance(max_agents, bool)
            or max_agents <= 0
        ):
            errors.append(
                "setup_answers.yaml: workflow.max_agents must be a positive "
                "integer or 'unlimited'"
            )
        if workflow.get("agents_integration") not in {"fragment", "create", "none"}:
            errors.append("setup_answers.yaml: invalid workflow.agents_integration")
    confirmation = setup.get("confirmation", {})
    if isinstance(confirmation, dict):
        for key in ("confirmed_by", "confirmed_at"):
            value = confirmation.get(key)
            if not isinstance(value, str) or value.lower() in {
                "",
                "unknown",
                "unconfirmed",
                "pending",
            }:
                errors.append(
                    f"setup_answers.yaml: confirmation.{key} is not confirmed"
                )

    required_resource_keys = (
        "schema_version",
        "project",
        "repositories",
        "environments",
        "hosts",
        "compute_pools",
        "storage",
        "network",
        "secrets",
        "tools",
        "approval_boundaries",
        "budgets",
        "validated_at",
        "validated_by",
    )
    for key in required_resource_keys:
        if key not in resources:
            errors.append(f"resources_manifest.yaml: missing {key}")
    if resources.get("schema_version") != 1:
        errors.append("resources_manifest.yaml: schema_version must be 1")
    list_keys = (
        "repositories",
        "environments",
        "hosts",
        "compute_pools",
        "storage",
        "secrets",
        "tools",
    )
    for key in list_keys:
        if key in resources and not isinstance(resources[key], list):
            errors.append(f"resources_manifest.yaml: {key} must be a list")
    for index, entry in enumerate(resources.get("secrets", [])):
        if not isinstance(entry, dict):
            errors.append(
                f"resources_manifest.yaml: secrets[{index}] must be a mapping"
            )
            continue
        reference = entry.get("reference")
        prefixes = (
            "env:",
            "keyring:",
            "secret:",
            "vault:",
            "aws-secretsmanager:",
            "gcp-secretmanager:",
            "azure-keyvault:",
        )
        if reference != "unknown" and (
            not isinstance(reference, str) or not reference.startswith(prefixes)
        ):
            errors.append(
                f"resources_manifest.yaml: secrets[{index}] "
                "is not a secret reference"
            )
    return setup


def validate_task_records(repo: Path, docs: Path, errors: list[str]) -> None:
    tasks_root = docs / "tasks"
    task_ids: list[str] = []
    task_serials: list[tuple[str, str]] = []
    active_directories = [
        path
        for path in tasks_root.iterdir()
        if path.is_dir() and path.name not in {"_template", "archived"}
    ]
    archive_root = tasks_root / "archived"
    archived_directories = []
    if archive_root.is_dir():
        archived_directories = [
            task
            for classname in archive_root.iterdir()
            if classname.is_dir()
            for task in classname.iterdir()
            if task.is_dir()
        ]
    archived_set = set(archived_directories)
    for directory in sorted(active_directories + archived_directories):
        goal = directory / "goal_manifest.md"
        inspection = directory / "inspection_report.md"
        if not goal.is_file() or not inspection.is_file():
            errors.append(
                f"{directory.relative_to(repo)}: task requires "
                "goal_manifest.md and inspection_report.md"
            )
            continue
        text = goal.read_text(encoding="utf-8")
        task_id = table_value(text, "Task ID")
        phase = table_value(text, "Phase")
        status = table_value(text, "Status")
        owner = table_value(text, "Owner")
        reviewer = table_value(text, "Reviewer/evaluator")
        if not task_id:
            errors.append(f"{goal.relative_to(repo)}: missing Task ID")
        else:
            task_ids.append(task_id)
            serial_match = TASK_SERIAL_RE.search(task_id)
            if not serial_match:
                errors.append(
                    f"{goal.relative_to(repo)}: Task ID must end in a numeric serial"
                )
            else:
                task_serials.append((serial_match.group(1), task_id))
        if phase not in PHASES:
            errors.append(f"{goal.relative_to(repo)}: invalid phase {phase!r}")
        if status not in STATUSES:
            errors.append(f"{goal.relative_to(repo)}: invalid status {status!r}")
        if directory in archived_set and status != "archived":
            errors.append(
                f"{goal.relative_to(repo)}: archived task directory requires "
                "status 'archived'"
            )
        if directory in archived_set and task_id:
            expected_class = task_id.split("-", 1)[0]
            actual_class = directory.parent.name
            if actual_class != expected_class:
                errors.append(
                    f"{directory.relative_to(repo)}: archive class must be "
                    f"{expected_class!r} for task {task_id!r}"
                )
        if not owner or owner.lower() in {"unknown", "unassigned", "none"}:
            errors.append(f"{goal.relative_to(repo)}: accountable owner is required")
        if not reviewer or reviewer.lower() in {"unknown", "unassigned", "none"}:
            errors.append(
                f"{goal.relative_to(repo)}: reviewer/evaluator is required"
            )
        if "## Acceptance Requirements" not in text or not re.search(
            r"^\|\s*A\d+\s*\|", text, re.MULTILINE
        ):
            errors.append(
                f"{goal.relative_to(repo)}: measurable acceptance gate is required"
            )
    for task_id, count in Counter(task_ids).items():
        if count > 1:
            errors.append(
                "task IDs must be globally unique across active and archived "
                f"history; duplicate goal-manifest ID: {task_id}"
            )
    serial_to_ids: dict[str, set[str]] = {}
    for serial, task_id in task_serials:
        serial_to_ids.setdefault(serial, set()).add(task_id)
    for serial, serial_ids in sorted(serial_to_ids.items()):
        if len(serial_ids) > 1:
            errors.append(
                "task numeric serials must be globally unique across all prefixes "
                f"and classes; serial {serial} is used by {', '.join(sorted(serial_ids))}"
            )


def validate_live_status(docs: Path, errors: list[str]) -> None:
    text = (docs / "task_status.md").read_text(encoding="utf-8")
    required_sections = (
        "Running",
        "Waiting",
        "Blocked",
        "Completed",
        "Archived",
        "Superseded",
        "Live Agent Status",
    )
    for section in required_sections:
        if not re.search(
            rf"^##\s+{re.escape(section)}\s*$", text, re.MULTILINE
        ):
            errors.append(f"task_status.md: missing {section} section")
    headers, rows = markdown_rows(text, "Live Agent Status")
    required_headers = {
        "Agent",
        "Task",
        "Agent state",
        "External job state",
        "Evidence",
        "Resource / job ID",
        "Last verified",
        "Next check",
        "Next gate / blocker",
        "Materials",
    }
    if not required_headers.issubset(set(headers)):
        errors.append(
            "task_status.md: live agent table is missing heartbeat/job fields"
        )
        return
    positions = {header: headers.index(header) for header in headers}
    for row in rows:
        agent_state = row[positions["Agent state"]].strip(chr(96))
        job_state = row[positions["External job state"]].strip(chr(96))
        if agent_state not in AGENT_STATES:
            errors.append(f"task_status.md: invalid agent state {agent_state!r}")
        if job_state not in JOB_STATES:
            errors.append(
                f"task_status.md: invalid external job state {job_state!r}"
            )
        for field in ("Last verified", "Next check", "Next gate / blocker"):
            if row[positions[field]].lower() in {"", "none", "unknown", "n/a"}:
                errors.append(f"task_status.md: live row requires {field}")


def validate_reservations(docs: Path, errors: list[str]) -> None:
    text = (docs / "resource_status.md").read_text(encoding="utf-8")
    headers, rows = markdown_rows(text, "Reservations")
    required_headers = {
        "Reservation ID",
        "Task",
        "Resource",
        "Owner",
        "State",
        "Start / expiry",
        "Process/job ID",
        "Last verified",
        "Output path",
        "Release condition",
    }
    if not required_headers.issubset(set(headers)):
        errors.append(
            "resource_status.md: reservation table is missing required fields"
        )
        return
    positions = {header: headers.index(header) for header in headers}
    for row in rows:
        state = row[positions["State"]].strip(chr(96))
        if state not in RESERVATION_STATES:
            errors.append(
                f"resource_status.md: invalid reservation state {state!r}"
            )
        if state in {"reserved", "active"}:
            fields = (
                "Task",
                "Resource",
                "Owner",
                "Start / expiry",
                "Last verified",
                "Output path",
                "Release condition",
            )
            for field in fields:
                if row[positions[field]].lower() in {
                    "",
                    "none",
                    "unknown",
                    "n/a",
                }:
                    errors.append(
                        f"resource_status.md: {state} reservation requires {field}"
                    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only agent-team workflow validator"
    )
    parser.add_argument("--repo", required=True, help="Repository root")
    parser.add_argument(
        "--docs-dir",
        default="agent_team",
        help="Repository-relative workflow directory",
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit result as JSON on stdout"
    )
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    docs_relative = Path(args.docs_dir)
    errors: list[str] = []
    if docs_relative.is_absolute() or ".." in docs_relative.parts:
        errors.append("--docs-dir must be repository-relative")
        docs = repo
    else:
        docs = repo / docs_relative

    if not repo.is_dir():
        errors.append(f"repository does not exist: {repo}")
    elif not docs.is_dir():
        errors.append(f"workflow directory does not exist: {docs_relative}")
    else:
        validate_required_files(docs, errors)
        if not any(
            error.startswith("missing required file") for error in errors
        ):
            validate_setup_and_resources(docs, errors)
            validate_placeholders_and_links(repo, docs, errors)
            validate_secret_like_values(repo, docs, errors)
            validate_retention(repo, docs, errors)
            validate_task_records(repo, docs, errors)
            validate_live_status(docs, errors)
            validate_reservations(docs, errors)

    result = {
        "ok": not errors,
        "errors": errors,
        "repo": str(repo),
        "docs_dir": str(docs_relative),
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for error in errors:
            print(f"ERROR: {error}")
        if errors:
            print(f"FAIL: {len(errors)} validation error(s)")
        else:
            print("PASS: agent-team workflow is valid")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
