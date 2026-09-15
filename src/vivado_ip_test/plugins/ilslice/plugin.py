from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.bit_patterns import bit_identity_frames
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.inline_metadata import INLINE_BD_GLOB
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.ilslice.reference import InlineSliceModel


class IlSlicePlugin(CycleIpPlugin):
    ip_type = ip_name = "ilslice"
    version = "1.0"

    def describe(self, p):
        validate_parameters(p, {"input_width": range(2, 4097), "high_bit": range(4096), "low_bit": range(4096)})
        width, high, low = p["input_width"], p["high_bit"], p["low_bit"]
        if not low <= high < width:
            raise PluginError("Inline slice requires 0 <= low_bit <= high_bit < input_width")
        ports = (Port("Din", width),)
        settings = {"DIN_WIDTH": width, "DIN_FROM": high, "DIN_TO": low}

        def prefix():
            yield from bit_identity_frames(ports)
            for bit in sorted({*range(low, high+1), max(0, low-1), min(width-1, high+1), width-1}):
                yield {"Din": 1 << bit}
                yield {"Din": ((1 << width)-1) ^ (1 << bit)}

        return CycleSpec(ports, (Port("Dout", high-low+1),), settings, {},
            lambda: InlineSliceModel(low, high), clock=None, prefix=prefix,
            inline_bd_glob=INLINE_BD_GLOB)
