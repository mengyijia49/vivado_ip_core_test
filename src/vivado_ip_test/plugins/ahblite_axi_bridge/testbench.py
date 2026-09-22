import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.ahblite_axi_bridge.reference import (
    AhbLiteAxiReference,
    axi_attributes,
    write_strobe,
)
from vivado_ip_test.plugins.ahblite_axi_bridge.vectors import prepare_operations
from vivado_ip_test.plugins.common.metadata import load_metadata


def _signals_and_mappings(spec):
    signals, mappings = [], []
    for port in (*spec.metadata.inputs, *spec.metadata.outputs):
        kind = "std_logic" if port.scalar else f"std_logic_vector({port.width-1} downto 0)"
        initial = "'0'" if port.scalar else "(others=>'0')"
        signals.append(f"  signal {port.name} : {kind} := {initial};")
        mappings.append(f"{port.name}=>{port.name}")
    mappings.append("s_ahb_hclk=>clk")
    return "\n".join(signals), ",\n      ".join(mappings)


def _calls(operations, parameters):
    lines = []
    for index, op in enumerate(operations):
        prot, cache = axi_attributes(op["hprot"], parameters["non_secure"])
        strobe = write_strobe(op["address"], op["size"], parameters["data_width"],
                               parameters["narrow_burst"])
        common = (f'{index}, "{op["address"]:0{parameters["address_width"]}b}", '
                  f'{op["size"]}, "{op["hprot"]:04b}", "{prot:03b}", "{cache:04b}", '
                  f'"{op["response"]:02b}"')
        if op["kind"] == "write":
            lines.append(f'    run_write({common}, "{op["data"]:0{parameters["data_width"]}b}", '
                         f'"{strobe:0{parameters["data_width"]//8}b}");')
        else:
            lines.append(f'    run_read({common}, "{op["read_data"]:0{parameters["data_width"]}b}");')
    return "\n".join(lines)


def render_testbench(parameters, operations, spec, output_path):
    signals, mappings = _signals_and_mappings(spec)
    return Template((Path(__file__).parent / "templates/tb_ahblite_axi_bridge.vhd.tpl").read_text()).substitute(
        data_width=parameters["data_width"], address_width=parameters["address_width"],
        id_width=parameters["id_width"], lanes=parameters["data_width"] // 8,
        stall_cycles=parameters["stall_cycles"], response_delay=parameters["response_delay_cycles"],
        operation_count=len(operations), signals=signals, mappings=mappings,
        operation_calls=_calls(operations, parameters),
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=5000 + len(operations) * 3000)


class AhbLiteAxiTestbenchBackend:
    def __init__(self, layout):
        self.layout = layout

    def generate(self, case, spec):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec.metadata, "ahblite_axi_bridge", "3.0")
        operations = prepare_operations(case.parameters, case.verification)
        model = AhbLiteAxiReference(case.parameters)
        rows = model.expected(operations)
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_ahblite_axi_bridge.vhd",
            "input_vectors": "vectors/ahb_operations.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        lanes = case.parameters["data_width"] // 8
        paths["expected_output"].write_text("".join(
            f"{row['write']:b}{row['address']:0{case.parameters['address_width']}b}"
            f"{row['data']:0{case.parameters['data_width']}b}{row['strobe']:0{lanes}b}{row['error']:b}\n"
            for row in rows))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(
            case.parameters, operations, spec, paths["actual_output"]))
        paths["xci"] = xci
        metrics = {"checked_transaction_count": len(rows),
            "comparison_kind": "ahblite_to_axi_exact_single_transfers",
            "sequence_coverage": "sizes_lane_boundaries_protection_backpressure_and_error_mapping",
            "reference_sequence_events": dict(model.event_counts)}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((("write", 1),
                ("address", case.parameters["address_width"]),
                ("data", case.parameters["data_width"]), ("strobe", lanes), ("error", 1))),
            "verification": {**case.verification.as_dict(), "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(rows), metrics)
