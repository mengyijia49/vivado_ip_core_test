from dataclasses import dataclass

from vivado_ip_test.plugins.base import PluginError


@dataclass(frozen=True)
class ClockPlan:
    input_frequency_mhz: int
    output_frequency_mhz: int
    primitive: str
    reset_active_high: bool
    input_half_period_ps: int
    output_period_ps: int
    output_high_ps: int

    @classmethod
    def from_parameters(cls, parameters):
        input_frequency = parameters["input_frequency_mhz"]
        output_frequency = parameters["output_frequency_mhz"]
        input_half = cls._exact_period(2 * input_frequency, "输入半周期")
        output_period = cls._exact_period(output_frequency, "输出周期")
        output_high = cls._exact_period(2 * output_frequency, "输出高电平宽度")
        return cls(input_frequency, output_frequency, parameters["primitive"],
                   parameters["reset_active_high"], input_half, output_period, output_high)

    @staticmethod
    def _exact_period(frequency_mhz, description):
        if 1_000_000 % frequency_mhz:
            raise PluginError(f"{description}不能用整数 ps 精确表示")
        return 1_000_000 // frequency_mhz

    def as_dict(self):
        return {
            "model": "ideal_clock_period:1.0",
            "input_frequency_mhz": self.input_frequency_mhz,
            "output_frequency_mhz": self.output_frequency_mhz,
            "input_half_period_ps": self.input_half_period_ps,
            "output_period_ps": self.output_period_ps,
            "output_high_ps": self.output_high_ps,
            "primitive": self.primitive,
            "reset_active_high": self.reset_active_high,
        }
