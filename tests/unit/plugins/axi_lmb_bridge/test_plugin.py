from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axi_lmb_bridge.reference import (
    AxiLmbBridgeReference, BURSTS, beat_data, burst_addresses, read_data)
from vivado_ip_test.plugins.axi_lmb_bridge.testbench import render_testbench
from vivado_ip_test.plugins.axi_lmb_bridge.vectors import operation, prepare_operations
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxiLmbBridgeTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_lmb_bridge")
        self.p = dict(self.case.parameters)

    def test_burst_addresses_cover_fixed_increment_and_wrap(self):
        self.assertEqual(burst_addresses(0x104, 3, 2, BURSTS["Fixed"], 32),
                         [0x104, 0x104, 0x104])
        self.assertEqual(burst_addresses(0x104, 3, 2, BURSTS["Increment"], 32),
                         [0x104, 0x108, 0x10C])
        self.assertEqual(burst_addresses(0x11C, 4, 2, BURSTS["Wrap"], 32),
                         [0x11C, 0x110, 0x114, 0x118])

    def test_data_helpers_are_width_bounded_and_deterministic(self):
        self.assertEqual(beat_data(0xFFFFFFFF, 1, 32), 0xFFFFFEFE)
        self.assertEqual(read_data(0x100, 32), 0x93623100)
        self.assertEqual(read_data(0x100, 64), 0x5726F5C493623100)

    def test_reference_checks_lmb_sequence_responses_and_protection(self):
        parameters = {**self.p, "protection": True}
        operations = [
            operation("write", 1, 0x100, beats=2, data=0x12345678,
                      strobe=15, prot=0),
            operation("read", 1, 0x108, fault="Address_Error", prot=1),
        ]
        accesses, outputs = AxiLmbBridgeReference(parameters).evaluate(operations)
        self.assertEqual([row["address"] for row in accesses], [0x100, 0x104, 0x108])
        # The IP exposes M_Prot as (0 to 1); positional mapping reverses its
        # display order in the testbench's (1 downto 0) signal.
        self.assertEqual([row["prot"] for row in accesses], [1, 1, 2])
        self.assertEqual(outputs[0]["resp"], 0)
        self.assertEqual(outputs[1]["resp"], 2)
        self.assertEqual(outputs[1]["last"], 1)

    def test_directed_operations_cover_bridge_specific_behavior(self):
        samples = [{"sample_address": 0, "sample_data": 1, "sample_strobe": 15,
                    "sample_id": 0, "sample_prot": 0, "sample_wait": 0}]
        operations = prepare_operations(samples, self.p)
        self.assertTrue(any(row["beats"] == 4 and row["burst_name"] == "Increment"
                            for row in operations))
        self.assertTrue(any(row["burst_name"] == "Wrap" for row in operations))
        self.assertTrue(any(row["w_before_aw"] for row in operations))
        self.assertTrue(any(row["strobe"] == 0 for row in operations))
        self.assertEqual({row["fault_name"] for row in operations},
                         {"Normal", "Address_Error", "Uncorrectable_Error"})
        self.assertEqual([(row["kind"], row["fault_name"], row["strobe"])
                          for row in operations[12:16]],
                         [("read", "Uncorrectable_Error", 15),
                          ("write", "Normal", 15), ("read", "Normal", 15),
                          ("write", "Normal", 15)])

    def test_normal_write_after_ue_read_expects_okay(self):
        operations = [
            operation("read", 1, 0x2C0, fault="Uncorrectable_Error"),
            operation("write", 1, 0x2D0, data=0x13579BDF, strobe=15),
        ]
        _, outputs = AxiLmbBridgeReference(self.p).evaluate(operations)
        self.assertEqual([(row["kind"], row["resp"]) for row in outputs],
                         [(1, 2), (0, 0)])

    def test_ports_and_settings_follow_parameters(self):
        parameters = {**self.p, "data_width": 64, "address_width": 40,
                      "id_width": 8, "use_pause": True,
                      "lmb_protocol": "Frequency", "protection": True}
        spec = self.plugin.describe(parameters)
        ports = {port.name: port.width for port in (*spec.inputs, *spec.outputs)}
        self.assertEqual(ports["S_AXI_WDATA"], 64)
        self.assertEqual(ports["M_ABus"], 40)
        self.assertEqual(ports["S_AXI_AWID"], 8)
        self.assertIn("Pause", ports)
        self.assertIn("Pause_Ack", ports)
        self.assertEqual(spec.settings["C_LMB_PROTOCOL"], 1)
        self.assertEqual(spec.settings["C_LMB_HAS_PROT"], 1)

    def test_rendered_testbench_has_protocol_and_pause_checks(self):
        parameters = {**self.p, "use_pause": True, "protection": True}
        operations = [operation("write", 0, 0, data=1, strobe=15)]
        accesses, _ = AxiLmbBridgeReference(parameters).evaluate(operations)
        text = render_testbench(parameters, operations, accesses, Path("/tmp/actual.txt"))
        self.assertIn("responder_state_t", text)
        self.assertIn("LMB protection mismatch", text)
        self.assertIn("pause did not quiesce inputs", text)
        self.assertIn("B changed under backpressure", text)

    def test_invalid_parameters_and_identity_are_rejected(self):
        for changes in ({"data_width": 48}, {"address_width": 48}, {"id_width": 2},
                        {"lmb_protocol": "Other"}, {"extra": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.p, **changes}))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case, ip_name="wrong"))

    def test_frequency_responder_delays_only_read_payload_and_read_error(self):
        operations = [operation("read", 0, 0xF0, beats=2)]
        accesses, _ = AxiLmbBridgeReference(self.p).evaluate(operations)
        for protocol, flag in (("Standard", 0), ("Frequency", 1)):
            text = render_testbench({**self.p, "lmb_protocol": protocol},
                                   operations, accesses, Path("/tmp/actual.txt"))
            self.assertIn(f"FREQUENCY_PROTOCOL : boolean := {flag} = 1", text)
            self.assertIn("read_data_delayed <= read_data_now;", text)
            self.assertIn("read_ue_delayed <= read_ue_now;", text)
            self.assertIn("LMB_ReadDBus <= read_data_delayed when FREQUENCY_PROTOCOL", text)
            self.assertIn("(read_ue_delayed or write_ue_now) when FREQUENCY_PROTOCOL", text)
            self.assertIn("write_ue_now <= not request_is_read;", text)

    def test_extended_matrix_has_unique_valid_parameters(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_lmb_bridge/extended.json")
        self.assertEqual(len(cases), 192)
        seen = set()
        for case in cases:
            self.plugin.validate_case(case)
            key = tuple(sorted(case.parameters.items()))
            self.assertNotIn(key, seen)
            seen.add(key)


if __name__ == "__main__":
    unittest.main()
