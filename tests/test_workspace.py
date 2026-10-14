import sys

sys.dont_write_bytecode = True

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from workspace_core import (PACKAGE, WorkflowError, apply_change, binding_plan,
                            initialize, load_catalog, load_config, validate_state, writer_lock)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        (self.data / "alpha/slides/private").mkdir(parents=True)
        (self.data / "alpha/slides/talk.txt").write_text("original", encoding="utf-8")
        self.config = self.root / "config.json"
        self.settings = {
            "schema_version": 2,
            "workspace": {"id": "team", "name": "Team", "root": str(self.root / "team")},
            "stores": {"materials": {"root": str(self.data), "access": "maintain"}},
            "repositories": {},
            "policy": {"commit": "local", "external_actions": "task authority", "acceptance": "reviewer"},
            "adapters": {},
        }
        self.save_config()
        self.env = load_config(self.config)

    def save_config(self):
        self.config.write_text(json.dumps(self.settings), encoding="utf-8")

    def patch(self, revision=0, change_id="add-project", changes=None):
        return {"base_revision": revision, "change_id": change_id, "reason": "test",
                "changes": changes or [{"collection": "projects", "id": "alpha", "set": {
                    "label": "Alpha", "store": "materials", "path": "alpha", "steward": "owner",
                    "lifecycle": "active", "protected": ["slides/private"], "maintenance": "preserve sources"}}]}

    def populated(self):
        initialize(self.env, True)
        apply_change(self.env, self.patch(), True)
        manifest = self.env["records"] / "tasks/DOC-001/goal_manifest.md"
        manifest.parent.mkdir(parents=True)
        manifest.write_text("# DOC-001\nScoped task", encoding="utf-8")
        binding = {"task_id": "DOC-001", "task_manifest": "tasks/DOC-001/goal_manifest.md", "project": "alpha",
                   "scope": "slides", "roles": ["reference", "maintain"], "state": "active",
                   "authorization": "user authorized edits to slides",
                   "writes": [{"path": ".", "recursive": True, "operations": ["update", "create"]}]}
        apply_change(self.env, self.patch(1, "bind", [{"collection": "bindings", "id": "b1", "set": binding}]), True)

    def test_preview_writes_nothing(self):
        result = initialize(self.env)
        self.assertFalse(result["applied"])
        self.assertFalse(self.env["root"].exists())

    def test_initialization_collision_preserves_data(self):
        initialize(self.env, True)
        before = (self.env["records"] / "workspace.json").read_bytes()
        with self.assertRaisesRegex(WorkflowError, "collision"):
            initialize(self.env, True)
        self.assertEqual(before, (self.env["records"] / "workspace.json").read_bytes())

    def test_workspace_isolated_and_package_untouched(self):
        before = {str(p): p.stat().st_mtime_ns for p in PACKAGE.rglob("*") if p.is_file() and ".git" not in p.parts}
        initialize(self.env, True)
        apply_change(self.env, self.patch(), True)
        after = {str(p): p.stat().st_mtime_ns for p in PACKAGE.rglob("*") if p.is_file() and ".git" not in p.parts}
        self.assertEqual(before, after)
        self.settings["workspace"].update(id="other", root=str(self.root / "other"))
        self.save_config()
        other = load_config(self.config)
        initialize(other, True)
        self.assertEqual(load_catalog(other)[0]["revision"], 0)
        self.assertEqual(load_catalog(self.env)[0]["revision"], 1)

    def test_reject_package_config_and_destination(self):
        with self.assertRaises(WorkflowError):
            load_config(PACKAGE / "assets/workspace.example.json")
        self.settings["workspace"]["root"] = str(PACKAGE)
        self.save_config()
        with self.assertRaises(WorkflowError):
            load_config(self.config)

    def test_reject_traversal_and_overlapping_roots(self):
        for path in ("../escape", "C:/escape", "\\\\host\\share", "/absolute", ".git/state"):
            with self.subTest(path=path):
                self.settings["workspace"]["records"] = path
                self.save_config()
                with self.assertRaises(WorkflowError):
                    load_config(self.config)
        self.settings["workspace"]["records"] = ".agent-team-runtime/sub"
        self.save_config()
        with self.assertRaises(WorkflowError):
            load_config(self.config)

    def test_store_overlap_rejected(self):
        self.settings["stores"]["materials"]["root"] = self.settings["workspace"]["root"]
        self.save_config()
        with self.assertRaises(WorkflowError):
            load_config(self.config)

    def test_field_update_preserves_other_fields_and_idempotence(self):
        initialize(self.env, True)
        apply_change(self.env, self.patch(), True)
        patch = self.patch(1, "rename", [{"collection": "projects", "id": "alpha", "set": {"label": "New name"}}])
        self.assertFalse(apply_change(self.env, patch)["applied"])
        self.assertEqual(load_catalog(self.env)[0]["revision"], 1)
        apply_change(self.env, patch, True)
        self.assertEqual(load_catalog(self.env)[0]["state"]["projects"]["alpha"]["maintenance"], "preserve sources")
        self.assertTrue(apply_change(self.env, patch, True)["already_applied"])
        patch["reason"] = "different request"
        with self.assertRaises(WorkflowError):
            apply_change(self.env, patch, True)

    def test_stale_update_does_not_append(self):
        initialize(self.env, True)
        apply_change(self.env, self.patch(), True)
        with self.assertRaisesRegex(WorkflowError, "Stale"):
            apply_change(self.env, self.patch(change_id="stale"), True)
        self.assertEqual(load_catalog(self.env)[0]["revision"], 1)

    def test_unknown_field_rejected(self):
        initialize(self.env, True)
        patch = self.patch()
        patch["changes"][0]["set"]["lifecyle"] = "active"
        with self.assertRaises(WorkflowError):
            apply_change(self.env, patch, True)

    def test_lock_blocks_second_writer(self):
        initialize(self.env, True)
        with writer_lock(self.env):
            with self.assertRaises(WorkflowError):
                apply_change(self.env, self.patch(), True)

    def test_tampered_event_detected(self):
        initialize(self.env, True)
        target = self.env["records"] / "catalog/events/00000000.json"
        event = json.loads(target.read_text())
        event["reason"] = "tampered"
        target.write_text(json.dumps(event))
        with self.assertRaisesRegex(WorkflowError, "integrity"):
            load_catalog(self.env)

    def test_plan_hashes_without_modifying_payload(self):
        self.populated()
        target = self.data / "alpha/slides/talk.txt"
        before = target.read_bytes()
        result = binding_plan(self.env, "b1", "talk.txt", "update")
        self.assertEqual(len(result["base_identity"]), 64)
        self.assertFalse(result["executes_payload_operations"])
        self.assertEqual(before, target.read_bytes())
        self.assertEqual(binding_plan(self.env, "b1", "new.txt", "create")["base_identity"], "absent")

    def test_protected_paths_and_scope_escape(self):
        self.populated()
        for name in ("private/secret.txt", "../outside.txt", ".git/config"):
            with self.subTest(name=name), self.assertRaises(WorkflowError):
                binding_plan(self.env, "b1", name, "update")

    def test_reference_binding_cannot_write(self):
        self.populated()
        patch = self.patch(2, "reference", [{"collection": "bindings", "id": "b1", "set": {"roles": ["reference"]}}])
        with self.assertRaises(WorkflowError):
            apply_change(self.env, patch, True)
        patch["changes"][0]["set"]["writes"] = []
        apply_change(self.env, patch, True)
        with self.assertRaises(WorkflowError):
            binding_plan(self.env, "b1", "talk.txt", "update")

    def test_symlink_escape(self):
        self.populated()
        link = self.data / "alpha/slides/escape"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except OSError:
            self.skipTest("Host does not permit symlink creation")
        with self.assertRaises(WorkflowError):
            binding_plan(self.env, "b1", "escape/config.json", "update")

    def test_cli_works_from_external_directory(self):
        proc = subprocess.run([sys.executable, "-B", str(SCRIPTS / "workflow.py"), "--config", str(self.config), "init"],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["applied"])

    def test_workspace_identity_and_missing_manifest(self):
        self.populated()
        (self.env["records"] / "tasks/DOC-001/goal_manifest.md").unlink()
        state = load_catalog(self.env)[0]["state"]
        with self.assertRaises(WorkflowError):
            validate_state(self.env, state)
        apply_change(self.env, self.patch(2, "retire", [{"collection": "bindings", "id": "b1", "set": {"state": "retired"}}]), True)


if __name__ == "__main__":
    unittest.main()
