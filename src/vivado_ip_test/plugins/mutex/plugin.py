from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.mutex.reference import MutexPlan
from vivado_ip_test.plugins.mutex.testbench import MutexTestbenchBackend


class MutexPlugin:
    ip_type = ip_name = "mutex"
    version = "2.1"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = MutexTestbenchBackend(layout)

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError(f"{case.case_id} 的 vendor 或 ip_name 不匹配")
        validate_parameters(case.parameters, {
            "num_interfaces": range(2, 9),
            "num_mutexes": range(1, 33),
            "enable_user": bool,
            "hardware_protection": bool,
        })
        if Stage.SIM_DEMO in case.stages:
            raise PluginError("Mutex 没有接入官方示例")
        wanted = {"ownership", "cross_port_visibility", "arbitration", "reset"}
        if set(case.verification.coverage_targets) != wanted:
            raise PluginError("Mutex 覆盖目标必须包含所有权、跨端口可见性、仲裁和复位")
        if case.verification.case_budget != 1:
            raise PluginError("Mutex 每组配置使用一个确定性状态计划")
        MutexPlan.from_parameters(case.parameters)

    def build_request(self, case):
        plan = MutexPlan.from_parameters(case.parameters)
        settings = self._backend.metadata_spec(plan).settings
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(
            description="Running Mutex IP creation:",
            source_path=self._layout.tcl_path("ip/mutex/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                     *(item for key, value in settings.items()
                       for item in (f"CONFIG.{key}", str(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.",
            artifact_glob="proj/*.srcs/sources_1/ip/dut_0/dut_0.xci",
        )

    def generate_testbench(self, case):
        return self._backend.generate(case)

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Mutex 不支持仿真阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(
            description="Running Mutex behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_mutex_selfcheck.vhd",
            top_name="tb_mutex_selfcheck",
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="MUTEX_SELF_CHECK_STATUS: PASS",
            failure_markers=("MUTEX_SELF_CHECK_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED,
        )

    def verify_simulation(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"Mutex 不支持仿真阶段：{stage.value}")
        run = self._layout.case_run_dir(case)
        expected = run / "vectors/expected_output.txt"
        actual = run / "outputs/actual_output.txt"
        if not expected.is_file() or not actual.is_file():
            return Status.VERIFICATION_FAILED
        return Status.PASS if expected.read_bytes() == actual.read_bytes() else Status.VERIFICATION_FAILED
