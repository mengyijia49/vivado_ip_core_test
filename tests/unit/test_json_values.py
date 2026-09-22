from dataclasses import replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

from vivado_ip_test.infrastructure.json_values import with_hex_large_integers
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.services.failure_analysis import analyze_outputs
from unit.plugins.cycle_helpers import plugin_case
from unit.test_inline_metadata import write_design


class WideJsonValueTests(unittest.TestCase):
    def test_recursive_encoding_is_exact_without_changing_small_values_or_input(self):
        limit = sys.get_int_max_str_digits()
        value = (1 << 65535) | 1
        original = {"inputs": {"a": value, "b": 7}, "mask": -value,
                    "control": True, "empty": None, "label": "0x55", "rows": (0,value)}
        result = json.loads(json.dumps(with_hex_large_integers(original)))
        self.assertEqual(int(result["inputs"]["a"],16),value)
        self.assertEqual(int(result["mask"],16),-value)
        self.assertEqual(result["inputs"]["b"],7)
        self.assertIs(result["control"],True)
        self.assertIsNone(result["empty"])
        self.assertEqual(result["label"],"0x55")
        self.assertEqual(original["inputs"]["a"],value)
        self.assertIsInstance(original["rows"],tuple)
        self.assertEqual(sys.get_int_max_str_digits(),limit)

    def test_single_wide_port_coverage_uses_matching_hex_labels(self):
        width = 65536
        space = port_space((Port("Op1",width),),False)
        label = "Op1:" + hex((1 << width)-1)
        self.assertIn(label,space.target_bins["port_boundaries"])
        self.assertEqual(space.coverage_features(((1 << width)-1,)),frozenset({label}))
        self.assertIn("Op1:0",space.target_bins["port_boundaries"])
        self.assertIn("Op1:1",space.target_bins["port_boundaries"])

    def test_wide_generation_and_failure_mapping_keep_recoverable_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin, case = plugin_case("ilvector_logic",root)
            case = replace(case,parameters={"width":65536,"operation":"not"},
                verification=replace(case.verification,strategy="directed_random",case_budget=8,
                                     coverage_targets=("port_boundaries",)))
            plugin.validate_case(case)
            run = plugin._layout.case_run_dir(case)
            write_design(run,{"design":{
                "design_info":{"name":"dut_0","validated":"true","tool_version":"2026.1"},
                "design_tree":{"core":""},"components":{"core":{
                    "vlnv":"xilinx.com:inline_hdl:ilvector_logic:1.0",
                    "parameters":{"C_SIZE":{"value":"65536"},"C_OPERATION":{"value":"not"}}}},
                "ports":{"Op1":{"direction":"I","left":"65535","right":"0"},
                         "Res":{"direction":"O","left":"65535","right":"0"}},
                "nets":{name:{"ports":[name,"core/"+name]} for name in ("Op1","Res")}}})
            artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest["numeric_value_encoding"],"integer_or_hex:1.0")
            cycles = json.loads((run/"vectors/cycles.json").read_text())
            self.assertEqual(cycles[0]["inputs"]["Op1"],0)
            self.assertEqual(int(cycles[1]["inputs"]["Op1"],16),(1 << 65536)-1)
            expected = artifacts.expected_path.read_text().splitlines()
            self.assertEqual(expected[0],"1"*65536)
            self.assertEqual(expected[1],"0"*65536)
            artifacts.actual_path.write_text(expected[0]+"\n"+"1"+expected[1][1:]+"\n")
            evidence = analyze_outputs(run)
            self.assertEqual(evidence["output_index"],1)
            self.assertEqual(evidence["sampled_cycle"]["inputs"],cycles[1]["inputs"])
            json.dumps(evidence)
            with self.assertRaises(PluginError):
                plugin.validate_case(replace(case,verification=replace(case.verification,case_budget=1)))
