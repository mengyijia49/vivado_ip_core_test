import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axi_memory_init.reference import AxiMemoryInitReference, initial_value
from vivado_ip_test.plugins.common.metadata import load_metadata


def _signals_and_mappings(spec):
    signals, mappings = [], []
    for port in (*spec.metadata.inputs, *spec.metadata.outputs):
        kind = "std_logic" if port.scalar else f"std_logic_vector({port.width-1} downto 0)"
        initial = "'0'" if port.scalar else "(others=>'0')"
        signals.append(f"  signal {port.name} : {kind} := {initial};")
        mappings.append(f"{port.name}=>{port.name}")
    mappings.append("aclk=>aclk")
    return "\n".join(signals), ",\n      ".join(mappings)


def render_testbench(parameters, spec, output_path):
    model = AxiMemoryInitReference(parameters)
    value = initial_value(parameters["init_pattern"], parameters["data_width"])
    post_value = value ^ ((1 << parameters["data_width"]) - 1)
    signals, mappings = _signals_and_mappings(spec)
    return Template((Path(__file__).parent / "templates/tb_axi_memory_init.vhd.tpl").read_text()).substitute(
        data_width=parameters["data_width"], address_width=parameters["address_width"],
        id_width=parameters["id_width"], lanes=parameters["data_width"] // 8,
        beat_count=model.beat_count, burst_count=model.burst_count,
        data_size=(parameters["data_width"] // 8).bit_length() - 1,
        base_bits=format(parameters["base_address"], f"0{parameters['address_width']}b"),
        init_bits=format(value, f"0{parameters['data_width']}b"),
        post_bits=format(post_value, f"0{parameters['data_width']}b"),
        pause_cycles=parameters["aclken_pause_cycles"], stall_cycles=parameters["stall_cycles"],
        response_delay=parameters["response_delay_cycles"], signals=signals, mappings=mappings,
        output_path=str(output_path.resolve()).replace('"', '""'),
        timeout_ns=5000 + model.beat_count * 300)


class AxiMemoryInitTestbenchBackend:
    def __init__(self, layout):
        self.layout = layout

    def generate(self, case, spec):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec.metadata, "axi_memory_init", "1.0")
        model = AxiMemoryInitReference(case.parameters)
        addresses = model.burst_addresses()
        rows = model.output_rows()
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_axi_memory_init.vhd",
            "input_vectors": "vectors/initialization_plan.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps({"burst_addresses": addresses,
            "beat_count": model.beat_count, "init_value": initial_value(
                case.parameters["init_pattern"], case.parameters["data_width"])}, indent=2) + "\n")
        paths["expected_output"].write_text("".join(
            f"{data:0{case.parameters['data_width']}b}{strobe:0{model.lanes}b}{last:b}\n"
            for data, strobe, last in rows))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(case.parameters, spec, paths["actual_output"]))
        paths["xci"] = xci
        metrics = {"checked_transaction_count": len(rows), "initialization_bursts": model.burst_count,
            "initialization_beats": model.beat_count, "comparison_kind": "axi_initialization_exact_sequence",
            "sequence_coverage": "init_aw_w_b_aclken_backpressure_and_post_init_five_channel_passthrough",
            "reference_sequence_events": dict(model.event_counts)}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((("data", case.parameters["data_width"]),
                ("strobe", model.lanes), ("last", 1))),
            "verification": {**case.verification.as_dict(), "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(rows), metrics)

