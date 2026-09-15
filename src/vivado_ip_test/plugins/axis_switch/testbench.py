import json

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.plugins.axis_switch.reference import expected_transactions
from vivado_ip_test.plugins.axis_switch.render import render_testbench
from vivado_ip_test.plugins.axis_switch.vectors import prepare_frames, source_schedules, ready_matrix, routing_prefix_groups
from vivado_ip_test.services.stimulus_schedule import build_schedule


def write_vectors(run, spec, frames, expected, schedules, profile):
    if not frames or len(expected) != len(frames) or len(schedules) != spec.input_lane_count:
        raise ValueError("Switch stimulus and reference counts do not match")
    for rows, ports in ((frames, spec.payload), (expected, spec.sink_payload)):
        for row in rows:
            if set(row) != {p.name for p in ports} or any(type(row[p.name]) is not int or
                    not 0 <= row[p.name] <= p.limit for p in ports):
                raise ValueError("Invalid switch payload shape or width")
    for lane, schedule in enumerate(schedules):
        if len(schedule.gaps) != len(frames) or any(type(g) is not int or g < 0 for g in schedule.gaps):
            raise ValueError("Invalid switch source schedule")
        if any((frame[f"s{lane:02d}_{spec.tag_field}"] & ((1 << spec.tag_bits)-1)) != lane for frame in frames):
            raise ValueError("Switch source tags do not identify their input lane")
        if any(frame[f"s{lane:02d}_route"] >= spec.branch_count for frame in expected):
            raise ValueError("Invalid switch output port")
    paths = {name: run / path for name, path in {
        "input_vectors": "vectors/input_vectors.txt", "expected_output": "vectors/expected_output.txt",
        "actual_output": "outputs/actual_output.txt", "accepted_input": "outputs/accepted_input.txt",
        "protocol_events": "outputs/protocol_events.txt", "protocol_summary": "outputs/protocol_summary.txt",
        "ready": "vectors/ready.txt", "vectors": "vectors/vectors.json", "schedule": "vectors/schedule.json",
        "testbench": "tb/tb_stream_selfcheck.vhd"}.items()}
    mapping, output_counts = [], []
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    with paths["input_vectors"].open("w") as inputs, paths["expected_output"].open("w") as reference:
        for lane in range(spec.input_lane_count):
            prefix = f"s{lane:02d}_"
            for name, relative in ((f"input_{lane}", f"vectors/inputs/s{lane:02d}/input.txt"),
                                   (f"gaps_{lane}", f"vectors/inputs/s{lane:02d}/gaps.txt"),
                                   (f"input_events_{lane}", f"outputs/inputs/s{lane:02d}/handshakes.txt"),
                                   (f"accepted_{lane}", f"outputs/inputs/s{lane:02d}/accepted.txt")):
                paths[name] = run / relative
                paths[name].parent.mkdir(parents=True, exist_ok=True)
            paths[f"gaps_{lane}"].write_text("".join(f"{gap}\n" for gap in schedules[lane].gaps))
            with paths[f"input_{lane}"].open("w") as source:
                for frame, wanted in zip(frames, expected):
                    raw = {p.name: frame[prefix+p.name] for p in spec.lane_payload}
                    inputs.write(packed(raw, spec.lane_payload) + "\n")
                    source.write(packed({"route": wanted[prefix+"route"], **raw}, spec.lane_output) + "\n")
            counts = []
            for branch in range(spec.branch_count):
                paths[f"expected_{lane}_{branch}"] = run / f"vectors/outputs/s{lane:02d}/m{branch:02d}.txt"
                paths[f"actual_{lane}_{branch}"] = run / f"outputs/streams/s{lane:02d}/m{branch:02d}.txt"
                paths[f"expected_{lane}_{branch}"].parent.mkdir(parents=True, exist_ok=True)
                paths[f"actual_{lane}_{branch}"].parent.mkdir(parents=True, exist_ok=True)
                count = 0
                with paths[f"expected_{lane}_{branch}"].open("w") as target:
                    for index, frame in enumerate(expected):
                        if frame[prefix+"route"] == branch:
                            row = {p.name: frame[prefix+p.name] for p in spec.lane_output}
                            text = packed(row, spec.lane_output) + "\n"
                            reference.write(text)
                            target.write(text)
                            mapping.append({"input_lane": lane, "output_port": branch, "input_index": index})
                            count += 1
                counts.append(count)
            output_counts.append(counts)
    paths["ready"].write_text("".join(row+"\n" for row in ready_matrix(profile, spec.branch_count)))
    paths["vectors"].write_text(json.dumps(frames, indent=2) + "\n")
    for path in paths.values():
        if path.is_relative_to(run / "outputs"):
            path.unlink(missing_ok=True)
    return paths, mapping, output_counts


class SwitchTestbenchBackend:
    def __init__(self, layout, registry):
        self._layout, self._registry = layout, registry

    def generate(self, case, spec, ip_name, version):
        run = self._layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, ip_name, version)
        generation = self._registry.generate(
            port_space(spec.generated_ports, case.verification.boundary_mode == "systematic"), case.verification)
        selection = build_schedule(len(generation.cases), case.verification, can_idle=True)
        names = [p.name for p in spec.generated_ports]
        frames = prepare_frames([dict(zip(names, generation.cases[i])) for i in selection.transaction_indices], spec)
        expected = expected_transactions(frames, spec)
        schedules = source_schedules(len(frames), case.verification, spec.input_lane_count)
        paths, mapping, output_counts = write_vectors(run, spec, frames, expected, schedules, case.verification)
        paths["xci"] = xci
        initial_stall = 64 + spec.input_lane_count * 4
        metrics = {**generation.as_dict(), "simulation_mode": "behavioral",
            "comparison_kind": "axis_routing_by_source_and_output", "schedule_version": "1.0",
            "input_groups": len(frames), "checked_transaction_count": len(mapping),
            "input_lane_count": spec.input_lane_count, "output_branch_count": spec.branch_count,
            "checked_input_transfers": len(mapping), "checked_output_transfers": len(mapping),
            "input_cycles": max(s.input_cycles for s in schedules),
            "gap_cycles": sum(sum(s.gaps) for s in schedules),
            "max_observed_gap": max(max(s.gaps) for s in schedules),
            "source_timing_pattern": "switch_independent_queues:1.0",
            "backpressure_pattern": "switch_independent_outputs:1.0",
            "initial_sink_stall_cycles": initial_stall,
            "tag_field": spec.tag_field, "reserved_source_tag_bits": spec.tag_bits,
            "numeric_coverage_scope": "generated_fields_excluding_source_tag_and_routing",
            "payload_byte_qualifiers": "all_bytes_valid", "routing_ranges": spec.routes,
            "expected_transfers_by_source_and_output": output_counts,
            "expected_packet_boundaries": sum(v for f in frames for k, v in f.items() if k.endswith("_tlast")),
            "prepared_additional_groups": len(frames)-len(generation.cases),
            "directed_routing_minimum_groups": routing_prefix_groups(spec),
            "output_file_order": "source_then_output_then_stream_index",
            "sequence_coverage": "see_protocol_summary_not_measured_as_percentage"}
        paths["schedule"].write_text(json.dumps({**metrics, "mapping_kind": "accepted_transaction",
            "timing_mode": case.verification.timing_mode,
            "selected_vector_indices": selection.transaction_indices,
            "transaction_vector_indices": [m["input_index"] for m in mapping],
            "output_mapping": mapping, "gaps_by_input_lane": [s.gaps for s in schedules]}, indent=2) + "\n")
        paths["testbench"].write_text(render_testbench(spec, paths, len(frames), output_counts,
                                                       case.verification.max_gap_cycles, initial_stall))
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "output_layout": binary_output_layout((p.name, p.width) for p in spec.lane_output),
            "vendor": case.vendor, "ip_name": case.ip_name, "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(mapping),
                             "generation": generation.as_dict(), "schedule": metrics},
            "generated_ip": metadata, "artifacts": {name: str(path.resolve()) for name, path in paths.items()},
            "artifact_sha256": {name: sha256_file(path) for name, path in paths.items()
                                if not path.is_relative_to(run / "outputs")}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"], paths["expected_output"],
                                  paths["actual_output"], manifest, len(mapping), metrics)
