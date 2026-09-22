from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_sideband_util.reference import AxiSidebandUtilModel
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiSidebandUtilTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_sideband_util")
        self.p = dict(self.case.parameters)

    def frame(self, parameters=None, **changes):
        frame = self.plugin.describe(parameters or self.p).frame()
        frame.update(changes)
        return frame

    def test_insert_transforms_only_address_user_fields(self):
        parameters = {**self.p, "data_width": 64, "id_width": 3,
                      "address_user_width": 5, "smid_mode": "Insert",
                      "smid_width": 2, "smid_value": 2}
        model = AxiSidebandUtilModel(parameters)
        inputs = self.frame(parameters,
            s_axi_awuser=0x1B, s_axi_aruser=0x12,
            s_axi_awid=5, s_axi_arid=3, s_axi_awaddr=0x1234,
            s_axi_wdata=0x0123456789ABCDEF, m_axi_rdata=0xFEDCBA9876543210,
            m_axi_awready=1, m_axi_wready=1, m_axi_arready=1,
        )
        outputs = model.step(inputs)
        self.assertEqual(outputs["m_axi_awuser"], (0x1B << 2) | 2)
        self.assertEqual(outputs["m_axi_aruser"], (0x12 << 2) | 2)
        self.assertEqual(outputs["m_axi_awid"], 5)
        self.assertEqual(outputs["m_axi_awaddr"], 0x1234)
        self.assertEqual(outputs["m_axi_wdata"], 0x0123456789ABCDEF)
        self.assertEqual(outputs["s_axi_rdata"], 0xFEDCBA9876543210)

    def test_bypass_and_remove_user_mapping(self):
        for mode, expected in (("Bypass", 0b110101), ("Remove", 0b1101)):
            parameters = {**self.p, "address_user_width": 6,
                          "smid_mode": mode, "smid_width": 2, "smid_value": 0}
            model = AxiSidebandUtilModel(parameters)
            outputs = model.step(self.frame(parameters, s_axi_awuser=0b110101))
            with self.subTest(mode=mode):
                self.assertEqual(outputs["m_axi_awuser"], expected)

    def test_directed_sequence_exercises_all_five_axi_channels(self):
        spec = self.plugin.describe(self.p)
        model = spec.model_factory()
        for row in spec.prefix():
            model.step(spec.frame(row))
        for channel in ("aw", "w", "b", "ar", "r"):
            self.assertGreater(model.event_counts[f"{channel}_handshake"], 0)
            self.assertGreater(model.event_counts[f"{channel}_backpressure"], 0)

    def test_port_widths_follow_smid_mode(self):
        for mode, width in (("Bypass", 5), ("Insert", 7), ("Remove", 3)):
            parameters = {**self.p, "address_user_width": 5,
                          "smid_mode": mode, "smid_width": 2,
                          "smid_value": 1 if mode == "Insert" else 0}
            outputs = {port.name: port.width for port in self.plugin.describe(parameters).outputs}
            with self.subTest(mode=mode):
                self.assertEqual(outputs["m_axi_awuser"], width)
                self.assertEqual(outputs["m_axi_aruser"], width)

    def test_invalid_parameters_are_rejected(self):
        bad = (
            {"data_width": 48}, {"id_width": 0}, {"address_user_width": 0},
            {"smid_mode": "Extract"}, {"smid_width": 6}, {"smid_value": 4},
            {"smid_mode": "Remove", "smid_value": 1},
            {"smid_mode": "Remove", "address_user_width": 2, "smid_width": 2},
            {"extra": 1},
        )
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.p, **changes}))

    def test_extended_matrix_has_unique_valid_parameters(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_sideband_util/extended.json")
        self.assertEqual(len(cases), 1152)
        seen = set()
        for case in cases:
            self.plugin.validate_case(case)
            key = tuple(sorted(case.parameters.items()))
            self.assertNotIn(key, seen)
            seen.add(key)

    def test_identity_is_checked(self):
        self.plugin.validate_case(self.case)
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))


if __name__ == "__main__":
    unittest.main()
