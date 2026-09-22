import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.mailbox.reference import AxisMailboxPlan


EXPECTED_EVENTS = (
    "RESET", "S0_TO_M1", "S1_TO_M0", "FIFO_FULL_BACKPRESSURE",
    "BIDIRECTIONAL_CONCURRENT", "RESET_FLUSH",
)


def _vhdl_data(beats):
    return ", ".join(f'x"{beat.data:08X}"' for beat in beats)


def _vhdl_last(beats):
    return ", ".join("'1'" if beat.last else "'0'" for beat in beats)


class AxisMailboxTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_mailbox_axis_selfcheck.vhd.tpl"

    @staticmethod
    def metadata_spec(plan):
        inputs = [Port("SYS_Rst", scalar=True)]
        outputs = [Port("Interrupt_0", scalar=True), Port("Interrupt_1", scalar=True)]
        for index in range(2):
            inputs.extend((Port(f"S{index}_AXIS_TDATA", 32),
                           Port(f"S{index}_AXIS_TLAST", scalar=True),
                           Port(f"S{index}_AXIS_TVALID", scalar=True),
                           Port(f"M{index}_AXIS_TREADY", scalar=True)))
            outputs.extend((Port(f"S{index}_AXIS_TREADY", scalar=True),
                            Port(f"M{index}_AXIS_TDATA", 32),
                            Port(f"M{index}_AXIS_TLAST", scalar=True),
                            Port(f"M{index}_AXIS_TVALID", scalar=True)))
        style_number = 0 if plan.memory_style == "Distributed_RAM" else 1
        settings = {
            "C_INTERCONNECT_PORT_0": 4, "C_INTERCONNECT_PORT_1": 4,
            "C_MAILBOX_DEPTH": plan.depth, "C_IMPL_STYLE": style_number,
            "C_ASYNC_CLKS": int(plan.async_clocks),
            "C_S0_AXIS_DATA_WIDTH": 32, "C_M0_AXIS_DATA_WIDTH": 32,
            "C_S1_AXIS_DATA_WIDTH": 32, "C_M1_AXIS_DATA_WIDTH": 32,
        }
        models = dict(settings)
        models["C_NUM_SYNC_FF"] = 2
        return CycleSpec(
            inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=models, model_factory=lambda: None,
            clock="S0_AXIS_ACLK",
            clock_aliases=("M0_AXIS_ACLK", "S1_AXIS_ACLK", "M1_AXIS_ACLK"),
        )

    def generate(self, case):
        run = self._layout.case_run_dir(case)
        plan = AxisMailboxPlan.from_parameters(case.parameters)
        xci_path, metadata = load_metadata(run, self.metadata_spec(plan), "mailbox", "2.1")
        paths = {
            "state_plan": run / "vectors/state_plan.json",
            "expected_output": run / "vectors/expected_output.txt",
            "actual_output": run / "outputs/actual_output.txt",
            "testbench": run / "tb/tb_mailbox_axis_selfcheck.vhd",
        }
        for directory in (run / "vectors", run / "outputs", run / "tb"):
            directory.mkdir(parents=True, exist_ok=True)
        paths["state_plan"].write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
        paths["expected_output"].write_text("\n".join(EXPECTED_EVENTS) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        sources = plan.input_sequences()
        outputs = plan.expected_outputs()
        paths["testbench"].write_text(Template(self._template.read_text()).substitute(
            depth=plan.depth, vector_count=len(sources[0]),
            s0_data=_vhdl_data(sources[0]), s0_last=_vhdl_last(sources[0]),
            s1_data=_vhdl_data(sources[1]), s1_last=_vhdl_last(sources[1]),
            m0_data=_vhdl_data(outputs[0]), m0_last=_vhdl_last(outputs[0]),
            m1_data=_vhdl_data(outputs[1]), m1_last=_vhdl_last(outputs[1]),
            actual_path=str(paths["actual_output"].resolve()).replace('"', '""'),
        ))
        manifest_path = run / "manifest.json"
        manifest = {
            "schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(),
                             "total_vectors": len(EXPECTED_EVENTS),
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
            testbench_path=paths["testbench"], input_path=paths["state_plan"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest_path, vector_count=len(EXPECTED_EVENTS),
            metrics={"checked_directions": 2, "fill_transactions": plan.depth,
                     "reference_contract": plan.as_dict()},
        )
