import sys
sys.dont_write_bytecode = True

import hashlib
import json
import subprocess
import unittest
import test_workspace
from adapter_labweft import command_plan, inspect_project
from workspace_core import WorkflowError, digest, load_config


class LabweftTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workspace.WorkspaceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.tool = f.root / "LabWeft"
        self.tool.mkdir()
        (self.tool / "labweft.py").write_text("raise RuntimeError('must never execute')")
        self.research = f.root / "research/.research"
        (self.research / "events").mkdir(parents=True)
        self.source = f.data / "alpha/slides/talk.txt"
        self.source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        (self.research / "manifest.json").write_text(json.dumps({"schema_version": 1, "id": "research-alpha"}))
        (self.research / "local.json").write_text(json.dumps({"sources": {"code": str(self.source.parent)}}))
        self.event = {"revision": 1, "previous_hash": "", "at": "2026-10-14", "actor": "test", "reason": "fixture",
                      "files": [{"id": "file-a", "source": "code", "path": "talk.txt", "size": self.source.stat().st_size,
                                 "sha256": self.source_hash, "missing": False}],
                      "nodes": [{"id": "claim-a", "evidence": [{"file_id": "file-a", "sha256": self.source_hash}]}]}
        self.write_event()
        f.settings["adapters"] = {"labweft": {"tool_root": str(self.tool), "python": sys.executable,
            "projects": {"alpha": {"workspace": str(self.research.parent), "project_id": "research-alpha"}}}}
        f.save_config()
        f.env = load_config(f.config)
        f.populated()
        self.env = f.env

    def write_event(self):
        self.event["hash"] = digest({k: v for k, v in self.event.items() if k != "hash"})
        (self.research / "events/00000001.json").write_text(json.dumps(self.event))

    def test_source_change_invalidates_checkpoint_and_reports_nodes(self):
        observed = inspect_project(self.env, "alpha")
        checkpoint = self.fixture.root / "checkpoint.json"
        checkpoint.write_text(json.dumps(observed))
        stable = inspect_project(self.env, "alpha", checkpoint)
        self.assertTrue(stable["unchanged_since_checkpoint"])
        self.assertFalse(stable["semantics_verified"])
        self.source.write_text("modified source")
        changed = inspect_project(self.env, "alpha", checkpoint)
        self.assertTrue(changed["needs_review"])
        self.assertFalse(changed["unchanged_since_checkpoint"])
        self.assertEqual(changed["directly_affected_node_ids"], ["claim-a"])

    def test_binary_metadata_is_not_content_verification(self):
        self.event["files"][0]["sha256"] = None
        self.write_event()
        result = inspect_project(self.env, "alpha")
        self.assertEqual(result["content_unverified_file_ids"], ["file-a"])
        self.assertFalse(result["semantics_verified"])

    def test_snapshot_only_source_is_not_called_modified(self):
        self.event["files"][0]["source"] = "synthetic-snapshot"
        self.write_event()
        result = inspect_project(self.env, "alpha")
        self.assertEqual(result["changed_file_ids"], [])
        self.assertEqual(result["unavailable_source_file_ids"], ["file-a"])
        self.assertTrue(result["needs_review"])

    def test_changed_identity_rejected(self):
        (self.research / "manifest.json").write_text(json.dumps({"schema_version": 1, "id": "other"}))
        with self.assertRaises(WorkflowError):
            inspect_project(self.env, "alpha")

    def test_tampered_backend_event_rejected(self):
        path = self.research / "events/00000001.json"
        event = json.loads(path.read_text())
        event["reason"] = "tampered"
        path.write_text(json.dumps(event))
        with self.assertRaises(WorkflowError):
            inspect_project(self.env, "alpha")

    def test_plan_never_executes_backend(self):
        result = command_plan(self.env, "alpha", "sync")
        self.assertFalse(result["executed"])
        self.assertEqual(result["argv"][-2:], ["sync", str(self.research.parent)])

    def test_semantic_patch_revision_checked(self):
        patch = self.fixture.root / "patch.json"
        patch.write_text(json.dumps({"base_revision": 0, "reason": "test", "nodes": []}))
        with self.assertRaises(WorkflowError):
            command_plan(self.env, "alpha", "apply", patch)
        patch.write_text(json.dumps({"base_revision": 1, "reason": "test", "nodes": []}))
        self.assertFalse(command_plan(self.env, "alpha", "apply", patch)["executed"])

    def test_checkpoint_preview_and_collision(self):
        script = test_workspace.SCRIPTS / "labweft_bridge.py"
        argv = [sys.executable, "-B", str(script), "--config", str(self.fixture.config), "--project", "alpha",
                "checkpoint", "--output", "alpha/check.json"]
        target = self.env["records"] / "receipts/alpha/check.json"
        run = subprocess.run(argv, capture_output=True, text=True, cwd=self.fixture.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(target.exists())
        run = subprocess.run(argv + ["--apply"], capture_output=True, text=True, cwd=self.fixture.root)
        self.assertEqual(run.returncode, 0, run.stderr)
        before = target.read_bytes()
        run = subprocess.run(argv + ["--apply"], capture_output=True, text=True, cwd=self.fixture.root)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual(before, target.read_bytes())

    def test_source_mapping_cannot_escape_with_relative_paths(self):
        self.event["files"][0]["path"] = "../secret.txt"
        self.write_event()
        with self.assertRaises(WorkflowError):
            inspect_project(self.env, "alpha")


if __name__ == "__main__":
    unittest.main()
