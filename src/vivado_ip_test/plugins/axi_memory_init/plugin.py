from dataclasses import dataclass

from vivado_ip_test.domain import BuildRequest, SimulationRequest, Stage, Status
from vivado_ip_test.infrastructure import output_files_match
from vivado_ip_test.plugins.axi_memory_init.reference import PATTERNS, initial_value
from vivado_ip_test.plugins.axi_memory_init.testbench import AxiMemoryInitTestbenchBackend
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.metadata import setting_text


DATA_WIDTHS = {32, 64, 128, 256, 512, 1024}
ADDRESS_WIDTHS = {24, 32, 64}
ID_WIDTHS = {1, 4, 8, 16, 32}
ADDRESS_SIZES = {11, 12, 13, 14}
STALL_CYCLES = {0, 1, 3, 7}
RESPONSE_DELAYS = {0, 1, 4, 8}
ACLKEN_PAUSES = {0, 1, 4, 8}


@dataclass(frozen=True)
class AxiMemoryInitSpec:
    metadata: CycleSpec
    settings: dict[str, object]
    parameters: dict[str, object]


def _ports(p):
    data, addr, ident, lanes = p["data_width"], p["address_width"], p["id_width"], p["data_width"] // 8
    scalar = lambda name: Port(name, scalar=True)
    vector = lambda name, width: Port(name, width)
    inputs = [scalar("init_complete_in"), scalar("aresetn"), scalar("aclken")]
    outputs = [scalar("init_complete_out")]
    for prefix in ("s_axi_aw",):
        inputs += [vector(prefix+"id", ident), vector(prefix+"addr", addr), vector(prefix+"len", 8),
            vector(prefix+"size", 3), vector(prefix+"burst", 2), vector(prefix+"lock", 1),
            vector(prefix+"cache", 4), vector(prefix+"prot", 3), vector(prefix+"qos", 4),
            vector(prefix+"region", 4), scalar(prefix+"valid")]
        outputs += [scalar(prefix+"ready")]
    inputs += [vector("s_axi_wdata", data), vector("s_axi_wstrb", lanes), scalar("s_axi_wlast"),
        scalar("s_axi_wvalid"), scalar("s_axi_bready")]
    outputs += [scalar("s_axi_wready"), vector("s_axi_bid", ident), vector("s_axi_bresp", 2),
        scalar("s_axi_bvalid")]
    inputs += [vector("s_axi_arid", ident), vector("s_axi_araddr", addr), vector("s_axi_arlen", 8),
        vector("s_axi_arsize", 3), vector("s_axi_arburst", 2), vector("s_axi_arlock", 1),
        vector("s_axi_arcache", 4), vector("s_axi_arprot", 3), vector("s_axi_arqos", 4),
        vector("s_axi_arregion", 4), scalar("s_axi_arvalid"), scalar("s_axi_rready")]
    outputs += [scalar("s_axi_arready"), vector("s_axi_rid", ident), vector("s_axi_rdata", data),
        vector("s_axi_rresp", 2), scalar("s_axi_rlast"), scalar("s_axi_rvalid")]
    outputs += [vector("m_axi_awid", ident), vector("m_axi_awaddr", addr), vector("m_axi_awlen", 8),
        vector("m_axi_awsize", 3), vector("m_axi_awburst", 2), vector("m_axi_awlock", 1),
        vector("m_axi_awcache", 4), vector("m_axi_awprot", 3), vector("m_axi_awqos", 4),
        vector("m_axi_awregion", 4), scalar("m_axi_awvalid")]
    inputs += [scalar("m_axi_awready")]
    outputs += [vector("m_axi_wdata", data), vector("m_axi_wstrb", lanes), scalar("m_axi_wlast"),
        scalar("m_axi_wvalid")]
    inputs += [scalar("m_axi_wready"), vector("m_axi_bid", ident), vector("m_axi_bresp", 2),
        scalar("m_axi_bvalid")]
    outputs += [scalar("m_axi_bready"), vector("m_axi_arid", ident), vector("m_axi_araddr", addr),
        vector("m_axi_arlen", 8), vector("m_axi_arsize", 3), vector("m_axi_arburst", 2),
        vector("m_axi_arlock", 1), vector("m_axi_arcache", 4), vector("m_axi_arprot", 3),
        vector("m_axi_arqos", 4), vector("m_axi_arregion", 4), scalar("m_axi_arvalid")]
    inputs += [scalar("m_axi_arready"), vector("m_axi_rid", ident), vector("m_axi_rdata", data),
        vector("m_axi_rresp", 2), scalar("m_axi_rlast"), scalar("m_axi_rvalid")]
    outputs += [scalar("m_axi_rready")]
    return tuple(inputs), tuple(outputs)


class AxiMemoryInitPlugin:
    ip_type = ip_name = "axi_memory_init"
    version = "1.0"

    def __init__(self, layout, strategy_registry):
        self._layout = layout
        self._backend = AxiMemoryInitTestbenchBackend(layout)

    def describe(self, p):
        validate_parameters(p, {"data_width": range(32, 1025), "address_width": range(24, 65),
            "id_width": range(1, 33), "address_size": range(11, 15),
            "base_address": range(0, 1 << 64), "init_pattern": PATTERNS,
            "stall_cycles": range(0, 8), "response_delay_cycles": range(0, 9),
            "aclken_pause_cycles": range(0, 9)})
        for name, allowed in (("data_width", DATA_WIDTHS), ("address_width", ADDRESS_WIDTHS),
                ("id_width", ID_WIDTHS), ("address_size", ADDRESS_SIZES),
                ("stall_cycles", STALL_CYCLES), ("response_delay_cycles", RESPONSE_DELAYS),
                ("aclken_pause_cycles", ACLKEN_PAUSES)):
            if p[name] not in allowed:
                raise PluginError(f"AXI Memory Initialization 参数 {name} 不受支持")
        minimum = (p["data_width"] // 8).bit_length() - 1 + 4
        if p["address_size"] < minimum:
            raise PluginError("address_size 至少要容纳一个 16 拍完整宽度 burst")
        if p["base_address"] % (1 << p["address_size"]):
            raise PluginError("base_address 必须按初始化地址范围对齐")
        if p["base_address"] + (1 << p["address_size"]) > 1 << p["address_width"]:
            raise PluginError("初始化地址范围超出 address_width")
        value = initial_value(p["init_pattern"], p["data_width"])
        settings = {"INIT_VALUE": f"0x{value:0{p['data_width']//4}X}",
            "ADDR_SIZE": p["address_size"], "BASE_ADDR": f"0x{p['base_address']:016X}",
            "ADDR_WIDTH": p["address_width"], "PROTOCOL": "AXI4",
            "READ_WRITE_MODE": "READ_WRITE", "DATA_WIDTH": p["data_width"],
            "ID_WIDTH": p["id_width"], "AWUSER_WIDTH": 0, "ARUSER_WIDTH": 0,
            "RUSER_WIDTH": 0, "WUSER_WIDTH": 0, "BUSER_WIDTH": 0,
            "HAS_ACLKEN": 1, "HAS_ARESETN": 1}
        models = {"C_PROTOCOL": 0, "C_ID_WIDTH": p["id_width"],
            "C_ADDR_WIDTH": p["address_width"], "C_RDATA_WIDTH": p["data_width"],
            "C_WDATA_WIDTH": p["data_width"], "C_AWUSER_WIDTH": 0, "C_ARUSER_WIDTH": 0,
            "C_WUSER_WIDTH": 0, "C_RUSER_WIDTH": 0, "C_BUSER_WIDTH": 0,
            "C_ADDR_SIZE": p["address_size"], "C_BASE_ADDR": f"0x{p['base_address']:X}",
            "C_INIT_VALUE": f"0x{value:X}"}
        inputs, outputs = _ports(p)
        metadata = CycleSpec(inputs, outputs, settings, models, lambda: None, clock="aclk",
            model_parameter_radices={"C_BASE_ADDR": 16, "C_INIT_VALUE": 16})
        return AxiMemoryInitSpec(metadata, settings, dict(p))

    def validate_case(self, case):
        if case.vendor != "xilinx.com" or case.ip_name != self.ip_name:
            raise PluginError("AXI Memory Initialization IP 标识不匹配")
        if tuple(case.stages) != (Stage.CREATE_IP, Stage.GENERATE_TESTBENCH, Stage.SIM_SELFCHECK):
            raise PluginError("AXI Memory Initialization 只支持创建、自检生成和行为仿真")
        if set(case.verification.coverage_targets) - {"port_boundaries"}:
            raise PluginError("AXI Memory Initialization 仅支持 port_boundaries")
        self.describe(case.parameters)

    def build_request(self, case):
        spec = self.describe(case.parameters)
        log = self._layout.stage_log_path(case, Stage.CREATE_IP)
        return BuildRequest(description="Running AXI Memory Initialization IP creation:",
            source_path=self._layout.tcl_path("ip/axi_memory_init/create_ip.tcl"),
            tclargs=(str(self._layout.case_run_dir(case)), *(item for key, value in spec.settings.items()
                for item in (f"CONFIG.{key}", setting_text(value)))), log_path=log,
            journal_path=log.with_suffix(".jou"), success_marker="Configured IP generated successfully.",
            artifact_glob="**/dut_0.xci")

    def generate_testbench(self, case):
        return self._backend.generate(case, self.describe(case.parameters))

    def simulation_request(self, case, stage):
        if stage is not Stage.SIM_SELFCHECK:
            raise PluginError(f"AXI Memory Initialization 不支持阶段：{stage}")
        run, log = self._layout.case_run_dir(case), self._layout.stage_log_path(case, stage)
        return SimulationRequest(description="Running AXI Memory Initialization behavioral self-check:",
            project_path=run / "proj/ip_test.xpr", testbench_path=run / "tb/tb_axi_memory_init.vhd",
            top_name="tb_axi_memory_init", log_path=log, journal_path=log.with_suffix(".jou"),
            success_marker="AXI_MEMORY_INIT_STATUS: PASS",
            failure_markers=("AXI_MEMORY_INIT_STATUS: FAIL",), failure_status=Status.SIMULATION_FAILED)

    def verify_simulation(self, case, stage):
        run = self._layout.case_run_dir(case)
        return Status.PASS if output_files_match(run / "vectors/expected_output.txt",
            run / "outputs/actual_output.txt") else Status.VERIFICATION_FAILED
