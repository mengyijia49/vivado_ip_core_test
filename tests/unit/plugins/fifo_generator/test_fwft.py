import unittest

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import DefinedBits
from unit.plugins.cycle_helpers import plugin_case


class FwftFifoTests(unittest.TestCase):
    def spec(self, **updates):
        plugin, case = plugin_case("fifo_generator")
        return plugin.describe({**case.parameters, "depth": 16, "read_mode": "fwft", **updates})

    def test_first_word_latency_and_output_hold_without_read(self):
        spec = self.spec()
        model = spec.model_factory()
        rows = [({"srst": 1}, 165, 1, 0, 0),
                ({"wr_en": 1, "rd_en": 1, "din": 37}, None, 1, 0, 1),
                ({"rd_en": 1}, None, 1, 0, 1),
                ({"rd_en": 1}, 37, 0, 1, 1),
                ({}, 37, 0, 1, 0), ({}, 37, 0, 1, 0),
                ({"rd_en": 1}, None, 1, 0, 0),
                ({"rd_en": 1}, None, 1, 0, 1)]
        for inputs, data, empty, valid, underflow in rows:
            result = model.step(spec.frame(inputs))
            self.assertEqual((result["empty"], result["valid"], result["underflow"]),
                             (empty, valid, underflow))
            if data is None:
                self.assertEqual(result["dout"], DefinedBits(0, 0, "fwft_no_valid_output"))
            else:
                self.assertEqual(result["dout"], data)

    def test_almost_empty_write_latency_and_contiguous_reads(self):
        spec = self.spec()
        model = spec.model_factory()
        rows = [({"wr_en": 1, "din": 11}, 1, 1, None),
                ({"wr_en": 1, "din": 22}, 1, 1, None),
                ({}, 0, 0, 11), ({"rd_en": 1}, 0, 1, 22),
                ({"rd_en": 1}, 1, 1, None)]
        for inputs, empty, almost_empty, data in rows:
            result = model.step(spec.frame(inputs))
            self.assertEqual((result["empty"], result["almost_empty"]), (empty, almost_empty))
            if data is not None:
                self.assertEqual(result["dout"], data)

    def test_capacity_is_depth_plus_two_and_full_write_is_rejected(self):
        spec = self.spec()
        model = spec.model_factory()
        for value in range(18):
            result = model.step(spec.frame({"wr_en": 1, "din": value}))
            self.assertEqual(result["full"], int(value == 17))
            self.assertEqual(result["almost_full"], int(value >= 16))
        result = model.step(spec.frame({"wr_en": 1, "rd_en": 1, "din": 99}))
        self.assertEqual((result["overflow"], result["wr_ack"], result["full"], result["dout"]),
                         (1, 0, 0, 1))
        for value in range(2, 18):
            self.assertEqual(model.step(spec.frame({"rd_en": 1}))["dout"], value)
        self.assertEqual(model.step(spec.frame({"rd_en": 1}))["empty"], 1)
        self.assertEqual(len(model.words), 0)

    def test_reset_clears_pending_first_word_and_active_low_flags(self):
        for wait in range(4):
            spec = self.spec(active_low_flags=True)
            model = spec.model_factory()
            model.step(spec.frame({"wr_en": 1, "din": 42}))
            for _ in range(wait):
                model.step(spec.frame())
            result = model.step(spec.frame({"srst": 1}))
            self.assertEqual(result["dout"], 165)
            for _ in range(4):
                result = model.step(spec.frame({"rd_en": 1}))
                self.assertEqual((result["empty"], result["valid"], result["underflow"]), (1, 1, 0))
            self.assertEqual(model.event_counts["reset_nonempty"], 1)

    def test_prefix_covers_state_boundaries_and_all_five_cycle_control_sequences(self):
        spec = self.spec()
        model = spec.model_factory()
        seen = set()
        pending = []
        for values in spec.prefix():
            frame = spec.frame(values)
            if frame["srst"]:
                pending = []
            else:
                pending.append(frame["wr_en"] | frame["rd_en"] << 1)
                if len(pending) == 5:
                    seen.add(tuple(pending))
            model.step(frame)
        self.assertEqual(len(seen), 4 ** 5)
        for event in ("full_cycle", "empty_cycle", "read", "write", "overflow", "underflow",
                      "write_wrap", "simultaneous_read_write", "reset_nonempty",
                      "fwft_waiting_for_first_word", "fwft_output_hold", "fwft_extra_capacity"):
            self.assertGreater(model.event_counts[event], 0, event)

    def test_modes_are_explicit_and_parameters_are_frozen(self):
        plugin, case = plugin_case("fifo_generator")
        original = plugin.describe(case.parameters)
        standard = plugin.describe({**case.parameters, "read_mode": "standard"})
        self.assertEqual(original.settings, standard.settings)
        self.assertEqual(list(original.prefix()), list(standard.prefix()))
        self.assertEqual(original.model_parameters, standard.model_parameters)
        params = {**case.parameters, "read_mode": "fwft"}
        spec = plugin.describe(params)
        params["read_mode"] = "standard"
        params["dout_reset_value"] = 0
        self.assertEqual(spec.settings["Performance_Options"], "First_Word_Fall_Through")
        self.assertEqual(spec.model_parameters["C_PRELOAD_LATENCY"], 0)
        self.assertEqual(spec.model_parameters["C_PRELOAD_REGS"], 1)
        self.assertEqual(spec.model_factory().step(spec.frame({"srst": 1}))["dout"], 165)
        for mode in (None, True, 0, "FWFT", "async"):
            with self.subTest(mode=mode), self.assertRaises(PluginError):
                plugin.describe({**case.parameters, "read_mode": mode})
