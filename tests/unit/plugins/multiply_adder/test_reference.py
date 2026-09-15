from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.multiply_adder.reference import MultiplyAdderModel
from unit.plugins.cycle_helpers import plugin_case


class MultiplyAdderTests(unittest.TestCase):
    def model(self, timing=None, **changes):
        plugin, case = plugin_case("multiply_adder")
        p = {**case.parameters, **changes}
        timing = timing or {"ab_latency": 0, "c_latency": 0, "implementation": 0}
        spec = plugin.describe(p, timing)
        return spec, spec.model_factory()

    def test_subtract_is_c_minus_product_and_signed_operands_are_decoded(self):
        spec, model = self.model()
        self.assertEqual(model.step(spec.frame({"A": 3, "B": 5, "C": 19, "SUBTRACT": 1})),
                         {"P": 4, "PCOUT": 4})
        spec, model = self.model(a_type="Signed")
        result = model.step(spec.frame({"A": 254, "B": 3, "C": 5}))
        self.assertEqual(result, {"P": (1 << 17) - 1, "PCOUT": (1 << 48) - 1})

    def test_output_slice_and_unused_cascade_are_separate(self):
        spec, model = self.model({"ab_latency": 0, "c_latency": 0, "implementation": 2},
                                 output_high=12, output_low=3)
        result = model.step(spec.frame({"A": 17, "B": 23, "C": 11}))
        self.assertEqual(result, {"P": (17 * 23 + 11) >> 3, "PCOUT": 0})

    def test_product_addend_and_subtract_use_their_own_histories(self):
        spec, model = self.model({"ab_latency": 3, "c_latency": 2, "implementation": 0}, pipelined=True)
        self.assertEqual(model.step(spec.frame({"A": 2, "B": 3, "C": 10}))["P"], 0)
        self.assertEqual(model.step(spec.frame({"C": 20, "SUBTRACT": 1}))["P"], 10)
        self.assertEqual(model.step(spec.frame())["P"], 14)

    def test_pcin_bypasses_c_and_has_its_own_latency(self):
        spec, model = self.model({"ab_latency": 3, "c_latency": 1, "implementation": 0},
                                 c_width=48, c_type="Signed", use_pcin=True, pipelined=True)
        self.assertEqual(model.step(spec.frame({"A": 2, "B": 3, "PCIN": 7, "C": 999, "SUBTRACT": 1}))["P"], 7)
        self.assertEqual(model.step(spec.frame({"PCIN": 11, "C": 888}))["P"], 11)
        self.assertEqual(model.step(spec.frame({"PCIN": 13, "C": 777}))["P"], 19)

    def test_swapped_single_dsp_mapping_keeps_cascade_and_control_latency(self):
        spec, model = self.model({"ab_latency": 3, "c_latency": 1, "implementation": 1},
            a_width=18, b_width=25, a_type="Signed", b_type="Signed", c_width=48,
            c_type="Signed", use_pcin=True, pipelined=True)
        result = model.step(spec.frame({"PCIN": 7, "SUBTRACT": 1, "A": 2, "B": 3}))
        self.assertEqual(result, {"P": 7, "PCOUT": 7})
        model.step(spec.frame({"PCIN": 11, "SUBTRACT": 1}))
        result = model.step(spec.frame({"PCIN": 13}))
        self.assertEqual(result, {"P": 7, "PCOUT": 7})

    def test_ce_holds_all_paths_and_reset_priority_is_explicit(self):
        for priority in (False, True):
            spec, model = self.model({"ab_latency": 3, "c_latency": 2, "implementation": 0},
                                     pipelined=True, ce_overrides_reset=priority)
            model.step(spec.frame({"C": 7}))
            self.assertEqual(model.step(spec.frame())["P"], 7)
            self.assertEqual(model.step(spec.frame({"CE": 0, "C": 88}))["P"], 7)
            self.assertEqual(model.step(spec.frame({"CE": 0, "SCLR": 1}))["P"], 7 if priority else 0)
            self.assertEqual(model.step(spec.frame({"SCLR": 1}))["P"], 0)
            self.assertTrue(all(not any(q) for q in model.history.values()))

    def test_directed_prefix_fills_long_pipelines_and_exercises_each_operand(self):
        for pcin, latency in ((False, 16), (True, 3)):
            spec, model = self.model({"ab_latency": latency, "c_latency": 1 if pcin else 4,
                                      "implementation": 0 if pcin else 2},
                pipelined=True, use_pcin=pcin, c_width=48 if pcin else 16,
                c_type="Signed" if pcin else "Unsigned")
            frames = [spec.frame(row) for row in spec.prefix()]
            active = longest = 0
            addend = "PCIN" if pcin else "C"
            for frame in frames:
                active = active + 1 if (frame["A"] and frame["B"] and frame[addend]
                    and frame["CE"] and not frame["SCLR"]) else 0
                longest = max(longest, active)
            self.assertGreaterEqual(longest, max(16, 2 * latency))
            for pulse, companion in (("A", "B"), ("B", "A")):
                self.assertTrue(any(not a[pulse] and b[pulse] and not c[pulse]
                    and a[companion] == b[companion] == c[companion] > 0
                    for a, b, c in zip(frames, frames[1:], frames[2:])))
            self.assertTrue(any(f[addend] and not f["A"] and not f["B"] for f in frames))
            self.assertTrue(any(not f["CE"] and f["SCLR"] for f in frames))
            for frame in frames:
                model.step(frame)
            self.assertTrue(all(not any(q) for q in model.history.values()))

    def test_invalid_parameters_and_missing_timing_fail_before_simulation(self):
        plugin, case = plugin_case("multiply_adder")
        for change in ({"a_width": 1, "a_type": "Signed"}, {"a_width": 53},
                       {"output_low": 17}, {"output_high": 106},
                       {"use_pcin": True}, {"ce_overrides_reset": True}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))
        with self.assertRaises(PluginError):
            plugin.describe(case.parameters).model_factory()

    def test_timing_file_is_required_validated_and_archived_by_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("multiply_adder", Path(directory))
            run = plugin._layout.case_run_dir(case)
            path = run / "vectors/ip_timing.json"
            path.parent.mkdir(parents=True)
            timing = {"schema_version": 1, "ab_latency": 0, "c_latency": 0, "implementation": 0}
            for broken in ([], {**timing, "schema_version": 2}, {**timing, "ab_latency": 1},
                           {**timing, "c_latency": 3}, {**timing, "implementation": True}):
                path.write_text(json.dumps(broken))
                with self.assertRaises(PluginError):
                    plugin.generate_testbench(case)
            path.write_text(json.dumps(timing))
            fixture = run / "fixture.xci"
            fixture.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(fixture, {})):
                artifacts = plugin.generate_testbench(case)
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertIn("ip_timing", manifest["artifact_sha256"])
            self.assertEqual(manifest["artifacts"]["ip_timing"], str(path.resolve()))
