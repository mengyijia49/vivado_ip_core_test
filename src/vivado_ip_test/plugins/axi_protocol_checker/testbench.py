import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axi_protocol_checker.reference import AxiProtocolCheckerReference
from vivado_ip_test.plugins.axi_protocol_checker.vectors import prepare_operations
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.vectors import port_space


def operation_calls(operations, parameters):
    lines = []
    for operation in operations:
        ident = format(operation["id"], f'0{parameters["id_width"]}b')
        address = format(operation["address"], f'0{parameters["address_width"]}b')
        data = format(operation["data"], f'0{parameters["data_width"]}b')
        lines.append(f'    run_case({operation["scenario_code"]}, "{ident}", '
                     f'"{address}", "{data}");')
    return "\n".join(lines)


def render_testbench(parameters, operations, output_path):
    template = Template((Path(__file__).parent /
        "templates/tb_axi_protocol_checker.vhd.tpl").read_text())
    return template.substitute(data_width=parameters["data_width"],
        address_width=parameters["address_width"], id_width=parameters["id_width"],
        data_size=(parameters["data_width"] // 8).bit_length() - 1,
        aw_width_violation=('awburst<="00"; awlen<=std_logic_vector(to_unsigned(16,8));'
            if parameters["data_width"] == 1024 else
            'awsize<=std_logic_vector(to_unsigned(DATA_SIZE+1,3));'),
        ar_width_violation=('arburst<="00"; arlen<=std_logic_vector(to_unsigned(16,8));'
            if parameters["data_width"] == 1024 else
            'arsize<=std_logic_vector(to_unsigned(DATA_SIZE+1,3));'),
        operation_calls=operation_calls(operations, parameters),
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=5000 + len(operations) * 300)


class AxiProtocolCheckerTestbenchBackend:
    def __init__(self, layout, registry):
        self.layout, self.registry = layout, registry

    def generate(self, case, spec, generated_ports):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, "axi_protocol_checker", "2.0")
        generation = self.registry.generate(
            port_space(generated_ports, case.verification.boundary_mode == "systematic"),
            case.verification)
        samples = [dict(zip((port.name for port in generated_ports), row))
                   for row in generation.cases]
        operations = prepare_operations(samples, case.parameters)
        model = AxiProtocolCheckerReference()
        outputs = model.evaluate(operations)
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_axi_protocol_checker.vhd",
            "input_vectors": "vectors/protocol_scenarios.json",
            "samples": "vectors/numeric_samples.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        paths["samples"].write_text(json.dumps(samples, indent=2) + "\n")
        paths["expected_output"].write_text("".join(
            format(row["status"], "0160b") + "\n" for row in outputs))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(
            case.parameters, operations, paths["actual_output"]))
        paths["xci"] = xci
        metrics = {**generation.as_dict(), "scenario_count": len(operations),
            "checked_transaction_count": len(outputs),
            "comparison_kind": "axi_protocol_checker_exact_status_bits",
            "reference_sequence_events": dict(model.event_counts),
            "sequence_coverage": "legal_reserved_wrap_size_and_handshake_violations"}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((("pc_status", 160),)),
            "verification": {**case.verification.as_dict(), "generation": generation.as_dict(),
                             "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(outputs), metrics)
