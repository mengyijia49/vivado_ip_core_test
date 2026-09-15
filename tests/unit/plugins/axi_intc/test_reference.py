from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from vivado_ip_test.configuration import load_test_cases
from vivado_ip_test.domain import Stage, Status
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.axi_intc.reference import IntcModel, ISR, IPR, IER, IAR, SIE, CIE, IVR, MER, ILR, WORD
from unit.plugins.cycle_helpers import ROOT, plugin_case


class IntcTests(unittest.TestCase):
    def setUp(self):
        self.plugin, self.case = plugin_case("axi_intc")
        self.p = {**self.case.parameters, "input_modes": ["rising", "high", "falling", "low"]}

    def command(self, action, address=0, data=0, pins=12):
        return {"action": int(action), "address": address, "data": data,
                "strobe": 15 if action == Action.WRITE else 0, "intr": pins}

    def test_reset_values_and_empty_priority(self):
        model = IntcModel(self.p)
        self.assertEqual([model.read(a) for a in (ISR, IPR, IER, MER, IVR, ILR)],
                         [0, 0, 0, 0, WORD, WORD])
        self.assertEqual(model.step(self.command(Action.IDLE))["irq"], 0)

    def test_isr_write_zero_and_separate_writes_preserve_old_bits_in_both_modes(self):
        for hie, first, second in ((0, 1, 2), (2, 16, 32)):
            model = IntcModel(self.p)
            model.write(MER, hie | 1)
            model.write(IER, WORD)
            model.write(ISR, first)
            model.write(ISR, 0)
            self.assertEqual(model.read(ISR), first)
            model.write(ISR, second)
            self.assertEqual(model.read(ISR), first | second)
            model.write(IAR, first)
            self.assertEqual(model.read(ISR), second)
            model.write(IAR, 0)
            self.assertEqual(model.read(ISR), second)

    def test_hardware_write_blocked_after_hie_software_remains_writable(self):
        model = IntcModel(self.p)
        model.write(MER, 3)
        model.write(ISR, WORD)
        self.assertEqual(model.read(ISR), 48)
        for value, expected in ((0, 2), (1, 3), (0, 2), (WORD, 3)):
            model.write(MER, value)
            self.assertEqual(model.read(MER), expected)

    def test_all_four_trigger_modes_latch_and_acknowledge_differently(self):
        model = IntcModel(self.p)
        model.write(MER, 3)
        model.drive(3)
        self.assertEqual(model.read(ISR), 15)
        self.assertEqual(model.read(IPR), 0)
        model.write(IAR, 15)
        self.assertEqual(model.read(ISR), 10)
        model.drive(12)
        self.assertEqual(model.read(ISR), 10)
        model.write(IAR, 15)
        self.assertEqual(model.read(ISR), 0)
        model.drive(3)
        model.drive(12)
        self.assertEqual(model.read(ISR), 15)

    def test_enable_and_master_masks_do_not_destroy_captured_status(self):
        model = IntcModel(self.p)
        model.write(MER, 2)
        model.drive(3)
        model.drive(12)
        self.assertEqual(model.read(ISR), 15)
        model.write(IER, 10)
        self.assertEqual((model.read(IPR), model.read(IVR)), (10, 1))
        self.assertEqual(model.step(self.command(Action.IDLE))["irq"], 0)
        self.assertEqual(model.step(self.command(Action.WRITE, MER, 1))["irq"], 1)
        model.write(IER, 0)
        self.assertEqual((model.read(ISR), model.read(IPR), model.read(IVR)), (15, 0, WORD))

    def test_priority_limit_only_gates_irq(self):
        model = IntcModel(self.p)
        model.write(ISR, 32)
        model.write(IER, 63)
        model.write(MER, 1)
        for limit, irq in ((0, 0), (5, 0), (6, 1), (WORD, 1)):
            row = model.step(self.command(Action.WRITE, ILR, limit))
            self.assertEqual((model.read(ILR), model.read(IPR), model.read(IVR), row["irq"]),
                             (limit, 32, 5, irq))

    def test_active_low_output_and_disabled_ilr(self):
        model = IntcModel({**self.p, "irq_active_high": False, "has_ilr": False})
        self.assertEqual(model.step(self.command(Action.IDLE))["irq"], 1)
        model.write(ISR, 1)
        model.write(IER, 1)
        model.write(ILR, 0)
        self.assertEqual(model.step(self.command(Action.WRITE, MER, 1))["irq"], 0)

    def test_atomic_enable_and_unused_register_bits(self):
        model = IntcModel(self.p)
        model.write(SIE, 5)
        model.write(SIE, 10)
        model.write(SIE, 0)
        self.assertEqual(model.read(IER), 15)
        model.write(CIE, 9)
        model.write(CIE, 0)
        self.assertEqual(model.read(IER), 6)
        model.write(IER, WORD)
        model.write(ISR, WORD)
        self.assertEqual((model.read(IER), model.read(ISR)), (63, 63))
        model.write(IAR, WORD)
        model.write(MER, WORD)
        self.assertEqual(model.read(MER), 3)

    def test_reset_clears_pending_and_write_once_hie(self):
        model = IntcModel(self.p)
        model.write(MER, 3)
        model.drive(3)
        row = model.step(self.command(Action.RESET))
        self.assertEqual((model.read(ISR), model.read(MER), model.read(ILR), row["irq"]), (0, 0, WORD, 0))
        model.write(ISR, 1)
        self.assertEqual(model.read(ISR), 1)

    def test_unspecified_or_unsupported_accesses_are_not_silently_scored(self):
        model = IntcModel(self.p)
        for address in (IAR, SIE, CIE, 32, 256):
            with self.assertRaises(ValueError):
                model.read(address)
        with self.assertRaises(ValueError):
            model.step({**self.command(Action.WRITE), "strobe": 0})
        with self.assertRaises(ValueError):
            model.drive(3)
        with self.assertRaises(ValueError):
            model.write(ILR, 0x80000000)
        model.write(ISR, 1)
        with self.assertRaises(ValueError):
            model.write(MER, 3)

    def test_optional_registers_and_read_only_writes(self):
        model = IntcModel(self.p)
        model.write(ISR, 2)
        model.write(IER, 3)
        for address in (IPR, IVR):
            before = model.read(address)
            model.write(address, WORD)
            self.assertEqual(model.read(address), before)
        absent = IntcModel({**self.p, "has_sie": False, "has_cie": False, "has_ipr": False,
                            "has_ivr": False, "has_ilr": False})
        absent.write(SIE, WORD)
        self.assertEqual(absent.read(IER), 0)
        absent.write(IER, WORD)
        absent.write(CIE, WORD)
        self.assertEqual(absent.read(IER), 63)
        for address in (IPR, IVR, ILR):
            with self.assertRaises(ValueError):
                absent.read(address)

    def test_parameters_ports_masks_and_zero_synchronizer_boundary(self):
        spec = self.plugin.describe({**self.p, "async_mask": 15, "synchronizer_stages": 0})
        self.assertEqual(spec.settings["C_KIND_OF_INTR"], "0x00000005")
        self.assertEqual(spec.settings["C_KIND_OF_EDGE"], "0x00000001")
        self.assertEqual(spec.settings["C_KIND_OF_LVL"], "0x00000002")
        self.assertEqual(spec.settings["C_NUM_SYNC_FF"], 0)
        self.assertEqual(spec.settings["C_IRQ_CONNECTION"], 0)
        self.assertNotIn("C_IRQ_CONNECTION", spec.model_parameters)
        self.assertEqual((spec.side_inputs[0].name, spec.side_inputs[0].width), ("intr", 4))
        self.assertEqual((spec.side_outputs[0].name, spec.side_outputs[0].scalar), ("irq", True))
        self.assertEqual(spec.settle_cycles, 64)
        self.assertNotIn("strobe", [p.name for p in spec.generated_ports])
        self.assertEqual(next(p.limit for p in spec.generated_ports if p.name == "priority_limit"), 6)
        one = self.plugin.describe(self.case.parameters)
        self.assertEqual((one.side_inputs[0].width, one.side_inputs[0].scalar), (1, False))

    def test_rejects_invalid_parameters_and_total_overflow(self):
        for changes in ({"input_modes": []}, {"input_modes": ["edge"]}, {"input_modes": "high"},
                        {"input_modes": ["low"]*33}, {"software_interrupts": 29},
                        {"software_interrupts": True}, {"async_mask": 16}, {"async_mask": -1},
                        {"synchronizer_stages": 8}, {"synchronizer_stages": 0},
                        {"has_ilr": 1}, {"irq_active_high": 0}, {"extra": 0}):
            with self.subTest(changes=changes), self.assertRaises(PluginError):
                self.plugin.describe({**self.p, **changes})

    def test_directed_groups_are_reset_isolated_and_keep_isr_zero_writes(self):
        spec = self.plugin.describe(self.p)
        operations = spec.prepare_operations([])
        model = spec.model_factory()
        groups = {}
        for op in operations:
            spec.validate_command(op["command"])
            model.step(op["command"])
            groups.setdefault(op["phase"], []).append(op["command"])
        for phase, commands in groups.items():
            if phase.startswith(("hardware_capture", "isr_preservation")):
                self.assertEqual(commands[0]["action"], Action.RESET)
            if phase.startswith("isr_preservation"):
                self.assertTrue(any(c["action"] == Action.WRITE and c["address"] == ISR and c["data"] == 0
                                    for c in commands))
        self.assertIn("isr_preservation_hie1_bit5", groups)
        self.assertIn("reset_suffix", groups)

    def test_all_intc_matrices_validate_and_have_no_duplicate_parameters(self):
        signatures = set()
        extended = load_test_cases(ROOT / "configs/ip/axi_intc/extended.json")
        self.assertEqual(len(extended), 8960)
        for case in extended:
            self.plugin.validate_case(case)
            signatures.add(json.dumps(dict(case.parameters), sort_keys=True))
        self.assertEqual(len(signatures), len(extended))
        common = load_test_cases(ROOT / "configs/ip/axi_intc/regression.json")
        self.assertEqual(len(common), 12)
        for case in common:
            self.plugin.validate_case(case)
            spec = self.plugin.describe(case.parameters)
            sample = {port.name: port.limit for port in spec.generated_ports}
            model = spec.model_factory()
            for op in spec.prepare_operations([sample, dict.fromkeys(sample, 0)]):
                spec.validate_command(op["command"])
                model.step(op["command"])

    def test_artifacts_hashes_input_audit_and_irq_fault_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin, case = plugin_case("axi_intc", Path(directory))
            case = replace(case, parameters=self.p)
            xci = Path(directory)/"fake.xci"
            xci.write_text('{"ip_inst": {"ip_revision": "22"}}')
            with patch("vivado_ip_test.plugins.common.axilite.testbench.load_metadata", return_value=(xci, {})):
                result = plugin.generate_testbench(case)
            manifest = json.loads(result.manifest_path.read_text())
            paths = {key: Path(value) for key, value in manifest["artifacts"].items()}
            for name, digest in manifest["artifact_sha256"].items():
                self.assertEqual(sha256_file(paths[name]), digest)
            paths["actual_output"].write_bytes(paths["expected_output"].read_bytes())
            paths["accepted_input"].write_bytes(paths["input_vectors"].read_bytes())
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.PASS)
            rows = paths["actual_output"].read_text().splitlines()
            rows[0] = rows[0][:-1] + str(1-int(rows[0][-1]))
            paths["actual_output"].write_text("\n".join(rows)+"\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
            paths["actual_output"].write_bytes(paths["expected_output"].read_bytes())
            paths["accepted_input"].write_text("0\n")
            self.assertIs(plugin.verify_simulation(case, Stage.SIM_SELFCHECK), Status.VERIFICATION_FAILED)
            schedule = json.loads(paths["schedule"].read_text())
            self.assertIn(32, schedule["response_holds"])
            self.assertTrue(all(result.metrics["defined_output_bits_by_port"].values()))
