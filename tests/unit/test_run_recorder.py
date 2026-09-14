import json
from pathlib import Path
import tempfile
import unittest
from dataclasses import replace

from vivado_ip_test.domain import Stage, StageResult, Status
from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file
from vivado_ip_test.infrastructure.workspace_lock import WorkspaceBusy, workspace_lock
from vivado_ip_test.services import RunRecorder
from unit.test_pipeline import make_case
from vivado_ip_test.configuration import load_test_cases


class RunRecorderTests(unittest.TestCase):
    def test_multi_ip_archive_preserves_order_without_mixing_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = [make_case(), replace(make_case(), case_id="second", ip_type="other"),
                     replace(make_case(), case_id="third")]
            with RunRecorder(RepositoryLayout(root), cases) as recorder:
                pass
            config_path = recorder.artifact_dir / "ip_matrix.json"
            config = json.loads(config_path.read_text())
            self.assertNotIn("cases", config)
            self.assertEqual(len(config["includes"]), 3)
            self.assertEqual(load_test_cases(config_path), cases)
            for path in config["includes"]:
                child_cases = load_test_cases(config_path.parent / path)
                self.assertEqual(len({case.ip_type for case in child_cases}), 1)

    def test_missing_main_log_still_archives_process_diagnostics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "runs/logs/create.log"
            log.parent.mkdir(parents=True)
            log.with_suffix(".process.log").write_text("VIVADO_NOT_FOUND")
            log.with_suffix(".invocation.json").write_text('{"state": "unavailable"}')
            result = StageResult(
                case_id=make_case().case_id, stage=Stage.CREATE_IP,
                status=Status.VIVADO_NOT_FOUND, run_dir=root / "runs/case", log_path=log,
            )
            with RunRecorder(RepositoryLayout(root), [make_case()]) as recorder:
                recorder.capture(result)
            destination = recorder.log_dir / make_case().ip_type / make_case().case_id / "create_ip"
            self.assertFalse((destination / "create.log").exists())
            self.assertEqual((destination / "create.process.log").read_text(), "VIVADO_NOT_FOUND")
            self.assertEqual(json.loads((destination / "create.invocation.json").read_text())["state"], "unavailable")

    def test_archives_failure_and_survives_next_run_overwrites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout = RepositoryLayout(root)
            source = root / "src/module.py"
            source.parent.mkdir(parents=True)
            source.write_text("original source")
            log = layout.log_dir / "case_sim.log"
            log.parent.mkdir(parents=True)
            log.write_text("mismatch at output 7 expected=01 actual=X1")
            result = StageResult(
                case_id=make_case().case_id, stage=Stage.SIM_DEMO,
                status=Status.LOG_CHECK_FAILED,
                run_dir=layout.case_run_dir(make_case()), log_path=log,
            )
            with RunRecorder(layout, [make_case()]) as first:
                first.capture(result)
            original = (first.report_dir / "run.json").read_bytes()
            log.write_text("next run passes")
            source.write_text("new source")
            with RunRecorder(RepositoryLayout(root), [make_case()]) as second:
                second.capture(result)
            self.assertNotEqual(first.run_id, second.run_id)
            self.assertEqual((first.report_dir / "run.json").read_bytes(), original)
            self.assertEqual((first.artifact_dir / "source/src/module.py").read_text(), "original source")
            record = json.loads(original)
            self.assertEqual(record["outcome"], "FAILURES_OBSERVED")
            self.assertEqual(record["observed_failures"][0]["status"], "LOG_CHECK_FAILED")
            for relative, digest in record["artifact_sha256"].items():
                self.assertEqual(sha256_file(root / relative), digest)
            config = json.loads((first.artifact_dir / "ip_matrix.json").read_text())
            self.assertEqual(config["cases"][0]["verification"], make_case().verification.as_dict())
            archived_results = json.loads((first.report_dir / "report.json").read_text())
            self.assertIn("actual=X1", Path(archived_results[0]["log_path"]).read_text())

    def test_new_run_preserves_working_files_and_updates_latest_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_layout = RepositoryLayout(root)
            with RunRecorder(first_layout, [make_case()]) as first:
                working = first_layout.case_run_dir(make_case()) / "proj/generated.txt"
                working.parent.mkdir(parents=True)
                working.write_text("first run")
                log = first_layout.stage_log_path(make_case(), Stage.CREATE_IP)
                log.parent.mkdir(parents=True)
                log.write_text("first log")
                self.assertEqual(first.run_id, first_layout.run_id)
            report = (first.report_dir / "run.json").read_bytes()
            second_layout = RepositoryLayout(root)
            with RunRecorder(second_layout, [make_case()]) as second:
                self.assertEqual((root / "reports/latest").resolve(), second.report_dir)
                self.assertEqual(json.loads((root / "reports/latest/report.json").read_text()), [])
            self.assertEqual(working.read_text(), "first run")
            self.assertEqual(log.read_text(), "first log")
            self.assertEqual((first.report_dir / "run.json").read_bytes(), report)
            self.assertFalse(second_layout.case_run_dir(make_case()).exists())
            with self.assertRaises(FileExistsError):
                with RunRecorder(first_layout, [make_case()]):
                    self.fail("不能复用运行编号覆盖旧产物")
            self.assertEqual((root / "reports/latest").resolve(), second.report_dir)

    def test_preserves_old_latest_directory_when_publishing_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest = root / "reports/latest"
            latest.mkdir(parents=True)
            (latest / "report.csv").write_text("old report")
            with RunRecorder(RepositoryLayout(root), [make_case()]) as recorder:
                pass
            backup = root / "reports/legacy" / recorder.run_id / "latest/report.csv"
            self.assertEqual(backup.read_text(), "old report")
            self.assertTrue(latest.is_symlink())
            self.assertEqual(latest.resolve(), recorder.report_dir)

    def test_replaces_broken_latest_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            latest = root / "reports/latest"
            latest.parent.mkdir(parents=True)
            latest.symlink_to("history/missing", target_is_directory=True)
            with RunRecorder(RepositoryLayout(root), [make_case()]) as recorder:
                self.assertEqual(latest.resolve(), recorder.report_dir)

    def test_interrupted_run_is_not_a_success(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = RunRecorder(RepositoryLayout(Path(directory)), [make_case()])
            with self.assertRaises(KeyboardInterrupt):
                with recorder:
                    raise KeyboardInterrupt()
            metadata = json.loads((recorder.report_dir / "run.json").read_text())
            self.assertEqual(metadata["state"], "interrupted")
            self.assertEqual(metadata["outcome"], "INCOMPLETE")

    def test_missing_stages_are_not_reported_as_no_failure_observed(self):
        with tempfile.TemporaryDirectory() as directory:
            with RunRecorder(RepositoryLayout(Path(directory)), [make_case()]) as recorder:
                pass
            metadata = json.loads((recorder.report_dir / "run.json").read_text())
            self.assertEqual(metadata["outcome"], "INCOMPLETE")

    def test_workspace_lock_releases_after_interruption(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(KeyboardInterrupt):
                with workspace_lock(Path(directory)):
                    with self.assertRaises(WorkspaceBusy):
                        with workspace_lock(Path(directory)):
                            self.fail("不应获得第二个工作目录锁")
                    raise KeyboardInterrupt()
            with workspace_lock(Path(directory)):
                pass
