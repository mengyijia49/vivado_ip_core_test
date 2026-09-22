from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.xfft.reference import (
    bit_reverse, expected_transactions, integer_dft, output_width, pack_complex,
    unpack_complex)
from vivado_ip_test.plugins.xfft.vectors import prepare_frames
from unit.plugins.cycle_helpers import plugin_case


PARAMETERS = {"transform_length": 8, "input_width": 8, "phase_factor_width": 8,
              "direction": "forward", "output_ordering": "natural_order",
              "architecture": "pipelined_streaming_io"}


class XfftTests(unittest.TestCase):
    def test_integer_dft_known_vectors_and_inverse_has_no_normalization(self):
        self.assertEqual(integer_dft([(3, -2)] + [(0, 0)] * 7, True), [(3, -2)] * 8)
        self.assertEqual(integer_dft([(2, 0)] * 8, False),
                         [(16, 0)] + [(0, 0)] * 7)
        with self.assertRaises(ValueError):
            integer_dft([(0, 0), (1, 0)] + [(0, 0)] * 6, True)

    def test_pack_padding_sign_and_width(self):
        packed = pack_complex(-7, 31, 12)
        self.assertEqual(unpack_complex(packed, 12), (-7, 31))
        self.assertEqual((packed >> 12) & 0xF, 0xF)
        self.assertEqual(packed >> 28, 0)
        self.assertEqual(output_width(12, 16), 17)

    def test_bit_reversed_output_carries_true_index_and_tlast(self):
        frames = prepare_frames([{"tdata": pack_complex(1, 0, 8)}], PARAMETERS)
        p = {**PARAMETERS, "output_ordering": "bit_reversed_order"}
        output = expected_transactions(frames, p)
        first_frame = output[:8]
        self.assertEqual([row["tuser"] for row in first_frame],
                         [bit_reverse(index, 3) for index in range(8)])
        self.assertEqual([row["tlast"] for row in first_frame], [0] * 7 + [1])

    def test_directed_frames_cover_exact_patterns_and_preserve_seed_impulse(self):
        seed = pack_complex(-128, 127, 8)
        frames = prepare_frames([{"tdata": seed}], PARAMETERS)
        self.assertEqual(len(frames), 9 * 8)
        self.assertEqual(frames[-8]["tdata"], seed)
        self.assertTrue(all(frame["tlast"] == int(index % 8 == 7)
                            for index, frame in enumerate(frames)))
        expected_transactions(frames, PARAMETERS)

    def test_ports_settings_and_model_widths(self):
        plugin, case = plugin_case("xfft")
        spec = plugin.describe(case.parameters)
        self.assertIn("s_axis_config_tdata", [port.name for port in spec.inputs])
        self.assertIn("s_axis_config_tready", [port.name for port in spec.outputs])
        self.assertEqual(spec.model_parameters["C_OUTPUT_WIDTH"], 12)
        self.assertEqual(spec.model_parameters["C_M_AXIS_DATA_TDATA_WIDTH"], 32)
        self.assertEqual(spec.config_value, 1)

    def test_invalid_parameters_and_all_extended_cases(self):
        root = Path(__file__).resolve().parents[4]
        plugin, case = plugin_case("xfft")
        for change in ({"transform_length": 12}, {"input_width": 7},
                       {"phase_factor_width": 35}, {"direction": "sideways"},
                       {"architecture": "unknown"},
                       {"transform_length": 32, "architecture": "radix_4_burst_io"},
                       {"unknown": 1}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))
        cases = load_test_cases(root / "configs/ip/xfft/extended.json")
        self.assertEqual(len(cases), 1344)
        for extended_case in cases:
            plugin.validate_case(extended_case)

    def test_generation_has_config_handshake_events_and_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("xfft", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            text = artifacts.testbench_path.read_text()
            self.assertIn("s_axis_config_tvalid => config_tvalid", text)
            self.assertIn("event_tlast_missing = '0'", text)
            manifest = json.loads(artifacts.manifest_path.read_text())
            contract = manifest["verification"]["schedule"]["reference_contract"]
            self.assertFalse(contract["vendor_bit_accurate_model"])
            self.assertEqual(contract["normalization"], "none")

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["xfft"], "ip/xfft/parameters.schema.json")
