from dataclasses import replace
from pathlib import Path
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.axi_apb_bridge.reference import AxiApbBridgeModel, merge_bytes
from vivado_ip_test.plugins.axi_apb_bridge.vectors import prepare_operations
from vivado_ip_test.plugins.common.axilite.render import render_testbench
from vivado_ip_test.plugins.common.axilite.spec import Action
from unit.plugins.cycle_helpers import plugin_case


class AxiApbBridgeTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_apb_bridge")

    def test_byte_strobes_and_slave_memories_are_independent(self):
        self.assertEqual(merge_bytes(0x11223344, 0xAABBCCDD, 0b0101), 0x11BB33DD)
        model = AxiApbBridgeModel(self.case.parameters)
        base = self.case.parameters["base_address"]
        write = {"action": int(Action.WRITE), "address": base, "data": 0x11223344,
                 "strobe": 15, "s_axi_awprot": 0, "s_axi_arprot": 0}
        self.assertEqual(model.step(write)["response"], 0)
        read = {**write, "action": int(Action.READ), "data": 0, "strobe": 0}
        self.assertEqual(model.step(read), {"response": 0, "read_data": 0x11223344})
        if self.case.parameters["num_slaves"] > 1:
            self.assertEqual(model.step({**read, "address": base + 4096})["read_data"], 0)

    def test_error_response_does_not_modify_memory(self):
        p = {**self.case.parameters, "error_response": True}
        model = AxiApbBridgeModel(p)
        address = p["base_address"] + 4092
        command = {"action": int(Action.WRITE), "address": address, "data": 0xFFFFFFFF,
                   "strobe": 15, "s_axi_awprot": 0, "s_axi_arprot": 0}
        self.assertEqual(model.step(command)["response"], 2)
        result = model.step({**command, "action": int(Action.READ), "data": 0, "strobe": 0})
        self.assertEqual(result, {"response": 2, "read_data": 0})

    def test_directed_plan_covers_every_slave_attributes_and_strobes(self):
        p = {**self.case.parameters, "num_slaves": 2, "error_response": True}
        rows = [{"sample_slave": 1, "sample_word": 17, "sample_data": 0xA55AA55A,
                 "sample_strobe": 9, "sample_prot": 5}]
        operations = prepare_operations(rows, p)
        commands = [item["command"] for item in operations]
        self.assertEqual({c["strobe"] for c in commands if c["action"] == Action.WRITE}, set(range(16)))
        self.assertEqual({(c["address"]-p["base_address"]) // 4096 for c in commands
                          if c["action"] in (Action.WRITE, Action.READ)}, {0, 1})
        self.assertTrue(any(c["s_axi_awprot"] == 5 for c in commands))
        self.assertTrue(any(c["address"] % 4096 == 4092 for c in commands))

    def test_spec_has_exact_apb4_ports_and_protocol_monitor(self):
        spec = self.plugin.describe({**self.case.parameters, "num_slaves": 2, "wait_cycles": 2})
        self.assertEqual(spec.settings["C_M_APB_PROTOCOL"], "apb4")
        self.assertEqual(spec.settings["C_S_AXI_RNG2_BASEADDR"], "0x0000000000001000")
        self.assertIn("m_apb_prdata2", [p.name for p in spec.metadata_spec.inputs])
        self.assertIn("m_apb_pstrb", [p.name for p in spec.metadata_spec.outputs])
        paths = {name: Path("/tmp") / name for name in (
            "input_vectors", "expected_output", "expected_mask", "timing", "actual_output",
            "accepted_input", "mismatches", "protocol_summary", "protocol_events")}
        text = render_testbench(spec, paths, 4, 2, {"write": 2, "read": 2})
        self.assertIn("m_apb_prdata2 => apb_prdata_1", text)
        self.assertIn("APB access without setup", text)
        self.assertIn("APB control changed during access", text)
        self.assertIn("APB4 write attributes", text)
        self.assertIn("apb_pprot = p_s_axi_awprot", text)

    def test_invalid_parameters_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"address_width": 17}, {"num_slaves": 3}, {"base_address": 1},
                       {"wait_cycles": 5}, {"address_width": 16, "num_slaves": 16,
                                            "base_address": 4096}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_apb_bridge/extended.json")
        self.assertEqual(len(cases), 210)
        for case in cases:
            self.plugin.validate_case(case)


if __name__ == "__main__":
    unittest.main()
