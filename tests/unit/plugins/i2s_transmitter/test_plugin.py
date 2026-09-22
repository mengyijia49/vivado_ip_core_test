from dataclasses import replace
import json
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.i2s_transmitter.reference import prepare_audio, serialized_samples
from unit.plugins.cycle_helpers import plugin_case


class I2sTransmitterTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("i2s_transmitter")

    def test_reference_packs_samples_and_serializes_lanes(self):
        verification = replace(self.case.verification, case_budget=8)
        samples = prepare_audio(self.case.parameters, verification)
        self.assertEqual(len(samples), 388)
        self.assertEqual(samples[0]["sample"], 0)
        self.assertEqual(samples[0]["tdata"], (1 << 30) | 1)
        self.assertEqual(samples[0]["tid"], 0)
        self.assertEqual(samples[1]["tid"], 1)
        self.assertEqual(samples[1]["tdata"] & 0xF, 3)
        checked = samples[:verification.case_budget * 2]
        self.assertEqual(serialized_samples(checked, 2),
                         [row["sample"] for row in checked[2:]])

    def test_reference_orders_multilane_output_by_lr_side_then_lane(self):
        parameters = {**self.case.parameters, "channels": 4}
        samples = prepare_audio(parameters, self.case.verification)
        indexed = {(row["frame"], row["channel"]): row["sample"] for row in samples}
        self.assertEqual(serialized_samples(samples, 4)[:4], [
            indexed[(1, 0)], indexed[(1, 2)], indexed[(1, 1)], indexed[(1, 3)]])

    def test_spec_matches_optional_serial_lanes_and_model_parameters(self):
        parameters = {**self.case.parameters, "sample_width": 24, "channels": 8,
                      "use_32bit_lr": True, "fifo_depth": 1024}
        spec = self.plugin.describe(parameters)
        outputs = {port.name for port in spec.metadata.outputs}
        self.assertTrue({f"sdata_{lane}_out" for lane in range(4)} <= outputs)
        self.assertNotIn("sdata_4_out", outputs)
        self.assertEqual(spec.metadata.model_parameters["C_NUM_CHANNELS"], 4)
        self.assertEqual(spec.metadata.model_parameters["C_DWIDTH"], 24)
        self.assertEqual(spec.metadata.model_parameters["C_32BIT_LR"], 1)
        self.assertEqual(spec.metadata.clock_aliases, ("aud_mclk", "s_axis_aud_aclk"))

    def test_invalid_parameters_identity_and_budget_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"sample_width": 20}, {"channels": 3}, {"fifo_depth": 32},
                       {"sclk_divider": 0}, {"sclk_divider": 16}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))
        for budget in (7, 65):
            with self.subTest(budget=budget), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(self.case,
                    verification=replace(self.case.verification, case_budget=budget)))

    def test_all_extended_parameters_are_unique_and_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/i2s_transmitter/extended.json")
        self.assertEqual(len(cases), 1200)
        parameters = set()
        for case in cases:
            self.plugin.validate_case(case)
            parameters.add(json.dumps(dict(case.parameters), sort_keys=True))
        self.assertEqual(len(parameters), 1200)

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = (root / "configs/schemas/ip_matrix.schema.json").read_text()
        self.assertIn("ip/i2s_transmitter/parameters.schema.json", schema)


if __name__ == "__main__":
    unittest.main()
