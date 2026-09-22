import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axis_protocol_checker.reference import (
    AxisProtocolCheckerReference,
    STATUS_BITS,
    prepare_operations,
)
from vivado_ip_test.plugins.common.metadata import load_metadata


def _port_map(parameters):
    optional = []
    for enabled, text in (
        (parameters["has_system_reset"], "system_resetn=>system_resetn"),
        (parameters["has_aclken"], "aclken=>aclken"),
        (parameters["has_tready"], "pc_axis_tready=>tready"),
        (parameters["has_tstrb"], "pc_axis_tstrb=>tstrb"),
        (parameters["has_tkeep"], "pc_axis_tkeep=>tkeep"),
        (parameters["has_tlast"], "pc_axis_tlast=>tlast"),
        (parameters["tid_width"] > 0, "pc_axis_tid=>tid"),
        (parameters["tdest_width"] > 0, "pc_axis_tdest=>tdest"),
        (parameters["tuser_width"] > 0, "pc_axis_tuser=>tuser"),
    ):
        if enabled:
            optional.append(",\n    " + text)
    return "".join(optional)


def _operation_calls(operations):
    codes = {name: index for index, name in enumerate(STATUS_BITS)}
    return "\n".join(f"    run_case({codes[item['scenario']]});" for item in operations)


def render_testbench(parameters, operations, output_path):
    template = Template((Path(__file__).parent /
        "templates/tb_axis_protocol_checker.vhd.tpl").read_text())
    return template.substitute(
        data_width=parameters["data_bytes"] * 8,
        lane_width=parameters["data_bytes"],
        id_width=max(1, parameters["tid_width"]),
        dest_width=max(1, parameters["tdest_width"]),
        user_width=max(1, parameters["tuser_width"]),
        max_waits=parameters["max_waits"],
        port_map=_port_map(parameters),
        operation_calls=_operation_calls(operations),
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=10000 + len(operations) * (parameters["max_waits"] + 30) * 10,
    )


class AxisProtocolCheckerTestbenchBackend:
    def __init__(self, layout):
        self.layout = layout

    def generate(self, case, spec):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec.metadata, "axis_protocol_checker", "2.0")
        operations = prepare_operations(case.parameters, case.verification)
        model = AxisProtocolCheckerReference()
        outputs = model.evaluate(operations)
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_axis_protocol_checker.vhd",
            "input_vectors": "vectors/protocol_scenarios.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        paths["expected_output"].write_text("".join(
            format(row["status"], "032b") + "\n" for row in outputs))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(
            case.parameters, operations, paths["actual_output"]))
        paths["xci"] = xci
        metrics = {"checked_transaction_count": len(outputs),
            "comparison_kind": "axis_protocol_checker_exact_status_bits",
            "reference_sequence_events": dict(model.event_counts),
            "sequence_coverage": "reset_stability_valid_wait_and_keep_strb_rules"}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((("pc_status", 32),)),
            "verification": {**case.verification.as_dict(), "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(outputs), metrics)
