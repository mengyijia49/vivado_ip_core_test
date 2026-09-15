from vivado_ip_test.plugins.common.cycle import (
    CycleSpec, Port, control_ports, control_settings, validate_parameters,
)
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.counter.reference import CounterModel


class CounterPlugin(CycleIpPlugin):
    ip_type = "counter"
    ip_name = "c_counter_binary"
    version = "12.0"

    def describe(self, p):
        validate_parameters(p, {
            "width": range(1, 257), "increment": range(1, 1 << 256),
            "direction": {"UP", "DOWN", "UPDOWN"}, "clock_enable": bool,
            "sync_clear": bool, "ce_overrides_reset": bool,
        })
        validate_parameters({"increment": p["increment"]}, {"increment": range(1, 1 << p["width"])})
        controls = control_ports(p, dynamic="UP" if p["direction"] == "UPDOWN" else None)
        neutral = {port.name: int(port.name in {"CE", "UP"}) for port in controls}
        maximum = (1 << p["width"]) - 1
        prefix = []
        for load in (0, maximum, maximum // 2, p["increment"]):
            prefix += [{"LOAD": 1, "L": load}] + [{"LOAD": 0}] * 5
        return CycleSpec(
            inputs=(Port("L", p["width"]), Port("LOAD", scalar=True), *controls),
            outputs=(Port("Q", p["width"]),),
            settings={"Output_Width": p["width"], "Increment_Value": p["increment"],
                      "Count_Mode": p["direction"], "Implementation": "Fabric",
                      "Latency": 1, "Latency_Configuration": "Manual", "Fb_Latency": 0,
                      "Fb_Latency_Configuration": "Manual", "Load": True, "Load_Sense": "Active_High",
                      "Restrict_Count": False, "Sync_Threshold_Output": False, **control_settings(p)},
            model_parameters={"C_LATENCY": 1, "C_FB_LATENCY": 0, "C_IMPLEMENTATION": 0,
                              "C_COUNT_BY": format(p["increment"], "b"), "C_RESTRICT_COUNT": 0,
                              "C_COUNT_MODE": ("UP", "DOWN", "UPDOWN").index(p["direction"]),
                              "C_CE_OVERRIDES_SYNC": int(p["ce_overrides_reset"])},
            model_factory=lambda: CounterModel(p), prefix=tuple(prefix), neutral=neutral,
            model_parameter_radices={"C_COUNT_BY": 2},
        )
