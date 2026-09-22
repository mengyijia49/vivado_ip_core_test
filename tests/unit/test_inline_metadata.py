from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.ilconcat.plugin import IlConcatPlugin
from unit.plugins.cycle_helpers import plugin_case


def sample_design():
    return {"design": {
        "design_info": {"name": "dut_0", "validated": "true", "tool_version": "2026.1"},
        "design_tree": {"core": ""},
        "components": {"core": {"vlnv": "xilinx.com:inline_hdl:ilconcat:1.0", "parameters": {
            "NUM_PORTS": {"value": "3"}, "IN0_WIDTH": {"value": "1"},
            "IN1_WIDTH": {"value": "3"}, "IN2_WIDTH": {"value": "4"}}}},
        "ports": {"In0": {"direction": "I", "left": "0", "right": "0"},
                  "In1": {"direction": "I", "left": "2", "right": "0"},
                  "In2": {"direction": "I", "left": "3", "right": "0"},
                  "dout": {"direction": "O", "left": "7", "right": "0"}},
        "nets": {name: {"ports": [name, "core/" + name]} for name in ("In0", "In1", "In2", "dout")}}}


def write_design(root, value):
    path = root / "proj/ip_test.srcs/sources_1/bd/dut_0/dut_0.bd"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return path


class InlineMetadataTests(unittest.TestCase):
    def check_design(self, value, succeeds=False):
        spec = IlConcatPlugin(None, None).describe({"input_widths": [1, 3, 4]})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = write_design(root, value)
            before = path.read_bytes()
            if succeeds:
                actual, metadata = load_metadata(root, spec, "ilconcat", "1.0")
                self.assertEqual(actual, path)
                self.assertEqual(metadata["artifact_format"], "inline_bd")
                self.assertEqual(metadata["nets"], value["design"]["nets"])
            else:
                with self.assertRaises(PluginError):
                    load_metadata(root, spec, "ilconcat", "1.0")
            self.assertEqual(path.read_bytes(), before)

    def test_complete_design_is_checked_without_xci(self):
        self.check_design(sample_design(), True)

    def test_wrong_vlnv_or_additional_core_is_rejected(self):
        for reference in ("xilinx.com:ip:xlconcat:2.1", "xilinx.com:inline_hdl:ilconcat:2.0"):
            design = sample_design()
            design["design"]["components"]["core"]["vlnv"] = reference
            self.check_design(design)
        design = sample_design()
        design["design"]["components"]["extra"] = {}
        self.check_design(design)

    def test_missing_and_changed_parameters_are_rejected(self):
        for value in (None, "2", 3, ["3"]):
            design = sample_design()
            params = design["design"]["components"]["core"]["parameters"]
            if value is None:
                del params["NUM_PORTS"]
            else:
                params["NUM_PORTS"]["value"] = value
            self.check_design(design)

    def test_port_direction_bounds_scalar_and_extra_ports_are_rejected(self):
        for port in ({"direction": "O", "left": "2", "right": "0"},
                     {"direction": "I", "left": "3", "right": "0"},
                     {"direction": "I", "left": "0", "right": "2"},
                     {"direction": "I"}, {"direction": "I", "left": "2"}):
            design = sample_design()
            design["design"]["ports"]["In1"] = port
            self.check_design(design)
        design = sample_design()
        design["design"]["ports"]["unexpected"] = {"direction": "I"}
        self.check_design(design)

    def test_disconnected_crossed_duplicate_and_extra_nets_are_rejected(self):
        for endpoints in (["In0"], ["In0", "core/In1"], ["In0", "core/In0", "core/In1"],
                          ["In0", "In0"], "In0 core/In0"):
            design = sample_design()
            design["design"]["nets"]["In0"]["ports"] = endpoints
            self.check_design(design)
        design = sample_design()
        design["design"]["nets"]["duplicate"] = deepcopy(design["design"]["nets"]["In0"])
        self.check_design(design)

    def test_bad_validation_metadata_and_unexpected_bus_are_rejected(self):
        for key in ("name", "validated", "tool_version"):
            design = sample_design()
            del design["design"]["design_info"][key]
            self.check_design(design)
        design = sample_design()
        design["design"]["interface_ports"] = {"AXI": {}}
        self.check_design(design)

    def test_missing_or_ambiguous_bd_does_not_fall_back_to_xci(self):
        spec = IlConcatPlugin(None, None).describe({"input_widths": [1, 3, 4]})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(PluginError):
                load_metadata(root, spec, "ilconcat", "1.0")
            first = write_design(root, sample_design())
            second = root / "proj/other.srcs/sources_1/bd/dut_0/dut_0.bd"
            second.parent.mkdir(parents=True)
            second.write_bytes(first.read_bytes())
            with self.assertRaises(PluginError):
                load_metadata(root, spec, "ilconcat", "1.0")

    def test_manifest_names_and_hashes_the_actual_bd(self):
        with tempfile.TemporaryDirectory() as temp:
            plugin, case = plugin_case("ilconcat", Path(temp))
            case = replace(case, parameters={"input_widths": [1, 3, 4]},
                           verification=replace(case.verification, case_budget=256))
            run = plugin._layout.case_run_dir(case)
            path = write_design(run, sample_design())
            artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest["artifacts"]["block_design"], str(path.resolve()))
            self.assertIn("block_design", manifest["artifact_sha256"])
            self.assertNotIn("xci", manifest["artifacts"])
