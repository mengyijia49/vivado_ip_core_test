from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_fifo_mm_s.reference import (
    AxiFifoModel, IER, ISR, RDFD, RDFO, RDR, RLR, TDFD, TDFV, TDR, TLR, RC, TC,
)
from vivado_ip_test.plugins.axi_fifo_mm_s.vectors import (
    ALIGNED_PACKET_LENGTHS, PARTIAL_PACKET_LENGTHS,
)
from unit.plugins.cycle_helpers import plugin_case


class AxiFifoMmSTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_fifo_mm_s")
        self.p = dict(self.case.parameters)

    @staticmethod
    def command(action, address=0, data=0, strobe=0):
        return {"action": int(action), "address": address, "data": data,
                "strobe": strobe if action == Action.WRITE else 0}

    def test_reference_loops_packets_and_masks_unused_final_bytes(self):
        model = AxiFifoModel({**self.p, "has_keep": True, "destination_width": 3})
        model.step(self.command(Action.WRITE, IER, TC | RC, 15))
        model.step(self.command(Action.WRITE, TDR, 5, 15))
        model.step(self.command(Action.WRITE, TDFD, 0x44332211, 15))
        model.step(self.command(Action.WRITE, TDFD, 0x88776655, 15))
        start = model.step(self.command(Action.WRITE, TLR, 5, 15))
        self.assertEqual(start["interrupt"], 1)
        self.assertEqual(model.step(self.command(Action.READ, RDFO))["read_data"], 2)
        self.assertEqual(model.step(self.command(Action.READ, RLR))["read_data"], 5)
        self.assertEqual(model.step(self.command(Action.READ, RDR))["read_data"], 5)
        first = model.step(self.command(Action.READ, RDFD))["read_data"]
        last = model.step(self.command(Action.READ, RDFD))["read_data"]
        self.assertEqual((first.value, first.mask), (0x44332211, 0xFFFFFFFF))
        self.assertEqual((last.value, last.mask), (0x88776655, 0xFF))
        self.assertEqual(model.step(self.command(Action.READ, RDFO))["read_data"], 0)

    def test_reference_vacancy_and_scored_interrupt_mask(self):
        model = AxiFifoModel(self.p)
        self.assertEqual(model.step(self.command(Action.READ, TDFV))["read_data"], 508)
        initial = model.step(self.command(Action.READ, ISR))["read_data"]
        self.assertEqual(initial.value & initial.mask, initial.value)
        self.assertEqual(initial.mask & ((1 << 23) | (1 << 24)), (1 << 23) | (1 << 24))

    def test_directed_sequence_covers_lengths_data_and_resets(self):
        spec = self.plugin.describe(self.p)
        samples = [{"word": value} for value in range(256)]
        operations = spec.prepare_operations(samples)
        starts = [op for op in operations if op["phase"] == "packet_start"]
        writes = [op for op in operations if op["phase"] == "packet_data_write"]
        reads = [op for op in operations if op["phase"] == "packet_data_read"]
        self.assertEqual([op["command"]["data"] for op in starts],
                         list(ALIGNED_PACKET_LENGTHS))
        self.assertEqual(len(writes), sum(n // 4 for n in ALIGNED_PACKET_LENGTHS))
        self.assertEqual(len(writes), len(reads))
        self.assertTrue(all(op["command"]["strobe"] == 15 for op in writes))
        self.assertTrue(any(op["phase"] == "tx_reset" for op in operations))
        self.assertTrue(any(op["phase"] == "rx_reset" for op in operations))

        keep_spec = self.plugin.describe({**self.p, "has_keep": True})
        keep_operations = keep_spec.prepare_operations(samples)
        keep_starts = [op["command"]["data"] for op in keep_operations
                       if op["phase"] == "packet_start"]
        self.assertEqual(keep_starts, list(PARTIAL_PACKET_LENGTHS))

    def test_spec_has_store_forward_loopback_and_optional_sidebands(self):
        spec = self.plugin.describe({**self.p, "has_keep": True, "destination_width": 4})
        self.assertEqual(spec.settings["C_USE_TX_CUT_THROUGH"], 0)
        self.assertEqual(spec.settings["C_USE_RX_CUT_THROUGH"], False)
        self.assertEqual(spec.settings["C_USE_TX_CTRL"], 0)
        self.assertIn("axi_str_txd_tkeep => txd_tkeep", spec.extra_mappings)
        self.assertIn("axi_str_txd_tdest => txd_tdest", spec.extra_mappings)
        self.assertIn("TX stream changed under backpressure", spec.testbench_statements)

    def test_invalid_parameters_are_rejected(self):
        for changes in ({"tx_depth": 513}, {"rx_depth": 256}, {"has_keep": 1},
                        {"destination_width": 5}, {"use_xpm": "yes"}, {"unknown": 1}):
            with self.subTest(changes=changes), self.assertRaises((PluginError, ValueError)):
                self.plugin.validate_case(replace(self.case, parameters={**self.p, **changes}))

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axi_fifo_mm_s/extended.json")
        self.assertEqual(len(cases), 1620)
        for case in cases:
            self.plugin.validate_case(case)

    def test_generation_contains_stream_checks_and_auditable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axi_fifo_mm_s", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text('{"ip_inst": {"ip_revision": "7"}}')
            with patch("vivado_ip_test.plugins.common.axilite.testbench.load_metadata",
                       return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            text = artifacts.testbench_path.read_text()
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn("txd_tready <= rxd_tready and stream_gate;", text)
            self.assertIn("rxd_tdata <= txd_tdata;", text)
            self.assertIn("TX stream changed under backpressure", text)
            self.assertGreater(artifacts.metrics["reference_sequence_events"]["packets_looped"], 0)
            self.assertTrue(Path(manifest["artifacts"]["expected_mask"]).is_file())

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["axi_fifo_mm_s"], "ip/axi_fifo_mm_s/parameters.schema.json")
