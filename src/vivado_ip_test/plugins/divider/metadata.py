import json
from dataclasses import asdict, dataclass
from pathlib import Path

from vivado_ip_test.plugins.base import PluginError


@dataclass(frozen=True)
class DividerMetadata:
    module_name: str
    component_reference: str
    ip_revision: str
    vivado_version: str
    dividend_width: int
    divisor_width: int
    dout_width: int
    latency: int
    operand_sign: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def _value(mapping: dict, key: str) -> str:
    try:
        return mapping[key][0]["value"]
    except (KeyError, IndexError, TypeError) as exc:
        raise PluginError(f"XCI 缺少字段：{key}") from exc


def load_divider_metadata(run_dir: Path) -> tuple[Path, DividerMetadata]:
    xci_paths = list(run_dir.rglob("div_gen_0.xci"))
    if len(xci_paths) != 1:
        raise PluginError(
            f"{run_dir} 中应存在一份 div_gen_0.xci，实际为 {len(xci_paths)} 份"
        )

    xci_path = xci_paths[0]
    try:
        data = json.loads(xci_path.read_text())
        ip_inst = data["ip_inst"]
        parameters = ip_inst["parameters"]
        component = parameters["component_parameters"]
        model = parameters["model_parameters"]
        runtime = parameters["runtime_parameters"]
        metadata = DividerMetadata(
            module_name=ip_inst["xci_name"],
            component_reference=ip_inst["component_reference"],
            ip_revision=str(ip_inst["ip_revision"]),
            vivado_version=_value(runtime, "SWVERSION"),
            dividend_width=int(_value(model, "C_S_AXIS_DIVIDEND_TDATA_WIDTH")),
            divisor_width=int(_value(model, "C_S_AXIS_DIVISOR_TDATA_WIDTH")),
            dout_width=int(_value(model, "C_M_AXIS_DOUT_TDATA_WIDTH")),
            latency=int(_value(model, "C_LATENCY")),
            operand_sign=_value(component, "operand_sign"),
        )
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PluginError(f"无法解析 XCI：{xci_path}") from exc

    return xci_path, metadata
