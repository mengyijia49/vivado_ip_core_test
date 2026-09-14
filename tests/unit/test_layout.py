from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage
from vivado_ip_test.infrastructure import RepositoryLayout
from vivado_ip_test.infrastructure.run_identity import create_run_id
from unit.test_pipeline import make_case


class LayoutTests(unittest.TestCase):
    def test_case_paths_are_separated_by_explicit_ip_type(self):
        layout = RepositoryLayout(Path("/workspace"))
        first = replace(make_case(), case_id="same_name", ip_type="divider")
        second = replace(first, ip_type="multiplier")
        self.assertEqual(layout.case_run_dir(first), Path(f"/workspace/runs/batches/{layout.run_id}/divider/same_name"))
        self.assertNotEqual(layout.case_run_dir(first), layout.case_run_dir(second))
        self.assertEqual(layout.stage_log_path(second, Stage.SIM_SELFCHECK),
                         Path(f"/workspace/runs/logs/batches/{layout.run_id}/multiplier/same_name/sim_selfcheck.log"))
        self.assertEqual(layout.stage_work_dir(first, Stage.CREATE_IP),
                         layout.case_run_dir(first) / "work/create_ip")
        self.assertEqual(layout.report_path, Path(f"/workspace/reports/history/{layout.run_id}/report.csv"))

    def test_run_id_contains_local_date_time_and_offset(self):
        local = datetime(2026, 9, 14, 20, 55, 3, tzinfo=timezone(timedelta(hours=8)))
        with patch("vivado_ip_test.infrastructure.run_identity.datetime") as clock:
            clock.now.return_value.astimezone.return_value = local
            self.assertRegex(create_run_id(), r"^2026-09-14_20-55-03_UTC\+0800_[0-9a-f]{8}$")

    def test_runs_started_at_same_time_have_different_ids(self):
        moment = datetime(2026, 9, 14, 20, 55, 3, tzinfo=timezone.utc)
        self.assertEqual(len({create_run_id(moment) for _ in range(100)}), 100)
