import sys
sys.dont_write_bytecode = True

import json
import unittest
import test_workspace
from adapter_sftr import backup_handoff, check_target, inspect_project
from workspace_core import WorkflowError, binding_plan, load_config


class SftrTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_workspace.WorkspaceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        f.settings["adapters"] = {"sftr": {"stores": ["materials"]}}
        f.save_config()
        f.env = load_config(f.config)
        f.populated()
        self.env = f.env
        self.root = f.data / "alpha"
        self.marker = self.root / ".projectcfg"
        self.marker.write_text(json.dumps({"meta": {"name": "Alpha", "version": 9, "backupDate": "20261001"}}))
        self.project = {"store": "materials", "path": "alpha"}

    def test_inspect_does_not_write_or_claim_backup(self):
        before = self.marker.read_bytes()
        result = inspect_project(self.env, "alpha")
        self.assertFalse(result["backup_verified"])
        self.assertFalse(result["writes_performed"])
        self.assertEqual(result["observed_metadata"]["version"], 9)
        self.assertEqual(before, self.marker.read_bytes())

    def test_legacy_marker_is_not_migrated(self):
        self.marker.unlink()
        (self.root / "_CacheInfo").write_bytes(b"legacy")
        self.assertEqual(inspect_project(self.env, "alpha")["format"], "legacy")
        self.assertFalse(self.marker.exists())

    def test_backend_metadata_and_temp_are_protected(self):
        for path, op in ((".projectcfg", "update"), ("_CacheInfo", "delete"), ("_Temp/final.pptx", "promote")):
            with self.subTest(path=path), self.assertRaises(WorkflowError):
                check_target(self.env, self.project, self.root / path, op)

    def test_existing_event_entry_requires_new_name(self):
        (self.root / "_Event Records/old").mkdir(parents=True)
        with self.assertRaises(WorkflowError):
            check_target(self.env, self.project, self.root / "_Event Records/old/new.txt", "create")
        check_target(self.env, self.project, self.root / "_Event Records/new", "promote")

    def test_common_plan_enforces_backend_checks(self):
        from workspace_core import apply_change
        patch = self.fixture.patch(2, "root-scope", [{"collection": "bindings", "id": "b1", "set": {"scope": "."}}])
        apply_change(self.env, patch, True)
        with self.assertRaisesRegex(WorkflowError, "metadata"):
            binding_plan(self.env, "b1", ".projectcfg", "update")

    def test_handoff_stays_planned(self):
        result = backup_handoff(self.env, "alpha")
        self.assertEqual(result["status"], "planned")
        self.assertFalse(result["executed"])
        self.assertEqual(result["backup_unit"], str(self.root))


if __name__ == "__main__":
    unittest.main()
