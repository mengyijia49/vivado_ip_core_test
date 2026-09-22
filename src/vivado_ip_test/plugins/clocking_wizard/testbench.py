import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.clocking_wizard.reference import ClockPlan


EXPECTED_EVENTS = ("INITIAL_LOCK", "PERIOD_BEFORE_RESET", "RESET_UNLOCK",
                   "RELOCK", "PERIOD_AFTER_RESET")


class ClockingWizardTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_clocking_wizard_selfcheck.vhd.tpl"

    @staticmethod
    def metadata_spec(plan):
        reset_name = "reset" if plan.reset_active_high else "resetn"
        settings = {
            "PRIMITIVE": plan.primitive,
            "PRIM_IN_FREQ": f"{plan.input_frequency_mhz:.3f}",
            "CLKOUT1_REQUESTED_OUT_FREQ": f"{plan.output_frequency_mhz:.3f}",
            "CLKOUT1_REQUESTED_DUTY_CYCLE": "50.000",
            "NUM_OUT_CLKS": 1,
            "USE_RESET": True,
            "RESET_TYPE": "ACTIVE_HIGH" if plan.reset_active_high else "ACTIVE_LOW",
            "USE_LOCKED": True,
        }
        model_parameters = {
            "C_PRIM_IN_FREQ": f"{plan.input_frequency_mhz:.3f}",
            "C_CLKOUT1_REQUESTED_OUT_FREQ": f"{plan.output_frequency_mhz:.3f}",
            "C_CLKOUT1_REQUESTED_DUTY_CYCLE": "50.000",
            "C_NUM_OUT_CLKS": 1, "C_USE_RESET": 1,
            "C_RESET_LOW": int(not plan.reset_active_high), "C_USE_LOCKED": 1,
            "C_PRIMITIVE": plan.primitive,
        }
        return CycleSpec(
            inputs=(Port(reset_name, scalar=True),),
            outputs=(Port("clk_out1", scalar=True), Port("locked", scalar=True)),
            settings=settings, model_parameters=model_parameters,
            model_factory=lambda: None, clock="clk_in1",
        )

    def generate(self, case):
        run = self._layout.case_run_dir(case)
        plan = ClockPlan.from_parameters(case.parameters)
        xci_path, metadata = load_metadata(run, self.metadata_spec(plan), "clk_wiz", "6.0")
        paths = {
            "clock_plan": run / "vectors/clock_plan.json",
            "expected_output": run / "vectors/expected_output.txt",
            "actual_output": run / "outputs/actual_output.txt",
            "testbench": run / "tb/tb_clocking_wizard_selfcheck.vhd",
        }
        for directory in (run / "vectors", run / "outputs", run / "tb"):
            directory.mkdir(parents=True, exist_ok=True)
        paths["clock_plan"].write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
        paths["expected_output"].write_text("\n".join(EXPECTED_EVENTS) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        reset_name = "reset" if plan.reset_active_high else "resetn"
        paths["testbench"].write_text(Template(self._template.read_text()).substitute(
            reset_name=reset_name,
            reset_initial="'1'" if plan.reset_active_high else "'0'",
            reset_asserted="'1'" if plan.reset_active_high else "'0'",
            reset_inactive="'0'" if plan.reset_active_high else "'1'",
            input_half_period_ps=plan.input_half_period_ps,
            output_period_ps=plan.output_period_ps,
            output_high_ps=plan.output_high_ps,
            actual_path=str(paths["actual_output"].resolve()).replace('"', '""'),
        ))
        manifest_path = run / "manifest.json"
        manifest = {
            "schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(EXPECTED_EVENTS),
                             "reference_contract": plan.as_dict()},
            "generated_ip": metadata,
            "artifacts": {"xci": str(xci_path.resolve()),
                          **{name: str(path.resolve()) for name, path in paths.items()}},
            "artifact_sha256": {"xci": sha256_file(xci_path),
                                **{name: sha256_file(path) for name, path in paths.items()
                                   if name != "actual_output"}},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        return TestbenchArtifacts(
            testbench_path=paths["testbench"], input_path=paths["clock_plan"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest_path, vector_count=len(EXPECTED_EVENTS),
            metrics={"checked_clock_windows": 2, "measured_periods": 32,
                     "reference_contract": plan.as_dict()},
        )
