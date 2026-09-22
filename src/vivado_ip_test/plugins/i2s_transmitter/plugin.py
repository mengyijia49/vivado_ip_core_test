from dataclasses import dataclass

from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.metadata import setting_text
from vivado_ip_test.plugins.i2s_transmitter.testbench import I2sTransmitterTestbenchBackend


CHANNELS = {2, 4, 6, 8}
SAMPLE_WIDTHS = {16, 24}
FIFO_DEPTHS = {64, 128, 256, 512, 1024}


@dataclass(frozen=True)
class I2sTransmitterSpec:
    metadata: CycleSpec
    settings: dict[str, object]
    parameters: dict[str, object]


class I2sTransmitterPlugin:
    ip_type = ip_name = "i2s_transmitter"
    version = "1.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = I2sTransmitterTestbenchBackend(layout)

    def describe(self, p):
        validate_parameters(p, {"sample_width": range(1, 33), "channels": range(1, 9),
            "use_32bit_lr": bool, "fifo_depth": range(1, 1025),
            "sclk_divider": range(1, 16)})
        if p["sample_width"] not in SAMPLE_WIDTHS:
            raise PluginError("I2S Transmitter 只支持 16 或 24 位样本")
        if p["channels"] not in CHANNELS:
            raise PluginError("I2S Transmitter 只支持 2、4、6 或 8 声道")
        if p["fifo_depth"] not in FIFO_DEPTHS:
            raise PluginError("I2S Transmitter FIFO 深度不受支持")
        settings = {"C_IS_MASTER": 1, "C_NUM_CHANNELS": p["channels"],
            "C_DWIDTH": p["sample_width"], "C_32BIT_LR": int(p["use_32bit_lr"]),
            "C_DEPTH": p["fifo_depth"], "C_ENABLE_FIFO_COUNT": False,
            "USE_BOARD_FLOW": False, "I2STX_BOARD_INTERFACE": "Custom"}
        inputs = [Port("s_axi_ctrl_aresetn", scalar=True), Port("aud_mrst", scalar=True),
            Port("s_axis_aud_aresetn", scalar=True), Port("s_axi_ctrl_awvalid", scalar=True),
            Port("s_axi_ctrl_awaddr", 8), Port("s_axi_ctrl_wvalid", scalar=True),
            Port("s_axi_ctrl_wdata", 32), Port("s_axi_ctrl_bready", scalar=True),
            Port("s_axi_ctrl_arvalid", scalar=True), Port("s_axi_ctrl_araddr", 8),
            Port("s_axi_ctrl_rready", scalar=True), Port("s_axis_aud_tdata", 32),
            Port("s_axis_aud_tid", 3), Port("s_axis_aud_tvalid", scalar=True)]
        outputs = [Port("s_axi_ctrl_awready", scalar=True),
            Port("s_axi_ctrl_wready", scalar=True), Port("s_axi_ctrl_bvalid", scalar=True),
            Port("s_axi_ctrl_bresp", 2), Port("s_axi_ctrl_arready", scalar=True),
            Port("s_axi_ctrl_rvalid", scalar=True), Port("s_axi_ctrl_rdata", 32),
            Port("s_axi_ctrl_rresp", 2), Port("irq", scalar=True),
            Port("lrclk_out", scalar=True), Port("sclk_out", scalar=True),
            Port("sdata_0_out", scalar=True), Port("s_axis_aud_tready", scalar=True)]
        for lane in range(1, p["channels"] // 2):
            outputs.append(Port(f"sdata_{lane}_out", scalar=True))
        models = {"C_IS_MASTER": 1, "C_NUM_CHANNELS": p["channels"] // 2,
            "C_DWIDTH": p["sample_width"], "C_32BIT_LR": int(p["use_32bit_lr"]),
            "C_DEPTH": p["fifo_depth"]}
        metadata = CycleSpec(tuple(inputs), tuple(outputs), settings, models,
            lambda: None, clock="s_axi_ctrl_aclk",
            clock_aliases=("aud_mclk", "s_axis_aud_aclk"))
        return I2sTransmitterSpec(metadata, settings, dict(p))

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("I2S Transmitter IP 标识不匹配")
        if tuple(case.stages) != (Stage.CREATE_IP, Stage.GENERATE_TESTBENCH, Stage.SIM_SELFCHECK):
            raise PluginError("I2S Transmitter 只支持创建、自检生成和行为仿真")
        if set(case.verification.coverage_targets) != {"serial_data", "channel_routing",
                                                       "clock_ratio", "axi_handshake"}:
            raise PluginError("I2S Transmitter 覆盖目标不完整")
        if not 8 <= case.verification.case_budget <= 64:
            raise PluginError("I2S Transmitter 每组需要 8 至 64 帧")
        self.describe(case.parameters)

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running I2S Transmitter IP creation:",
            source_path=self._layout.tcl_path("ip/i2s_transmitter/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)),
                *(item for key, value in spec.settings.items()
                  for item in (f"CONFIG.{key}", setting_text(value)))),
            log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"I2S Transmitter 不支持阶段：{stage}")
        run = self._layout.case_run_dir(case)
        log = self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running I2S Transmitter behavioral self-check:",
            project_path=run / "proj/ip_test.xpr",
            testbench_path=run / "tb/tb_i2s_transmitter.sv",
            top_name="tb_i2s_transmitter", log_path=log,
            journal_path=log.with_suffix(".jou"),
            success_marker="I2S_TRANSMITTER_STATUS: PASS",
            failure_markers=("I2S_TRANSMITTER_STATUS: FAIL",),
            failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
