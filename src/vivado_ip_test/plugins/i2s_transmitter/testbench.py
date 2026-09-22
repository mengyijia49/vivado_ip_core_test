import json
from pathlib import Path

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.i2s_transmitter.reference import prepare_audio, serialized_samples


def _lane_signals(channels):
    return "\n".join(f"  logic sdata_{lane};" for lane in range(channels // 2))


def _lane_mapping(channels):
    return "".join(f",\n    .sdata_{lane}_out(sdata_{lane})"
                   for lane in range(channels // 2))


def _lane_capture(channels):
    return "\n".join(
        f"      captured[{lane}][C_SAMPLE_WIDTH - 1 - bit_index] = sdata_{lane};"
        for lane in range(channels // 2))


class I2sTransmitterTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_i2s_transmitter.sv.tpl"

    def generate(self, case, spec):
        run = self._layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec.metadata, "i2s_transmitter", "1.0")
        samples = prepare_audio(case.parameters, case.verification)
        checked_samples = samples[:case.verification.case_budget * case.parameters["channels"]]
        expected = serialized_samples(checked_samples, case.parameters["channels"])
        paths = {name: run / value for name, value in {
            "testbench": "tb/tb_i2s_transmitter.sv",
            "input_vectors": "vectors/input_vectors.txt",
            "vectors": "vectors/audio_samples.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text("".join(
            f"{row['tid']:03b}{row['tdata']:032b}\n" for row in samples))
        paths["vectors"].write_text(json.dumps(samples, indent=2) + "\n")
        width = case.parameters["sample_width"]
        paths["expected_output"].write_text("".join(f"{value:0{width}b}\n" for value in expected))
        paths["actual_output"].unlink(missing_ok=True)
        rendered = self._template.read_text()
        replacements = {
            "sample_width": width, "lanes": case.parameters["channels"] // 2,
            "slot_width": 32 if case.parameters["use_32bit_lr"] else width,
            "input_count": len(samples), "expected_count": len(expected),
            "sync_sample": f"{width}'b{expected[0]:0{width}b}",
            "sclk_divider": case.parameters["sclk_divider"],
            "lane_signals": _lane_signals(case.parameters["channels"]),
            "lane_mapping": _lane_mapping(case.parameters["channels"]),
            "lane_capture": _lane_capture(case.parameters["channels"]),
            "input_path": str(paths["input_vectors"].resolve()),
            "actual_path": str(paths["actual_output"].resolve()),
            "timeout_ns": 20_000_000 + len(samples) * case.parameters["sclk_divider"] * 2000,
        }
        for name, value in replacements.items():
            rendered = rendered.replace(f"@@{name}@@", str(value))
        paths["testbench"].write_text(rendered)
        paths["xci"] = xci
        metrics = {"checked_transaction_count": len(expected),
            "input_audio_samples": len(samples), "audio_frames": case.verification.case_budget,
            "serial_lanes": case.parameters["channels"] // 2,
            "comparison_kind": "decoded_i2s_serial_samples",
            "sequence_coverage": "axi_lite_setup_axis_channel_order_and_i2s_serial_bits"}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout((("i2s_sample", width),)),
            "verification": {**case.verification.as_dict(), "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2, ensure_ascii=False) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(expected), metrics)
