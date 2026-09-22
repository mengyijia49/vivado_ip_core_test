from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.util_ff.reference import FF_TYPES, UtilFfModel, parse_init


class UtilFfPlugin(CycleIpPlugin):
    ip_type = ip_name = "util_ff"
    version = "1.0"

    def describe(self, p):
        rules = {
            "width": range(1, 1025), "ff_type": tuple(FF_TYPES),
            "control_active_high": bool, "data_inverted": bool, "gate_active_high": bool,
        }
        if set(p) != set(rules) | {"init_value"}:
            raise PluginError("util_ff 参数字段不完整或包含未知字段")
        validate_parameters({key: p[key] for key in rules}, rules)
        parse_init(p["init_value"], p["width"])
        is_ff = p["ff_type"].startswith("FD")
        if not is_ff and p["data_inverted"]:
            raise PluginError("util_ff 锁存器没有数据反相参数")
        if is_ff and not p["gate_active_high"]:
            raise PluginError("util_ff 触发器没有门控极性参数")
        number, control, _ = FF_TYPES[p["ff_type"]]
        control_inverted = int(not p["control_active_high"])
        settings = {
            "C_WIDTH": p["width"], "C_FF_TYPE": number,
            "C_INIT": p["init_value"], "C_C_INVERTED": 0,
            "C_R_INVERTED": control_inverted if control == "reset" else 0,
            "C_CLR_INVERTED": control_inverted if control == "clear" else 0,
            "C_S_INVERTED": control_inverted if control == "set" else 0,
            "C_PRE_INVERTED": control_inverted if control == "preset" else 0,
            "C_D_INVERTED": int(p["data_inverted"]),
            "C_G_INVERTED": int(not p["gate_active_high"]) if not is_ff else 0,
            "C_FF_LEVELS": 1,
        }
        enable = "clk_enable" if is_ff else "gate_enable"
        inputs = (Port("D", p["width"]), Port(control, scalar=True),
                  Port(enable, scalar=True))
        if not is_ff:
            inputs += (Port("G", scalar=True),)
        inactive = int(not p["control_active_high"])
        active = int(p["control_active_high"])
        prefix = (
            {control: inactive, enable: 0, "D": (1 << p["width"]) - 1},
            {control: inactive, enable: 1, "D": 1},
            {control: inactive, enable: 0, "D": (1 << p["width"]) - 1},
            {control: active, enable: 0, "D": 1},
            {control: inactive, enable: 1, "D": (1 << p["width"]) - 1},
        )
        if not is_ff:
            prefix = tuple({**frame, "G": int(p["gate_active_high"])} for frame in prefix)
        return CycleSpec(
            inputs=inputs, outputs=(Port("Q", p["width"]),), settings=settings,
            model_parameters=settings, model_parameter_radices={"C_INIT": 16},
            model_factory=lambda: UtilFfModel(p), clock="clk" if is_ff else None,
            prefix=prefix, neutral={control: inactive},
            initial_values={control: inactive}, flush_cycles=1,
        )
