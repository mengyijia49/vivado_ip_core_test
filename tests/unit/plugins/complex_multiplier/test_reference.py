from dataclasses import replace
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import DefinedBits
from vivado_ip_test.plugins.complex_multiplier.reference import product_components, quantize, unpack_complex
from vivado_ip_test.plugins.complex_multiplier.vectors import pack_complex
from unit.plugins.cycle_helpers import plugin_case


class ComplexMultiplierTests(unittest.TestCase):
    def spec(self, **changes):
        plugin, case = plugin_case("complex_multiplier")
        return plugin.describe({**case.parameters, "latency": 0, **changes})

    def frame(self, spec, a=(3, 4), b=(5, -2), **changes):
        return spec.frame({"s_axis_a_tdata": pack_complex(*a, 16),
            "s_axis_b_tdata": pack_complex(*b, 16),
            "s_axis_a_tvalid": 1, "s_axis_b_tvalid": 1, **changes})

    def test_complex_product_signs_extremes_and_conjugate_identity(self):
        self.assertEqual(product_components((3, 4), (5, -2)), (23, 14))
        self.assertEqual(product_components((0, 1), (0, 1)), (-1, 0))
        bound = 1 << 62
        self.assertEqual(product_components((-bound, -bound), (-bound, -bound)), (0, 2 * bound * bound))
        for real, imag in ((3, -7), (-bound, bound - 1), (0, 0)):
            self.assertEqual(product_components((real, imag), (real, -imag)), (real * real + imag * imag, 0))

    def test_input_padding_is_ignored_and_negative_output_padding_is_sign_extended(self):
        for padding in (0, 1):
            self.assertEqual(unpack_complex(pack_complex(-513, 701, 11, padding), 11), (-513, 701))
        self.assertEqual(quantize(-1, 21, 13), 0xFFFF)
        self.assertEqual(quantize(256, 21, 13), 1)

    def test_rounding_is_controlled_at_positive_and_negative_halfway_points(self):
        for value, low, high in ((128, 0, 1), (-128, 255, 0), (384, 1, 2), (-384, 254, 255)):
            self.assertEqual(quantize(value, 16, 8, 0), low)
            self.assertEqual(quantize(value, 16, 8, 1), high)
        self.assertEqual(quantize(127, 16, 8, 1), 0)
        self.assertEqual(quantize(129, 16, 8, 0), 1)
        with self.assertRaises(ValueError):
            quantize(1, 16, 16, 0)

    def test_valid_alignment_gaps_and_ce_hold(self):
        spec = self.spec(latency=3, clock_enable=True)
        model = spec.model_factory()
        model.step(self.frame(spec))
        model.step(self.frame(spec, s_axis_a_tvalid=0))
        result = model.step(spec.frame())
        self.assertEqual(result["m_axis_dout_tvalid"], 1)
        self.assertEqual(result["m_axis_dout_tdata"], 23 | (14 << 40))
        self.assertEqual(model.step(self.frame(spec, aclken=0)), result)
        invalid = model.step(spec.frame())
        self.assertEqual(invalid["m_axis_dout_tvalid"], 0)
        self.assertIsInstance(invalid["m_axis_dout_tdata"], DefinedBits)
        self.assertEqual(invalid["m_axis_dout_tdata"].mask, 0)

    def test_requested_long_latency_is_not_shortened_to_match_observed_dut_output(self):
        spec = self.spec(latency=55)
        model = spec.model_factory()
        for cycle in range(150):
            result = model.step(self.frame(spec, a=(2 if cycle == 80 else 0, 0), b=(1, 0)))
            if cycle >= 54:
                self.assertEqual(result["m_axis_dout_tvalid"], 1)
                self.assertEqual(result["m_axis_dout_tdata"], 2 if cycle == 134 else 0)

    def test_ctrl_valid_is_required_and_sidebands_are_concatenated_without_padding(self):
        spec = self.spec(output_width=16, rounding="Random_Rounding", a_user_width=3,
            b_user_width=5, ctrl_user_width=7, a_last=True, b_last=True, ctrl_last=True,
            last_mode="AND_all_TLASTs")
        model = spec.model_factory()
        values = self.frame(spec, s_axis_ctrl_tvalid=1, s_axis_a_tlast=1, s_axis_b_tlast=1,
            s_axis_ctrl_tlast=0, s_axis_a_tuser=5, s_axis_b_tuser=19, s_axis_ctrl_tuser=77)
        result = model.step(values)
        self.assertEqual(result["m_axis_dout_tvalid"], 1)
        self.assertEqual(result["m_axis_dout_tuser"], 5 | (19 << 3) | (77 << 8))
        self.assertEqual(result["m_axis_dout_tlast"], 0)
        self.assertEqual(model.step({**values, "s_axis_ctrl_tvalid": 0})["m_axis_dout_tvalid"], 0)

    def test_directed_sequence_covers_ties_padding_stalls_and_flush(self):
        spec = self.spec(a_width=11, b_width=9, output_width=8, latency=6,
            clock_enable=True, rounding="Random_Rounding")
        frames = [spec.frame(row) for row in spec.prefix()]
        self.assertTrue(all(0 <= row[port.name] <= port.limit for row in frames for port in spec.inputs))
        valid_patterns = {tuple(row[f"s_axis_{ch}_tvalid"] for ch in ("a", "b", "ctrl")) for row in frames}
        self.assertEqual(len(valid_patterns), 8)
        model = spec.model_factory()
        for row in frames:
            result = model.step(row)
        self.assertEqual(result["m_axis_dout_tvalid"], 0)
        self.assertGreater(model.event_counts["rounding_tie_components"], 0)
        self.assertGreater(model.event_counts["clock_enable_holds"], 0)
        self.assertGreater(model.event_counts["round_carry_0"], 0)
        self.assertGreater(model.event_counts["round_carry_1"], 0)

    def test_invalid_parameters_are_rejected_before_tools(self):
        plugin, case = plugin_case("complex_multiplier")
        for changes in ({"a_width": 7}, {"output_width": 34}, {"ctrl_last": True},
                        {"latency": 56}, {"latency": 0, "clock_enable": True},
                        {"rounding": "Random_Rounding"}, {"last_mode": "Pass_A_TLAST"},
                        {"a_last": True}, {"a_user_width": 257}, {"reset": True}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **changes}))
        with self.assertRaises(PluginError):
            plugin.describe(case.parameters).model_factory()

    def test_generated_latency_is_checked_and_passed_to_the_reference(self):
        plugin, case = plugin_case("complex_multiplier")
        for value in ("-1", "0", "56", "bad"):
            with patch("vivado_ip_test.plugins.complex_multiplier.plugin.load_metadata",
                       return_value=(None, {"model_parameters": {"C_LATENCY": value}})):
                with self.assertRaises(PluginError):
                    plugin.generate_testbench(case)
        with patch("vivado_ip_test.plugins.complex_multiplier.plugin.load_metadata",
                   return_value=(None, {"model_parameters": {"C_LATENCY": "6"}})), \
                patch.object(plugin._backend, "generate") as backend:
            plugin.generate_testbench(case)
        self.assertEqual(backend.call_args.args[1].model_parameters["C_LATENCY"], 6)
