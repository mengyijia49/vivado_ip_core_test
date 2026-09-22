from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_uartlite.reference import UartLiteModel
from unit.plugins.cycle_helpers import plugin_case


class AxiUartLiteTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_uartlite")
        self.p = dict(self.case.parameters)

    def command(self, action, address=0, data=0, strobe=0):
        return {"action": int(action), "address": address, "data": data,
                "strobe": strobe if action == Action.WRITE else 0}

    def test_registers_fifo_order_overrun_and_empty_response(self):
        model = UartLiteModel(self.p)
        self.assertEqual(model.step(self.command(Action.READ, 8))["read_data"].value, 4)
        model.step(self.command(Action.WRITE, 12, 0x10, 0))
        for value in range(16):
            model.step(self.command(Action.WRITE, 4, value, value & 15))
        self.assertEqual(model.status(), 0x17)
        model.step(self.command(Action.WRITE, 4, 0xAA, 0))
        status = model.step(self.command(Action.READ, 8))["read_data"]
        self.assertEqual((status.value, status.mask), (0x37, 0xFF))
        self.assertEqual(model.status(), 0x17)
        received = [model.step(self.command(Action.READ, 0))["read_data"].value
                    for _ in range(16)]
        self.assertEqual(received, list(range(16)))
        empty = model.step(self.command(Action.READ, 0))
        self.assertEqual(empty["response"], 2)
        self.assertEqual(empty["read_data"].mask, 0)

    def test_data_width_and_fifo_reset(self):
        model = UartLiteModel({**self.p, "data_bits": 5})
        model.step(self.command(Action.WRITE, 4, 0xFF, 0))
        value = model.step(self.command(Action.READ, 0))["read_data"]
        self.assertEqual((value.value, value.mask), (0x1F, 0x1F))
        model.step(self.command(Action.WRITE, 4, 7, 15))
        model.step(self.command(Action.WRITE, 12, 0x3, 15))
        self.assertEqual(model.status(), 4)

    def test_spec_has_physical_ports_but_no_driven_rx_field(self):
        spec = self.plugin.describe(self.p)
        self.assertIn("rx", [port.name for port in spec.inputs])
        self.assertIn("tx", [port.name for port in spec.outputs])
        self.assertNotIn("rx", [port.name for port in spec.command_ports])
        self.assertEqual(spec.loopbacks, (("rx", "tx"),))
        self.assertEqual(spec.model_parameters["C_USE_PARITY"], 0)
        odd = self.plugin.describe({**self.p, "parity": "Odd"})
        self.assertEqual((odd.model_parameters["C_USE_PARITY"],
                          odd.model_parameters["C_ODD_PARITY"]), (1, 1))

    def test_directed_sequence_fills_and_drains_fifo_with_all_strobes(self):
        spec = self.plugin.describe(self.p)
        operations = spec.prepare_operations([])
        fill = [op["command"] for op in operations if op["phase"] == "loopback_fill"]
        drain = [op for op in operations if op["phase"] == "loopback_drain"]
        self.assertEqual((len(fill), len(drain)), (16, 16))
        self.assertEqual({command["strobe"] for command in fill}, set(range(16)))
        self.assertTrue(any(op["phase"] == "receive_overrun" for op in operations))

    def test_invalid_parameters_are_rejected(self):
        for changes in ({"baud_rate": 460800}, {"data_bits": 4}, {"data_bits": True},
                        {"parity": "Mark"}, {"unknown": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.p, **changes}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_uartlite/extended.json")
        self.assertEqual(len(cases), 84)
        for case in cases:
            self.plugin.validate_case(case)

    def test_generation_contains_loopback_and_auditable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axi_uartlite", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text('{"ip_inst": {"ip_revision": "39"}}')
            with patch("vivado_ip_test.plugins.common.axilite.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn("p_rx <= p_tx;", artifacts.testbench_path.read_text())
            self.assertGreater(artifacts.metrics["settle_cycles_per_operation"], 4000)
            self.assertEqual(artifacts.metrics["reference_sequence_events"]["receive_overruns"], 1)
            self.assertTrue(Path(manifest["artifacts"]["expected_mask"]).is_file())

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["axi_uartlite"], "ip/axi_uartlite/parameters.schema.json")
