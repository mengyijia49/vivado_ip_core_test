import json
import os
import unittest

from integration.ip.protocol_probe import run_protocol_probe
from vivado_ip_test.infrastructure.run_identity import create_run_id
from vivado_ip_test.plugins.axi_lmb_bridge.plugin import AxiLmbBridgePlugin
from vivado_ip_test.plugins.axi_lmb_bridge.testbench import render_testbench
from vivado_ip_test.plugins.axi_lmb_bridge.vectors import operation


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "Requires Vivado integration opt-in")
class FrequencyResponseTests(unittest.TestCase):
    def test_fixed_burst_and_read_write_ue_in_both_protocols(self):
        run_id = create_run_id()
        operations = [
            operation("read", 0, 0xF0, beats=2, hold_cycles=2),
            operation("read", 0, 0x2C0, fault="Uncorrectable_Error"),
            operation("write", 0, 0x2D0, data=0x12345678, fault="Uncorrectable_Error"),
            operation("write", 0, 0x2E0, data=0x87654321),
            operation("read", 0, 0x2F0),
        ]
        # Literal requests and responses, not computed by AxiLmbBridgeReference.
        accesses = [dict(address=a, read=1-w, write=w, data=d, be=15 if w else 0, prot=1)
                    for a, w, d in ((0xF0, 0, 0), (0xF4, 0, 0), (0x2C0, 0, 0),
                                    (0x2D0, 1, 0x12345678), (0x2E0, 1, 0x87654321),
                                    (0x2F0, 0, 0))]
        expected = [(1, 0, 0x835221F0, 0, 0), (1, 0, 0x875625F4, 0, 1),
                    (1, 0, 0x5322F1C0, 2, 1), (0, 0, 0, 2, 0),
                    (0, 0, 0, 0, 0), (1, 0, 0x835221F0, 0, 1)]
        for protocol in ("Standard", "Frequency"):
            parameters = dict(data_width=32, address_width=32, id_width=1,
                              use_pause=False, protection=False, lmb_protocol=protocol)
            settings = AxiLmbBridgePlugin(None, None).describe(parameters).settings
            def render(run):
                (run / "operations.json").write_text(json.dumps(operations, indent=2) + "\n")
                return render_testbench(parameters, operations, accesses, run / "actual.txt")
            run, _ = run_protocol_probe(self, run_id, "axi_lmb_bridge", protocol.lower(),
                settings, render, "tb_axi_lmb_selfcheck", "AXI_LMB_SELF_CHECK_STATUS")
            actual = []
            for line in (run / "actual.txt").read_text().splitlines():
                self.assertEqual(len(line), 37)
                self.assertLessEqual(set(line), {"0", "1"})
                actual.append(tuple(int(line[a:b], 2) for a, b in
                                    ((0, 1), (1, 2), (2, 34), (34, 36), (36, 37))))
            (run / "observations.json").write_text(json.dumps(
                {"fields": ["kind", "id", "data", "resp", "last"],
                 "expected": expected, "actual": actual}, indent=2) + "\n")
            self.assertEqual(actual, expected)
