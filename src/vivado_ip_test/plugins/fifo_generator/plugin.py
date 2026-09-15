from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.fifo_generator.reference import FifoModel
from vivado_ip_test.plugins.fifo_generator.fwft import FwftFifoModel, fwft_prefix
from vivado_ip_test.plugins.fifo_generator.status import (
    STATUS_DEFAULTS, FifoStatusModel, status_ports, status_prefix, status_settings, validate_status,
)


class FifoGeneratorPlugin(CycleIpPlugin):
    ip_type = ip_name = "fifo_generator"
    version = "13.2"

    def describe(self, p):
        p = {"read_mode": "standard", **STATUS_DEFAULTS, **p}
        memories = {"Block_RAM": 1, "Distributed_RAM": 2}
        validate_parameters(p, {"width": range(1, 1025), "depth": range(16, 131073),
            "memory_type": set(memories), "active_low_flags": bool,
            "dout_reset_value": range(0, 1 << 1024), "read_mode": {"standard", "fwft"},
            **{key: range(0, 131073) for key in STATUS_DEFAULTS}})
        fwft = p["read_mode"] == "fwft"
        if p["depth"] & (p["depth"] - 1):
            raise PluginError("Native FIFO depth must be a power of two")
        limit = (1 << p["width"]) - 1
        if p["dout_reset_value"] > limit:
            raise PluginError("FIFO reset value does not fit the data width")
        validate_status(p)
        extra_settings, extra_metadata = status_settings(p)
        sense = "Active_Low" if p["active_low_flags"] else "Active_High"
        def prefix():
            yield from status_prefix(p)
            if fwft:
                yield from fwft_prefix(p["width"], p["depth"])
                return
            yield from ({"srst": 1}, {}, {"rd_en": 1}, {"wr_en": 1, "din": 0},
                        {"wr_en": 1, "rd_en": 1, "din": limit}, {"rd_en": 1})
            for lap in range(2):
                for i in range(p["depth"]):
                    yield {"wr_en": 1, "din": (i * 0x9E3779B1 + lap) & limit}
                yield from ({"wr_en": 1, "din": limit} for _ in range(2))
                for i in range(p["depth"] * 2):
                    yield {"wr_en": 1, "rd_en": 1, "din": (i + 7) & limit}
                yield from ({"rd_en": 1} for _ in range(p["depth"] + 3))
            yield from ({"wr_en": 1, "din": limit}, {"wr_en": 1, "din": 1},
                        {"srst": 1}, {"rd_en": 1}, {"srst": 1, "rd_en": 1})
            yield from ({"wr_en": 1, "din": i & limit} for i in range(p["depth"]))
            yield {"srst": 1, "wr_en": 1, "rd_en": 1}

        def suffix():
            yield from ({"rd_en": 1} for _ in range(p["depth"] + (7 if fwft else 3)))

        def model_factory():
            model = FwftFifoModel(p) if fwft else FifoModel(p)
            return FifoStatusModel(model, p) if any(p[key] for key in STATUS_DEFAULTS) else model
        flags = ("full", "almost_full", "wr_ack", "overflow", "empty", "almost_empty", "valid", "underflow")
        return CycleSpec(
            inputs=(Port("din", p["width"]), Port("wr_en", scalar=True),
                    Port("rd_en", scalar=True), Port("srst", scalar=True)),
            outputs=(Port("dout", p["width"]), *(Port(name, scalar=True) for name in flags), *status_ports(p)),
            settings={"INTERFACE_TYPE": "Native", "Fifo_Implementation": f"Common_Clock_{p['memory_type']}",
                "Input_Data_Width": p["width"], "Output_Data_Width": p["width"],
                "Input_Depth": p["depth"], "Output_Depth": p["depth"],
                "Performance_Options": "First_Word_Fall_Through" if fwft else "Standard_FIFO",
                "Reset_Pin": True, "Reset_Type": "Synchronous_Reset", "Enable_Reset_Synchronization": True,
                "Full_Flags_Reset_Value": 0, "Use_Dout_Reset": True, "Dout_Reset_Value": format(p["dout_reset_value"], "x"),
                "Valid_Flag": True, "Valid_Sense": sense, "Write_Acknowledge_Flag": True, "Write_Acknowledge_Sense": sense,
                "Overflow_Flag": True, "Overflow_Sense": sense, "Underflow_Flag": True, "Underflow_Sense": sense,
                "Almost_Full_Flag": True, "Almost_Empty_Flag": True, "Data_Count": bool(p["data_count_width"]),
                "Use_Embedded_Registers": False, "Enable_ECC": False, "Enable_Safety_Circuit": False,
                **extra_settings},
            model_parameters={"C_COMMON_CLOCK": 1, "C_MEMORY_TYPE": memories[p["memory_type"]],
                "C_IMPLEMENTATION_TYPE": 0, "C_PRELOAD_LATENCY": 0 if fwft else 1,
                "C_PRELOAD_REGS": int(fwft),
                "C_DIN_WIDTH": p["width"], "C_DOUT_WIDTH": p["width"],
                "C_WR_DEPTH": p["depth"], "C_RD_DEPTH": p["depth"], "C_HAS_SRST": 1,
                "C_HAS_VALID": 1, "C_HAS_WR_ACK": 1, "C_HAS_OVERFLOW": 1, "C_HAS_UNDERFLOW": 1,
                "C_HAS_ALMOST_FULL": 1, "C_HAS_ALMOST_EMPTY": 1, "C_HAS_DATA_COUNT": int(bool(p["data_count_width"])),
                "C_USE_EMBEDDED_REG": 0, "C_USE_PIPELINE_REG": 0, "C_USE_DOUT_RST": 1,
                "C_DOUT_RST_VAL": format(p["dout_reset_value"], "x"),
                **{f"C_{name}_LOW": int(p["active_low_flags"]) for name in ("VALID", "WR_ACK", "OVERFLOW", "UNDERFLOW")},
                **extra_metadata},
            model_parameter_radices={"C_DOUT_RST_VAL": 16},
            model_factory=model_factory, clock="clk", masked_outputs=True,
            idle_values={"wr_en": 0, "rd_en": 0, "srst": 0}, prefix=prefix, suffix=suffix)
