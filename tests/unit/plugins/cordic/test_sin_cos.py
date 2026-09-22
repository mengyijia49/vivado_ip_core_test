from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.cordic.sin_cos.reference import calculate, expected_transactions
from vivado_ip_test.plugins.cordic.sin_cos.vectors import legal_phase_codes, prepare_frames
from unit.plugins.cycle_helpers import plugin_case


class CordicSinCosTests(unittest.TestCase):
    def parameters(self, **changes):
        _, base = plugin_case("cordic")
        values = {"function":"Sin_and_Cos","input_width":8,"output_width":8,
                  "phase_format":"Scaled_Radians","rounding":"Nearest_Even",
                  "architecture":"Parallel","pipelining":"Maximum","optimization":"Performance",
                  "coarse_rotation":True,"has_last":True,"user_width":3}
        return {**values, **changes}

    def test_known_scaled_angles_and_packed_field_order(self):
        p = self.parameters()
        self.assertEqual(calculate(0, p), (64, 0))
        self.assertEqual(calculate(16, p), (0, 64))
        self.assertEqual(calculate((-16) & 0xFF, p), (0, -64))
        rows = expected_transactions([{"tdata":16,"tlast":1,"tuser":5}], p)
        self.assertEqual(rows, [{"tdata":0x4000,"tlast":1,"tuser":5}])

    def test_non_byte_fields_are_sign_extended_independently(self):
        p = self.parameters(input_width=9, output_width=9, rounding="Nearest_Even")
        result = expected_transactions([{"tdata":(-32) & 0x1FF,"tlast":0,"tuser":2}], p)
        self.assertEqual(result, [{"tdata":0xFF800000,"tlast":0,"tuser":2}])

    def test_valid_phase_generation_respects_coarse_rotation(self):
        full = legal_phase_codes(self.parameters(input_width=16, phase_format="Radians"))
        quadrant = legal_phase_codes(self.parameters(
            input_width=16, phase_format="Radians", coarse_rotation=False))
        self.assertGreater(max(full), 3 * max(quadrant))
        self.assertEqual(min(full), -max(full))
        self.assertIn(0, quadrant)

    def test_frame_preparation_maps_random_values_into_documented_range(self):
        plugin, _ = plugin_case("cordic")
        p = self.parameters(input_width=9, coarse_rotation=False)
        spec = plugin.describe(p)
        frames = [{"tdata":0x1FF,"tlast":1,"tuser":7}]
        before = deepcopy(frames)
        result = prepare_frames(frames, spec, p)
        self.assertEqual(frames, before)
        self.assertEqual(result[-1]["tlast"], 1)
        signed = result[-1]["tdata"]
        signed = signed - 512 if signed & 256 else signed
        self.assertLessEqual(abs(signed), 16)
        self.assertGreater(len(result), 20)

    def test_phase_channel_spec_and_model_metadata(self):
        plugin, _ = plugin_case("cordic")
        p = self.parameters(input_width=17, output_width=9)
        spec = plugin.describe(p)
        self.assertEqual(spec.input_prefix, "s_axis_phase")
        self.assertEqual(spec.output_prefix, "m_axis_dout")
        self.assertEqual({port.name: port.width for port in spec.payload},
                         {"tdata":24,"tlast":1,"tuser":3})
        self.assertEqual({port.name: port.width for port in spec.sink_payload},
                         {"tdata":32,"tlast":1,"tuser":3})
        self.assertEqual(spec.model_parameters["C_CORDIC_FUNCTION"], 2)
        self.assertEqual(spec.model_parameters["C_HAS_S_AXIS_PHASE"], 1)
        self.assertEqual(spec.model_parameters["C_HAS_S_AXIS_CARTESIAN"], 0)
        self.assertEqual(spec.model_parameters["C_TLAST_RESOLUTION"], 2)

    def test_invalid_sine_cosine_parameters_are_rejected(self):
        plugin, case = plugin_case("cordic")
        for changes in ({"input_width":7}, {"output_width":49}, {"phase_format":"Turns"},
                        {"architecture":"Word_Serial"}, {"coarse_rotation":0},
                        {"data_format":"SignedFraction"}):
            p = self.parameters(**changes)
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, case_id="invalid", parameters=p))

    def test_generated_testbench_records_independent_reference_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("cordic", Path(directory))
            profile = replace(case.verification, strategy="directed_random", case_budget=256)
            case = replace(case, case_id="sincos", parameters=self.parameters(), verification=profile)
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.stream.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertGreater(artifacts.metrics["prepared_additional_transfers"], 20)
            contract = artifacts.metrics["reference_contract"]
            self.assertEqual(contract["model"], "cordic_sin_cos_decimal:1.0")
            self.assertFalse(contract["vendor_bit_accurate"])
            self.assertEqual(contract["accuracy"],
                             "ideal_result_within_two_lsb_per_cartesian_field")
            tolerance = artifacts.expected_path.parent / "output_tolerance.txt"
            self.assertTrue(tolerance.is_file())
            first = tolerance.read_text().splitlines()[0]
            self.assertEqual(int(first[:16], 2), 0x0202)
            self.assertIn("not actual", artifacts.testbench_path.read_text())
            text = artifacts.testbench_path.read_text()
            self.assertIn("s_axis_phase_tdata =>", text)
            self.assertIn("m_axis_dout_tdata =>", text)


if __name__ == "__main__":
    unittest.main()
