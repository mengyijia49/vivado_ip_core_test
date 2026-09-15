import unittest

from vivado_ip_test.plugins.common.cycle import DefinedBits
from unit.plugins.cycle_helpers import plugin_case


class NativeFifoTests(unittest.TestCase):
    def test_pre_edge_flags_control_simultaneous_full_and_empty_access(self):
        plugin, case = plugin_case("fifo_generator")
        spec = plugin.describe({**case.parameters, "depth": 16})
        model = spec.model_factory()
        result = model.step(spec.frame({"wr_en": 1, "rd_en": 1, "din": 5}))
        self.assertEqual((result["wr_ack"], result["underflow"], result["valid"]), (1, 1, 0))
        self.assertIsInstance(result["dout"], DefinedBits)
        for i in range(15):
            result = model.step(spec.frame({"wr_en": 1, "din": i + 10}))
        self.assertEqual(result["full"], 1)
        result = model.step(spec.frame({"wr_en": 1, "rd_en": 1, "din": 255}))
        self.assertEqual((result["dout"], result["wr_ack"], result["overflow"], result["full"]), (5, 0, 1, 0))
        self.assertEqual(len(model.words), 15)

    def test_reset_value_flags_and_active_low_handshakes(self):
        plugin, case = plugin_case("fifo_generator")
        spec = plugin.describe({**case.parameters, "active_low_flags": True})
        model = spec.model_factory()
        model.step(spec.frame({"wr_en": 1, "din": 123}))
        result = model.step(spec.frame({"srst": 1}))
        self.assertEqual(result["dout"], 165)
        self.assertEqual((result["empty"], result["valid"], result["wr_ack"]), (1, 1, 1))
        self.assertEqual(model.event_counts["reset_nonempty"], 1)
        self.assertEqual(model.step(spec.frame({"rd_en": 1}))["underflow"], 0)

    def test_prefix_reaches_boundaries_wraps_and_reset_nonempty(self):
        plugin, case = plugin_case("fifo_generator")
        spec = plugin.describe(case.parameters)
        model = spec.model_factory()
        for frame in spec.prefix():
            model.step(spec.frame(frame))
        for event in ("full_cycle", "empty_cycle", "read", "write", "overflow", "underflow",
                      "write_wrap", "simultaneous_read_write", "reset_nonempty"):
            self.assertGreater(model.event_counts[event], 0, event)

    def test_synchronous_reset_does_not_mask_overflow_or_underflow_requests(self):
        plugin, case = plugin_case("fifo_generator")
        for low in (False, True):
            spec = plugin.describe({**case.parameters, "active_low_flags": low})
            model = spec.model_factory()
            result = model.step(spec.frame({"srst": 1, "wr_en": 1, "rd_en": 1}))
            self.assertEqual((result["underflow"], result["overflow"]), (1 ^ low, low))
            self.assertEqual((result["valid"], result["wr_ack"]), (low, low))
            for _ in range(case.parameters["depth"]):
                model.step(spec.frame({"wr_en": 1}))
            result = model.step(spec.frame({"srst": 1, "wr_en": 1, "rd_en": 1}))
            self.assertEqual((result["overflow"], result["underflow"]), (1 ^ low, low))
            self.assertEqual((result["full"], result["empty"]), (0, 1))
