from vivado_ip_test.plugins.axi_timebase_wdt.reference import AxiTimebaseWdtModel
from vivado_ip_test.plugins.axi_timebase_wdt.vectors import prepare_operations
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec, ClockWindow
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters


class AxiTimebaseWdtPlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_timebase_wdt"
    version = "3.0"

    def describe(self, p):
        validate_parameters(p, {"interval": range(8, 16), "enable_once": bool})
        settings = {
            "C_WDT_INTERVAL": p["interval"],
            "WDT_ENABLE_ONCE": "Enable_only_once" if p["enable_once"] else "Enable_repeatedly",
            "ENABLE_WINDOW_WDT": 0,
        }
        models = {
            "C_WDT_INTERVAL": p["interval"], "C_WDT_ENABLE_ONCE": int(p["enable_once"]),
            "C_S_AXI_DATA_WIDTH": 32, "C_S_AXI_ADDR_WIDTH": 4,
            "C_ENABLE_WINDOW_WDT": 0, "C_SST_COUNT_WIDTH": 8, "C_MAX_COUNT_WIDTH": 32,
        }
        parameters = dict(p)
        return AxiLiteSpec(
            4, (Port("freeze", scalar=True),),
            tuple(Port(name, scalar=True) for name in
                  ("timebase_interrupt", "wdt_interrupt", "wdt_reset")),
            (Port("sample_cycles", 8),), settings, models,
            lambda: AxiTimebaseWdtModel(parameters),
            lambda samples: prepare_operations(samples, parameters),
            settle_cycles=12, reset_cycles=20, minimum_ip_revision=27,
            window=ClockWindow("freeze", active=0, width=16),
        )
