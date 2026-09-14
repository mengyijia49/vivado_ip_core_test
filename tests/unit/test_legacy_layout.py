import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/maintenance/archive_legacy_layout.py"
SPEC = importlib.util.spec_from_file_location("archive_legacy_layout", SOURCE)
MAINTENANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAINTENANCE)


class LegacyLayoutTests(unittest.TestCase):
    def test_plans_moves_without_touching_current_or_history(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("runs/logs", "runs/history", "runs/current", "runs/batches", "runs/old_case"):
                (root / name).mkdir(parents=True)
            (root / "runs/old_case/manifest.json").write_text(json.dumps({"ip_type": "divider"}))
            (root / "runs/logs/old_case_create.log").write_text("old log")
            (root / "runs/history/proof.txt").write_text("unchanged")
            plan = MAINTENANCE.migration_plan(root, "batch")
            self.assertEqual(len(plan), 2)
            self.assertEqual(plan[0][1], root / "runs/legacy/batch/ip/divider/old_case")
            self.assertEqual((root / "runs/history/proof.txt").read_text(), "unchanged")
            self.assertTrue((root / "runs/old_case").is_dir())

    def test_digest_detects_content_change_but_not_parent_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (source / "test.txt").write_text("old")
            digest = MAINTENANCE.content_digest(source)
            target = root / "target"
            source.rename(target)
            self.assertEqual(MAINTENANCE.content_digest(target), digest)
            (target / "test.txt").write_text("changed")
            self.assertNotEqual(MAINTENANCE.content_digest(target), digest)

    def test_refuses_unclassified_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "runs/logs").mkdir(parents=True)
            (root / "runs/user_material").mkdir()
            with self.assertRaisesRegex(ValueError, "不能自动归类"):
                MAINTENANCE.migration_plan(root, "batch")
