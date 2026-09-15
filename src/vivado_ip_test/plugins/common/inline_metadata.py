import json

from vivado_ip_test.plugins.base import PluginError


INLINE_BD_GLOB = "proj/*.srcs/sources_1/bd/dut_0/dut_0.bd"


def load_inline_metadata(run_dir, spec, ip_name, version):
    candidates = list(run_dir.glob(spec.inline_bd_glob))
    if len(candidates) != 1:
        raise PluginError("Expected exactly one matching Inline HDL block design")
    path = candidates[0]
    try:
        design = json.loads(path.read_text())["design"]
        info = design["design_info"]
        tool_version = info["tool_version"]
        if not isinstance(tool_version, str) or not tool_version:
            raise PluginError("Inline block design does not record the tool version")
        if info["name"] != "dut_0" or info["validated"] != "true":
            raise PluginError("Inline block design name or validation state does not match")
        if set(design["components"]) != {"core"} or design["design_tree"] != {"core": ""}:
            raise PluginError("Expected a single Inline HDL core")
        core = design["components"]["core"]
        reference = core["vlnv"]
        if reference != f"xilinx.com:inline_hdl:{ip_name}:{version}":
            raise PluginError(f"Inline HDL identifier does not match: {reference}")
        parameters = core["parameters"]
        for name, expected in spec.settings.items():
            actual = parameters[name]["value"]
            if not isinstance(actual, str) or actual != str(expected):
                raise PluginError(f"Inline HDL parameter {name} does not match")
        if spec.clock or spec.clock_aliases:
            raise PluginError("Inline metadata currently supports combinational blocks only")
        wanted = {p.name: (p, "I") for p in spec.inputs}
        wanted.update({p.name: (p, "O") for p in spec.outputs})
        ports = design["ports"]
        if set(ports) != set(wanted):
            raise PluginError("Inline HDL port set does not match")
        for name, (port, direction) in wanted.items():
            actual = ports[name]
            vector = "left" in actual and "right" in actual
            if actual["direction"] != direction or vector == port.scalar:
                raise PluginError(f"Inline HDL port {name} direction or type does not match")
            if vector and (int(actual["left"]) != port.width - 1 or int(actual["right"]) != 0):
                raise PluginError(f"Inline HDL port {name} bounds do not match")
            if ("left" in actual) != ("right" in actual):
                raise PluginError(f"Inline HDL port {name} has incomplete bounds")
        # Each external vector must connect directly to its corresponding core pin.
        nets = design["nets"]
        expected_nets = {frozenset((name, f"core/{name}")) for name in wanted}
        actual_nets = []
        for net in nets.values():
            endpoints = net["ports"]
            if not isinstance(endpoints, list) or len(endpoints) != 2:
                raise PluginError("Inline HDL net is not a direct two-pin connection")
            actual_nets.append(frozenset(endpoints))
        if len(actual_nets) != len(expected_nets) or set(actual_nets) != expected_nets:
            raise PluginError("Inline HDL wiring does not match the requested ports")
        if design.get("interface_ports") or design.get("interface_nets"):
            raise PluginError("Unexpected Inline HDL bus interfaces")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PluginError(f"Cannot read Inline HDL metadata: {path}: {exc}") from exc
    return path, {"artifact_format": "inline_bd", "component_reference": reference,
                  "component_parameters": parameters, "ports": ports, "nets": nets,
                  "tool_version": tool_version}
