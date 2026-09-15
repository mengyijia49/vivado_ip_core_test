from vivado_ip_test.plugins.axis_data_fifo.reference import expected_transactions
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import (
    PAYLOAD_RULES, StreamSpec, payload_ports, payload_settings,
)


class AxisDataFifoPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_data_fifo"
    version = "2.0"
    expected_transactions = staticmethod(expected_transactions)

    def describe(self, p):
        validate_parameters(p, {**PAYLOAD_RULES, "depth": range(16, 4097),
            "packet_mode": bool, "independent_clocks": bool,
            "memory_type": {"auto", "block", "distributed"}, "synchronization_stages": range(2, 9)})
        if p["depth"] & (p["depth"] - 1):
            raise PluginError("Stream FIFO depth must be a power of two")
        if p["packet_mode"] and not p["has_last"]:
            raise PluginError("Stream packet FIFO requires TLAST")
        if not p["independent_clocks"] and p["synchronization_stages"] != 3:
            raise PluginError("Common-clock FIFO fixes the unused synchronization_stages field at 3")
        mode = 2 if p["packet_mode"] else 1
        asynchronous = int(p["independent_clocks"])
        return StreamSpec(payload_ports(p),
            {**payload_settings(p), "HAS_TREADY": 1, "FIFO_DEPTH": p["depth"], "FIFO_MODE": mode,
             "IS_ACLK_ASYNC": asynchronous, "FIFO_MEMORY_TYPE": p["memory_type"],
             "SYNCHRONIZATION_STAGES": p["synchronization_stages"], "ACLKEN_CONV_MODE": 0,
             "HAS_WR_DATA_COUNT": 0, "HAS_RD_DATA_COUNT": 0, "HAS_AEMPTY": 0,
             "HAS_PROG_EMPTY": 0, "HAS_AFULL": 0, "HAS_PROG_FULL": 0, "ENABLE_ECC": 0},
            {"C_AXIS_TDATA_WIDTH": p["data_bytes"] * 8, "C_FIFO_DEPTH": p["depth"],
             "C_FIFO_MODE": mode, "C_IS_ACLK_ASYNC": asynchronous,
             "C_SYNCHRONIZER_STAGE": p["synchronization_stages"]},
            input_clock="s_axis_aclk", input_reset="s_axis_aresetn",
            output_clock="m_axis_aclk" if asynchronous else None,
            output_period_ns=14 if asynchronous else 10, capacity=p["depth"])
