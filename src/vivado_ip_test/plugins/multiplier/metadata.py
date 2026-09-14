import json
from dataclasses import asdict, dataclass
from pathlib import Path

from vivado_ip_test.plugins.base import PluginError


@dataclass(frozen=True)
class MultiplierMetadata:
    module_name: str
    component_reference: str
    ip_revision: str
    vivado_version: str
    a_width: int
    b_width: int
    a_type: str
    b_type: str
    output_high: int
    output_low: int
    latency: int

    @property
    def output_width(self) -> int:
        return self.output_high - self.output_low + 1

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["output_width"] = self.output_width
        return result


def _value(mapping: dict, key: str) -> str:
    try:
        return mapping[key][0]["value"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PluginError(f"XCI 缺少字段：{key}") from exc


def load_multiplier_metadata(run_dir: Path) -> tuple[Path, MultiplierMetadata]:
    xci_paths = list(run_dir.rglob("mult_gen_0.xci"))
    if len(xci_paths) != 1:
        raise PluginError(
            f"{run_dir} 中应存在一份 mult_gen_0.xci，实际为 {len(xci_paths)} 份"
        )

    xci_path = xci_paths[0]
    try:
        data = json.loads(xci_path.read_text())
        ip_inst = data["ip_inst"]
        parameters = ip_inst["parameters"]
        component = parameters["component_parameters"]
        model = parameters["model_parameters"]
        runtime = parameters["runtime_parameters"]
        metadata = MultiplierMetadata(
            module_name=ip_inst["xci_name"],
            component_reference=ip_inst["component_reference"],
            ip_revision=str(ip_inst["ip_revision"]),
            vivado_version=_value(runtime, "SWVERSION"),
            a_width=int(_value(model, "C_A_WIDTH")),
            b_width=int(_value(model, "C_B_WIDTH")),
            a_type=_value(component, "PortAType"),
            b_type=_value(component, "PortBType"),
            output_high=int(_value(model, "C_OUT_HIGH")),
            output_low=int(_value(model, "C_OUT_LOW")),
            latency=int(_value(model, "C_LATENCY")),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PluginError(f"无法解析 XCI：{xci_path}") from exc

    return xci_path, metadata
