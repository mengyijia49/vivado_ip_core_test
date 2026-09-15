from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.axi_intc.reference import IntcModel
from vivado_ip_test.plugins.axi_intc.vectors import prepare_operations


class AxiIntcPlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_intc"
    version = "4.1"

    def describe(self, p):
        modes = p.get("input_modes")
        if (not isinstance(modes, (list, tuple)) or not 1 <= len(modes) <= 32
                or any(mode not in ("rising", "falling", "high", "low") for mode in modes)):
            raise PluginError("INTC input_modes must contain 1..32 trigger modes")
        width = len(modes)
        flags = ("has_ipr", "has_sie", "has_cie", "has_ivr", "has_ilr")
        validate_parameters({k: v for k, v in p.items() if k != "input_modes"},
            {"software_interrupts": range(33-width), "async_mask": range(1 << width),
             "synchronizer_stages": range(8), "irq_active_high": bool,
             **dict.fromkeys(flags, bool)})
        if p["async_mask"] == 0 and p["synchronizer_stages"] != 2:
            raise PluginError("Unused INTC synchronizer stages must keep the canonical value 2")
        settings = {"C_NUM_INTR_INPUTS": width, "C_NUM_SW_INTR": p["software_interrupts"],
            "C_KIND_OF_INTR": f"0x{sum(1 << i for i, m in enumerate(modes) if m in ('rising', 'falling')):08X}",
            "C_KIND_OF_EDGE": f"0x{sum(1 << i for i, m in enumerate(modes) if m == 'rising'):08X}",
            "C_KIND_OF_LVL": f"0x{sum(1 << i for i, m in enumerate(modes) if m == 'high'):08X}",
            "C_ASYNC_INTR": f"0x{p['async_mask']:08X}", "C_NUM_SYNC_FF": p["synchronizer_stages"],
            "C_HAS_FAST": 0, "C_EN_CASCADE_MODE": 0, "C_CASCADE_MASTER": 0,
            "C_IRQ_IS_LEVEL": 1, "C_IRQ_CONNECTION": 0,
            **{name.upper().replace("HAS_", "C_HAS_"): int(p[name]) for name in flags}}
        model = {**settings, "C_IRQ_ACTIVE": "0x1" if p["irq_active_high"] else "0x0",
                 "C_S_AXI_ADDR_WIDTH": 9, "C_S_AXI_DATA_WIDTH": 32, "C_MB_CLK_NOT_CONNECTED": 1}
        del model["C_IRQ_CONNECTION"]
        settings["Sense_of_IRQ_Level_Type"] = "Active_High" if p["irq_active_high"] else "Active_Low"
        parameters = {**p, "input_modes": tuple(modes)}
        generated = (Port("pins", width), Port("set_bits", 32), Port("clear_bits", 32),
                     Port("enable_bits", 32), Port("master_enable", 1))
        if p["has_ilr"]:
            total = width+p["software_interrupts"]
            generated += (Port("priority_limit", total.bit_length(), maximum=total),)
        return AxiLiteSpec(9, (Port("intr", width),), (Port("irq", scalar=True),), generated,
            settings, model, lambda: IntcModel(parameters),
            lambda samples: prepare_operations(samples, parameters), settle_cycles=64)
