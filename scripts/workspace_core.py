"""External workspace records. No dataset writes, job execution or background service."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath

PACKAGE = Path(__file__).resolve().parents[1]
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\Z")
PROJECT_FIELDS = {"label", "store", "path", "steward", "lifecycle", "protected", "maintenance"}
BINDING_FIELDS = {"task_id", "task_manifest", "project", "scope", "roles", "state", "writes", "authorization"}


class WorkflowError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: non-empty text required")
    return value


def identity(value):
    require(isinstance(value, str) and bool(ID.fullmatch(value)), f"Invalid ID: {value!r}")
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def within(path, root):
    return path.resolve().is_relative_to(root.resolve())


def overlap(a, b):
    return within(a, b) or within(b, a)


def outside_package(path):
    require(not overlap(path, PACKAGE), f"Writable location overlaps the workflow package: {path}")


def relative(value):
    text(value, "relative path")
    require("\\" not in value and ":" not in value, "Use portable slash-separated relative paths")
    path = PurePosixPath(value)
    require(not path.is_absolute() and not PureWindowsPath(value).drive and ".." not in path.parts,
            f"Path escapes its root: {value}")
    require(not any(part.lower() in {".git", ".research"} for part in path.parts),
            f"Backend metadata is protected: {value}")
    return value


def resolve_under(root, value):
    relative(value)
    target = (root / value).resolve()
    require(within(target, root), f"Symlink/junction escapes root: {value}")
    return target


def load_config(path):
    path = Path(path).expanduser().resolve()
    require(not within(path, PACKAGE), "Put workspace configuration outside the workflow package")
    cfg = read_json(path)
    require(isinstance(cfg, dict) and cfg.get("schema_version") == 2, "Expected schema_version 2")
    require(set(cfg) <= {"schema_version", "workspace", "stores", "repositories", "policy", "adapters"},
            "Unknown configuration field")
    ws = cfg.get("workspace", {})
    require(isinstance(ws, dict), "workspace must be an object")
    identity(ws.get("id"))
    text(ws.get("name"), "workspace.name")
    root = Path(text(ws.get("root"), "workspace.root")).expanduser()
    require(root.is_absolute(), "workspace.root must be absolute")
    root = root.resolve()
    records = resolve_under(root, ws.get("records", "agent_team"))
    runtime = resolve_under(root, ws.get("runtime", ".agent-team-runtime"))
    outside_package(records)
    outside_package(runtime)
    require(not overlap(records, runtime), "Records and runtime must be separate directories")
    require(not within(path, records) and not within(path, runtime), "Keep configuration outside generated records/runtime")
    for group in ("stores", "repositories"):
        entries = cfg.get(group, {})
        require(isinstance(entries, dict), f"{group} must be an object keyed by stable ID")
        for key, entry in entries.items():
            identity(key)
            require(isinstance(entry, dict), f"{group}.{key} must be an object")
            location = Path(text(entry.get("root"), f"{group}.{key}.root")).expanduser()
            require(location.is_absolute(), f"{group}.{key}.root must be absolute")
            if group == "stores":
                require(entry.get("access", "reference") in {"reference", "maintain"}, "Invalid store access")
                require(not overlap(records, location) and not overlap(runtime, location),
                        "Dataset stores must not overlap generated records/runtime")
    require(isinstance(cfg.get("policy"), dict), "policy must be an object")
    for key in ("commit", "external_actions", "acceptance"):
        text(cfg["policy"].get(key), f"policy.{key}")
    adapters = cfg.get("adapters", {})
    require(isinstance(adapters, dict), "adapters must be an object")
    # Adapter modules only validate configuration; importing them never runs a backend.
    for name, settings in adapters.items():
        require(name in {"sftr", "labweft"}, f"Unknown adapter: {name}")
        try:
            from importlib import import_module
            adapter = import_module(f"adapter_{name}")
        except ModuleNotFoundError as exc:
            raise WorkflowError(f"Adapter {name} is not available on this branch") from exc
        adapter.validate_settings(settings, cfg, records, runtime)
    return {"data": cfg, "file": path, "root": root, "records": records, "runtime": runtime}


def project_root(env, project):
    store = env["data"].get("stores", {}).get(project["store"])
    require(store is not None, f"Unknown store: {project['store']}")
    return resolve_under(Path(store["root"]).expanduser().resolve(), project["path"])


def validate_state(env, state, check_local=True):
    require(isinstance(state, dict) and set(state) == {"projects", "bindings"}, "Invalid catalog shape")
    projects, bindings = state["projects"], state["bindings"]
    require(isinstance(projects, dict) and isinstance(bindings, dict), "Catalog collections must be objects")
    for pid, project in projects.items():
        identity(pid)
        require(isinstance(project, dict) and set(project) <= PROJECT_FIELDS, f"Invalid project {pid}")
        for key in ("label", "store", "path", "steward"):
            text(project.get(key), f"{pid}.{key}")
        require(project.get("lifecycle") in {"active", "dormant", "archived"}, "Invalid project lifecycle")
        root = project_root(env, project)
        protected = project.get("protected", [])
        require(isinstance(protected, list), "protected must be an array")
        for value in protected:
            resolve_under(root, value)
    for bid, binding in bindings.items():
        identity(bid)
        require(isinstance(binding, dict) and set(binding) <= BINDING_FIELDS, f"Invalid binding {bid}")
        identity(binding.get("task_id"))
        manifest = resolve_under(env["records"], binding.get("task_manifest"))
        if check_local and binding.get("state") != "retired":
            require(manifest.is_file(), f"Missing task manifest: {manifest}")
            require(re.search(r"(?<![\w.-])" + re.escape(binding["task_id"]) + r"(?![\w.-])",
                              manifest.read_text(encoding="utf-8")), "Task identity missing in manifest")
        require(binding.get("project") in projects, f"Unknown project in binding {bid}")
        project = projects[binding["project"]]
        scope = resolve_under(project_root(env, project), binding.get("scope"))
        roles = binding.get("roles")
        require(isinstance(roles, list) and bool(roles) and all(r in {"reference", "maintain", "promote"} for r in roles),
                "Invalid binding roles")
        require(binding.get("state") in {"proposed", "active", "retired"}, "Invalid binding state")
        writes = binding.get("writes", [])
        require(isinstance(writes, list), "writes must be an array")
        if binding["state"] == "active":
            if check_local:
                require(scope.is_dir(), f"Active binding scope unavailable: {scope}")
            require(project["lifecycle"] == "active", "Active binding requires an active project")
            text(binding.get("authorization"), "active binding authorization")
        if writes:
            require("maintain" in roles or "promote" in roles, "Reference-only binding cannot have writes")
            require(env["data"]["stores"][project["store"]].get("access") == "maintain", "Store is reference-only")
        for rule in writes:
            require(isinstance(rule, dict) and set(rule) == {"path", "recursive", "operations"}, "Invalid write rule")
            target = resolve_under(scope, rule["path"])
            outside_package(target)
            require(not overlap(target, env["records"]) and not overlap(target, env["runtime"]), "Write targets workflow records")
            require(isinstance(rule["recursive"], bool), "recursive must be boolean")
            ops = rule["operations"]
            require(isinstance(ops, list) and bool(ops) and all(op in {"create", "update", "promote", "rename", "delete"} for op in ops),
                    "Invalid write operations")
            require("promote" in roles or "promote" not in ops, "Promote operation needs promote role")
            require("maintain" in roles or all(op == "promote" for op in ops), "Working edits need maintain role")


def make_event(revision, previous, state, change_id, patch_hash, reason):
    body = {"revision": revision, "previous": previous, "state": state, "change_id": change_id,
            "patch_hash": patch_hash, "reason": reason, "at": datetime.now(timezone.utc).isoformat()}
    return {**body, "hash": digest(body)}


def load_catalog(env):
    require(within(env["records"] / "catalog/events", env["records"]), "Catalog path escapes records")
    header = read_json(env["records"] / "workspace.json")
    require(header.get("schema_version") == 2 and header.get("id") == env["data"]["workspace"]["id"],
            "Workspace identity/schema mismatch")
    events = sorted((env["records"] / "catalog" / "events").glob("*.json"))
    require(bool(events), "No catalog events; initialize workspace first")
    previous, seen, last = "", set(), None
    for index, path in enumerate(events):
        event = read_json(path)
        require(path.name == f"{index:08d}.json" and event.get("revision") == index, "Catalog revision gap")
        body = {k: v for k, v in event.items() if k != "hash"}
        require(event.get("previous") == previous and event.get("hash") == digest(body), "Catalog integrity failure")
        require(event["change_id"] not in seen, "Duplicate change ID")
        seen.add(event["change_id"])
        previous, last = event["hash"], event
    validate_state(env, last["state"], check_local=False)
    return last, [read_json(p) for p in events]


@contextmanager
def writer_lock(env):
    path = env["records"] / "catalog/.writer.lock"
    outside_package(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise WorkflowError("Another metadata writer is active") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def initialize(env, apply=False):
    records, runtime = env["records"], env["runtime"]
    plan = {}
    header = {"schema_version": 2, "id": env["data"]["workspace"]["id"], "name": env["data"]["workspace"]["name"]}
    plan[records / "workspace.json"] = json.dumps(header, indent=2) + "\n"
    event = make_event(0, "", {"projects": {}, "bindings": {}}, "initialization", "", "Workspace initialized")
    plan[records / "catalog/events/00000000.json"] = json.dumps(event, ensure_ascii=False, indent=2) + "\n"
    for folder, destination in (("assets/workspace-template", records),
                                ("assets/repo-template/agent_team/tasks/_template", records / "tasks/_template")):
        for source in (PACKAGE / folder).rglob("*"):
            if source.is_file():
                plan[destination / source.relative_to(PACKAGE / folder)] = source.read_text(encoding="utf-8")
    plan[runtime / ".gitignore"] = "*\n!.gitignore\n"
    for path in plan:
        outside_package(path)
        require(within(path, records) or within(path, runtime), "Initialization path escapes workspace outputs")
        require(not path.exists(), f"Initialization collision: {path}")
    if apply:
        for path, content in plan.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    return {"applied": apply, "files": [str(p) for p in plan]}


def apply_change(env, patch, apply=False):
    require(isinstance(patch, dict) and set(patch) == {"base_revision", "change_id", "reason", "changes"}, "Invalid patch envelope")
    identity(patch["change_id"])
    text(patch["reason"], "reason")
    require(type(patch["base_revision"]) is int, "base_revision must be an integer")
    require(isinstance(patch["changes"], list) and bool(patch["changes"]), "Non-empty changes required")

    def prepare():
        last, history = load_catalog(env)
        for event in history:
            if event["change_id"] == patch["change_id"]:
                require(event["patch_hash"] == digest(patch), "Change ID reused with different content")
                return None, {"already_applied": True, "revision": last["revision"]}
        require(last["revision"] == patch["base_revision"], "Stale revision; reload and reconcile")
        state, seen = copy.deepcopy(last["state"]), set()
        for change in patch["changes"]:
            require(isinstance(change, dict) and set(change) == {"collection", "id", "set"}, "Invalid field update")
            collection, key, fields = change["collection"], identity(change["id"]), change["set"]
            require(collection in {"projects", "bindings"}, "Unknown collection")
            require((collection, key) not in seen, "Repeated object in patch")
            seen.add((collection, key))
            require(isinstance(fields, dict) and bool(fields), "set must contain fields")
            state[collection][key] = {**state[collection].get(key, {}), **fields}
        validate_state(env, state)
        event = make_event(last["revision"] + 1, last["hash"], state, patch["change_id"], digest(patch), patch["reason"])
        return event, {"revision": event["revision"], "changes": patch["changes"], "applied": apply}

    if not apply:
        return prepare()[1]
    with writer_lock(env):
        event, result = prepare()
        if event is not None:
            target = env["records"] / "catalog/events" / f"{event['revision']:08d}.json"
            require(not target.exists(), "Concurrent catalog revision")
            # Complete bytes land before the event becomes visible to readers.
            fd, temp = tempfile.mkstemp(prefix=".pending-", dir=target.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(event, handle, ensure_ascii=False, indent=2)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp, target)
            finally:
                if Path(temp).exists():
                    Path(temp).unlink()
        return result


def binding_plan(env, binding_id, requested=None, operation="read"):
    last, _ = load_catalog(env)
    state = last["state"]
    require(binding_id in state["bindings"], "Unknown binding")
    binding = state["bindings"][binding_id]
    project = state["projects"][binding["project"]]
    root = project_root(env, project)
    scope = resolve_under(root, binding["scope"])
    result = {"binding": binding_id, "revision": last["revision"], "scope": str(scope),
              "available": scope.is_dir(), "state": binding["state"], "roles": binding["roles"],
              "writes": binding.get("writes", []), "executes_payload_operations": False}
    if requested is not None:
        target = resolve_under(scope, requested)
        if operation != "read":
            require(binding["state"] == "active", "Writes require active binding")
            require(scope.is_dir(), "Binding scope is unavailable")
            for protected in project.get("protected", []):
                require(not overlap(target, resolve_under(root, protected)), "Target overlaps protected content")
            permitted = any(operation in rule["operations"] and
                            (target == resolve_under(scope, rule["path"]) or
                             (rule["recursive"] and within(target, resolve_under(scope, rule["path"]))))
                            for rule in binding.get("writes", []))
            require(permitted, "Operation is outside binding write rules")
            outside_package(target)
        fingerprint = "absent"
        if target.is_file():
            hasher = hashlib.sha256()
            with target.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    hasher.update(block)
            fingerprint = hasher.hexdigest()
        elif target.exists():
            fingerprint = "directory; select exact files before execution"
        result.update({"target": str(target), "operation": operation, "base_identity": fingerprint})
    return result
