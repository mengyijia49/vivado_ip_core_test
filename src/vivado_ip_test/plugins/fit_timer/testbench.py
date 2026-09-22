import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.fit_timer.reference import FitTimerPlan


EXPECTED_EVENTS = ("RESET_SUPPRESSION", "FIRST_INTERRUPT", "PERIODS_BEFORE_RESET",
                   "RUNTIME_RESET", "FIRST_INTERRUPT_AFTER_RESET", "PERIODS_AFTER_RESET")


class FitTimerTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_fit_timer_selfcheck.vhd.tpl"

    @staticmethod
    def metadata_spec(plan):
        settings = {
            "C_NO_CLOCKS": plan.no_clocks,
            "C_INACCURACY": plan.inaccuracy,
            "C_EXT_RESET_HIGH": int(plan.reset_active_high),
        }
        return CycleSpec(
            inputs=(Port("Rst", scalar=True),), outputs=(Port("Interrupt", scalar=True),),
            settings=settings,
            model_parameters={"C_FAMILY": "artix7", **settings},
            model_factory=lambda: None, clock="Clk",
        )

    def generate(self, case):
        run = self._layout.case_run_dir(case)
        plan = FitTimerPlan.from_parameters(case.parameters)
        xci_path, metadata = load_metadata(run, self.metadata_spec(plan), "fit_timer", "2.0")
        paths = {
            "timing_plan": run / "vectors/timing_plan.json",
            "expected_output": run / "vectors/expected_output.txt",
            "actual_output": run / "outputs/actual_output.txt",
            "testbench": run / "tb/tb_fit_timer_selfcheck.vhd",
        }
        for directory in (run / "vectors", run / "outputs", run / "tb"):
            directory.mkdir(parents=True, exist_ok=True)
        paths["timing_plan"].write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
        paths["expected_output"].write_text("\n".join(EXPECTED_EVENTS) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(Template(self._template.read_text()).substitute(
            minimum_period=plan.minimum_period,
            maximum_period=plan.maximum_period,
            first_timeout=2 * plan.no_clocks + 20,
            watchdog_ns=(10 * plan.no_clocks + 200) * 10,
            reset_asserted="'1'" if plan.reset_active_high else "'0'",
            reset_inactive="'0'" if plan.reset_active_high else "'1'",
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
            testbench_path=paths["testbench"], input_path=paths["timing_plan"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest_path, vector_count=len(EXPECTED_EVENTS),
            metrics={"measured_periods": 6, "reset_windows": 2,
                     "reference_contract": plan.as_dict()},
        )
