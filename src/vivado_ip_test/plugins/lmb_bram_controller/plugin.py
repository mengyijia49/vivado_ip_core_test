from dataclasses import replace

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.lmb_bram_controller.reference import (
    LmbBramControllerModel,
    WRITE_ACCESS,
    address_mask,
)
from vivado_ip_test.plugins.lmb_bram_controller.vectors import directed_sequence


class LmbBramControllerPlugin(CycleIpPlugin):
    ip_type = "lmb_bram_controller"
    ip_name = "lmb_bram_if_cntlr"
    version = "4.0"

    def describe(self, p):
        validate_parameters(p, {
            "data_width": range(32, 65),
            "address_width": range(32, 65),
            "base_address": range(0, 1 << 64),
            "address_size": range(4096, 1048577),
            "write_access": set(WRITE_ACCESS),
            "protection": bool,
            "protection_mask": range(0, 256),
        })
        data_width = p["data_width"]
        address_width = p["address_width"]
        address_size = p["address_size"]
        if data_width not in {32, 64} or address_width not in {32, 64}:
            raise PluginError("LMB BRAM Controller 位宽只支持 32 或 64")
        if address_size not in {4096, 65536, 1048576}:
            raise PluginError("LMB BRAM Controller 地址范围不受支持")
        if p["base_address"] % address_size:
            raise PluginError("LMB BRAM Controller base_address 必须按 address_size 对齐")
        if p["base_address"] + address_size > 1 << address_width:
            raise PluginError("LMB BRAM Controller 地址范围超出 address_width")
        if not p["protection"] and p["protection_mask"] != 255:
            raise PluginError("未启用 protection 时 protection_mask 必须为 255")

        lanes = data_width // 8
        inputs = [Port("LMB_Rst", scalar=True), Port("LMB_ABus", address_width),
                  Port("LMB_WriteDBus", data_width), Port("LMB_AddrStrobe", scalar=True),
                  Port("LMB_ReadStrobe", scalar=True), Port("LMB_WriteStrobe", scalar=True),
                  Port("LMB_BE", lanes)]
        if p["protection"]:
            inputs.insert(2, Port("LMB_Prot", 2))
        inputs.append(Port("BRAM_Din_A", data_width))
        outputs = (Port("Sl_DBus", data_width), Port("Sl_Ready", scalar=True),
                   Port("Sl_Wait", scalar=True), Port("Sl_UE", scalar=True),
                   Port("Sl_CE", scalar=True), Port("BRAM_Rst_A", scalar=True),
                   Port("BRAM_Clk_A", scalar=True), Port("BRAM_Addr_A", 32),
                   Port("BRAM_EN_A", scalar=True), Port("BRAM_WEN_A", lanes),
                   Port("BRAM_Dout_A", data_width))
        base = p["base_address"]
        high = base + address_size - 1
        config = {
            "C_BASEADDR": f"0x{base:016X}", "C_HIGHADDR": f"0x{high:016X}",
            "C_MASK": f"0x{address_mask(address_size):016X}", "C_NUM_LMB": 1,
            "C_LMB_AWIDTH": address_width, "C_LMB_DWIDTH": data_width,
            "C_LMB_PROTOCOL": 0, "C_LMB_HAS_PROT": int(p["protection"]),
            "C_PROT_CFG": f"0x{p['protection_mask']:02X}", "C_ARBITRATION": 0,
            "C_ECC": 0, "C_WRITE_ACCESS": WRITE_ACCESS[p["write_access"]],
        }
        models = {**config, "C_BRAM_AWIDTH": 32}
        parameters = dict(p)
        spec = CycleSpec(
            inputs=tuple(inputs), outputs=outputs, settings=config, model_parameters=models,
            model_factory=lambda: LmbBramControllerModel(parameters), clock="LMB_Clk",
            prefix=(), flush_cycles=2,
            idle_values={"LMB_Rst": 0, "LMB_AddrStrobe": 0,
                         "LMB_ReadStrobe": 0, "LMB_WriteStrobe": 0},
        )
        return replace(spec, prefix=lambda: directed_sequence(parameters, spec))
