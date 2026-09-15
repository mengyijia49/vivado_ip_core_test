from functools import lru_cache

from vivado_ip_test.domain import SimulationRequest, Stage, Status
from vivado_ip_test.domain.counts import count_for_report
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.common.stream.testbench import StreamTestbenchBackend
from vivado_ip_test.plugins.common.vectors import port_space


@lru_cache(maxsize=512)
def _budget_bounds(ports, systematic):
    # Cache only immutable counts, not the vector generators or coverage state.
    space = port_space(ports, systematic)
    return len(space.directed_cases), space.total_case_count


class StreamIpPlugin(CycleIpPlugin):
    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = StreamTestbenchBackend(layout, strategy_registry)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("Stream IP identity does not match the plugin")
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("Stream official demo is not connected")
        if set(case.verification.coverage_targets) - {"port_boundaries", "complete_input_space"}:
            raise PluginError("Unsupported stream coverage target")
        spec = self.describe(case.parameters)
        minimum, maximum = _budget_bounds(tuple(spec.generated_ports),
                                          case.verification.boundary_mode == "systematic")
        budget = case.verification.case_budget
        if case.verification.strategy == "exhaustive":
            if budget < maximum:
                raise PluginError("Exhaustive stream budget is insufficient")
        elif not minimum <= budget <= maximum:
            raise PluginError(f"Stream budget must be between {minimum} "
                              f"and {count_for_report(maximum)}")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters), self.ip_name,
                                      self.version, self.expected_transactions)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Unsupported stream stage: {stage}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(
            description=f"Running {self.ip_type} behavioral stream self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_stream_selfcheck.vhd", top_name="tb_stream_selfcheck",
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXIS_SELF_CHECK_STATUS: PASS",
            failure_markers=("AXIS_SELF_CHECK_STATUS: FAIL",), failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        status = super().verify_simulation(case, stage)
        run = self._layout.case_run_dir(case)
        if status is Status.PASS and not output_files_match(
                run / "vectors/input_vectors.txt", run / "outputs/accepted_input.txt"):
            return Status.VERIFICATION_FAILED
        return status
