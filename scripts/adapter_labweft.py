"""Read-only LabWeft schema-v1 bridge and external command plans. No backend imports."""
import hashlib
from pathlib import Path

from workspace_core import (PACKAGE, digest, identity, load_catalog, outside_package,
                            overlap, read_json, require, resolve_under, text, within)


def validate_settings(settings, cfg, records, runtime):
    require(isinstance(settings, dict) and set(settings) <= {"tool_root", "python", "projects"}, "Invalid LabWeft settings")
    for key in ("tool_root", "python"):
        require(Path(text(settings.get(key), key)).expanduser().is_absolute(), f"{key} must be absolute")
    tool = Path(settings["tool_root"]).expanduser().resolve()
    require(not overlap(tool, records) and not overlap(tool, runtime), "LabWeft source overlaps workspace outputs")
    projects = settings.get("projects")
    require(isinstance(projects, dict), "LabWeft projects must be keyed by catalog project ID")
    roots = []
    for pid, item in projects.items():
        identity(pid)
        require(isinstance(item, dict) and set(item) <= {"workspace", "project_id", "code", "results"}, "Invalid LabWeft project mapping")
        root = Path(text(item.get("workspace"), "LabWeft workspace")).expanduser()
        require(root.is_absolute(), "LabWeft workspace must be absolute")
        root = root.resolve()
        outside_package(root)
        require(not overlap(root, tool) and not overlap(root, records) and not overlap(root, runtime),
                "Research workspace must be separate from tools and team records/runtime")
        require(not any(overlap(root, other) for other in roots), "Research workspace mappings overlap")
        roots.append(root)
        if item.get("project_id") is not None:
            text(item["project_id"], "LabWeft project_id")
        for key in ("code", "results"):
            if key in item:
                source = Path(text(item[key], key)).expanduser()
                require(source.is_absolute(), "Research sources must be absolute")
                require(not overlap(source, root), "Bootstrap sources must be separate from the research workspace")


def mapping(env, project_id):
    settings = env["data"].get("adapters", {}).get("labweft")
    require(settings is not None, "Enable adapters.labweft")
    last, _ = load_catalog(env)
    require(project_id in last["state"]["projects"], "Unknown catalog project")
    require(project_id in settings["projects"], "Project has no LabWeft mapping")
    return settings, settings["projects"][project_id]


def inspect_project(env, project_id, checkpoint=None):
    _, item = mapping(env, project_id)
    root = Path(item["workspace"]).expanduser().resolve()
    research = root / ".research"
    require(within(research, root), "Research metadata escapes workspace")
    manifest = research / "manifest.json"
    if not manifest.is_file():
        return {"project": project_id, "initialized": False, "needs_review": True, "reason": "Initialize external research workspace"}
    project = read_json(manifest)
    require(project.get("schema_version") == 1, "Unsupported LabWeft schema; adapt explicitly")
    require(item.get("project_id") == project.get("id"), "Pin the observed LabWeft project_id in external config before using its records")
    files, nodes, previous, revision = {}, {}, "", 0
    events = sorted((research / "events").glob("*.json"))
    for path in events:
        require(within(path, research), "Event path escapes research workspace")
        event = read_json(path)
        revision += 1
        require(path.name == f"{revision:08d}.json" and event.get("revision") == revision, "LabWeft revision gap")
        require(event.get("previous_hash") == previous and event.get("hash") == digest({k: v for k, v in event.items() if k != "hash"}),
                "LabWeft event integrity failure")
        previous = event["hash"]
        for entry in event.get("files", []):
            files[entry["id"]] = entry
        for entry in event.get("nodes", []):
            nodes[entry["id"]] = entry
    require(within(research / "local.json", research), "Source mapping escapes research workspace")
    sources = read_json(research / "local.json").get("sources", {})
    require(isinstance(sources, dict), "Invalid LabWeft source mapping")
    require(len(files) <= 10000, "Recorded file count exceeds bridge inspection budget")
    observed, changed, unverified, unavailable = {}, [], [], []
    total = 0
    for fid, entry in sorted(files.items()):
        alias = entry["source"]
        if alias not in sources:
            observed[fid] = "unmapped"
            unavailable.append(fid)
            continue
        source = Path(sources[alias]).expanduser()
        if not source.is_absolute():
            source = root / source
        target = resolve_under(source.resolve(), entry["path"])
        if not target.is_file():
            observed[fid] = "missing"
            if not entry.get("missing"):
                changed.append(fid)
            continue
        size = target.stat().st_size
        if entry.get("sha256") and size <= 2 * 1024 * 1024 and total + size <= 32 * 1024 * 1024:
            raw = target.read_bytes()
            require(len(raw) <= 2 * 1024 * 1024, "Source changed beyond inspection size budget")
            total += len(raw)
            observed[fid] = hashlib.sha256(raw).hexdigest()
            if observed[fid] != entry["sha256"] or entry.get("missing"):
                changed.append(fid)
        else:
            observed[fid] = {"size": size, "content_verified": False}
            unverified.append(fid)
            if size != entry.get("size") or entry.get("missing"):
                changed.append(fid)
    review_files = set(changed) | set(unavailable) | set(unverified)
    affected = sorted(nid for nid, node in nodes.items()
                      if any(ref.get("file_id") in review_files for ref in node.get("evidence", [])))
    source_state = digest({"sources": sources, "observed": observed})
    result = {"project": project_id, "labweft_project_id": project["id"], "initialized": True,
              "revision": revision, "event_hash": previous, "source_state_hash": source_state,
              "changed_file_ids": changed, "directly_affected_node_ids": affected,
              "unavailable_source_file_ids": unavailable,
              "content_unverified_file_ids": unverified, "coverage": "recorded-files-only",
              "semantics_verified": False, "needs_review": True,
              "note": "No discovery of unrecorded files or transitive semantic completeness; run backend sync/validate and review affected conclusions."}
    if checkpoint:
        saved = read_json(checkpoint)
        require(saved.get("project") == project_id and saved.get("labweft_project_id") == project["id"], "Checkpoint identity mismatch")
        unchanged = all(saved.get(k) == result[k] for k in ("revision", "event_hash", "source_state_hash"))
        result["unchanged_since_checkpoint"] = unchanged
        result["needs_review"] = not unchanged or bool(review_files)
    return result


def command_plan(env, project_id, operation, patch=None):
    settings, item = mapping(env, project_id)
    tool = Path(settings["tool_root"]).expanduser().resolve()
    interpreter = Path(settings["python"]).expanduser().resolve()
    require(interpreter.is_file(), "Configured Python executable does not exist")
    require((tool / "labweft.py").is_file(), "LabWeft launcher not found")
    workspace = str(Path(item["workspace"]).expanduser().resolve())
    base = [str(interpreter), "-B", str(tool / "labweft.py")]
    if operation == "bootstrap":
        require(not (Path(workspace) / ".research/manifest.json").exists(), "Workspace already initialized; use sync")
        require("code" in item and Path(item["code"]).is_dir(), "Bootstrap requires an existing configured code directory")
        argv = [str(interpreter), "-B", str(tool / "bootstrap.py"), "--project", item["code"], "--workspace", workspace, "--agent", "codex"]
        if "results" in item:
            require(Path(item["results"]).is_dir(), "Results directory is unavailable")
            argv.extend(["--results", item["results"]])
    else:
        observed = inspect_project(env, project_id)
        require(observed["initialized"], "Initialize the research workspace first")
        argv = base + [operation, workspace]
        if operation == "apply":
            require(patch is not None, "Semantic apply requires an external patch file")
            patch = Path(patch).expanduser().resolve()
            require(not within(patch, PACKAGE) and not within(patch, tool), "Keep semantic patches outside tool repositories")
            data = read_json(patch)
            require(data.get("base_revision") == observed["revision"], "Semantic patch has a stale base revision")
            argv.append(str(patch))
        if operation == "export":
            argv.extend(["--output", str(env["runtime"] / f"{project_id}-research.html")])
    require(operation in {"bootstrap", "sync", "context", "validate", "export", "apply"}, "Unsupported operation")
    return {"project": project_id, "argv": argv, "cwd": str(env["root"]), "executed": False,
            "writes_research_records": operation in {"bootstrap", "sync", "apply"},
            "note": "Run through the external task executor; recheck state before writes. Python must be 3.11+. Export omits evidence text by default."}
