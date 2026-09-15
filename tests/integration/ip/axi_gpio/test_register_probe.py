from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import unittest

from vivado_ip_test.adapters.vivado import VivadoBatchRunner
from vivado_ip_test.infrastructure import CommandRunner, RepositoryLayout, sha256_file


@unittest.skipUnless(os.environ.get("VIVADO_INTEGRATION") == "1", "需显式启用真实 Vivado 集成测试")
class GpioRegisterProbeTests(unittest.TestCase):
    def test_independent_register_observations(self):
        root = Path(__file__).resolve().parents[4]
        layout = RepositoryLayout(root)
        run = root / "runs/framework/register_probe" / layout.run_id / "axi_gpio"
        logs = root / "runs/logs/framework/register_probe" / layout.run_id / "axi_gpio"
        run.mkdir(parents=True)
        logs.mkdir(parents=True)
        fixture = root / "tests/fixtures/ip/axi_gpio/tb_register_probe.vhd"
        parameters = {"CONFIG.C_IS_DUAL": "0", "CONFIG.C_INTERRUPT_PRESENT": "0",
            "CONFIG.C_GPIO_WIDTH": "8", "CONFIG.C_ALL_INPUTS": "0", "CONFIG.C_ALL_OUTPUTS": "0",
            "CONFIG.C_DOUT_DEFAULT": "0x00000000", "CONFIG.C_TRI_DEFAULT": "0x000000FF"}
        runner = VivadoBatchRunner(CommandRunner(), run / "work")
        with redirect_stdout(io.StringIO()):
            created = runner.run(description="Create independent GPIO register probe:",
                source=root / "tcl/ip/axi_gpio/create_ip.tcl",
                tclargs=[str(run), *[item for pair in parameters.items() for item in pair]],
                log_path=logs / "create.log", journal_path=logs / "create.jou", timeout_sec=90)
            self.assertEqual(created.returncode, 0, created.output[-2000:])
            result = runner.run(description="Observe GPIO registers without generated vectors or Python oracle:",
                source=root / "tcl/run_xsim_batch.tcl", tclargs=[str(run / "proj/ip_test.xpr"), str(fixture),
                    "tb_register_probe", "GPIO_REGISTER_PROBE: COMPLETE", "GPIO_REGISTER_PROBE: FAIL"],
                log_path=logs / "simulate.log", journal_path=logs / "simulate.jou", timeout_sec=90)
        observations = {name: {"read": int(data, 16), "pins": int(pins, 16), "tri": int(tri, 16)}
            for name, data, pins, tri in re.findall(
                r"GPIO_REGISTER_OBSERVATION (\w+)=([0-9A-F]+) pins=([0-9A-F]+) tri=([0-9A-F]+)", result.output)}
        (run / "observations.json").write_text(json.dumps({"classification": "UNTRIAGED",
            "completion_is_not_a_bug_confirmation": True, "parameters": parameters,
            "fixture_sha256": sha256_file(fixture), "observations": observations,
            "returncode": result.returncode}, indent=2) + "\n")
        self.assertEqual(result.returncode, 0, result.output[-3000:])
        self.assertEqual(set(observations), {"initial_tri", "disabled_channel_tri", "output_read_control",
            "input_read_control", "after_input_write", "disabled_irq_read", "after_disabled_irq_write"})
