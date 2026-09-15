from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.axilite.plugin import AxiLiteIpPlugin
from vivado_ip_test.plugins.common.axilite.spec import AxiLiteSpec
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.axi_gpio.reference import GpioModel
from vivado_ip_test.plugins.axi_gpio.vectors import prepare_operations


class AxiGpioPlugin(AxiLiteIpPlugin):
    ip_type = ip_name = "axi_gpio"
    version = "2.0"

    def describe(self, p):
        rules = {"channels": range(1, 3), "interrupt": bool}
        for i in (1, 2):
            rules.update({f"width{i}": range(1, 33), f"mode{i}": ("bidirectional", "input", "output"),
                          f"default_data{i}": range(1 << 32), f"default_tri{i}": range(1 << 32)})
        validate_parameters(p, rules)
        if p["channels"] == 1 and (p["width2"], p["mode2"], p["default_data2"], p["default_tri2"]) != (
                1, "bidirectional", 0, 1):
            raise PluginError("Disabled GPIO channel 2 must keep canonical parameters")
        settings = {"C_IS_DUAL": p["channels"]-1, "C_INTERRUPT_PRESENT": int(p["interrupt"])}
        model = {"C_IS_DUAL": p["channels"]-1, "C_INTERRUPT_PRESENT": int(p["interrupt"]),
                 "C_S_AXI_DATA_WIDTH": 32, "C_S_AXI_ADDR_WIDTH": 9}
        inputs, outputs, generated = [], [], [Port("strobe", 4)]
        for i in range(1, p["channels"]+1):
            width, mode = p[f"width{i}"], p[f"mode{i}"]
            mask = (1 << width)-1
            data, tri = p[f"default_data{i}"], p[f"default_tri{i}"]
            if data > mask or tri > mask:
                raise PluginError("GPIO default values exceed the active channel width")
            if mode == "input" and (data != 0 or tri != 0) or mode == "output" and tri != 0:
                raise PluginError("Fixed GPIO directions must use canonical inactive defaults")
            number, suffix = ("", "") if i == 1 else ("2", "_2")
            controls = {f"C_GPIO{number}_WIDTH": width, f"C_ALL_INPUTS{suffix}": int(mode == "input"),
                        f"C_ALL_OUTPUTS{suffix}": int(mode == "output")}
            if mode != "input":
                controls[f"C_DOUT_DEFAULT{suffix}"] = f"0x{data:08X}"
            if mode == "bidirectional":
                controls[f"C_TRI_DEFAULT{suffix}"] = f"0x{tri:08X}"
            else:
                controls[f"C_TRI_DEFAULT{suffix}"] = "0xFFFFFFFF"
            settings.update(controls)
            model.update(controls)
            generated.append(Port(f"data{i}", 32))
            if mode != "output":
                inputs.append(Port(f"gpio{number}_io_i", width))
                generated.append(Port(f"pins{i}", width))
            if mode != "input":
                outputs.append(Port(f"gpio{number}_io_o", width))
            if mode == "bidirectional":
                outputs.append(Port(f"gpio{number}_io_t", width))
                generated.append(Port(f"tri{i}", width))
        if p["interrupt"]:
            outputs.append(Port("ip2intc_irpt", scalar=True))
            generated.extend((Port("irq_enable", 2), Port("irq_toggle", 2), Port("global_enable", 1)))
        parameters = dict(p)
        return AxiLiteSpec(9, tuple(inputs), tuple(outputs), tuple(generated), settings, model,
            lambda: GpioModel(parameters), lambda samples: prepare_operations(samples, parameters),
            minimum_ip_revision=14, settle_cycles=64)
