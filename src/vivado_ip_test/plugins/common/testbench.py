import json
from contextlib import ExitStack
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.infrastructure.json_values import with_hex_large_integers
from vivado_ip_test.plugins.common.cycle import DefinedBits
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.vectors import cycle_space
from vivado_ip_test.services.stimulus_schedule import build_schedule


def build_cycles(spec, vectors, profile):
    schedule = build_schedule(len(vectors), profile, can_idle=True)
    cycles = []

    def append(frame, phase, vector_index=None):
        if set(frame) != {port.name for port in spec.inputs}:
            raise ValueError("周期输入端口不匹配")
        if any(type(frame[port.name]) is not int or not 0 <= frame[port.name] <= port.limit
               for port in spec.inputs):
            raise ValueError("周期输入超出端口范围")
        cycles.append({"inputs": frame, "phase": phase, "vector_index": vector_index})

    for values in spec.prefix() if callable(spec.prefix) else spec.prefix:
        append(spec.frame(values), "directed_sequence")
    previous = spec.frame()
    for gap, index in zip(schedule.gaps, schedule.transaction_indices):
        for _ in range(gap):
            append(spec.idle(previous), "gap")
        previous = dict(zip((port.name for port in spec.inputs), vectors[index]))
        append(previous, "generated", index)
    for values in spec.suffix() if callable(spec.suffix) else spec.suffix:
        append(spec.frame(values), "directed_suffix")
    for _ in range(spec.flush_cycles):
        append(spec.frame(), "flush")
    return cycles, schedule


def packed(frame, ports):
    return "".join(format(frame[port.name], f"0{port.width}b") for port in ports)


def normalize_expected(spec, expected):
    if set(expected) != {port.name for port in spec.outputs}:
        raise ValueError("Reference output ports do not match the specification")
    values, masks, reasons = {}, {}, {}
    for port in spec.outputs:
        result = expected[port.name]
        if isinstance(result, DefinedBits):
            if not spec.masked_outputs or not isinstance(result.reason, str) or not result.reason:
                raise ValueError("Undefined output bits need an enabled mask and an explicit reason")
            value, mask = result.value, result.mask
            if mask != port.limit:
                reasons[port.name] = {"mask": mask, "reason": result.reason}
        else:
            value, mask = result, port.limit
        if any(type(v) is not int or not 0 <= v <= port.limit for v in (value, mask)):
            raise ValueError("Reference output or mask is outside the port width")
        values[port.name], masks[port.name] = value, mask
    return values, masks, reasons


class CycleTestbenchBackend:
    def __init__(self, layout, registry):
        self._layout = layout
        self._registry = registry

    def generate(self, case, spec, ip_name, version):
        run = self._layout.case_run_dir(case)
        design_path, metadata = load_metadata(run, spec, ip_name, version)
        generation = self._registry.generate(
            cycle_space(spec, case.verification.boundary_mode == "systematic"), case.verification)
        cycles, schedule = build_cycles(spec, generation.cases, case.verification)
        for directory in ("tb", "vectors", "outputs"):
            (run / directory).mkdir(parents=True, exist_ok=True)
        paths = {"input_vectors": run / "vectors/input_vectors.txt",
                 "expected_output": run / "vectors/expected_output.txt",
                 "actual_output": run / "outputs/actual_output.txt",
                 "vectors": run / "vectors/vectors.json", "cycles": run / "vectors/cycles.json",
                 "schedule": run / "vectors/schedule.json",
                 "testbench": run / "tb/tb_cycle_selfcheck.vhd",
                 "block_design" if spec.inline_bd_glob else "xci": design_path}
        if spec.masked_outputs:
            paths["expected_mask"] = run / "vectors/expected_mask.txt"
        if set(paths) & set(spec.supporting_artifacts):
            raise ValueError("Supporting artifact names must not replace standard artifacts")
        paths.update(spec.supporting_artifacts)
        metrics = {**generation.as_dict(), **schedule.metrics(),
                   "checked_transaction_count": len(cycles), "input_cycles": len(cycles),
                   "directed_sequence_cycles": sum(c["phase"] == "directed_sequence" for c in cycles),
                   "flush_cycles": spec.flush_cycles,
                   "directed_suffix_cycles": sum(c["phase"] == "directed_suffix" for c in cycles),
                   "comparison_kind": "post_edge_cycle" if spec.clock else "combinational",
                   "sequence_coverage": "not_measured"}
        model = spec.model_factory()
        defined = {port.name: 0 for port in spec.outputs}
        masked_reasons = {}
        fully_masked_cycles = 0
        with ExitStack() as stack:
            inputs = stack.enter_context(paths["input_vectors"].open("w"))
            outputs = stack.enter_context(paths["expected_output"].open("w"))
            masks_file = stack.enter_context(paths["expected_mask"].open("w")) if spec.masked_outputs else None
            for cycle in cycles:
                frame = cycle["inputs"]
                expected, masks, reasons = normalize_expected(spec, model.step(frame))
                fully_masked_cycles += int(not any(masks.values()))
                for port in spec.outputs:
                    defined[port.name] += masks[port.name].bit_count()
                if reasons:
                    cycle["undefined_outputs"] = reasons
                    for port, reason in reasons.items():
                        key = f"{port}:{reason['reason']}"
                        masked_reasons[key] = masked_reasons.get(key, 0) + 1
                inputs.write(packed(frame, spec.inputs) + "\n")
                outputs.write(packed(expected, spec.outputs) + "\n")
                if masks_file is not None:
                    masks_file.write(packed(masks, spec.outputs) + "\n")
        if not all(defined.values()):
            raise ValueError(f"No defined bits were checked on output ports: {[k for k, v in defined.items() if not v]}")
        metrics.update({"defined_output_bits_by_port": defined, "masked_reason_cycles": masked_reasons,
                        "fully_masked_cycles": fully_masked_cycles,
                        "checked_transaction_count": len(cycles) - fully_masked_cycles,
                        "masked_output_bits": len(cycles) * sum(p.width for p in spec.outputs) - sum(defined.values())})
        if not spec.inputs and not spec.clock:
            metrics.update({"comparison_kind": "constant_observation", "input_space_kind": "no_external_inputs",
                            "checked_transaction_count": 0, "checked_output_samples": len(cycles)})
        if hasattr(model, "event_counts"):
            metrics["reference_sequence_events"] = dict(model.event_counts)
        paths["vectors"].write_text(json.dumps(with_hex_large_integers([
            dict(zip((port.name for port in spec.inputs), row)) for row in generation.cases
        ]), indent=2) + "\n")
        paths["cycles"].write_text(json.dumps(with_hex_large_integers(cycles), indent=2) + "\n")
        paths["schedule"].write_text(json.dumps({
            **metrics, "mapping_kind": "sampled_cycle", "timing_mode": case.verification.timing_mode,
            "gaps_before_vector": schedule.gaps,
            "transaction_vector_indices": [cycle["vector_index"] for cycle in cycles],
        }, indent=2) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(spec, paths, len(cycles)))
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({
            "schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "numeric_value_encoding": "integer_or_hex:1.0",
            "output_layout": binary_output_layout((p.name, p.width) for p in spec.outputs),
            "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(cycles),
                             "generation": generation.as_dict(), "schedule": metrics},
            "generated_ip": metadata, "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"},
        }, indent=2) + "\n")
        return TestbenchArtifacts(
            testbench_path=paths["testbench"], input_path=paths["input_vectors"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest, vector_count=len(cycles), metrics=metrics)


def render_testbench(spec, paths, count):
    signals, assignments, mappings, captures = [], [], [], []
    for direction, ports in (("in", spec.inputs), ("out", spec.outputs)):
        left = sum(port.width for port in ports) - 1
        for port in ports:
            signal = f"p_{port.name}"
            kind = "std_logic" if port.scalar else f"std_logic_vector({port.width - 1} downto 0)"
            initial = "'0'" if port.scalar else "(others => '0')"
            signals.append(f"  signal {signal} : {kind} := {initial};")
            mappings.append(f"{port.name} => {signal}")
            part = str(left) if port.scalar else f"{left} downto {left - port.width + 1}"
            if direction == "in":
                assignments.append(f"      {signal} <= stimulus({part});")
            else:
                captures.append(f"      actual({part}) := {signal};")
            left -= port.width
    if spec.clock:
        mappings.append(f"{spec.clock} => clk")
    mappings.extend(f"{clock} => clk" for clock in spec.clock_aliases)
    mask_declaration = mask_read = mask_end = ""
    comparison = "not is_x(actual) and actual = expected"
    if spec.masked_outputs:
        mask_path = str(paths["expected_mask"].resolve()).replace('"', '""')
        mask_declaration = f'    file masks_file : text open read_mode is "{mask_path}";'
        mask_read = '''      assert not endfile(masks_file)
        report "CYCLE_SELF_CHECK_STATUS: FAIL missing output mask" severity failure;
      readline(masks_file, mask_line);
      read_binary(mask_line, expected_mask);
      assert not is_x(expected_mask)
        report "CYCLE_SELF_CHECK_STATUS: FAIL invalid output mask" severity failure;'''
        mask_end = " and endfile(masks_file)"
        comparison = "not is_x(actual and expected_mask) and (actual and expected_mask) = (expected and expected_mask)"
    input_width = sum(port.width for port in spec.inputs)
    stimulus_declaration = f"    variable stimulus : std_logic_vector({input_width - 1} downto 0);" if input_width else ""
    stimulus_read = "      read_binary(input_line, stimulus);" if input_width else '''      assert input_line.all'length = 0
        report "CYCLE_SELF_CHECK_STATUS: FAIL unexpected data for inputless DUT" severity failure;'''
    return Template((Path(__file__).parent / "templates/tb_cycle_selfcheck.vhd.tpl").read_text()).substitute(
        signals="\n".join(signals), mappings=",\n      ".join(mappings),
        assignments="\n".join(assignments), captures="\n".join(captures),
        stimulus_declaration=stimulus_declaration, stimulus_read=stimulus_read,
        output_width=sum(port.width for port in spec.outputs), count=count,
        timeout_ns=200 + (count + 10) * 10,
        mask_declaration=mask_declaration, mask_read=mask_read, mask_end=mask_end, comparison=comparison,
        input_path=str(paths["input_vectors"].resolve()).replace('"', '""'),
        expected_path=str(paths["expected_output"].resolve()).replace('"', '""'),
        actual_path=str(paths["actual_output"].resolve()).replace('"', '""'))
