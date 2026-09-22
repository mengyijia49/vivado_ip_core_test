from vivado_ip_test.plugins.axi_register_slice.reference import (
    AxiRegisterSliceModel, MODE_VALUES,
)
from vivado_ip_test.plugins.axi_register_slice.vectors import directed_sequence
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin


DATA_WIDTHS = {32, 64, 128, 256, 512, 1024}
MODES = set(MODE_VALUES)


class AxiRegisterSlicePlugin(CycleIpPlugin):
    ip_type = ip_name = "axi_register_slice"
    version = "2.1"

    def describe(self, p):
        validate_parameters(p, {
            "data_width": range(32, 1025), "id_width": range(1, 33),
            "address_user_width": range(1, 1025), "data_user_width": range(1, 1025),
            "response_user_width": range(1, 1025),
            "forward_mode": MODES, "response_mode": MODES,
        })
        if p["data_width"] not in DATA_WIDTHS:
            raise PluginError("AXI Register Slice 数据位宽不受支持")

        address_fields = (
            ("id", p["id_width"]), ("addr", 32), ("len", 8), ("size", 3),
            ("burst", 2), ("lock", 1), ("cache", 4), ("prot", 3),
            ("region", 4), ("qos", 4), ("user", p["address_user_width"]),
        )
        channel_fields = {
            "aw": address_fields,
            "w": (("data", p["data_width"]), ("strb", p["data_width"] // 8),
                  ("last", 1), ("user", p["data_user_width"])),
            "b": (("id", p["id_width"]), ("resp", 2),
                  ("user", p["response_user_width"])),
            "ar": address_fields,
            "r": (("id", p["id_width"]), ("data", p["data_width"]),
                  ("resp", 2), ("last", 1), ("user", p["data_user_width"])),
        }

        def payload_port(prefix, channel, name, width):
            return Port(f"{prefix}_{channel}{name}", width, scalar=name == "last")

        inputs = [Port("aresetn", scalar=True)]
        outputs = []
        for channel in ("aw", "w", "ar"):
            inputs.extend(payload_port("s_axi", channel, name, width)
                          for name, width in channel_fields[channel])
            inputs.extend((Port(f"s_axi_{channel}valid", scalar=True),
                           Port(f"m_axi_{channel}ready", scalar=True)))
            outputs.extend(payload_port("m_axi", channel, name, width)
                           for name, width in channel_fields[channel])
            outputs.extend((Port(f"m_axi_{channel}valid", scalar=True),
                            Port(f"s_axi_{channel}ready", scalar=True)))
        for channel in ("b", "r"):
            inputs.extend(payload_port("m_axi", channel, name, width)
                          for name, width in channel_fields[channel])
            inputs.extend((Port(f"m_axi_{channel}valid", scalar=True),
                           Port(f"s_axi_{channel}ready", scalar=True)))
            outputs.extend(payload_port("s_axi", channel, name, width)
                           for name, width in channel_fields[channel])
            outputs.extend((Port(f"s_axi_{channel}valid", scalar=True),
                            Port(f"m_axi_{channel}ready", scalar=True)))

        settings = {
            "PROTOCOL": "AXI4", "READ_WRITE_MODE": "READ_WRITE",
            "ADDR_WIDTH": 32, "DATA_WIDTH": p["data_width"], "ID_WIDTH": p["id_width"],
            "AWUSER_WIDTH": p["address_user_width"],
            "ARUSER_WIDTH": p["address_user_width"],
            "WUSER_WIDTH": p["data_user_width"], "RUSER_WIDTH": p["data_user_width"],
            "BUSER_WIDTH": p["response_user_width"], "RESERVE_MODE": 0,
            "REG_AW": MODE_VALUES[p["forward_mode"]],
            "REG_W": MODE_VALUES[p["forward_mode"]],
            "REG_AR": MODE_VALUES[p["forward_mode"]],
            "REG_B": MODE_VALUES[p["response_mode"]],
            "REG_R": MODE_VALUES[p["response_mode"]],
        }
        model_parameters = {
            "C_AXI_PROTOCOL": 0, "C_AXI_ID_WIDTH": p["id_width"],
            "C_AXI_ADDR_WIDTH": 32, "C_AXI_DATA_WIDTH": p["data_width"],
            "C_AXI_SUPPORTS_USER_SIGNALS": 1,
            "C_AXI_AWUSER_WIDTH": p["address_user_width"],
            "C_AXI_ARUSER_WIDTH": p["address_user_width"],
            "C_AXI_WUSER_WIDTH": p["data_user_width"],
            "C_AXI_RUSER_WIDTH": p["data_user_width"],
            "C_AXI_BUSER_WIDTH": p["response_user_width"],
            "C_REG_CONFIG_AW": MODE_VALUES[p["forward_mode"]],
            "C_REG_CONFIG_W": MODE_VALUES[p["forward_mode"]],
            "C_REG_CONFIG_AR": MODE_VALUES[p["forward_mode"]],
            "C_REG_CONFIG_B": MODE_VALUES[p["response_mode"]],
            "C_REG_CONFIG_R": MODE_VALUES[p["response_mode"]],
            "C_RESERVE_MODE": 0, "C_NUM_SLR_CROSSINGS": 0,
        }
        valid_inputs = {"s_axi_awvalid": 0, "s_axi_wvalid": 0, "s_axi_arvalid": 0,
                        "m_axi_bvalid": 0, "m_axi_rvalid": 0}
        ready_inputs = {"m_axi_awready": 1, "m_axi_wready": 1, "m_axi_arready": 1,
                        "s_axi_bready": 1, "s_axi_rready": 1}
        parameters = dict(p)
        return CycleSpec(
            inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=model_parameters,
            model_factory=lambda: AxiRegisterSliceModel(parameters), clock="aclk",
            prefix=lambda: directed_sequence(parameters), flush_cycles=8,
            neutral={"aresetn": 1, **ready_inputs}, idle_values=valid_inputs,
            masked_outputs=True, combine_scalar_controls=False,
        )
