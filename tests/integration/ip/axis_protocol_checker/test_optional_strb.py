import json
import os
from pathlib import Path
import re
from string import Template
import unittest

from integration.ip.protocol_probe import run_protocol_probe
from vivado_ip_test.infrastructure.run_identity import create_run_id


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "Requires Vivado integration opt-in")
class OptionalStrbTests(unittest.TestCase):
    def test_absent_and_present_strb_with_identical_stimulus(self):
        root = Path(__file__).resolve().parents[4]
        fixture = Template((root / "tests/fixtures/ip/axis_protocol_checker/tb_optional_strb.vhd.tpl").read_text())
        run_id = create_run_id()
        for enabled in (False, True):
            settings = {"TDATA_NUM_BYTES": 1, "TID_WIDTH": 0, "TDEST_WIDTH": 0,
                "TUSER_WIDTH": 0, "HAS_TREADY": 1, "HAS_TSTRB": int(enabled),
                "HAS_TKEEP": 1, "HAS_TLAST": 0, "HAS_ACLKEN": 0,
                "HAS_SYSTEM_RESET": 0, "MAX_WAITS": 0, "MESSAGE_LEVEL": 0,
                "ENABLE_CONTROL": 0, "ENABLE_MARK_DEBUG": 0}
            text = fixture.substitute(has_strb=str(enabled).lower(),
                strb_mapping=", pc_axis_tstrb => strb" if enabled else "")
            run, log = run_protocol_probe(self, run_id, "axis_protocol_checker",
                "strb_present" if enabled else "strb_absent", settings,
                lambda run: text, "tb_optional_strb", "OPTIONAL_STRB_STATUS")
            rows = [{"scenario": int(n), "expected": e, "actual": a}
                    for n, e, a in re.findall(
                        r"OPTIONAL_STRB scenario=(\d+) expected=(\w+) actual=(\w+)", log)]
            (run / "observations.json").write_text(json.dumps(rows, indent=2) + "\n")
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(row["expected"] == row["actual"] for row in rows))
