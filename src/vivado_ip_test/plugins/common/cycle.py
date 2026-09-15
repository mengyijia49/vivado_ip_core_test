from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from vivado_ip_test.plugins.base import PluginError


Frame = dict[str, int]
SequenceSource = tuple[Frame, ...] | Callable[[], Iterable[Frame]]


@dataclass(frozen=True)
class DefinedBits:
    value: int
    mask: int
    reason: str


@dataclass(frozen=True)
class Port:
    name: str
    width: int = 1
    scalar: bool = False
    maximum: int | None = None

    @property
    def limit(self) -> int:
        return (1 << self.width) - 1 if self.maximum is None else self.maximum


class CycleModel(Protocol):
    def step(self, inputs: Frame) -> dict[str, int | DefinedBits]: ...


@dataclass(frozen=True)
class CycleSpec:
    inputs: tuple[Port, ...]
    outputs: tuple[Port, ...]
    settings: Mapping[str, object]
    model_parameters: Mapping[str, object]
    model_factory: Callable[[], CycleModel]
    clock: str | None = "CLK"
    prefix: SequenceSource = ()
    flush_cycles: int = 1
    neutral: Frame = field(default_factory=dict)
    idle_values: Frame = field(default_factory=dict)
    masked_outputs: bool = False
    clock_aliases: tuple[str, ...] = ()
    model_parameter_radices: Mapping[str, int] = field(default_factory=dict)
    suffix: SequenceSource = ()
    supporting_artifacts: Mapping[str, Path] = field(default_factory=dict)
    xci_glob: str = "proj/*.srcs/sources_1/ip/dut_0/dut_0.xci"
    inline_bd_glob: str | None = None

    def frame(self, values: Mapping[str, int] | None = None) -> Frame:
        frame = {port.name: self.neutral.get(port.name, 0) for port in self.inputs}
        if values:
            frame.update(values)
        return frame

    def idle(self, previous: Frame) -> Frame:
        frame = dict(previous)
        if "CE" in frame:
            frame["CE"] = 0
        if "SCLR" in frame:
            frame["SCLR"] = 0
        if "we" in frame:
            frame["we"] = 0
        frame.update(self.idle_values)
        return frame


def validate_parameters(parameters, rules):
    if set(parameters) != set(rules):
        raise PluginError(f"参数不匹配，缺少 {sorted(set(rules) - set(parameters))}，"
                          f"未知 {sorted(set(parameters) - set(rules))}")
    for name, rule in rules.items():
        value = parameters[name]
        if rule is bool:
            valid = type(value) is bool
        elif isinstance(rule, range):
            valid = type(value) is int and value in rule
        else:
            valid = isinstance(value, str) and value in rule
        if not valid:
            raise PluginError(f"参数 {name} 的值不受支持：{value!r}")


def decode(value: int, width: int, signed: bool) -> int:
    return value - (1 << width) if signed and value & (1 << (width - 1)) else value


def reset_active(inputs: Frame, ce_overrides_reset: bool) -> bool:
    return bool(inputs.get("SCLR", 0) and
                (not ce_overrides_reset or inputs.get("CE", 1)))


def control_ports(parameters, *, dynamic: str | None = None) -> tuple[Port, ...]:
    names = ([dynamic] if dynamic else [])
    names += [name for name, key in (("CE", "clock_enable"), ("SCLR", "sync_clear"))
              if parameters[key]]
    return tuple(Port(name, scalar=True) for name in names)


def control_settings(parameters) -> dict[str, object]:
    return {"CE": parameters["clock_enable"], "SCLR": parameters["sync_clear"],
            "Sync_CE_Priority": "CE_Overrides_Sync" if parameters["ce_overrides_reset"]
            else "Sync_Overrides_CE", "AINIT_Value": "0", "SINIT_Value": "0",
            "SINIT": False, "SSET": False}
