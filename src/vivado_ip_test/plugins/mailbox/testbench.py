import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.mailbox.reference import AxisMailboxPlan, MailboxPlan


EXPECTED_EVENTS = (
    "RESET_STATUS", "FIFO_0_TO_1", "FIFO_1_TO_0", "FULL_ERROR",
    "EMPTY_ERROR", "CLEAR_RECEIVE", "CLEAR_SEND", "THRESHOLD_INTERRUPTS",
    "RESET_RECOVERY",
)


class AxiLiteMailboxTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_mailbox_selfcheck.vhd.tpl"

    @staticmethod
    def metadata_spec(plan):
        inputs, outputs = [], []
        for index in range(2):
            prefix = f"S{index}_AXI_"
            inputs.extend((
                Port(prefix + "ARESETN", scalar=True), Port(prefix + "AWADDR", 32),
                Port(prefix + "AWVALID", scalar=True), Port(prefix + "WDATA", 32),
                Port(prefix + "WSTRB", 4), Port(prefix + "WVALID", scalar=True),
                Port(prefix + "BREADY", scalar=True), Port(prefix + "ARADDR", 32),
                Port(prefix + "ARVALID", scalar=True), Port(prefix + "RREADY", scalar=True),
            ))
            outputs.extend((
                Port(prefix + "AWREADY", scalar=True), Port(prefix + "WREADY", scalar=True),
                Port(prefix + "BRESP", 2), Port(prefix + "BVALID", scalar=True),
                Port(prefix + "ARREADY", scalar=True), Port(prefix + "RDATA", 32),
                Port(prefix + "RRESP", 2), Port(prefix + "RVALID", scalar=True),
            ))
        outputs.extend((Port("Interrupt_0", scalar=True), Port("Interrupt_1", scalar=True)))
        style_number = 0 if plan.memory_style == "Distributed_RAM" else 1
        settings = {
            "C_INTERCONNECT_PORT_0": 2, "C_INTERCONNECT_PORT_1": 2,
            "C_MAILBOX_DEPTH": plan.depth, "C_IMPL_STYLE": style_number,
            "C_ASYNC_CLKS": 0, "C_ENABLE_BUS_ERROR": int(plan.enable_bus_error),
            "C_ASYNC_INTERRUPTS": int(plan.registered_interrupts),
        }
        models = {
            "C_INTERCONNECT_PORT_0": 2, "C_INTERCONNECT_PORT_1": 2,
            "C_MAILBOX_DEPTH": plan.depth, "C_IMPL_STYLE": style_number,
            "C_ASYNC_CLKS": 0, "C_ENABLE_BUS_ERROR": int(plan.enable_bus_error),
            "C_ASYNC_INTERRUPTS": int(plan.registered_interrupts),
            "C_NUM_SYNC_FF": 2, "C_S0_AXI_ADDR_WIDTH": 32,
            "C_S0_AXI_DATA_WIDTH": 32, "C_S1_AXI_ADDR_WIDTH": 32,
            "C_S1_AXI_DATA_WIDTH": 32,
        }
        return CycleSpec(
            inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=models, model_factory=lambda: None,
            clock="S0_AXI_ACLK", clock_aliases=("S1_AXI_ACLK",),
        )

    def generate(self, case):
        run = self._layout.case_run_dir(case)
        plan = MailboxPlan.from_parameters(case.parameters)
        xci_path, metadata = load_metadata(run, self.metadata_spec(plan), "mailbox", "2.1")
        paths = {
            "state_plan": run / "vectors/state_plan.json",
            "expected_output": run / "vectors/expected_output.txt",
            "actual_output": run / "outputs/actual_output.txt",
            "testbench": run / "tb/tb_mailbox_selfcheck.vhd",
        }
        for directory in (run / "vectors", run / "outputs", run / "tb"):
            directory.mkdir(parents=True, exist_ok=True)
        paths["state_plan"].write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
        paths["expected_output"].write_text("\n".join(EXPECTED_EVENTS) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(Template(self._template.read_text()).substitute(
            depth=plan.depth,
            error_response='"10"' if plan.enable_bus_error else '"00"',
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
            testbench_path=paths["testbench"], input_path=paths["state_plan"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest_path, vector_count=len(EXPECTED_EVENTS),
            metrics={"checked_directions": 2, "fill_transactions": plan.depth,
                     "reference_contract": plan.as_dict()},
        )


class MailboxTestbenchBackend:
    def __init__(self, layout):
        from vivado_ip_test.plugins.mailbox.axis_testbench import AxisMailboxTestbenchBackend
        self._axi_lite = AxiLiteMailboxTestbenchBackend(layout)
        self._axis = AxisMailboxTestbenchBackend(layout)

    def _select(self, plan):
        if isinstance(plan, MailboxPlan):
            return self._axi_lite
        if isinstance(plan, AxisMailboxPlan):
            return self._axis
        raise TypeError(f"未知 Mailbox 计划：{type(plan).__name__}")

    def metadata_spec(self, plan):
        return self._select(plan).metadata_spec(plan)

    def generate(self, case):
        from vivado_ip_test.plugins.mailbox.reference import mailbox_plan
        return self._select(mailbox_plan(case.parameters)).generate(case)
