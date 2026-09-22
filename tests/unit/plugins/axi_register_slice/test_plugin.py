from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_register_slice.reference import AxiRegisterSliceModel
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiRegisterSliceTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_register_slice")
        self.p = dict(self.case.parameters)

    def frame(self, parameters=None, **changes):
        frame = self.plugin.describe(parameters or self.p).frame()
        frame.update(changes)
        return frame

    def activate(self, model, parameters):
        for _ in range(3):
            model.step(self.frame(parameters, aresetn=0))
        for _ in range(4):
            model.step(self.frame(parameters, aresetn=1))

    def test_bypass_is_combinational_on_all_channels(self):
        model = AxiRegisterSliceModel(self.p)
        outputs = model.step(self.frame(
            s_axi_awaddr=0x12345678, s_axi_awvalid=1, m_axi_awready=1,
            m_axi_rdata=0xA5A5A5A5, m_axi_rvalid=1, s_axi_rready=1))
        self.assertEqual(outputs["m_axi_awaddr"], 0x12345678)
        self.assertEqual(outputs["m_axi_awvalid"], 1)
        self.assertEqual(outputs["s_axi_awready"], 1)
        self.assertEqual(outputs["s_axi_rdata"], 0xA5A5A5A5)
        self.assertEqual(outputs["s_axi_rvalid"], 1)
        self.assertEqual(outputs["m_axi_rready"], 1)

    def test_full_mode_holds_payload_under_backpressure(self):
        parameters = {**self.p, "forward_mode": "Full", "response_mode": "Full"}
        model = AxiRegisterSliceModel(parameters)
        self.activate(model, parameters)
        first = model.step(self.frame(parameters, s_axi_awaddr=0x11111111,
                                      s_axi_awvalid=1, m_axi_awready=0))
        held = model.step(self.frame(parameters, s_axi_awaddr=0x22222222,
                                     s_axi_awvalid=0, m_axi_awready=0))
        self.assertEqual(first["m_axi_awvalid"], 1)
        self.assertEqual(first["m_axi_awaddr"], 0x11111111)
        self.assertEqual(held["m_axi_awvalid"], 1)
        self.assertEqual(held["m_axi_awaddr"], 0x11111111)

    def test_directed_sequence_accepts_and_stalls_every_channel(self):
        parameters = {**self.p, "forward_mode": "Light", "response_mode": "Reverse"}
        spec = self.plugin.describe(parameters)
        model = spec.model_factory()
        for row in spec.prefix():
            model.step(spec.frame(row))
        for channel in ("aw", "w", "b", "ar", "r"):
            self.assertGreater(model.event_counts[f"{channel}_accepted"], 0)
            self.assertGreater(model.event_counts[f"{channel}_backpressure"], 0)

    def test_ports_and_model_parameters_follow_widths_and_modes(self):
        parameters = {**self.p, "data_width": 64, "id_width": 3,
                      "address_user_width": 5, "data_user_width": 2,
                      "response_user_width": 4, "forward_mode": "Forward",
                      "response_mode": "Reverse"}
        spec = self.plugin.describe(parameters)
        ports = {port.name: port.width for port in (*spec.inputs, *spec.outputs)}
        self.assertEqual(ports["s_axi_wdata"], 64)
        self.assertEqual(ports["m_axi_awuser"], 5)
        self.assertEqual(ports["s_axi_buser"], 4)
        self.assertEqual(spec.model_parameters["C_REG_CONFIG_AW"], 2)
        self.assertEqual(spec.model_parameters["C_REG_CONFIG_B"], 3)

    def test_invalid_parameters_are_rejected(self):
        bad = ({"data_width": 48}, {"id_width": 0}, {"address_user_width": 0},
               {"data_user_width": 1025}, {"response_user_width": 0},
               {"forward_mode": "SLR"}, {"response_mode": "Inputs"}, {"extra": 1})
        for changes in bad:
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.p, **changes}))

    def test_extended_matrix_has_unique_valid_parameters(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_register_slice/extended.json")
        self.assertEqual(len(cases), 16200)
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
