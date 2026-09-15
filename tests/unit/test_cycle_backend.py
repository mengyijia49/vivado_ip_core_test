from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port
from vivado_ip_test.plugins.common.metadata import load_metadata, setting_text
from vivado_ip_test.plugins.common.testbench import build_cycles, render_testbench
from vivado_ip_test.plugins.common.vectors import cycle_space
from vivado_ip_test.services.failure_analysis import analyze_outputs
from vivado_ip_test.strategies import create_default_strategy_registry
from unit.plugins.cycle_helpers import plugin_case


class CycleBackendTests(unittest.TestCase):
    def test_generated_files_include_prefix_flush_schedule_and_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("shift_register", Path(directory))
            case = replace(case, parameters={"width": 1, "depth": 2, "clock_enable": False},
                           verification=replace(case.verification, case_budget=2))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.common.testbench.load_metadata", return_value=(xci, {})):
                artifacts = plugin.generate_testbench(case)
            self.assertEqual(artifacts.vector_count, 7)
            self.assertEqual(artifacts.expected_path.read_text().splitlines(), ["0", "1", "0", "0", "0", "1", "0"])
            self.assertFalse(artifacts.actual_path.exists())
            manifest = json.loads(artifacts.manifest_path.read_text())
            self.assertEqual(manifest["verification"]["generation"]["unique_count"], 2)
            self.assertIn("cycles", manifest["artifact_sha256"])
            self.assertIn("schedule", manifest["artifact_sha256"])

    def test_numeric_boundaries_are_also_driven_with_enable_and_without_reset(self):
        plugin, case = plugin_case("adder_subtractor")
        spec = plugin.describe(case.parameters)
        rows = [dict(zip((p.name for p in spec.inputs), values))
                for values in cycle_space(spec, True).directed_cases]
        self.assertTrue(any(row["A"] == 255 and row["B"] == 0 and row["CE"] == 1
                            and row["SCLR"] == 0 for row in rows))

    def test_each_backend_has_deterministic_generation_and_checked_cycles(self):
        for ip_type in ("adder_subtractor", "accumulator", "counter", "shift_register",
                        "distributed_memory", "vector_logic", "reduced_logic"):
            with self.subTest(ip_type=ip_type):
                plugin, case = plugin_case(ip_type)
                spec = plugin.describe(case.parameters)
                space = cycle_space(spec, False)
                registry = create_default_strategy_registry()
                generation = registry.generate(space, case.verification)
                self.assertEqual(generation, registry.generate(space, case.verification))
                for mode in ("continuous", "random_gaps", "bursts"):
                    profile = replace(case.verification, timing_mode=mode, input_order="shuffled")
                    cycles, schedule = build_cycles(spec, generation.cases, profile)
                    self.assertEqual(len(cycles), len(spec.prefix) + schedule.input_cycles + spec.flush_cycles)
                    model = spec.model_factory()
                    for cycle in cycles:
                        result = model.step(cycle["inputs"])
                        self.assertEqual(set(result), {port.name for port in spec.outputs})
                        for port in spec.outputs:
                            self.assertTrue(0 <= result[port.name] <= port.limit)
                    gaps = [c["inputs"] for c in cycles if c["phase"] == "gap"]
                    if "CE" in spec.frame():
                        self.assertTrue(all(frame["CE"] == 0 for frame in gaps))

    def test_one_bit_vector_and_scalar_remain_distinct(self):
        plugin, case = plugin_case("reduced_logic")
        spec = plugin.describe({"width": 1, "operation": "xor"})
        paths = {name: Path(f"/tmp/{name}") for name in ("input_vectors", "expected_output", "actual_output")}
        text = render_testbench(spec, paths, 2)
        self.assertIn("p_Op1 : std_logic_vector(0 downto 0)", text)
        self.assertIn("p_Res : std_logic :=", text)
        self.assertIn("actual(0) := p_Res", text)
        self.assertIn("not is_x(actual)", text)
        self.assertLess(text.index("writeline(actual_file"), text.index("assert not is_x"))

    def test_xci_requires_requested_parameters_and_exact_ports(self):
        plugin, case = plugin_case("vector_logic")
        spec = plugin.describe(case.parameters)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "proj/ip_test.srcs/sources_1/ip/dut_0/dut_0.xci"
            path.parent.mkdir(parents=True)
            ports = {}
            for direction, items in (("in", spec.inputs), ("out", spec.outputs)):
                for port in items:
                    ports[port.name] = [{"direction": direction, **({} if port.scalar else
                        {"size_left": str(port.width - 1), "size_right": "0"})}]
            instance = {"component_reference": "xilinx.com:ip:util_vector_logic:2.0",
                        "parameters": {category: {key: [{"value": setting_text(value)}]
                                       for key, value in values.items()} for category, values in
                                       (("component_parameters", spec.settings), ("model_parameters", spec.model_parameters))},
                        "boundary": {"ports": ports}}
            path.write_text(json.dumps({"ip_inst": instance}))
            self.assertEqual(load_metadata(root, spec, plugin.ip_name, plugin.version)[0], path)
            instance["parameters"]["model_parameters"]["C_SIZE"][0]["value"] = "7"
            path.write_text(json.dumps({"ip_inst": instance}))
            with self.assertRaises(PluginError):
                load_metadata(root, spec, plugin.ip_name, plugin.version)
            instance["parameters"]["model_parameters"]["C_SIZE"][0]["value"] = "8"
            instance["boundary"]["ports"]["Res"][0]["size_left"] = "6"
            path.write_text(json.dumps({"ip_inst": instance}))
            with self.assertRaises(PluginError):
                load_metadata(root, spec, plugin.ip_name, plugin.version)

    def test_stateful_failure_maps_sampled_cycle_not_causal_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "vectors").mkdir()
            (root / "outputs").mkdir()
            (root / "vectors/expected_output.txt").write_text("00\n01\n")
            (root / "outputs/actual_output.txt").write_text("00\nXX\n")
            (root / "vectors/schedule.json").write_text(json.dumps(
                {"mapping_kind": "sampled_cycle", "timing_mode": "continuous"}))
            (root / "vectors/cycles.json").write_text(json.dumps(
                [{"phase": "directed_sequence"}, {"phase": "gap"}]))
            evidence = analyze_outputs(root)
            self.assertEqual(evidence["sampled_cycle"], {"phase": "gap"})
            self.assertTrue(evidence["causal_input_not_identified"])
            self.assertTrue(evidence["contains_unknown_bits"])
            self.assertNotIn("input_vector", evidence)

    def test_invalid_parameter_and_budget_fail_before_vivado(self):
        plugin, case = plugin_case("counter")
        for change in ({"width": True}, {"increment": 256}, {"unexpected": 1}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters={**case.parameters, **change}))
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, verification=replace(case.verification, case_budget=1)))
