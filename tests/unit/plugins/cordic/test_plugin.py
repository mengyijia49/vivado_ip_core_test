from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.stream.testbench import render_testbench
from unit.plugins.cycle_helpers import plugin_case


class CordicPluginTests(unittest.TestCase):
    def test_named_axis_channels_and_optional_sidebands(self):
        plugin, case = plugin_case("cordic")
        p = {**case.parameters, "input_width": 17, "output_width": 9, "has_last": True, "user_width": 256}
        spec = plugin.describe(p)
        self.assertEqual({port.name: port.width for port in spec.inputs}, {
            "aclk": 1, "aresetn": 1, "s_axis_cartesian_tvalid": 1, "m_axis_dout_tready": 1,
            "s_axis_cartesian_tdata": 24, "s_axis_cartesian_tlast": 1, "s_axis_cartesian_tuser": 256})
        self.assertEqual(spec.model_parameters["C_M_AXIS_DOUT_TDATA_WIDTH"], 16)
        self.assertEqual(spec.model_parameters["C_CORDIC_FUNCTION"], 6)
        self.assertEqual(spec.settings["flow_control"], "Blocking")
        self.assertEqual(spec.settings["Precision"], 0)
        paths = {name: Path("/tmp") / name for name in ("input_vectors", "gaps", "ready", "accepted_input",
                 "expected_output", "actual_output", "protocol_events", "protocol_summary")}
        text = render_testbench(spec, paths, 10, 8, 100)
        for name in ("s_axis_cartesian_tvalid", "s_axis_cartesian_tready", "s_axis_cartesian_tdata",
                     "m_axis_dout_tvalid", "m_axis_dout_tready", "m_axis_dout_tdata", "m_axis_dout_tuser"):
            self.assertIn(name + " =>", text)
        self.assertNotIn("s_axis_tdata =>", text)
        self.assertIn("output changed under backpressure", text)

    def test_invalid_and_silently_normalized_configurations_are_rejected(self):
        plugin, case = plugin_case("cordic")
        for changes in ({"function": "Sin_and_Cos"}, {"input_width": 7}, {"input_width": True},
                        {"output_width": 8}, {"architecture": "Word_Serial"}, {"user_width": 257},
                        {"data_format": "SignedFraction"}, {"data_format": "UnsignedFraction", "output_width": 7},
                        {"flow_control": "NonBlocking"}, {"rounding": "ceil"}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **changes}))

    def test_generation_is_reproducible_and_audits_both_transaction_files(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("cordic", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata", return_value=(xci, {})):
                first = plugin.generate_testbench(case)
                content = first.testbench_path.read_bytes()
                second = plugin.generate_testbench(case)
            self.assertEqual(content, second.testbench_path.read_bytes())
            self.assertNotEqual(first.input_path.read_bytes(), first.expected_path.read_bytes())
            self.assertGreater(first.metrics["prepared_additional_transfers"], 0)
            contract = first.metrics["reference_contract"]
            self.assertFalse(contract["vendor_bit_accurate"])
            self.assertTrue(contract["mismatch_requires_precision_review"])
            manifest = json.loads(first.manifest_path.read_text())
            accepted = Path(manifest["artifacts"]["accepted_input"])
            first.actual_path.write_bytes(first.expected_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
            accepted.write_bytes(first.input_path.read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
