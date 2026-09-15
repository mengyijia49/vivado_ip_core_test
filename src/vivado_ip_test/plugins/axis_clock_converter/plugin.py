from vivado_ip_test.plugins.axis_clock_converter.reference import expected_transactions
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import (
    PAYLOAD_RULES, StreamSpec, payload_ports, payload_settings,
)


class AxisClockConverterPlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_clock_converter"
    version = "1.1"
    expected_transactions = staticmethod(expected_transactions)

    def describe(self, p):
        validate_parameters(p, {**PAYLOAD_RULES, "synchronization_stages": range(2, 9)})
        return StreamSpec(payload_ports(p),
            {**payload_settings(p), "IS_ACLK_ASYNC": 1, "ACLKEN_CONV_MODE": 0,
             "SYNCHRONIZATION_STAGES": p["synchronization_stages"]},
            {"C_AXIS_TDATA_WIDTH": p["data_bytes"] * 8, "C_IS_ACLK_ASYNC": 1,
             "C_SYNCHRONIZER_STAGE": p["synchronization_stages"]},
            input_clock="s_axis_aclk", input_reset="s_axis_aresetn",
            output_clock="m_axis_aclk", output_reset="m_axis_aresetn", output_period_ns=14,
            capacity=32)
