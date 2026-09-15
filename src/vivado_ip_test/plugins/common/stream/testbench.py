import json
import random
from dataclasses import replace
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.testbench import packed
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.services.stimulus_schedule import build_schedule


def packetize(spec, vectors, schedule):
    lengths = (1, 2, 3, 7, 16, max(1, spec.capacity - 1), spec.capacity, spec.capacity + 1)
    remaining, packet = lengths[0], 0
    frames = []
    for index, vector_index in enumerate(schedule.transaction_indices):
        frame = dict(zip((p.name for p in spec.generated_ports), vectors[vector_index]))
        for port in spec.payload:
            if port.name in {"tkeep", "tstrb"}:
                frame[port.name] = port.limit
            elif port.name == "tlast":
                frame[port.name] = int(remaining == 1 or index == len(vectors) - 1)
        frames.append(frame)
        remaining -= 1
        if remaining == 0:
            packet += 1
            remaining = lengths[packet % len(lengths)]
    return frames


def ready_pattern(profile):
    rng = random.Random(f"stream-ready:1.0:{profile.random_seed}")
    # Guaranteed progress and sustained stalls, plus independent seeded backpressure.
    return ([0] * profile.max_gap_cycles + [1] * profile.burst_length +
            [rng.randrange(2) for _ in range(256)] + [1] * 32)


class StreamTestbenchBackend:
    def __init__(self, layout, registry):
        self._layout, self._registry = layout, registry

    def generate(self, case, spec, ip_name, version, reference, *, prepare=None,
                 renderer=None, sink_pattern=None, source_timing=None, reference_contract=None):
        run = self._layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, ip_name, version)
        generation = self._registry.generate(
            port_space(spec.generated_ports, case.verification.boundary_mode == "systematic"),
            case.verification)
        schedule = build_schedule(len(generation.cases), case.verification, can_idle=True)
        selected_indices = schedule.transaction_indices
        frames = packetize(spec, generation.cases, schedule)
        if prepare is not None:
            frames = prepare(frames)
            schedule = build_schedule(len(frames), replace(case.verification, input_order="generated"), can_idle=True)
        for frame in frames:
            if set(frame) != {port.name for port in spec.payload} or any(
                    type(frame[p.name]) is not int or not 0 <= frame[p.name] <= p.limit for p in spec.payload):
                raise ValueError("Stream input preparation returned an invalid payload")
        expected = reference(frames)
        if len(expected) != len(frames) or not frames:
            raise ValueError("Beat stream reference must preserve transaction count")
        for frame in expected:
            if set(frame) != {port.name for port in spec.sink_payload} or any(
                    type(frame[p.name]) is not int or not 0 <= frame[p.name] <= p.limit
                    for p in spec.sink_payload):
                raise ValueError("Stream reference returned an invalid payload")
        for directory in ("tb", "vectors", "outputs"):
            (run / directory).mkdir(parents=True, exist_ok=True)
        paths = {"input_vectors": run / "vectors/input_vectors.txt",
                 "expected_output": run / "vectors/expected_output.txt",
                 "actual_output": run / "outputs/actual_output.txt",
                 "accepted_input": run / "outputs/accepted_input.txt",
                 "protocol_events": run / "outputs/protocol_events.txt",
                 "protocol_summary": run / "outputs/protocol_summary.txt",
                 "gaps": run / "vectors/gaps.txt", "ready": run / "vectors/ready.txt",
                 "vectors": run / "vectors/vectors.json", "schedule": run / "vectors/schedule.json",
                 "testbench": run / "tb/tb_stream_selfcheck.vhd", "xci": xci}
        for name, rows, ports in (("input_vectors", frames, spec.payload),
                                 ("expected_output", expected, spec.sink_payload)):
            with paths[name].open("w") as output:
                for row in rows:
                    output.write(packed(row, ports) + "\n")
        lanes = getattr(spec, "input_lane_count", 1)
        gaps = (source_timing(schedule, case.verification) if source_timing else
                [(gap,) for gap in schedule.gaps])
        if len(gaps) != len(frames) or any(len(row) != lanes or any(type(gap) is not int or gap < 0
                for gap in row) for row in gaps):
            raise ValueError("Stream timing returned invalid input gaps")
        paths["gaps"].write_text("".join(" ".join(str(gap) for gap in row) + "\n" for row in gaps))
        paths["ready"].write_text("".join(f"{bits}\n" for bits in
            (sink_pattern or ready_pattern)(case.verification)))
        paths["vectors"].write_text(json.dumps(frames, indent=2) + "\n")
        initial_stall = (spec.capacity + 8) * (case.verification.max_gap_cycles + 2) * 10
        initial_stall = (initial_stall + spec.output_period_ns - 1) // spec.output_period_ns
        metrics = {**generation.as_dict(), **schedule.metrics(),
                   "input_cycles": len(frames) + sum(max(row) for row in gaps),
                   "gap_cycles": sum(max(row) for row in gaps),
                   "max_observed_gap": max(max(row) for row in gaps),
                   "input_lane_count": lanes, "checked_input_transfers": len(frames) * lanes,
                   "source_timing_pattern": getattr(spec, "source_timing_pattern", "single_input:1.0"),
                   "checked_transaction_count": len(frames), "comparison_kind": "accepted_axis_payload",
                   "simulation_mode": "behavioral", "backpressure_pattern": getattr(
                       spec, "backpressure_pattern", "seeded_with_long_stalls:1.0"),
                   "initial_sink_stall_cycles": initial_stall,
                   "input_clock_period_ns": 10, "output_clock_period_ns": spec.output_period_ns,
                   "payload_byte_qualifiers": "all_bytes_valid",
                   "prepared_additional_transfers": len(frames) - len(generation.cases),
                   "expected_packet_boundaries": sum(value for f in expected for name, value in f.items()
                                                       if name == "tlast" or name.endswith("_tlast")),
                   "output_branch_count": getattr(spec, "branch_count", 1),
                   "checked_output_transfers": len(frames) * getattr(spec, "branch_count", 1),
                   "input_payload_width": spec.width,
                   "output_payload_width": sum(p.width for p in spec.sink_payload),
                   "sequence_coverage": "see_protocol_summary_not_measured_as_percentage",
                   **({"reference_contract": dict(reference_contract)} if reference_contract else {})}
        paths["schedule"].write_text(json.dumps({
            **metrics, "mapping_kind": "accepted_transaction", "timing_mode": case.verification.timing_mode,
            "gaps_before_vector": [max(row) for row in gaps], "selected_vector_indices": selected_indices,
            **({"gaps_by_lane": gaps, "base_gaps_before_vector": schedule.gaps} if source_timing else {}),
            "transaction_vector_indices": list(range(len(frames))),
        }, indent=2) + "\n")
        outputs = {"actual_output", "accepted_input", "protocol_events", "protocol_summary"}
        for name in outputs:
            paths[name].unlink(missing_ok=True)
        paths["testbench"].write_text((renderer or render_testbench)(spec, paths, len(frames),
                                                      case.verification.max_gap_cycles, initial_stall))
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "output_layout": binary_output_layout((p.name, p.width) for p in spec.sink_payload),
            "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(frames),
                             "generation": generation.as_dict(), "schedule": metrics},
            "generated_ip": metadata, "artifacts": {name: str(path.resolve()) for name, path in paths.items()},
            "artifact_sha256": {name: sha256_file(path) for name, path in paths.items() if name not in outputs},
        }, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"], paths["expected_output"],
                                  paths["actual_output"], manifest, len(frames), metrics)


def signal_wiring(spec):
    signals, mappings, assignments, captures = [], [], [], []
    source = getattr(spec, "input_prefix", "s_axis")
    sink = getattr(spec, "output_prefix", "m_axis")
    for prefix, ports in (("s", spec.payload), ("m", spec.sink_payload)):
        left = sum(port.width for port in ports) - 1
        for port in ports:
            kind = "std_logic" if port.scalar else f"std_logic_vector({port.width - 1} downto 0)"
            initial = "'0'" if port.scalar else "(others => '0')"
            part = str(left) if port.scalar else f"{left} downto {left - port.width + 1}"
            signals.append(f"  signal {prefix}_{port.name} : {kind} := {initial};")
            mappings.append(f"{source if prefix == 's' else sink}_{port.name} => {prefix}_{port.name}")
            if prefix == "s":
                assignments.append(f"      s_{port.name} <= stimulus({part});")
            else:
                captures.append(f"      actual({part}) := m_{port.name};")
            left -= port.width
    mappings.extend(f"{name} => {signal}" for name, signal in
                    ((spec.input_clock, "s_clk"), (spec.input_reset, "resetn")) if name)
    mappings.extend((f"{source}_tvalid => s_valid", f"{source}_tready => s_ready",
                     f"{sink}_tvalid => m_valid", f"{sink}_tready => m_ready"))
    if spec.output_clock:
        mappings.append(f"{spec.output_clock} => m_clk")
    if spec.output_reset:
        mappings.append(f"{spec.output_reset} => resetn")
    return {"signals": "\n".join(signals), "mappings": ",\n      ".join(mappings),
            "assignments": "\n".join(assignments), "captures": "\n".join(captures)}


def render_testbench(spec, paths, count, max_gap, initial_stall, *, scoreboard=None, extra=None):
    templates = Path(__file__).parent / "templates"
    output_clock = (f"m_clk <= not m_clk after {spec.output_period_ns // 2} ns;"
                    if spec.output_clock else "m_clk <= not m_clk after 5 ns;")
    timeout = 1000 + initial_stall * spec.output_period_ns + (
        count + 1024) * (max_gap + 32 + 2 * (spec.transfer_interval_cycles - 1)) * max(10, spec.output_period_ns)
    values = {**signal_wiring(spec), "width": spec.width, "count": count,
        "output_width": sum(p.width for p in spec.sink_payload),
        "initial_stall": initial_stall, "output_clock": output_clock, "timeout_ns": timeout,
        "drain_cycles": spec.drain_cycles,
        **{name + "_path": str(path.resolve()).replace('"', '""') for name, path in paths.items()},
        **(extra or {})}
    body = scoreboard or (templates / "scoreboard_transparent.vhd.tpl").read_text()
    values["scoreboard"] = Template(body).substitute(values)
    return Template((templates / "tb_stream_selfcheck.vhd.tpl").read_text()).substitute(values)
