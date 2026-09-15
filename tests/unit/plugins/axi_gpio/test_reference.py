from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.axilite.testbench import write_operations
from vivado_ip_test.plugins.axi_gpio.reference import GpioModel
from vivado_ip_test.services.failure_analysis import analyze_outputs
from unit.plugins.cycle_helpers import plugin_case


class GpioTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_gpio")
        self.p = {**self.case.parameters, "width1": 4, "default_tri1": 10,
                  "default_data1": 5, "interrupt": True}

    def command(self, action, address=0, data=0, strobe=15, pins=0):
        return {"action": int(action), "address": address, "data": data,
                "strobe": strobe if action == Action.WRITE else 0, "gpio_io_i": pins}

    def test_data_read_direction_and_output_masks_are_distinct(self):
        model = GpioModel(self.p)
        row = model.step(self.command(Action.READ, pins=15))
        self.assertEqual((row["read_data"].value, row["read_data"].mask), (15, 15))
        self.assertEqual((row["gpio_io_o"].value, row["gpio_io_o"].mask), (5, 5))
        self.assertEqual(row["gpio_io_t"], 10)
        self.assertEqual(model.read(4), 10)
        self.assertEqual(model.read(8), 0)

    def test_input_configured_bits_do_not_store_data_writes(self):
        model = GpioModel(self.p)
        model.step(self.command(Action.WRITE, 0, 0, strobe=0))
        self.assertEqual(model.data, [0])
        model.step(self.command(Action.WRITE, 0, 15, strobe=0))
        self.assertEqual(model.data, [5])
        model.step(self.command(Action.WRITE, 4, 0))
        self.assertEqual(model.data, [5])

    def test_wstrb_is_ignored_for_all_sixteen_values(self):
        for strobe in range(16):
            model = GpioModel({**self.p, "default_tri1": 0})
            row = model.step(self.command(Action.WRITE, 0, 0xFFFFFFF9, strobe=strobe))
            self.assertEqual(row["gpio_io_o"].value, 9)
            self.assertEqual(row["gpio_io_o"].mask, 15)
            self.assertEqual(model.read(0), 9)

    def test_irq_input_events_toggle_mask_and_global_enable(self):
        model = GpioModel({**self.p, "default_tri1": 15})
        model.step(self.command(Action.DRIVE, pins=1))
        self.assertEqual(model.read(0x120), 1)
        model.step(self.command(Action.WRITE, 0x128, 1, pins=1))
        row = model.step(self.command(Action.WRITE, 0x11C, 0x80000000, pins=1))
        self.assertEqual(row["ip2intc_irpt"], 1)
        row = model.step(self.command(Action.WRITE, 0x120, 1, pins=1))
        self.assertEqual(row["ip2intc_irpt"], 0)
        row = model.step(self.command(Action.WRITE, 0x120, 1, pins=1))
        self.assertEqual(row["ip2intc_irpt"], 1)
        row = model.step(self.command(Action.WRITE, 0x128, 0, pins=1))
        self.assertEqual(row["ip2intc_irpt"], 0)
        self.assertEqual(model.read(0x120), 1)

    def test_reset_restores_defaults_and_clears_interrupt_state(self):
        model = GpioModel(self.p)
        model.step(self.command(Action.WRITE, 4, 0))
        model.step(self.command(Action.WRITE, 0, 8))
        model.step(self.command(Action.WRITE, 0x120, 3))
        row = model.step(self.command(Action.RESET))
        self.assertEqual((row["gpio_io_o"].value, row["gpio_io_t"], row["ip2intc_irpt"]), (5, 10, 0))
        self.assertEqual([model.read(a) for a in (0x11C, 0x120, 0x128)], [0, 0, 0])

    def test_disabled_registers_and_fixed_direction_ports(self):
        spec = self.plugin.describe({**self.p, "mode1": "input", "default_tri1": 0, "default_data1": 0})
        self.assertEqual([p.name for p in spec.side_outputs], ["ip2intc_irpt"])
        self.assertEqual(spec.model_factory().read(4), 0xFFFFFFFF)
        spec = self.plugin.describe({**self.p, "mode1": "output", "default_tri1": 0, "interrupt": False})
        self.assertEqual(spec.side_inputs, ())
        self.assertEqual([p.name for p in spec.side_outputs], ["gpio_io_o"])
        model = spec.model_factory()
        model.write(0x120, 3)
        self.assertEqual(model.read(0x120), 0)

    def test_invalid_and_inactive_parameters_are_rejected(self):
        for changes in ({"channels": 0}, {"width1": True}, {"width1": 33}, {"mode1": "mixed"},
                        {"default_tri1": 16}, {"default_data1": -1}, {"width2": 2},
                        {"mode1": "input"}, {"mode1": "output"}, {"interrupt": 1}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_commands_require_exact_fields_aligned_addresses_and_canonical_unused_values(self):
        spec = self.plugin.describe(self.p)
        command = self.command(Action.WRITE)
        for changes in ({"action": 5}, {"address": 1}, {"data": -1}, {"gpio_io_i": 16},
                        {"action": int(Action.READ)}, {"address": 512}, {"extra": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                spec.validate_command({**command, **changes})

    def test_directed_sequence_has_all_strobes_each_bit_and_both_reset_phases(self):
        spec = self.plugin.describe(self.p)
        sequence = spec.prepare_operations([])
        writes = [op["command"] for op in sequence if op["command"]["action"] == Action.WRITE]
        self.assertEqual({c["strobe"] for c in writes if c["address"] == 0}, set(range(16)))
        for bit in range(32):
            self.assertTrue(any(c["data"] == 1 << bit for c in writes))
        self.assertEqual(sequence[0]["command"]["action"], Action.RESET)
        self.assertTrue(any(op["phase"] == "reset_suffix" for op in sequence))

    def test_generated_files_masks_metadata_and_input_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axi_gpio", Path(directory))
            case = replace(case, parameters=self.p)
            xci = Path(directory)/"fake.xci"
            xci.write_text('{"ip_inst": {"ip_revision": "37"}}')
            with patch("vivado_ip_test.plugins.common.axilite.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            manifest = json.loads(result.manifest_path.read_text())
            paths = {k: Path(v) for k, v in manifest["artifacts"].items()}
            for name, digest in manifest["artifact_sha256"].items():
                self.assertEqual(sha256_file(paths[name]), digest)
            schedule = json.loads(paths["schedule"].read_text())
            self.assertEqual(schedule["mapping_kind"], "register_operation")
            self.assertEqual(schedule["transaction_vector_indices"], list(range(result.vector_count)))
            self.assertIn(32, schedule["response_holds"])
            self.assertTrue(all(result.metrics["defined_output_bits_by_port"].values()))
            paths["actual_output"].write_bytes(paths["expected_output"].read_bytes())
            paths["accepted_input"].write_bytes(paths["input_vectors"].read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
            paths["accepted_input"].write_text("0\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)

    def test_read_mask_only_excludes_bits_outside_gpio_width(self):
        model = GpioModel(self.p)
        tri = model.step(self.command(Action.READ, 4))["read_data"]
        self.assertEqual((tri.value, tri.mask), (10, 15))
        self.assertEqual(model.step(self.command(Action.READ, 12))["read_data"], 0)
        model.write(0x128, 3)
        model.write(0x120, 3)
        self.assertEqual((model.read(0x128), model.read(0x120)), (1, 1))

    def test_missing_register_writes_are_not_omitted_from_sequence(self):
        sequence = self.plugin.describe({**self.p, "interrupt": False}).prepare_operations([])
        writes = [op["command"] for op in sequence if op["phase"] == "unimplemented_registers"
                  and op["command"]["action"] == Action.WRITE]
        self.assertEqual({c["address"] for c in writes}, {8, 12, 0x11C, 0x120, 0x128})
        self.assertEqual(len(writes), 15)

    def test_direction_sequence_exposes_input_write_before_random_samples(self):
        spec = self.plugin.describe(self.p)
        commands = [op["command"] for op in spec.prepare_operations([])]
        trace = [(c["action"], c["address"], c["data"]) for c in commands]
        self.assertIn([(Action.WRITE, 0, 0), (Action.WRITE, 4, 15), (Action.WRITE, 0, 0xFFFFFFFF)],
                      [trace[i:i+3] for i in range(len(trace)-2)])

    def test_rejects_revision_before_documented_output_readback_change(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axi_gpio", Path(directory))
            xci = Path(directory)/"fake.xci"
            xci.write_text('{"ip_inst": {"ip_revision": "13"}}')
            with patch("vivado_ip_test.plugins.common.axilite.testbench.load_metadata", return_value=(xci, {})):
                with self.assertRaisesRegex(ValueError, "revision >= 14"):
                    plugin.generate_testbench(case)

    def test_failure_records_operation_history_not_a_single_causal_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = self.plugin.describe(self.p)
            paths, _ = write_operations(root, spec, spec.prepare_operations([]), self.case.verification)
            expected = paths["expected_output"].read_text().splitlines()
            paths["actual_output"].write_text("\n".join(expected[:10] + ["1" * len(expected[10])] + expected[11:]) + "\n")
            evidence = analyze_outputs(root)
            self.assertEqual(evidence["operation_index"], 10)
            self.assertEqual(evidence["preceding_reset_operation_index"], 0)
            self.assertEqual(len(evidence["preceding_operations"]), 8)
            self.assertTrue(evidence["causal_input_not_identified"])
