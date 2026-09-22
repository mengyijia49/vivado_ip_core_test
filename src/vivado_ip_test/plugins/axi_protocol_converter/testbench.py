import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axi_protocol_converter.reference import AxiProtocolConverterReference
from vivado_ip_test.plugins.axi_protocol_converter.vectors import prepare_operations
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.vectors import port_space


OUTPUT_FIELDS = (("kind", 1), ("id", None), ("data", None), ("response", 2), ("last", 1))


def packed_output(row, parameters):
    widths = (1, parameters["id_width"], parameters["data_width"], 2, 1)
    return "".join(format(row[name], f"0{width}b")
                   for (name, _), width in zip(OUTPUT_FIELDS, widths))


def natural_array(name, values):
    return f"  constant {name} : natural_array(0 to {len(values)-1}) := (" + \
        ", ".join(str(value) for value in values) + ");"


def vector_array(name, values, width, type_name):
    items = ", ".join(f'{index} => "{value:0{width}b}"'
                      for index, value in enumerate(values))
    return f"  constant {name} : {type_name}(0 to {len(values)-1}) := ({items});"


def operation_calls(operations, parameters):
    lines = []
    width = parameters["data_width"]
    for item in operations:
        ident = f'"{item["id"]:0{parameters["id_width"]}b}"'
        address = f'"{item["address"]:0{parameters["address_width"]}b}"'
        common = (f"{ident}, {address}, {item['beats']}, {item['size']}, "
                  f"{item['burst']}, {item['prot']}, {item['hold_cycles']}")
        if item["kind"] == "write":
            data = f'"{item["data"] & ((1 << width)-1):0{width}b}"'
            lines.append(f"    drive_write({common}, {data}, {item['strobe']}, "
                         f"{str(item['w_before_aw']).lower()});")
        else:
            lines.append(f"    drive_read({common});")
    return "\n".join(lines)


def render_testbench(parameters, operations, accesses, output_path):
    width, address_width = parameters["data_width"], parameters["address_width"]
    lanes = width // 8
    declarations = "\n".join((
        "  type natural_array is array(natural range <>) of natural;",
        f"  type address_array is array(natural range <>) of std_logic_vector({address_width-1} downto 0);",
        f"  type data_array is array(natural range <>) of std_logic_vector({width-1} downto 0);",
        f"  type strobe_array is array(natural range <>) of std_logic_vector({lanes-1} downto 0);",
        "  type prot_array is array(natural range <>) of std_logic_vector(2 downto 0);",
        "  type response_array is array(natural range <>) of std_logic_vector(1 downto 0);",
        natural_array("EXPECTED_KIND", [a["kind"] for a in accesses]),
        vector_array("EXPECTED_ADDR", [a["address"] for a in accesses], address_width, "address_array"),
        vector_array("EXPECTED_DATA", [a["data"] for a in accesses], width, "data_array"),
        vector_array("EXPECTED_STROBE", [a["strobe"] for a in accesses], lanes, "strobe_array"),
        vector_array("EXPECTED_PROT", [a["prot"] for a in accesses], 3, "prot_array"),
        vector_array("EXPECTED_RESPONSE", [a["response"] for a in accesses], 2, "response_array"),
    ))
    template = Template((Path(__file__).parent /
        "templates/tb_axi_protocol_converter.vhd.tpl").read_text())
    return template.substitute(data_width=width, address_width=address_width,
        id_width=parameters["id_width"], lanes=lanes, declarations=declarations,
        access_count=len(accesses), operation_count=len(operations),
        stall_cycles=parameters["downstream_stall_cycles"],
        operation_calls=operation_calls(operations, parameters),
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=10000 + len(accesses) * (parameters["downstream_stall_cycles"] + 8) * 20)


class AxiProtocolConverterTestbenchBackend:
    def __init__(self, layout, registry):
        self.layout, self.registry = layout, registry

    def generate(self, case, spec, generated_ports):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, "axi_protocol_converter", "2.1")
        generation = self.registry.generate(
            port_space(generated_ports, case.verification.boundary_mode == "systematic"),
            case.verification)
        samples = [dict(zip((port.name for port in generated_ports), row))
                   for row in generation.cases]
        operations = prepare_operations(samples, case.parameters)
        model = AxiProtocolConverterReference(case.parameters)
        accesses, outputs = model.evaluate(operations)
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_axi_protocol_converter.vhd",
            "input_vectors": "vectors/operations.json",
            "accesses": "vectors/axi_lite_accesses.json",
            "samples": "vectors/numeric_samples.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        paths["accesses"].write_text(json.dumps(accesses, indent=2) + "\n")
        paths["samples"].write_text(json.dumps(samples, indent=2) + "\n")
        paths["expected_output"].write_text("".join(
            packed_output(row, case.parameters) + "\n" for row in outputs))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(
            case.parameters, operations, accesses, paths["actual_output"]))
        paths["xci"] = xci
        metrics = {**generation.as_dict(), "operation_count": len(operations),
            "axi_lite_access_count": len(accesses), "checked_transaction_count": len(outputs),
            "comparison_kind": "axi4_burst_to_axi4lite_access_sequence",
            "reference_sequence_events": dict(model.event_counts),
            "sequence_coverage": "fixed_increment_wrap_narrow_errors_and_backpressure"}
        fields = tuple((name, case.parameters["id_width"] if name == "id" else
                        case.parameters["data_width"] if name == "data" else field_width)
                       for name, field_width in OUTPUT_FIELDS)
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout(fields),
            "verification": {**case.verification.as_dict(), "generation": generation.as_dict(),
                             "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(outputs), metrics)
