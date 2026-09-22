from dataclasses import dataclass

from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axis_protocol_checker.reference import applicable_scenarios
from vivado_ip_test.plugins.axis_protocol_checker.testbench import AxisProtocolCheckerTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.metadata import setting_text


DATA_BYTES = {1, 4, 16, 128}
ID_DEST_WIDTHS = {0, 1, 4, 8, 16, 32}
USER_WIDTHS = {0, 1, 8, 16, 32, 128}
MAX_WAITS = {0, 16, 64, 256}


@dataclass(frozen=True)
class AxisProtocolCheckerSpec:
    metadata: CycleSpec
    settings: dict[str, object]
    parameters: dict[str, object]


class AxisProtocolCheckerPlugin:
    ip_type = ip_name = "axis_protocol_checker"
    version = "2.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxisProtocolCheckerTestbenchBackend(layout)

    def describe(self, p):
        validate_parameters(p, {"data_bytes": range(1, 129),
            "tid_width": range(0, 129), "tdest_width": range(0, 129),
            "tuser_width": range(0, 129), "has_tready": bool, "has_tstrb": bool,
            "has_tkeep": bool, "has_tlast": bool, "has_aclken": bool,
            "has_system_reset": bool, "max_waits": range(0, 257)})
        if p["data_bytes"] not in DATA_BYTES:
            raise PluginError("AXIS Protocol Checker 数据字节数不受支持")
        for name in ("tid_width", "tdest_width"):
            if p[name] not in ID_DEST_WIDTHS:
                raise PluginError(f"AXIS Protocol Checker 参数 {name} 不受支持")
        if p["tuser_width"] not in USER_WIDTHS:
            raise PluginError("AXIS Protocol Checker 参数 tuser_width 不受支持")
        if p["max_waits"] not in MAX_WAITS:
            raise PluginError("AXIS Protocol Checker 最大等待周期不受支持")
        effective_max_waits = p["max_waits"] if p["has_tready"] else 0
        settings = {"TDATA_NUM_BYTES": p["data_bytes"], "TID_WIDTH": p["tid_width"],
            "TDEST_WIDTH": p["tdest_width"], "TUSER_WIDTH": p["tuser_width"],
            "HAS_TREADY": int(p["has_tready"]), "HAS_TSTRB": int(p["has_tstrb"]),
            "HAS_TKEEP": int(p["has_tkeep"]), "HAS_TLAST": int(p["has_tlast"]),
            "HAS_ACLKEN": int(p["has_aclken"]),
            "HAS_SYSTEM_RESET": int(p["has_system_reset"]), "MAX_WAITS": effective_max_waits,
            "MESSAGE_LEVEL": 0, "ENABLE_CONTROL": 0, "ENABLE_MARK_DEBUG": 0}
        signal_set = (int(p["has_tready"]) | 2 | (int(p["has_tstrb"]) << 2) |
            (int(p["has_tkeep"]) << 3) | (int(p["has_tlast"]) << 4) |
            (int(p["tid_width"] > 0) << 5) | (int(p["tdest_width"] > 0) << 6) |
            (int(p["tuser_width"] > 0) << 7))
        models = {"C_AXIS_TDATA_WIDTH": p["data_bytes"] * 8,
            "C_AXIS_TID_WIDTH": max(1, p["tid_width"]),
            "C_AXIS_TDEST_WIDTH": max(1, p["tdest_width"]),
            "C_AXIS_TUSER_WIDTH": max(1, p["tuser_width"]),
            "C_AXIS_SIGNAL_SET": f"0b{signal_set:032b}", "C_PC_MAXWAITS": effective_max_waits,
            "C_PC_MESSAGE_LEVEL": 0, "C_PC_HAS_SYSTEM_RESET": int(p["has_system_reset"]),
            "C_ENABLE_CONTROL": 0, "C_PC_STATUS_WIDTH": 32, "C_ENABLE_MARK_DEBUG": 0}
        inputs = [Port("aresetn", scalar=True)]
        if p["has_system_reset"]:
            inputs.append(Port("system_resetn", scalar=True))
        if p["has_aclken"]:
            inputs.append(Port("aclken", scalar=True))
        inputs.append(Port("pc_axis_tvalid", scalar=True))
        if p["has_tready"]:
            inputs.append(Port("pc_axis_tready", scalar=True))
        inputs.append(Port("pc_axis_tdata", p["data_bytes"] * 8))
        if p["has_tstrb"]:
            inputs.append(Port("pc_axis_tstrb", p["data_bytes"]))
        if p["has_tkeep"]:
            inputs.append(Port("pc_axis_tkeep", p["data_bytes"]))
        if p["has_tlast"]:
            inputs.append(Port("pc_axis_tlast", scalar=True))
        for enabled, name, width in ((p["tid_width"], "pc_axis_tid", p["tid_width"]),
                (p["tdest_width"], "pc_axis_tdest", p["tdest_width"]),
                (p["tuser_width"], "pc_axis_tuser", p["tuser_width"])):
            if enabled:
                inputs.append(Port(name, width))
        metadata = CycleSpec(tuple(inputs), (Port("pc_asserted", scalar=True),
            Port("pc_status", 32)), settings, models, lambda: None, clock="aclk")
        return AxisProtocolCheckerSpec(metadata, settings, dict(p))

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXIS Protocol Checker IP 标识不匹配")
        if tuple(case.stages) != (Stage.CREATE_IP, Stage.GENERATE_TESTBENCH, Stage.SIM_SELFCHECK):
            raise PluginError("AXIS Protocol Checker 只支持创建、自检生成和行为仿真")
        if set(case.verification.coverage_targets) - {"protocol_rules"}:
            raise PluginError("AXIS Protocol Checker 仅支持 protocol_rules")
        self.describe(case.parameters)
        minimum = len(applicable_scenarios(case.parameters))
        if not minimum <= case.verification.case_budget <= 4096:
            raise PluginError("向量预算必须覆盖全部适用协议场景")

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXIS Protocol Checker IP creation:",
            source_path=self._layout.tcl_path("ip/axis_protocol_checker/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", setting_text(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXIS Protocol Checker 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXIS Protocol Checker behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_axis_protocol_checker.vhd",
            top_name="tb_axis_protocol_checker", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXIS_PROTOCOL_CHECKER_STATUS: PASS",
            failure_markers=("AXIS_PROTOCOL_CHECKER_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
