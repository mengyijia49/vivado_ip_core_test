from vivado_ip_test.plugins.axis_register_slice.reference import expected_transactions
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import (
    PAYLOAD_RULES, StreamSpec, payload_ports, payload_settings,
)


class AxisRegisterSlicePlugin(StreamIpPlugin):
    ip_type = ip_name = "axis_register_slice"
    version = "1.1"
    expected_transactions = staticmethod(expected_transactions)

    def describe(self, p):
        modes = {"Default": 1, "Bypass": 0, "Fully_Registered": 8, "Light_Weight": 7}
        validate_parameters(p, {**PAYLOAD_RULES, "register_mode": set(modes)})
        mode = modes[p["register_mode"]]
        return StreamSpec(payload_ports(p),
            {**payload_settings(p), "HAS_TREADY": 1, "HAS_ACLKEN": 0, "REG_CONFIG": mode},
            {"C_AXIS_TDATA_WIDTH": p["data_bytes"] * 8, "C_REG_CONFIG": mode})
