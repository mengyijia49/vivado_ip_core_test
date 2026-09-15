from vivado_ip_test.domain import SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.common.axilite.testbench import AxiLiteTestbenchBackend
from vivado_ip_test.plugins.common.vectors import port_space


class AxiLiteIpPlugin(CycleIpPlugin):
    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiLiteTestbenchBackend(layout, strategy_registry)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI-Lite IP identity does not match the plugin")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("AXI-Lite official demo is not connected")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("Unsupported AXI-Lite coverage target")
        spec = self.describe(case.parameters)
        space = port_space(spec.generated_ports, case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if case.verification.strategy == "exhaustive":
            if budget < space.total_case_count:
                raise PluginError("Exhaustive AXI-Lite numerical budget is insufficient")
        elif not len(space.directed_cases) <= budget <= space.total_case_count:
            raise PluginError(f"AXI-Lite budget must be between {len(space.directed_cases)} and {space.total_case_count}")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters), self.ip_name, self.version)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Unsupported AXI-Lite stage: {stage}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(description=f"Running {self.ip_type} AXI-Lite behavioral self-check:",
            project_path=run / "proj/ip_test.xpr", testbench_path=run / "tb/tb_axilite_selfcheck.vhd",
            top_name="tb_axilite_selfcheck", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXILITE_SELF_CHECK_STATUS: PASS",
            failure_markers=("AXILITE_SELF_CHECK_STATUS: FAIL",), failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Unsupported AXI-Lite stage: {stage}")
        run = self._layout.case_run_dir(case)
        matches = output_files_match(run / "vectors/expected_output.txt", run / "outputs/actual_output.txt",
                                     mask_path=run / "vectors/expected_mask.txt")
        matches &= output_files_match(run / "vectors/input_vectors.txt", run / "outputs/accepted_input.txt")
        return Status.PASS if matches else Status.VERIFICATION_FAILED
