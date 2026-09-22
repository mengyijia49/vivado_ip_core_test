import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.infrastructure.output_layout import binary_output_layout
from vivado_ip_test.plugins.axi_lmb_bridge.reference import AxiLmbBridgeReference
from vivado_ip_test.plugins.axi_lmb_bridge.vectors import prepare_operations
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.common.vectors import port_space


OUTPUT_FIELDS = (("kind", 1), ("id", None), ("data", None), ("resp", 2), ("last", 1))


def packed_output(row, parameters):
    widths = (1, parameters["id_width"], parameters["data_width"], 2, 1)
    return "".join(format(row[name], f"0{width}b")
                   for (name, _), width in zip(OUTPUT_FIELDS, widths))


def vhdl_nat_array(name, values):
    return f"  constant {name} : natural_array(0 to {len(values)-1}) := (" + \
        ", ".join(str(value) for value in values) + ");"


def vhdl_slv_array(name, values, width, type_name):
    items = ", ".join(f'{index} => "{value:0{width}b}"' for index, value in enumerate(values))
    return f"  constant {name} : {type_name}(0 to {len(values)-1}) := ({items});"


def operation_calls(operations, parameters):
    lines = []
    width = parameters["data_width"]
    for op in operations:
        address = f'"{op["address"]:0{parameters["address_width"]}b}"'
        common = (f"{op['id']}, {address}, {op['beats']}, {op['size']}, "
                  f"{op['burst']}, {op['prot']}, {op['fault']}, "
                  f"{op['wait_cycles']}, {op['hold_cycles']}")
        if op["kind"] == "write":
            data = f'"{op["data"] & ((1 << width)-1):0{width}b}"'
            lines.append(f"    drive_write({common}, {data}, "
                         f"{op['strobe']}, {str(op['w_before_aw']).lower()});")
        else:
            lines.append(f"    drive_read({common});")
    return "\n".join(lines)


def render_testbench(parameters, operations, accesses, output_path):
    width = parameters["data_width"]
    address_width = parameters["address_width"]
    id_width = parameters["id_width"]
    lanes = width // 8
    declarations = "\n".join((
        "  type natural_array is array(natural range <>) of natural;",
        f"  type address_array is array(natural range <>) of std_logic_vector({address_width-1} downto 0);",
        f"  type data_array is array(natural range <>) of std_logic_vector({width-1} downto 0);",
        f"  type be_array is array(natural range <>) of std_logic_vector({lanes-1} downto 0);",
        "  type protection_array is array(natural range <>) of std_logic_vector(1 downto 0);",
        vhdl_slv_array("EXPECTED_ADDR", [a["address"] for a in accesses], address_width, "address_array"),
        vhdl_nat_array("EXPECTED_READ", [a["read"] for a in accesses]),
        vhdl_nat_array("EXPECTED_WRITE", [a["write"] for a in accesses]),
        vhdl_slv_array("EXPECTED_DATA", [a["data"] for a in accesses], width, "data_array"),
        vhdl_slv_array("EXPECTED_BE", [a["be"] for a in accesses], lanes, "be_array"),
        vhdl_slv_array("EXPECTED_PROT", [a["prot"] for a in accesses], 2, "protection_array"),
    ))
    pause_signals = pause_mapping = pause_check = ""
    if parameters["use_pause"]:
        pause_signals = "  signal Pause, Pause_Ack : std_logic := '0';"
        pause_mapping = ",\n      Pause => Pause, Pause_Ack => Pause_Ack"
        pause_check = '''
    Pause <= '1';
    for i in 1 to 4 loop wait until rising_edge(Clk); end loop;
    assert Pause_Ack = '1' and S_AXI_AWREADY = '0' and S_AXI_ARREADY = '0'
      report "AXI_LMB_SELF_CHECK_STATUS: FAIL pause did not quiesce inputs" severity failure;
    Pause <= '0';
    wait until rising_edge(Clk);'''
    prot_signal = "  signal M_Prot : std_logic_vector(1 downto 0);"
    prot_mapping = ",\n      M_Prot => M_Prot"
    prot_check = ""
    if parameters["protection"]:
        prot_check = '''
        assert M_Prot = EXPECTED_PROT(access_index)
          report "AXI_LMB_SELF_CHECK_STATUS: FAIL LMB protection mismatch index=" &
            integer'image(access_index) & " actual=" & integer'image(to_integer(unsigned(M_Prot))) &
            " expected=" & integer'image(to_integer(unsigned(EXPECTED_PROT(access_index))))
            severity failure;'''
    template = Template((Path(__file__).parent / "templates/tb_axi_lmb_selfcheck.vhd.tpl").read_text())
    return template.substitute(
        data_width=width, address_width=address_width, id_width=id_width, lanes=lanes,
        declarations=declarations, access_count=len(accesses), operation_count=len(operations),
        output_path=str(output_path.resolve()).replace('"', '""'),
        pause_signals=pause_signals, pause_mapping=pause_mapping, pause_check=pause_check,
        prot_signal=prot_signal, prot_mapping=prot_mapping, prot_check=prot_check,
        frequency_protocol=int(parameters["lmb_protocol"] == "Frequency"),
        operation_calls=operation_calls(operations, parameters),
        timeout_ns=5000 + len(operations) * 1000)


class AxiLmbTestbenchBackend:
    def __init__(self, layout, registry):
        self.layout, self.registry = layout, registry

    def generate(self, case, spec, generated_ports):
        run = self.layout.case_run_dir(case)
        xci, metadata = load_metadata(run, spec, "axi_lmb_bridge", "1.0")
        generation = self.registry.generate(
            port_space(generated_ports, case.verification.boundary_mode == "systematic"),
            case.verification)
        samples = [dict(zip((port.name for port in generated_ports), row))
                   for row in generation.cases]
        operations = prepare_operations(samples, case.parameters)
        model = AxiLmbBridgeReference(case.parameters)
        accesses, outputs = model.evaluate(operations)
        paths = {name: run / path for name, path in {
            "testbench": "tb/tb_axi_lmb_selfcheck.vhd",
            "input_vectors": "vectors/operations.json",
            "expected_output": "vectors/expected_output.txt",
            "actual_output": "outputs/actual_output.txt",
            "accesses": "vectors/lmb_accesses.json",
            "samples": "vectors/numeric_samples.json"}.items()}
        for path in paths.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        paths["input_vectors"].write_text(json.dumps(operations, indent=2) + "\n")
        paths["accesses"].write_text(json.dumps(accesses, indent=2) + "\n")
        paths["samples"].write_text(json.dumps(samples, indent=2) + "\n")
        paths["expected_output"].write_text(
            "".join(packed_output(row, case.parameters) + "\n" for row in outputs))
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(render_testbench(
            case.parameters, operations, accesses, paths["actual_output"]))
        metrics = {**generation.as_dict(), "operation_count": len(operations),
            "lmb_access_count": len(accesses), "checked_transaction_count": len(outputs),
            "comparison_kind": "axi4_burst_and_lmb_access_sequence",
            "reference_sequence_events": dict(model.event_counts),
            "sequence_coverage": "directed_legal_bursts_and_generated_single_beats"}
        paths["xci"] = xci
        manifest = run / "manifest.json"
        fields = tuple((name, case.parameters["id_width"] if name == "id" else
                        case.parameters["data_width"] if name == "data" else width)
                       for name, width in OUTPUT_FIELDS)
        manifest.write_text(json.dumps({"schema_version": 1, "case_id": case.case_id,
            "ip_type": case.ip_type, "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters), "generated_ip": metadata,
            "output_layout": binary_output_layout(fields),
            "verification": {**case.verification.as_dict(), "generation": generation.as_dict(),
                             "schedule": metrics},
            "artifacts": {key: str(path.resolve()) for key, path in paths.items()},
            "artifact_sha256": {key: sha256_file(path) for key, path in paths.items()
                                if key != "actual_output"}}, indent=2) + "\n")
        return TestbenchArtifacts(paths["testbench"], paths["input_vectors"],
            paths["expected_output"], paths["actual_output"], manifest, len(outputs), metrics)
