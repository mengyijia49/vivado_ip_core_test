from math import ceil

from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.axi_uartlite.reference import UartLiteModel
from vivado_ip_test.plugins.axi_uartlite.vectors import prepare_operations


BAUD_RATES = (9600, 19200, 38400, 57600, 115200, 128000, 230400)


class AxiUartLitePlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_uartlite"
    version = "2.0"

    def describe(self, p):
        validate_parameters(p, {"baud_rate": range(1, 1_000_001),
                                "data_bits": range(5, 9),
                                "parity": {"None", "Even", "Odd"}})
        if p["baud_rate"] not in BAUD_RATES:
            raise PluginError(f"参数 baud_rate 的值不受支持：{p['baud_rate']!r}")
        use_parity = p["parity"] != "None"
        frame_bits = 1 + p["data_bits"] + int(use_parity) + 1
        settle_cycles = ceil(100_000_000 / p["baud_rate"]) * frame_bits + 256
        settings = {"C_S_AXI_ACLK_FREQ_HZ": 100_000_000,
                    "C_BAUDRATE": p["baud_rate"], "C_DATA_BITS": p["data_bits"],
                    "PARITY": "No_Parity" if not use_parity else p["parity"]}
        model = {"C_S_AXI_ACLK_FREQ_HZ": 100_000_000,
                 "C_S_AXI_ADDR_WIDTH": 4, "C_S_AXI_DATA_WIDTH": 32,
                 "C_BAUDRATE": p["baud_rate"], "C_DATA_BITS": p["data_bits"],
                 "C_USE_PARITY": int(use_parity), "C_ODD_PARITY": int(p["parity"] == "Odd")}
        parameters = dict(p)
        return AxiLiteSpec(4, (Port("rx", scalar=True),),
            (Port("interrupt", scalar=True), Port("tx", scalar=True)),
            (Port("character", p["data_bits"]), Port("strobe", 4)), settings, model,
            lambda: UartLiteModel(parameters),
            lambda samples: prepare_operations(samples, parameters),
            settle_cycles=settle_cycles, reset_cycles=32, minimum_ip_revision=39,
            loopbacks=(("rx", "tx"),))
