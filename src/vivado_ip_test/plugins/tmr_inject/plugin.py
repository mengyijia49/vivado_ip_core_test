from dataclasses import replace

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.tmr_inject.reference import (
    TmrInjectModel, address_mask, protection_allowed,
)
from vivado_ip_test.plugins.tmr_inject.vectors import directed_sequence


SIZES = {2048, 4096, 65536}


class TmrInjectPlugin(CycleIpPlugin):
    ip_type = ip_name = "tmr_inject"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {
            "base_address": range(0, 1 << 32), "address_size": range(2048, 65537),
            "magic": range(0, 256), "cpu_id": range(1, 4),
            "protection": bool, "protection_mask": range(0, 256),
        })
        if p["address_size"] not in SIZES:
            raise PluginError("TMR Inject 地址范围不受支持")
        if p["base_address"] % p["address_size"]:
            raise PluginError("TMR Inject base_address 必须按 address_size 对齐")
        if p["base_address"] + p["address_size"] > 1 << 32:
            raise PluginError("TMR Inject 地址范围超出 32 位")
        if not p["protection"] and p["protection_mask"] != 255:
            raise PluginError("未启用 protection 时 protection_mask 必须为 255")
        if p["protection"] and not any(protection_allowed(
                p["protection_mask"], value, True) for value in range(4)):
            raise PluginError("TMR Inject 至少需要一种允许写入的保护属性")

        inputs = [Port("Rst", scalar=True), Port("LMB_ABus", 32),
                  Port("LMB_WriteDBus", 32), Port("LMB_AddrStrobe", scalar=True),
                  Port("LMB_ReadStrobe", scalar=True), Port("LMB_WriteStrobe", scalar=True),
                  Port("LMB_BE", 4)]
        if p["protection"]:
            inputs.insert(2, Port("LMB_Prot", 2))
        inputs.extend((Port("MB_LMB_ABus", 32), Port("MB_LMB_WriteDBus", 32),
                       Port("MB_LMB_AddrStrobe", scalar=True),
                       Port("MB_LMB_ReadStrobe", scalar=True),
                       Port("MB_LMB_WriteStrobe", scalar=True), Port("MB_LMB_BE", 4)))
        if p["protection"]:
            inputs.insert(len(inputs) - 4, Port("MB_LMB_Prot", 2))
        inputs.extend((Port("BRAM_Sl_DBus", 32), Port("BRAM_Sl_Ready", scalar=True),
                       Port("BRAM_Sl_Wait", scalar=True), Port("BRAM_Sl_UE", scalar=True),
                       Port("BRAM_Sl_CE", scalar=True)))

        outputs = [Port("Sl_DBus", 32), Port("Sl_Ready", scalar=True),
                   Port("Sl_Wait", scalar=True), Port("Sl_UE", scalar=True),
                   Port("Sl_CE", scalar=True), Port("MB_Sl_DBus", 32),
                   Port("MB_Sl_Ready", scalar=True), Port("MB_Sl_Wait", scalar=True),
                   Port("MB_Sl_UE", scalar=True), Port("MB_Sl_CE", scalar=True),
                   Port("BRAM_LMB_ABus", 32), Port("BRAM_LMB_WriteDBus", 32),
                   Port("BRAM_LMB_AddrStrobe", scalar=True),
                   Port("BRAM_LMB_ReadStrobe", scalar=True),
                   Port("BRAM_LMB_WriteStrobe", scalar=True), Port("BRAM_LMB_BE", 4)]
        if p["protection"]:
            outputs.insert(12, Port("BRAM_LMB_Prot", 2))

        base = p["base_address"]
        config = {
            "C_BASEADDR": f"0x{base:016X}",
            "C_HIGHADDR": f"0x{base + p['address_size'] - 1:016X}",
            "C_MASK": f"0x{address_mask(p['address_size']):016X}",
            "C_PROT_CFG": f"0x{p['protection_mask']:02X}",
            "C_LMB_AWIDTH": 32, "C_LMB_DWIDTH": 32, "C_LMB_PROTOCOL": 0,
            "C_LMB_HAS_PROT": int(p["protection"]),
            "C_INJECT_LMB_AWIDTH": 32, "C_INJECT_LMB_DWIDTH": 32,
            "C_MAGIC": f"0x{p['magic']:02X}", "C_CPU_ID": p["cpu_id"],
        }
        parameters = dict(p)
        spec = CycleSpec(
            tuple(inputs), tuple(outputs), config, config,
            lambda: TmrInjectModel(parameters), clock="Clk", flush_cycles=3,
            idle_values={"Rst": 0, "LMB_AddrStrobe": 0, "LMB_ReadStrobe": 0,
                         "LMB_WriteStrobe": 0, "MB_LMB_AddrStrobe": 0,
                         "MB_LMB_ReadStrobe": 0, "MB_LMB_WriteStrobe": 0},
        )
        return replace(spec, prefix=lambda: directed_sequence(parameters, spec))
