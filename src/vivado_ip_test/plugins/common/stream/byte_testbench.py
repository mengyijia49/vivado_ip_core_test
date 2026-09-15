from dataclasses import replace
from itertools import zip_longest
import json
from pathlib import Path

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.stream.bytes import bit_fields, raw_output_tokens, token_ports
from vivado_ip_test.plugins.common.stream.testbench import ready_pattern, render_testbench
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.services.stimulus_schedule import build_schedule


def byte_decoder(spec):
    fields = bit_fields(spec.sink_payload)
    tokens = bit_fields(token_ports(spec.sink_payload))
    nbytes = fields["tdata"][1] // 8
    user_width = fields.get("tuser", (0, 0))[1] // nbytes

    def part(name, lane=None, token=False):
        low, width = (tokens if token else fields)[name]
        if lane is not None:
            width = 8 if name == "tdata" else user_width if name == "tuser" else 1
            low += lane * width
        return str(low) if width == 1 else f"{low + width - 1} downto {low}"

    qualification, extraction = [], []
    for lane in range(nbytes):
        keep = f"actual({part('tkeep', lane)}) = '1'" if "tkeep" in fields else "true"
        data = f"actual({part('tstrb', lane)}) = '1'" if "tstrb" in fields else "true"
        qualification += [f"        if not ({keep}) or not ({data}) then",
                          f"          qualified({part('tdata', lane)}) := (others => '0');", "        end if;"]
        if user_width:
            assignment = "'0'" if user_width == 1 else "(others => '0')"
            qualification += [f"        if not ({keep}) then",
                f"          qualified({part('tuser', lane)}) := {assignment};", "        end if;"]
        if "tstrb" in fields and "tkeep" in fields:
            qualification += [f"        if not ({keep}) then",
                f"          assert actual({part('tstrb', lane)}) = '0'",
                '            report "AXIS_SELF_CHECK_STATUS: FAIL reserved byte qualifier" severity failure;',
                "        end if;"]
        extraction += [f"          if {keep} then", "            token := (others => '0');",
                       f"            token({part('data', token=True)}) := actual({part('tdata', lane)});"]
        byte_kind = f"actual({part('tstrb', lane)})" if "tstrb" in fields else "'1'"
        extraction.append(f"            token({part('data_byte', token=True)}) := {byte_kind};")
        for name in ("tid", "tdest", "tuser"):
            if name in fields:
                extraction.append(f"            token({part(name, token=True)}) := actual({part(name, lane if name == 'tuser' else None)});")
        extraction += ["            check_token(token);", "          end if;"]
    if "tlast" in fields:
        extraction += [f"          if actual({part('tlast')}) = '1' then",
                       "            token := (others => '0');",
                       f"            token({part('end_packet', token=True)}) := '1';"]
        for name in ("tid", "tdest"):
            if name in fields:
                extraction.append(f"            token({part(name, token=True)}) := actual({part(name)});")
        extraction += ["            check_token(token);", "          end if;"]
    return "\n".join(qualification), "\n".join(extraction)


def render_byte_testbench(spec, paths, input_count, token_count, profile, initial_stall):
    qualification, extraction = byte_decoder(spec)
    template = (Path(__file__).parent / "templates/scoreboard_bytes.vhd.tpl").read_text()
    return render_testbench(spec, paths, input_count, profile.max_gap_cycles, initial_stall,
        scoreboard=template, extra={"qualification": qualification, "token_extraction": extraction,
            "output_width": sum(p.width for p in spec.sink_payload),
            "token_width": sum(p.width for p in token_ports(spec.sink_payload)), "token_count": token_count,
            "timeout_ns": 2000 + initial_stall * spec.output_period_ns +
                (input_count + token_count + 1024) * (profile.max_gap_cycles + 64) * max(10, spec.output_period_ns)})


class ByteStreamTestbenchBackend:
    def __init__(self, layout, registry):
        self._layout, self._registry = layout, registry

    def generate(self, case, spec, ip_name, version, prepare, reference):
        run = self._layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, ip_name, version)
        generation = self._registry.generate(port_space(spec.generated_ports,
            case.verification.boundary_mode == "systematic"), case.verification)
        order = build_schedule(len(generation.cases), case.verification, can_idle=True).transaction_indices
        generated = [dict(zip((p.name for p in spec.generated_ports), generation.cases[i])) for i in order]
        frames = prepare(generated)
        for frame in frames:
            if set(frame) != {p.name for p in spec.payload} or any(
                    type(frame[p.name]) is not int or not 0 <= frame[p.name] <= p.limit for p in spec.payload):
                raise ValueError("Invalid prepared byte stream input")
        expected = reference(frames)
        if not frames or type(expected.count) is not int or expected.count < 1:
            raise ValueError("Empty byte stream reference")
        if expected.ports != token_ports(spec.sink_payload):
            raise ValueError("Byte stream input/output token formats differ")
        schedule = build_schedule(len(frames), replace(case.verification, input_order="generated"), can_idle=True)
        for directory in ("tb", "vectors", "outputs"):
            (run / directory).mkdir(parents=True, exist_ok=True)
        paths = {"input_vectors": run / "vectors/input_vectors.txt",
            "expected_output": run / "vectors/expected_output.txt", "expected_mask": run / "vectors/expected_mask.txt",
            "required_inputs": run / "vectors/required_inputs.txt", "actual_output": run / "outputs/actual_output.txt",
            "raw_output": run / "outputs/accepted_output.txt", "accepted_input": run / "outputs/accepted_input.txt",
            "protocol_events": run / "outputs/protocol_events.txt", "protocol_summary": run / "outputs/protocol_summary.txt",
            "gaps": run / "vectors/gaps.txt", "ready": run / "vectors/ready.txt",
            "vectors": run / "vectors/vectors.json", "schedule": run / "vectors/schedule.json",
            "testbench": run / "tb/tb_stream_selfcheck.vhd", "xci": xci}
        with paths["input_vectors"].open("w") as output:
            for row in frames:
                output.write(packed(row, spec.payload) + "\n")
        indices = []
        boundaries = positions = previous = 0
        with paths["expected_output"].open("w") as values_file, paths["expected_mask"].open("w") as masks_file, \
                paths["required_inputs"].open("w") as causal_file:
            for row, mask, required in expected:
                for values in (row, mask):
                    if set(values) != {p.name for p in expected.ports} or any(
                            type(values[p.name]) is not int or not 0 <= values[p.name] <= p.limit for p in expected.ports):
                        raise ValueError("Invalid byte stream reference token")
                if not any(mask.values()) or type(required) is not int or not 1 <= required <= len(frames):
                    raise ValueError("Invalid token mask or accepted-input requirement")
                if required < previous:
                    raise ValueError("Byte stream causal indices must be ordered")
                previous = required
                indices.append(required - 1)
                values_file.write(packed(row, expected.ports) + "\n")
                masks_file.write(packed(mask, expected.ports) + "\n")
                causal_file.write(f"{required}\n")
                boundaries += row["end_packet"]
                positions += not row["end_packet"] and not row["data_byte"]
        if len(indices) != expected.count:
            raise ValueError("Byte stream reference count differs from emitted records")
        for name, rows in (("gaps", schedule.gaps), ("ready", ready_pattern(case.verification))):
            paths[name].write_text("".join(f"{value}\n" for value in rows))
        paths["vectors"].write_text(json.dumps(frames, indent=2) + "\n")
        initial_stall = (spec.capacity + 8) * (case.verification.max_gap_cycles + 2)
        metrics = {**generation.as_dict(), **schedule.metrics(), "checked_transaction_count": expected.count,
            "input_transfer_count": len(frames), "reference_token_count": expected.count,
            "comparison_kind": "axis_byte_and_packet_tokens", "simulation_mode": "behavioral",
            "byte_qualifiers": "data_position_null", "initial_sink_stall_cycles": initial_stall,
            "sequence_coverage": "see_protocol_summary_not_measured_as_percentage",
            "input_clock_period_ns": 10, "output_clock_period_ns": spec.output_period_ns,
            "prepared_additional_transfers": len(frames) - len(generated),
            "reference_packet_boundaries": boundaries, "reference_position_bytes": positions}
        paths["schedule"].write_text(json.dumps({**metrics, "mapping_kind": "accepted_transaction",
            "timing_mode": case.verification.timing_mode, "gaps_before_vector": schedule.gaps,
            "transaction_vector_indices": indices}, indent=2) + "\n")
        outputs = {"actual_output", "raw_output", "accepted_input", "protocol_events", "protocol_summary"}
        for name in outputs:
            paths[name].unlink(missing_ok=True)
        paths["testbench"].write_text(render_byte_testbench(spec, paths, len(frames), expected.count,
                                                         case.verification, initial_stall))
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "output_layout": binary_output_layout((p.name, p.width) for p in expected.ports),
            "vendor": case.vendor, "ip_name": case.ip_name, "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(frames),
                             "generation": generation.as_dict(), "schedule": metrics},
            "generated_ip": metadata, "token_fields": [{"name": p.name, "width": p.width} for p in expected.ports],
            "mask_policy": "position_data_and_packet_marker_nonpayload_only",
            "artifacts": {name: str(path.resolve()) for name, path in paths.items()},
            "artifact_sha256": {name: sha256_file(path) for name, path in paths.items() if name not in outputs}},
            indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"], paths["expected_output"],
            paths["actual_output"], manifest, expected.count, metrics)


def raw_audit(run, spec):
    try:
        with (run / "vectors/expected_output.txt").open() as expected, (run / "vectors/expected_mask.txt").open() as masks:
            tokens = raw_output_tokens(run / "outputs/accepted_output.txt", spec.sink_payload)
            count = 0
            for token, line, mask_line in zip_longest(tokens, expected, masks):
                if token is None or line is None or mask_line is None:
                    return False
                value, mask = line.strip(), mask_line.strip()
                if not len(token) == len(value) == len(mask) or any(
                        bit == "1" and actual != wanted for actual, wanted, bit in zip(token, value, mask)):
                    return False
                count += 1
            return count > 0
    except (OSError, ValueError, KeyError):
        return False
