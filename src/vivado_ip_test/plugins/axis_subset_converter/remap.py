from dataclasses import dataclass
import re

from vivado_ip_test.plugins.base import PluginError


FIELDS = ("tdata", "tstrb", "tkeep", "tlast", "tid", "tdest", "tuser")
MAPPINGS = ("resize", "reverse_bytes", "reverse_bits", "rotate_bytes", "repeat_low_byte",
            "user_to_data", "data_user_swap")


@dataclass(frozen=True)
class Part:
    width: int
    source: str | None = None
    low: int = 0
    value: int = 0

    def text(self):
        if self.source is None:
            return f"{self.width}'b{self.value:0{self.width}b}"
        if self.width == 1:
            return f"{self.source}[{self.low}]"
        return f"{self.source}[{self.low + self.width - 1}:{self.low}]"


def parse_remap(expression, widths, output_width):
    if not isinstance(expression, str) or not 1 <= len(expression) <= 100000:
        raise PluginError("映射表达式必须是非空字符串，长度不能超过 100000")
    parts = []
    for element in expression.split(","):
        element = element.strip().lower()
        constant = re.fullmatch(r"([1-9][0-9]*)'b([01]+)", element)
        field = re.fullmatch(r"(tdata|tstrb|tkeep|tlast|tid|tdest|tuser)\[([0-9]+)(?::([0-9]+))?\]", element)
        if constant:
            width = int(constant[1])
            if width != len(constant[2]):
                raise PluginError("二进制常量的位数与声明宽度不一致")
            parts.append(Part(width, value=int(constant[2], 2)))
        elif field:
            name, high, low = field[1], int(field[2]), int(field[3] or field[2])
            if name not in widths or not 0 <= low <= high < widths[name]:
                raise PluginError("映射引用了不存在的输入或越界切片")
            parts.append(Part(high - low + 1, name, low))
        else:
            raise PluginError(f"不支持的映射元素：{element!r}")
    if sum(part.width for part in parts) != output_width:
        raise PluginError("映射总宽度与输出端口不一致")
    return tuple(parts)


def evaluate(parts, frame):
    result = 0
    for part in parts:
        value = part.value if part.source is None else frame[part.source] >> part.low
        result = (result << part.width) | (value & ((1 << part.width) - 1))
    return result


def resize_expression(name, source_width, output_width, fill=0):
    copied = min(source_width, output_width)
    parts = []
    if output_width > copied:
        width = output_width - copied
        parts.append(Part(width, value=((1 << width) - 1) if fill else 0).text())
    if copied:
        parts.append(Part(copied, name).text())
    return ",".join(parts)


def build_remaps(parameters, source, sink):
    source_widths = {p.name: p.width for p in source}
    sink_widths = {p.name: p.width for p in sink}
    result = {}
    for name in FIELDS:
        if name not in sink_widths:
            result[name] = "1'b0"
            continue
        origin = "tkeep" if name == "tstrb" and name not in source_widths and "tkeep" in source_widths else name
        result[name] = resize_expression(origin, source_widths.get(origin, 0), sink_widths[name],
                                         fill=int(name in {"tkeep", "tstrb"}))
    mode = parameters["mapping"]
    if "tdata" in sink_widths and mode != "resize":
        if mode in {"user_to_data", "data_user_swap"}:
            result["tdata"] = resize_expression("tuser", source_widths["tuser"], sink_widths["tdata"])
        else:
            source_bytes = parameters["input_bytes"]
            elements = []
            if mode == "reverse_bits":
                for bit in reversed(range(sink_widths["tdata"])):
                    elements.append(Part(1, "tdata", source_bytes * 8 - 1 - bit).text()
                                    if bit < source_bytes * 8 else "1'b0")
            else:
                for lane in reversed(range(parameters["output_bytes"])):
                    if mode != "repeat_low_byte" and lane >= source_bytes:
                        elements.append("8'b00000000")
                    else:
                        origin = (source_bytes - lane - 1 if mode == "reverse_bytes" else
                                  (lane - 1) % source_bytes if mode == "rotate_bytes" else 0)
                        elements.append(Part(8, "tdata", origin * 8).text())
            result["tdata"] = ",".join(elements)
    if mode == "data_user_swap":
        result["tuser"] = resize_expression("tdata", source_widths["tdata"], sink_widths["tuser"])
    result.update(parameters.get("remap", {}))
    if parameters["last_period"]:
        result["tlast"] = "tlast[0]"
    for name, width in sink_widths.items():
        widths = {**source_widths, "tlast": 1} if name == "tlast" and parameters["last_period"] else source_widths
        parts = parse_remap(result[name], widths, width)
        if name == "tdata" and name not in source_widths and (len(parts) != 1 or parts[0].source is not None):
            raise PluginError("没有输入 TDATA 时，输出 TDATA 映射只能是单个二进制常量")
        result[name] = ",".join(part.text() for part in parts)
    return result
