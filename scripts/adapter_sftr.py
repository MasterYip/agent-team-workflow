"""Inspect ProjectKeeper metadata directly. Never import ProjectKeeper classes."""
from pathlib import Path

from workspace_core import (load_catalog, overlap, project_root, read_json, require,
                            resolve_under, text, within)


def validate_settings(settings, cfg, records, runtime):
    require(isinstance(settings, dict) and set(settings) <= {"stores", "projectkeeper_root"}, "Invalid SFTR settings")
    stores = settings.get("stores")
    require(isinstance(stores, list) and bool(stores) and all(s in cfg.get("stores", {}) for s in stores),
            "SFTR stores must reference configured store IDs")
    if "projectkeeper_root" in settings:
        path = Path(text(settings["projectkeeper_root"], "projectkeeper_root")).expanduser()
        require(path.is_absolute(), "ProjectKeeper root must be absolute")
        require(not overlap(path, records) and not overlap(path, runtime), "ProjectKeeper source overlaps workspace outputs")


def settings(env):
    result = env["data"].get("adapters", {}).get("sftr")
    require(result is not None, "Enable adapters.sftr in the external configuration")
    return result


def check_target(env, project, target, operation):
    if project["store"] not in settings(env)["stores"] or operation == "read":
        return
    root = project_root(env, project)
    for name in (".projectcfg", "_CacheInfo"):
        require(not overlap(target, root / name), "ProjectKeeper metadata is protected")
    if operation == "promote":
        require(not overlap(target, root / "_Temp"), "Do not promote durable deliverables into SFTR _Temp")
    event_root = root / "_Event Records"
    if within(target, event_root):
        require(operation in {"create", "promote"}, "Event packages are immutable; select a new release name")
        require(not target.exists(), "Do not overwrite existing event packages")
        parts = target.relative_to(event_root).parts
        require(bool(parts) and not (event_root / parts[0]).exists(), "Existing event entry requires a new release name")


def inspect_project(env, project_id):
    config = settings(env)
    last, _ = load_catalog(env)
    require(project_id in last["state"]["projects"], "Unknown project")
    project = last["state"]["projects"][project_id]
    require(project["store"] in config["stores"], "Project is not mapped to an SFTR store")
    root = project_root(env, project)
    require(root.is_dir(), "SFTR project is unavailable")
    cfg_path = resolve_under(root, ".projectcfg")
    legacy = resolve_under(root, "_CacheInfo")
    result = {"project": project_id, "project_root": str(root), "catalog_revision": last["revision"],
              "backup_verified": False, "writes_performed": False}
    if cfg_path.is_file():
        require(cfg_path.stat().st_size <= 8 * 1024 * 1024, "Project metadata exceeds inspection limit")
        data = read_json(cfg_path)
        require(isinstance(data, dict) and isinstance(data.get("meta"), dict), "Invalid .projectcfg metadata")
        result["format"] = "projectcfg"
        result["observed_metadata"] = {k: data["meta"].get(k) for k in ("name", "type", "version", "backupDate", "writeDate")}
    elif legacy.is_file():
        result.update(format="legacy", note="Legacy marker observed; no conversion or ProjectKeeper constructor invoked")
    else:
        result.update(format="unrecognized", note="Select the existing parent ProjectKeeper project; a task subfolder is not a new project")
    return result


def backup_handoff(env, project_id):
    observed = inspect_project(env, project_id)
    require(observed["format"] != "unrecognized", "No ProjectKeeper project marker at mapped root")
    return {"project": project_id, "backup_unit": observed["project_root"], "status": "planned",
            "backend": "ProjectKeeper", "executed": False,
            "source_observation": observed,
            "required_external_steps": [
                "Select a backend operation after inspecting its behavior and destination.",
                "Attach the accepted delivery receipt and exact affected paths/hashes.",
                "Check prior archives and avoid same-day backup destination collisions.",
                "Execute the authorized backup outside the workflow tool.",
                "Verify actual archive/payload and a bounded restore/hash check before recording verified."],
            "note": "A project backupDate/version is an observation, not proof of a recoverable backup."}
