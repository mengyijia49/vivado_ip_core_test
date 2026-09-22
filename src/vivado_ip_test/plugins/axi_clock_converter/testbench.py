import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axi_clock_converter.reference import (
    AxiClockConverterReference, prepare_operations,
)
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.vectors import port_space


FIELDS = (("channel", 3), ("id", None), ("addr", None), ("len", 8), ("size", 3),
          ("burst", 2), ("lock", 1), ("cache", 4), ("prot", 3), ("region", 4),
          ("qos", 4), ("data", None), ("strb", None), ("last", 1), ("resp", 2),
          ("user", None))


def widths(p):
    return {"id": p["id_width"], "addr": p["address_width"], "data": p["data_width"],
            "strb": p["data_width"] // 8, "user": p["user_width"],
            **{name: width for name, width in FIELDS if width is not None}}


def packed(item, p):
    field_widths = widths(p)
    return "".join(format(item[name], f"0{field_widths[name]}b") for name, _ in FIELDS)


def bits(value, width):
    return f'"{value:0{width}b}"'


def operation_calls(operations, p):
    w = widths(p)
    return "\n".join(
        "    drive(%d, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %d);" % (
            item["channel"], bits(item["id"], w["id"]), bits(item["addr"], w["addr"]),
            bits(item["len"], 8), bits(item["size"], 3), bits(item["burst"], 2),
            "'1'" if item["lock"] else "'0'", bits(item["cache"], 4),
            bits(item["prot"], 3), bits(item["region"], 4), bits(item["qos"], 4),
            bits(item["data"], w["data"]), bits(item["strb"], w["strb"]),
            "'1'" if item["last"] else "'0'", bits(item["resp"], 2),
            bits(item["user"], w["user"]), item["hold"]) for item in operations)


def render_testbench(p, operations, output_path):
    template = Template((Path(__file__).parent / "templates/tb_axi_clock_converter.vhd.tpl").read_text())
    return template.substitute(data_width=p["data_width"], address_width=p["address_width"],
        id_width=p["id_width"], user_width=p["user_width"], lanes=p["data_width"] // 8,
        output_half_period=p["output_period_ns"] // 2, operation_count=len(operations),
        operation_calls=operation_calls(operations, p),
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=3000 + len(operations) * 500)


class AxiClockConverterTestbenchBackend:
    def __init__(self, layout, registry):
        self.layout, self.registry = layout, registry

    def generate(self, case, spec, generated_ports):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, "axi_clock_converter", "2.1")
        generation = self.registry.generate(
            port_space(generated_ports, case.verification.boundary_mode == "systematic"),
            case.verification)
        samples = [dict(zip((port.name for port in generated_ports), row))
                   for row in generation.cases]
        operations = prepare_operations(samples, case.parameters)
        model = AxiClockConverterReference()
        expected = model.evaluate(operations)
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_axi_clock_converter.vhd",
            "input_vectors": "vectors/operations.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt",
            "samples": "vectors/numeric_samples.json"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        paths["samples"].write_text(json.dumps(samples, indent=2) + "\n")
        paths["expected_output"].write_text("".join(packed(row, case.parameters) + "\n"
                                                     for row in expected))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(case.parameters, operations,
                                                        paths["actual_output"]))
        paths["xci"] = xci
        metrics = {**generation.as_dict(), "operation_count": len(operations),
            "checked_transaction_count": len(expected),
            "comparison_kind": "per_channel_axi_transaction_sequence",
            "reference_sequence_events": dict(model.event_counts),
            "sequence_coverage": "all_five_channels_with_independent_backpressure"}
        manifest = run / "manifest.json"
        field_widths = widths(case.parameters)
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((name, field_widths[name]) for name, _ in FIELDS),
            "verification": {**case.verification.as_dict(), "generation": generation.as_dict(),
                             "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(expected), metrics)
