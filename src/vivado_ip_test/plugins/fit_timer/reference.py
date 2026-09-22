from dataclasses import dataclass

from vivado_ip_test.plugins.base import PluginError


@dataclass(frozen=True)
class FitTimerPlan:
    no_clocks: int
    inaccuracy: int
    reset_active_high: bool
    minimum_period: int
    maximum_period: int

    @classmethod
    def from_parameters(cls, parameters):
        no_clocks = parameters["no_clocks"]
        inaccuracy = parameters["inaccuracy"]
        if type(no_clocks) is not int or not 3 <= no_clocks <= 1_000_000:
            raise PluginError("FIT Timer 周期必须在 3 至 1000000 个时钟之间")
        if type(inaccuracy) is not int or not 0 <= inaccuracy <= 999:
            raise PluginError("FIT Timer 允许误差必须在千分之 0 至 999 之间")
        if type(parameters["reset_active_high"]) is not bool:
            raise PluginError("FIT Timer 复位极性必须是布尔值")
        difference = no_clocks * inaccuracy // 1000
        return cls(no_clocks, inaccuracy, parameters["reset_active_high"],
                   no_clocks - difference, no_clocks + difference)

    def as_dict(self):
        return {
            "model": "fit_timer_period_contract:1.0",
            "requested_period_cycles": self.no_clocks,
            "allowed_inaccuracy_per_thousand": self.inaccuracy,
            "minimum_period_cycles": self.minimum_period,
            "maximum_period_cycles": self.maximum_period,
            "reset_active_high": self.reset_active_high,
            "measured_periods_before_reset": 4,
            "measured_periods_after_reset": 2,
        }
