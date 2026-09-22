from dataclasses import replace
from pathlib import Path
import json
import unittest

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.plugins.axis_protocol_checker.reference import (
    AxisProtocolCheckerReference,
    applicable_scenarios,
    prepare_operations,
)
from vivado_ip_test.plugins.base import PluginError
from unit.plugins.cycle_helpers import plugin_case


class AxisProtocolCheckerTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axis_protocol_checker")

    def test_reference_maps_each_public_rule_to_an_exact_status_bit(self):
        parameters = {**self.case.parameters, "has_tready": True, "has_tstrb": True,
            "has_tkeep": True, "has_tlast": True, "has_aclken": True,
            "has_system_reset": False, "tid_width": 8, "tdest_width": 8,
            "tuser_width": 8, "max_waits": 16}
        operations = [{"scenario": name} for name in applicable_scenarios(parameters)]
        rows = AxisProtocolCheckerReference().evaluate(operations)
        statuses = {operation["scenario"]: row["status"]
                    for operation, row in zip(operations, rows)}
        self.assertEqual(statuses["tvalid_after_reset"], 1 << 0)
        self.assertEqual(statuses["tdata_changed"], 1 << 4)
        self.assertEqual(statuses["max_wait_exceeded"], 1 << 8)
        self.assertEqual(statuses["tkeep_tstrb_conflict"], 1 << 10)
        self.assertEqual(statuses["legal"], 0)
        self.assertEqual(statuses["aclken_pauses_wait_counter"], 0)

    def test_absent_ports_remove_only_their_dependent_scenarios(self):
        scenarios = set(applicable_scenarios(self.case.parameters))
        self.assertEqual(scenarios, {"legal", "tvalid_after_reset"})
        operations = prepare_operations(self.case.parameters, self.case.verification)
        self.assertEqual(len(operations), self.case.verification.case_budget)
        self.assertEqual({item["scenario"] for item in operations}, scenarios)

    def test_spec_matches_optional_ports_and_signal_set(self):
        full = load_test_cases(Path(__file__).resolve().parents[4] /
            "configs/ip/axis_protocol_checker/regression.json")[1]
        spec = self.plugin.describe(full.parameters)
        names = {port.name for port in spec.metadata.inputs}
        for name in ("system_resetn", "aclken", "pc_axis_tready", "pc_axis_tstrb",
                     "pc_axis_tkeep", "pc_axis_tlast", "pc_axis_tid",
                     "pc_axis_tdest", "pc_axis_tuser"):
            self.assertIn(name, names)
        self.assertEqual(spec.metadata.model_parameters["C_AXIS_SIGNAL_SET"],
                         "0b00000000000000000000000011111111")
        self.assertEqual(spec.metadata.model_parameters["C_PC_STATUS_WIDTH"], 32)

    def test_no_ready_disables_wait_counter_in_generated_xci(self):
        parameters = {**self.case.parameters, "has_tready": False, "max_waits": 256}
        spec = self.plugin.describe(parameters)
        self.assertEqual(spec.settings["MAX_WAITS"], 0)
        self.assertEqual(spec.metadata.model_parameters["C_PC_MAXWAITS"], 0)

    def test_invalid_parameters_identity_and_budget_are_rejected(self):
        self.plugin.validate_case(self.case)
        for change in ({"data_bytes": 3}, {"tid_width": 2}, {"tdest_width": 128},
                       {"tuser_width": 64}, {"max_waits": 15}):
            with self.subTest(change=change), self.assertRaises(PluginError):
                self.plugin.validate_case(replace(
                    self.case, parameters={**self.case.parameters, **change}))
        with self.assertRaises(PluginError):
            self.plugin.validate_case(replace(self.case,
                verification=replace(self.case.verification, case_budget=1)))

    def test_all_extended_parameters_are_unique_and_validate_without_vivado(self):
        root = Path(__file__).resolve().parents[4]
        cases = load_test_cases(root / "configs/ip/axis_protocol_checker/extended.json")
        self.assertEqual(len(cases), 65536)
        parameters = set()
        for case in cases:
            self.plugin.validate_case(case)
            parameters.add(json.dumps(dict(case.parameters), sort_keys=True))
        self.assertEqual(len(parameters), 65536)

    def test_parameter_schema_is_referenced(self):
        root = Path(__file__).resolve().parents[4]
        schema = (root / "configs/schemas/ip_matrix.schema.json").read_text()
        self.assertIn("ip/axis_protocol_checker/parameters.schema.json", schema)


if __name__ == "__main__":
    unittest.main()
