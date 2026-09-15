from collections import Counter
from dataclasses import replace
import json
import random

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.common.axilite.render import render_testbench
from vivado_ip_test.plugins.common.axilite.spec import Action
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.testbench import normalize_expected, packed
from vivado_ip_test.plugins.common.vectors import port_space
from vivado_ip_test.services.stimulus_schedule import build_schedule


def write_operations(run, spec, operations, profile):
    if not operations:
        raise ValueError("AXI-Lite operation sequence must not be empty")
    paths = {name: run / relative for name, relative in {
        "input_vectors": "vectors/input_vectors.txt", "expected_output": "vectors/expected_output.txt",
        "expected_mask": "vectors/expected_mask.txt", "actual_output": "outputs/actual_output.txt",
        "accepted_input": "outputs/accepted_input.txt", "protocol_events": "outputs/axi_events.txt",
        "mismatches": "outputs/mismatches.txt",
        "protocol_summary": "outputs/protocol_summary.txt", "timing": "vectors/timing.txt",
        "vectors": "vectors/vectors.json", "schedule": "vectors/schedule.json",
        "testbench": "tb/tb_axilite_selfcheck.vhd"}.items()}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    schedule = build_schedule(len(operations), replace(profile, input_order="generated"), can_idle=True)
    rng = random.Random(f"axilite-response:1.0:{profile.random_seed}")
    holds = [(0, 1, 2, 7, 16, 32)[i % 6] if i < 96 else rng.randrange(33)
             for i in range(len(operations))]
    model = spec.model_factory()
    defined = Counter({port.name: 0 for port in spec.observation.outputs})
    reasons, actions, strobes, addresses = Counter(), Counter(), Counter(), Counter()
    fully_masked = 0
    trace = []
    with paths["input_vectors"].open("w") as inp, paths["expected_output"].open("w") as out, \
            paths["expected_mask"].open("w") as masks:
        for op in operations:
            command = op["command"]
            spec.validate_command(command)
            action = Action(command["action"])
            values, mask, undefined = normalize_expected(spec.observation, model.step(command))
            fully_masked += int(not any(mask.values()))
            defined.update({name: value.bit_count() for name, value in mask.items()})
            reasons.update(f"{name}:{reason['reason']}" for name, reason in undefined.items())
            actions[action.name.lower()] += 1
            if action in (Action.WRITE, Action.READ):
                addresses[f"{action.name.lower()}:0x{command['address']:03x}"] += 1
            if action == Action.WRITE:
                strobes[f"0x{command['strobe']:x}"] += 1
            trace.append({**op, "undefined_outputs": undefined})
            inp.write(packed(command, spec.command_ports) + "\n")
            out.write(packed(values, spec.observation.outputs) + "\n")
            masks.write(packed(mask, spec.observation.outputs) + "\n")
    if not all(defined.values()):
        raise ValueError(f"AXI-Lite sequence never checks some observations: {dict(defined)}")
    paths["timing"].write_text("".join(f"{gap} {hold}\n" for gap, hold in zip(schedule.gaps, holds)))
    paths["vectors"].write_text(json.dumps(trace, indent=2) + "\n")
    metrics = {"simulation_mode": "behavioral", "comparison_kind": "axi_lite_register_sequence",
        "command_count": len(operations), "checked_transaction_count": len(operations)-fully_masked,
        "planned_actions": dict(actions), "planned_register_accesses": dict(addresses),
        "planned_write_strobes": dict(strobes), "gap_cycles": sum(schedule.gaps),
        "max_observed_gap": max(schedule.gaps), "schedule_version": "1.0",
        "response_delay_pattern": "axilite_after_valid:1.0", "maximum_response_hold_cycles": max(holds),
        "settle_cycles_per_operation": spec.settle_cycles, "reset_cycles_per_operation": spec.reset_cycles,
        "masked_reason_operations": dict(reasons), "fully_masked_operations": fully_masked,
        "defined_output_bits_by_port": dict(defined),
        "reference_sequence_events": dict(getattr(model, "event_counts", {})),
        "sequence_coverage": "directed_operations_and_protocol_counts_not_state_percentage"}
    if spec.window:
        metrics.update(clock_window_control=spec.window.control,
            requested_running_cycles=sum(op['command']['run_cycles'] for op in operations),
            clock_window_count=actions['window'],
            pulse_observations={pulse.port: {'active': pulse.active, 'counting': 'active_clock_edges'}
                                for pulse in spec.pulses})
    paths["schedule"].write_text(json.dumps({**metrics, "mapping_kind": "register_operation",
        "transaction_vector_indices": list(range(len(operations))),
        "timing_mode": profile.timing_mode, "gaps": schedule.gaps, "response_holds": holds}, indent=2) + "\n")
    for path in paths.values():
        if path.is_relative_to(run / "outputs"):
            path.unlink(missing_ok=True)
    paths["testbench"].write_text(render_testbench(spec, paths, len(operations), max(schedule.gaps), actions))
    return paths, metrics


class AxiLiteTestbenchBackend:
    def __init__(self, layout, registry):
        self._layout, self._registry = layout, registry

    def generate(self, case, spec, ip_name, version):
        run = self._layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, ip_name, version)
        revision = int(json.loads(xci.read_text())["ip_inst"]["ip_revision"])
        if revision < spec.minimum_ip_revision:
            raise ValueError(f"This reference requires IP revision >= {spec.minimum_ip_revision}, found {revision}")
        metadata["ip_revision"] = revision
        generation = self._registry.generate(
            port_space(spec.generated_ports, case.verification.boundary_mode == "systematic"), case.verification)
        selection = build_schedule(len(generation.cases), case.verification, can_idle=True)
        samples = [dict(zip((p.name for p in spec.generated_ports), generation.cases[index]))
                   for index in selection.transaction_indices]
        operations = spec.prepare_operations(samples)
        paths, schedule_metrics = write_operations(run, spec, operations, case.verification)
        paths.update(xci=xci, numeric_samples=run / "vectors/numeric_samples.json")
        changelogs = list(run.glob(f"proj/*.gen/sources_1/ip/dut_0/doc/{ip_name}_v{version.replace('.', '_')}_changelog.txt"))
        if changelogs:
            if len(changelogs) != 1:
                raise ValueError("Expected one IP change log")
            paths["ip_changelog"] = changelogs[0]
        paths["numeric_samples"].write_text(json.dumps(samples, indent=2) + "\n")
        metrics = {**generation.as_dict(), **schedule_metrics,
                   "minimum_ip_revision": spec.minimum_ip_revision, "ip_revision": revision,
                   "numeric_coverage_scope": "generated_fields_not_register_state_or_operation_sequences"}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "output_layout": binary_output_layout((p.name, p.width) for p in spec.observation.outputs),
            "vendor": case.vendor, "ip_name": case.ip_name, "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(operations),
                             "generation": generation.as_dict(), "schedule": schedule_metrics},
            "generated_ip": metadata, "artifacts": {k: str(p.resolve()) for k, p in paths.items()},
            "artifact_sha256": {k: sha256_file(p) for k, p in paths.items()
                                if not p.is_relative_to(run / "outputs")}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"], paths["expected_output"],
                                  paths["actual_output"], manifest, len(operations), metrics)
