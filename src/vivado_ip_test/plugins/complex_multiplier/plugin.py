from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.complex_multiplier.reference import ComplexMultiplierModel, byte_width
from vivado_ip_test.plugins.complex_multiplier.vectors import directed_sequence


LAST_MODES = {"Null", "Pass_A_TLAST", "Pass_B_TLAST", "Pass_CTRL_TLAST",
              "OR_all_TLASTs", "AND_all_TLASTs"}


class ComplexMultiplierPlugin(CycleIpPlugin):
    ip_type = "complex_multiplier"
    ip_name = "cmpy"
    version = "6.0"

    def describe(self, p, latency=None):
        rules = {"a_width": range(8, 64), "b_width": range(8, 64), "output_width": range(2, 128),
                 "multiplier_type": {"Use_LUTs", "Use_Mults"}, "optimization": {"Resources", "Performance"},
                 "rounding": {"Truncate", "Random_Rounding"}, "latency": range(-1, 56),
                 "clock_enable": bool, "last_mode": LAST_MODES}
        rules.update({f"{ch}_last": bool for ch in ("a", "b", "ctrl")})
        rules.update({f"{ch}_user_width": range(257) for ch in ("a", "b", "ctrl")})
        validate_parameters(p, rules)
        if p["output_width"] > p["a_width"] + p["b_width"] + 1:
            raise PluginError("Complex multiplier output exceeds full precision")
        rounding = p["rounding"] == "Random_Rounding"
        if rounding and p["output_width"] == p["a_width"] + p["b_width"] + 1:
            raise PluginError("Full precision has no rounding control channel")
        if not rounding and (p["ctrl_last"] or p["ctrl_user_width"]):
            raise PluginError("CTRL sidebands require rounding")
        if p["multiplier_type"] == "Use_LUTs" and p["optimization"] != "Resources":
            raise PluginError("LUT implementation uses the canonical Resources setting")
        if p["latency"] == 0 and p["clock_enable"]:
            raise PluginError("Combinational mode has no clock enable")
        channels = ("a", "b", "ctrl") if rounding else ("a", "b")
        enabled_lasts = {ch for ch in channels if p[f"{ch}_last"]}
        mode = p["last_mode"]
        selected = {"Pass_A_TLAST": "a", "Pass_B_TLAST": "b", "Pass_CTRL_TLAST": "ctrl"}
        if ((mode == "Null") != (not enabled_lasts) or
                mode in selected and selected[mode] not in enabled_lasts):
            raise PluginError("TLAST behavior does not match enabled input channels")
        settings = {"DataType": "Integer", "HasAccumulator": False, "APortWidth": p["a_width"],
            "BPortWidth": p["b_width"], "OutputWidth": p["output_width"],
            "MultType": p["multiplier_type"], "OptimizeGoal": p["optimization"],
            "FlowControl": "NonBlocking", "RoundMode": p["rounding"], "OutTLASTBehv": mode,
            "LatencyConfig": "Automatic" if p["latency"] == -1 else "Manual",
            "ACLKEN": p["clock_enable"], "ARESETN": False}
        if p["latency"] != -1:
            settings["MinimumLatency"] = p["latency"]
        models = {"C_DATA_TYPE": 0, "C_HAS_ACCUMULATOR": 0, "C_A_WIDTH": p["a_width"],
            "C_B_WIDTH": p["b_width"], "C_OUT_WIDTH": p["output_width"],
            "C_MULT_TYPE": int(p["multiplier_type"] == "Use_Mults"),
            "C_OPTIMIZE_GOAL": int(p["optimization"] == "Performance"),
            "ROUND": int(rounding), "C_THROTTLE_SCHEME": 3,
            "C_HAS_ACLKEN": int(p["clock_enable"]), "C_HAS_ARESETN": 0}
        inputs = []
        for ch in ("a", "b", "ctrl"):
            width = p[f"{ch}_user_width"]
            settings.update({f"Has{ch.upper()}TLAST": p[f"{ch}_last"],
                             f"Has{ch.upper()}TUSER": bool(width), f"{ch.upper()}TUSERWidth": width or 1})
            models.update({f"C_HAS_S_AXIS_{ch.upper()}_TLAST": int(p[f"{ch}_last"]),
                           f"C_HAS_S_AXIS_{ch.upper()}_TUSER": int(bool(width)),
                           f"C_S_AXIS_{ch.upper()}_TUSER_WIDTH": width or 1})
            if ch not in channels:
                continue
            data_width = 8 if ch == "ctrl" else 2 * byte_width(p[f"{ch}_width"])
            inputs.extend((Port(f"s_axis_{ch}_tdata", data_width), Port(f"s_axis_{ch}_tvalid", scalar=True)))
            models[f"C_S_AXIS_{ch.upper()}_TDATA_WIDTH"] = data_width
            if width:
                inputs.append(Port(f"s_axis_{ch}_tuser", width))
            if p[f"{ch}_last"]:
                inputs.append(Port(f"s_axis_{ch}_tlast", scalar=True))
        outputs = [Port("m_axis_dout_tvalid", scalar=True), Port("m_axis_dout_tdata", 2 * byte_width(p["output_width"]))]
        models["C_M_AXIS_DOUT_TDATA_WIDTH"] = outputs[1].width
        user_width = sum(p[f"{ch}_user_width"] for ch in channels)
        models["C_M_AXIS_DOUT_TUSER_WIDTH"] = user_width or 1
        if user_width:
            outputs.append(Port("m_axis_dout_tuser", user_width))
        if enabled_lasts:
            outputs.append(Port("m_axis_dout_tlast", scalar=True))
        if p["clock_enable"]:
            inputs.append(Port("aclken", scalar=True))
        actual_latency = p["latency"] if latency is None else latency
        if actual_latency >= 0:
            models["C_LATENCY"] = actual_latency

        def factory():
            if actual_latency < 0:
                raise PluginError("Automatic latency must be read from the generated XCI")
            return ComplexMultiplierModel(p, actual_latency, tuple(outputs))

        drain = max(1, actual_latency)
        return CycleSpec(tuple(inputs), tuple(outputs), settings, models, factory,
            clock="aclk" if p["latency"] != 0 else None,
            neutral={"aclken": 1} if p["clock_enable"] else {},
            idle_values={f"s_axis_{ch}_tvalid": 0 for ch in channels},
            prefix=lambda: directed_sequence(p, drain), flush_cycles=drain + 2, masked_outputs=True)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        _, metadata = load_metadata(self._layout.case_run_dir(case), spec, self.ip_name, self.version)
        try:
            latency = int(metadata["model_parameters"]["C_LATENCY"])
            if not 0 <= latency <= 55 or case.parameters["latency"] == -1 and latency == 0:
                raise ValueError("Unsupported generated latency")
        except (KeyError, TypeError, ValueError) as exc:
            raise PluginError(f"Invalid complex multiplier latency: {exc}") from exc
        return self._backend.generate(case, self.describe(case.parameters, latency), self.ip_name, self.version)
