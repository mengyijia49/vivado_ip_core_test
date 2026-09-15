from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.bit_patterns import bit_identity_frames
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.inline_metadata import INLINE_BD_GLOB
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.ilconcat.reference import InlineConcatModel


class IlConcatPlugin(CycleIpPlugin):
    ip_type = ip_name = "ilconcat"
    version = "1.0"

    def describe(self, p):
        if set(p) != {"input_widths"} or not isinstance(p["input_widths"], list) or not 1 <= len(p["input_widths"]) <= 128:
            raise PluginError("Inline concat requires 1 to 128 input widths")
        if any(type(w) is not int or not 1 <= w <= 4096 for w in p["input_widths"]):
            raise PluginError("Inline concat widths must be integers from 1 to 4096")
        widths = tuple(p["input_widths"])
        ports = tuple(Port(f"In{i}", w) for i, w in enumerate(widths))
        settings = {"NUM_PORTS": len(widths), **{f"IN{i}_WIDTH": w for i, w in enumerate(widths)}}
        return CycleSpec(ports, (Port("dout", sum(widths)),), settings, {},
            lambda: InlineConcatModel(widths), clock=None, prefix=lambda: bit_identity_frames(ports),
            inline_bd_glob=INLINE_BD_GLOB)
