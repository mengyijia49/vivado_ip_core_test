import json

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.inline_metadata import load_inline_metadata


BLOCK_DESIGN_XCI_GLOB = "proj/*.srcs/sources_1/bd/dut_0/ip/dut_0_core_0/dut_0_core_0.xci"


def setting_text(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def parameter_text(value):
    # Vivado JSON XCI splits long scalar strings into ordered text chunks.
    if isinstance(value, list):
        if not value or any(not isinstance(chunk, str) for chunk in value):
            raise ValueError("XCI 字符串片段必须是非空字符串数组")
        return "".join(value)
    return str(value)


def load_metadata(run_dir, spec: CycleSpec, ip_name: str, version: str):
    if getattr(spec, "inline_bd_glob", None):
        return load_inline_metadata(run_dir, spec, ip_name, version)
    candidates = list(run_dir.glob(getattr(spec, "xci_glob", "proj/*.srcs/sources_1/ip/dut_0/dut_0.xci")))
    if len(candidates) != 1:
        raise PluginError("需要且只能有一个与配置路径匹配的 XCI")
    path = candidates[0]
    try:
        instance = json.loads(path.read_text())["ip_inst"]
        reference = instance["component_reference"]
        if reference != f"xilinx.com:ip:{ip_name}:{version}":
            raise PluginError(f"XCI IP 标识不匹配：{reference}")
        parameters = instance["parameters"]
        for category, requested in (("component_parameters", spec.settings),
                                    ("model_parameters", spec.model_parameters)):
            for key, value in requested.items():
                actual = parameter_text(parameters[category][key][0]["value"])
                expected = setting_text(value)
                radix = (getattr(spec, "model_parameter_radices", {}).get(key)
                         if category == "model_parameters" else None)
                matches = int(actual, radix) == int(expected, radix) if radix else actual.lower() == expected.lower()
                if not matches:
                    raise PluginError(f"XCI {key}={actual}，期望 {setting_text(value)}")
        wanted = {port.name: (port, "in") for port in spec.inputs}
        wanted.update({port.name: (port, "out") for port in spec.outputs})
        if spec.clock:
            wanted[spec.clock] = (Port(spec.clock, scalar=True), "in")
        for clock in getattr(spec, "clock_aliases", ()):
            wanted[clock] = (Port(clock, scalar=True), "in")
        ports = instance["boundary"]["ports"]
        if set(ports) != set(wanted):
            raise PluginError(f"XCI 端口集合不匹配：{sorted(ports)}，期望 {sorted(wanted)}")
        for name, (port, direction) in wanted.items():
            actual = ports[name][0]
            width = abs(int(actual.get("size_left", 0)) - int(actual.get("size_right", 0))) + 1
            if (actual["direction"] != direction or width != port.width
                    or ("size_left" not in actual) != port.scalar):
                raise PluginError(f"XCI 端口 {name} 的方向、位宽或类型不匹配")
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        raise PluginError(f"无法读取 XCI 元数据：{path}：{exc}") from exc
    return path, {"component_reference": reference, "ports": ports,
                  "model_parameters": {key: entry[0]["value"] for key, entry
                                       in parameters["model_parameters"].items()}}
