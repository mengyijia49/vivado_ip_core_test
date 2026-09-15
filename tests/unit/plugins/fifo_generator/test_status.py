import unittest

from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class FifoStatusTests(unittest.TestCase):
    def spec(self, **parameters):
        plugin, case = plugin_case("fifo_generator")
        return plugin.describe({**case.parameters, "depth": 16, **parameters})

    def test_standard_count_truncates_low_bits_and_wraps_at_full(self):
        for width in range(1, 5):
            spec = self.spec(data_count_width=width)
            model = spec.model_factory()
            for count in range(1, 17):
                result = model.step(spec.frame({"wr_en": 1, "din": count}))
                self.assertEqual(result["data_count"], (count % 16) // (2 ** (4 - width)))
            result = model.step(spec.frame({"wr_en": 1}))
            self.assertEqual((result["data_count"], result["overflow"]), (0, 1))
            result = model.step(spec.frame({"rd_en": 1}))
            self.assertEqual(result["data_count"], (1 << width) - 1)

    def test_fwft_count_includes_not_yet_readable_data_and_extra_capacity(self):
        spec = self.spec(read_mode="fwft", data_count_width=5)
        model = spec.model_factory()
        result = model.step(spec.frame({"wr_en": 1, "rd_en": 1, "din": 7}))
        self.assertEqual((result["data_count"], result["empty"], result["underflow"]), (1, 1, 1))
        for count in range(2, 19):
            result = model.step(spec.frame({"wr_en": 1, "din": count}))
            self.assertEqual(result["data_count"], count)
        result = model.step(spec.frame({"wr_en": 1, "rd_en": 1}))
        self.assertEqual((result["data_count"], result["overflow"]), (17, 1))

    def test_full_hysteresis_has_one_cycle_latency_and_keeps_state_in_band(self):
        spec = self.spec(prog_full_assert=12, prog_full_negate=10)
        model = spec.model_factory()
        for _ in range(12):
            result = model.step(spec.frame({"wr_en": 1}))
            self.assertEqual(result["prog_full"], 0)
        self.assertEqual(model.step(spec.frame())["prog_full"], 1)
        for _ in range(3):
            self.assertEqual(model.step(spec.frame({"rd_en": 1}))["prog_full"], 1)
        self.assertEqual(model.step(spec.frame())["prog_full"], 0)
        for _ in range(2):
            self.assertEqual(model.step(spec.frame({"wr_en": 1}))["prog_full"], 0)
        self.assertEqual(model.step(spec.frame())["prog_full"], 0)

    def test_empty_hysteresis_uses_strict_negate_boundary(self):
        spec = self.spec(prog_empty_assert=4, prog_empty_negate=6)
        model = spec.model_factory()
        for _ in range(7):
            self.assertEqual(model.step(spec.frame({"wr_en": 1}))["prog_empty"], 1)
        self.assertEqual(model.step(spec.frame())["prog_empty"], 0)
        for _ in range(3):
            self.assertEqual(model.step(spec.frame({"rd_en": 1}))["prog_empty"], 0)
        self.assertEqual(model.step(spec.frame())["prog_empty"], 1)

    def test_single_threshold_reset_and_flags_ignore_handshake_polarity(self):
        spec = self.spec(data_count_width=4, prog_full_assert=3, prog_empty_assert=2,
                         active_low_flags=True)
        model = spec.model_factory()
        for _ in range(4):
            result = model.step(spec.frame({"wr_en": 1}))
        self.assertEqual((result["data_count"], result["prog_full"], result["prog_empty"]), (4, 1, 0))
        result = model.step(spec.frame({"srst": 1, "wr_en": 1, "rd_en": 1}))
        self.assertEqual((result["data_count"], result["prog_full"], result["prog_empty"]), (0, 0, 1))
        self.assertEqual((result["valid"], result["wr_ack"]), (1, 1))

    def test_optional_ports_metadata_and_new_width_limits(self):
        spec = self.spec(width=1024, depth=131072, read_mode="fwft", data_count_width=18,
                         prog_full_assert=131071, prog_empty_assert=4)
        self.assertEqual([(p.name, p.width) for p in spec.outputs[-3:]],
                         [("data_count", 18), ("prog_full", 1), ("prog_empty", 1)])
        self.assertFalse(spec.outputs[-3].scalar)
        self.assertEqual(spec.model_parameters["C_USE_FWFT_DATA_COUNT"], 1)
        self.assertEqual(spec.model_parameters["C_PROG_FULL_TYPE"], 1)
        self.assertEqual(spec.model_parameters["C_PROG_FULL_THRESH_NEGATE_VAL"], 131070)
        self.assertEqual(spec.model_parameters["C_PROG_EMPTY_THRESH_NEGATE_VAL"], 5)
        self.assertNotIn("data_count", {p.name for p in self.spec().outputs})

    def test_invalid_thresholds_and_counts_are_rejected_before_vivado(self):
        invalid = [dict(data_count_width=5), dict(data_count_width=True), dict(width=1025),
                   dict(depth=131073), dict(depth=32769), dict(prog_full_assert=2),
                   dict(prog_full_assert=15), dict(prog_empty_assert=1), dict(prog_empty_assert=14),
                   dict(prog_full_negate=7), dict(prog_empty_negate=7),
                   dict(prog_full_assert=8, prog_full_negate=8),
                   dict(prog_full_assert=8, prog_full_negate=2),
                   dict(prog_empty_assert=4, prog_empty_negate=4),
                   dict(prog_empty_assert=4, prog_empty_negate=14),
                   dict(read_mode="fwft", prog_full_assert=4),
                   dict(read_mode="fwft", prog_empty_assert=3),
                   dict(read_mode="fwft", data_count_width=6)]
        for parameters in invalid:
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                self.spec(**parameters)
