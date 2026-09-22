from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.clocking_wizard.reference import ClockPlan
from unit.plugins.cycle_helpers import plugin_case


class ClockingWizardPluginTests(unittest.TestCase):
    def test_settings_ports_and_reference_contract(self):
        plugin, case = plugin_case("clocking_wizard")
        plan = plugin._backend.metadata_spec(ClockPlan.from_parameters(case.parameters))
        self.assertEqual(plan.clock, "clk_in1")
        self.assertEqual([p.name for p in plan.inputs], ["reset"])
        self.assertEqual([p.name for p in plan.outputs], ["clk_out1", "locked"])
        self.assertEqual(plan.settings["PRIMITIVE"], "MMCM")
        self.assertEqual(plan.settings["CLKOUT1_REQUESTED_OUT_FREQ"], "50.000")

    def test_active_low_uses_resetn_port(self):
        plugin, case = plugin_case("clocking_wizard")
        spec = plugin._backend.metadata_spec(ClockPlan.from_parameters(
            {**case.parameters, "reset_active_high": False}))
        self.assertEqual([p.name for p in spec.inputs], ["resetn"])
        self.assertEqual(spec.model_parameters["C_RESET_LOW"], 1)

    def test_invalid_parameters_and_profiles_are_rejected(self):
        plugin, case = plugin_case("clocking_wizard")
        for parameters in ({**case.parameters, "input_frequency_mhz": 99},
                           {**case.parameters, "output_frequency_mhz": 75},
                           {**case.parameters, "primitive": "PLL",
                            "output_frequency_mhz": 125},
                           {**case.parameters, "reset_active_high": 1},
                           {**case.parameters, "unknown": 1}):
            with self.subTest(parameters=parameters), self.assertRaises(PluginError):
                plugin.validate_case(replace(case, parameters=parameters))
        bad_profile = replace(case.verification, case_budget=2)
        with self.assertRaises(PluginError):
            plugin.validate_case(replace(case, verification=bad_profile))

    def test_generation_writes_independent_clock_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("clocking_wizard", Path(directory))
            xci = Path(directory) / "fixture.xci"
            xci.write_text("{}")
            with patch("vivado_ip_test.plugins.clocking_wizard.testbench.load_metadata",
                       return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            plan = json.loads(result.input_path.read_text())
            self.assertEqual(plan["model"], "ideal_clock_period:1.0")
            self.assertEqual(result.vector_count, 5)
            text = result.testbench_path.read_text()
            self.assertIn("C_OUTPUT_PERIOD : time := 20000 ps", text)
            self.assertIn("PERIOD_AFTER_RESET", text)

    def test_verification_compares_text_event_records(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("clocking_wizard", Path(directory))
            run = plugin._layout.case_run_dir(case)
            expected = run / "vectors/expected_output.txt"
            actual = run / "outputs/actual_output.txt"
            expected.parent.mkdir(parents=True)
            actual.parent.mkdir(parents=True)
            expected.write_text("INITIAL_LOCK\nRESET_UNLOCK\n")
            actual.write_text("INITIAL_LOCK\nRESET_UNLOCK\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK),
                          Status.PASS)
            actual.write_text("INITIAL_LOCK\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK),
                          Status.VERIFICATION_FAILED)

    def test_all_extended_parameters_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        plugin, _ = plugin_case("clocking_wizard")
        cases = load_test_cases(root / "configs/ip/clocking_wizard/extended.json")
        self.assertEqual(len(cases), 48)
        for case in cases:
            plugin.validate_case(case)

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = json.loads((root / "configs/schemas/ip_matrix.schema.json").read_text())
        rules = schema["$defs"]["case_fields"]["allOf"]
        refs = {rule["if"]["properties"]["ip_type"]["const"]:
                rule["then"]["properties"]["parameters"]["$ref"] for rule in rules}
        self.assertEqual(refs["clocking_wizard"],
                         "ip/clocking_wizard/parameters.schema.json")
