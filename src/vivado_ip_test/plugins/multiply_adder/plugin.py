import json

from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port, validate_parameters
from vivado_ip_test.plugins.common.plugin import CycleIpPlugin
from vivado_ip_test.plugins.multiply_adder.reference import MultiplyAdderModel


class MultiplyAdderPlugin(CycleIpPlugin):
    ip_type = "multiply_adder"
    ip_name = "xbip_multadd"
    version = "3.0"

    def describe(self, p, timing=None, timing_path=None):
        signs = {"Signed", "Unsigned"}
        validate_parameters(p, {"a_width": range(1, 54), "b_width": range(1, 54),
            "c_width": range(1, 107), "a_type": signs, "b_type": signs, "c_type": signs,
            "output_high": range(0, 107), "output_low": range(0, 107),
            "pipelined": bool, "use_pcin": bool, "ce_overrides_reset": bool})
        for port, maximum in (("a", 52), ("b", 52), ("c", 105)):
            signed = p[f"{port}_type"] == "Signed"
            if not 1 + signed <= p[f"{port}_width"] <= maximum + signed:
                raise PluginError(f"Multiply-adder {port} width does not match its signedness")
        if p["output_low"] > p["output_high"]:
            raise PluginError("Output low bit must not exceed the high bit")
        if p["output_high"] > max(p["a_width"] + p["b_width"], p["c_width"]):
            raise PluginError("Output exceeds the full-precision arithmetic width")
        if not p["pipelined"] and p["ce_overrides_reset"]:
            raise PluginError("Combinational configurations have no CE/reset priority")
        if p["use_pcin"]:
            a = p["a_width"] + (p["a_type"] == "Unsigned")
            b = p["b_width"] + (p["b_type"] == "Unsigned")
            if p["c_width"] != 48 or p["c_type"] != "Signed" or p["output_high"] > 47:
                raise PluginError("PCIN uses canonical signed C width 48 and at most 48 output bits")
            if not (a <= 25 and b <= 18 or a <= 18 and b <= 25):
                raise PluginError("PCIN is restricted to a single Artix-7 DSP multiply-adder")
        latency = -1 if p["pipelined"] else 0
        settings = {f"c_{port}_{key}": (int(p[f"{port}_type"] == "Unsigned") if key == "type" else p[f"{port}_width"])
                    for port in ("a", "b", "c") for key in ("width", "type")}
        settings.update({"c_out_high": p["output_high"], "c_out_low": p["output_low"],
            "c_ab_latency": latency, "c_c_latency": 0 if p["use_pcin"] else latency,
            "c_use_pcin": p["use_pcin"], "c_ce_overrides_sclr": int(p["ce_overrides_reset"])})
        inputs = [Port(port.upper(), p[f"{port}_width"]) for port in ("a", "b", "c")]
        if p["use_pcin"]:
            inputs.append(Port("PCIN", 48))
        inputs.append(Port("SUBTRACT", scalar=True))
        if p["pipelined"]:
            inputs += [Port("CE", scalar=True), Port("SCLR", scalar=True)]
        drain = max(timing["ab_latency"], timing["c_latency"], 2) if timing else 1

        def factory():
            if timing is None:
                raise PluginError("Multiply-adder timing metadata is required before reference generation")
            return MultiplyAdderModel(p, timing)

        def prefix():
            masks = {port.name: port.limit for port in inputs}
            addend = "PCIN" if p["use_pcin"] else "C"

            def row(**values):
                return {key: value & masks[key] for key, value in values.items()}

            if p["pipelined"]:
                yield {"SCLR": 1}
                yield from ({} for _ in range(drain))
            # Hold the other multiplier input nonzero so each input pulse is observable.
            for pulse, companion in (("A", "B"), ("B", "A")):
                held = max(1, masks[companion] >> 1)
                yield from ({companion: held} for _ in range(drain))
                yield {pulse: max(1, masks[pulse] >> 1), companion: held}
                yield from ({companion: held} for _ in range(drain))
            for values in ({addend: 1}, {"A": 3, "B": 5, addend: 19},
                           {"A": 3, "B": 5, addend: 19, "SUBTRACT": 1}):
                yield row(**values)
                yield from ({} for _ in range(drain))
            if p["use_pcin"]:
                yield {"C": masks["C"]}
                yield from ({} for _ in range(drain))
            for index in range(max(16, 2 * drain)):
                yield row(A=(1 << (index % p["a_width"])) | 1,
                          B=(1 << ((index + 1) % p["b_width"])) | 1,
                          **{addend: (1 << (index % masks[addend].bit_length())) | 1},
                          SUBTRACT=index % 2)
            if p["pipelined"]:
                yield from (row(A=7, B=11, **{addend: 23}, CE=0, SUBTRACT=i % 2)
                            for i in range(3))
                yield {"CE": 0, "SCLR": 1}
                yield from ({} for _ in range(drain))
                yield from (row(A=3, B=5, **{addend: 19}) for _ in range(drain))
                yield {"SCLR": 1}
                yield from ({} for _ in range(drain))

        return CycleSpec(tuple(inputs), (Port("P", p["output_high"] - p["output_low"] + 1), Port("PCOUT", 48)),
            settings=settings, model_parameters={key.upper(): int(value) if isinstance(value, bool) else value
                                                for key, value in settings.items()},
            model_factory=factory, clock="CLK" if p["pipelined"] else None,
            neutral={"CE": 1} if p["pipelined"] else {}, prefix=prefix, flush_cycles=drain + 2,
            supporting_artifacts={"ip_timing": timing_path} if timing_path else {})

    def generate_testbench(self, case):
        path = self._layout.case_run_dir(case) / "vectors/ip_timing.json"
        try:
            timing = json.loads(path.read_text())
            expected = {"schema_version", "ab_latency", "c_latency", "implementation"}
            if not isinstance(timing, dict) or set(timing) != expected or any(type(v) is not int for v in timing.values()):
                raise ValueError("Timing metadata fields are invalid")
            if timing["schema_version"] != 1 or timing["implementation"] not in (0, 1, 2):
                raise ValueError("Timing metadata version or implementation is unsupported")
            if any(not 0 <= timing[k] <= 64 for k in ("ab_latency", "c_latency")):
                raise ValueError("Timing metadata latency is outside the supported range")
            pipelined = case.parameters["pipelined"]
            if (pipelined and min(timing["ab_latency"], timing["c_latency"]) == 0 or
                    not pipelined and max(timing["ab_latency"], timing["c_latency"]) != 0):
                raise ValueError("Timing metadata conflicts with the requested pipeline mode")
            if case.parameters["use_pcin"] and timing["implementation"] not in (0, 1):
                raise ValueError("PCIN requires a single DSP configuration")
            if pipelined and timing["implementation"] in (0, 1):
                if (timing["ab_latency"], timing["c_latency"]) != (3, 1 if case.parameters["use_pcin"] else 2):
                    raise ValueError("Single-DSP timing conflicts with the documented register paths")
        except (OSError, ValueError, TypeError) as exc:
            raise PluginError(f"Invalid multiply-adder timing metadata: {path}: {exc}") from exc
        return self._backend.generate(case, self.describe(case.parameters, timing, path), self.ip_name, self.version)
