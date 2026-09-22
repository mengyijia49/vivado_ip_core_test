from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest

from vivado_ip_test.configuration import ConfigError
from vivado_ip_test.domain import StageResult, Status
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.services import RunRecorder
from vivado_ip_test.services.resume import remaining_cases
from unit.test_pipeline import make_case


class ResumeTests(unittest.TestCase):
    def record(self, root, *, fail=False, interrupt=False):
        layout = RepositoryLayout(root)
        source = root / "src/driver.py"
        source.parent.mkdir(exist_ok=True)
        source.write_text("original")
        log = layout.log_dir / "test.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text("result")
        case = make_case()
        with RunRecorder(layout, [case]) as recorder:
            stages = case.stages[:1] if interrupt else case.stages
            for stage in stages:
                recorder.capture(StageResult(case.case_id, stage,
                    Status.SIMULATION_FAILED if fail else Status.PASS,
                    layout.case_run_dir(case), log))
        return layout, recorder.report_dir / "run.json"

    def test_only_skips_fully_passed_identical_cases(self):
        with tempfile.TemporaryDirectory() as directory:
            layout, record = self.record(Path(directory))
            changed_seed = replace(make_case(), verification=replace(make_case().verification, random_seed=999))
            self.assertEqual(remaining_cases(layout, [make_case(), changed_seed], [record]), [changed_seed])

    def test_retries_failed_or_incomplete_cases(self):
        for fail, interrupt in ((True, False), (False, True)):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as directory:
                layout, record = self.record(Path(directory), fail=fail, interrupt=interrupt)
                self.assertEqual(remaining_cases(layout, [make_case()], [record]), [make_case()])

    def test_refuses_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout, record = self.record(root)
            (root / "src/driver.py").write_text("changed")
            with self.assertRaisesRegex(ConfigError, "源码"):
                remaining_cases(layout, [make_case()], [record])

    def test_refuses_corrupted_or_deleted_artifacts(self):
        for deleted in (True, False):
            with self.subTest(deleted=deleted), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                layout, record = self.record(root)
                archived_source = next((root / "runs/history").glob("*/source/src/driver.py"))
                if deleted:
                    archived_source.unlink()
                else:
                    archived_source.write_text("corrupted")
                with self.assertRaises(ConfigError):
                    remaining_cases(layout, [make_case()], [record])

    def test_resume_rejects_a_different_vivado_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = RepositoryLayout(root, vivado_version="2026.0")
            case = make_case()
            log = old.stage_log_path(case, case.stages[0])
            with RunRecorder(old, [case]) as recorder:
                log.parent.mkdir(parents=True)
                log.write_text("PASS")
                for stage in case.stages:
                    recorder.capture(StageResult(case.case_id, stage, Status.PASS,
                                                 old.case_run_dir(case), log))
            record = recorder.report_dir / "run.json"
            self.assertEqual(remaining_cases(old, [case], [record]), [])
            current = RepositoryLayout(root, vivado_version="2026.1")
            with self.assertRaisesRegex(ConfigError, "版本不匹配"):
                remaining_cases(current, [case], [record])

    def test_legacy_record_uses_its_recorded_executable_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout, path = self.record(root)
            metadata = json.loads(path.read_text())
            metadata.pop("vivado_version")
            metadata["vivado_executable"] = "/data/Xilinx/2026.0/Vivado/bin/vivado"
            path.write_text(json.dumps(metadata))
            self.assertEqual(remaining_cases(RepositoryLayout(root, vivado_version="2026.0"),
                                             [make_case()], [path]), [])
            with self.assertRaisesRegex(ConfigError, "版本不匹配"):
                remaining_cases(RepositoryLayout(root, vivado_version="2026.1"),
                                [make_case()], [path])
