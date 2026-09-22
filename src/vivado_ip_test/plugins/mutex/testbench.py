import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestbenchArtifacts
from vivado_ip_test.infrastructure import sha256_file
from vivado_ip_test.plugins.common.cycle import CycleSpec, Port
from vivado_ip_test.plugins.common.metadata import load_metadata
from vivado_ip_test.plugins.mutex.reference import MutexModel, MutexPlan


EXPECTED_EVENTS = (
    "RESET_READY", "PORT0_ACQUIRE", "CROSS_PORT_VISIBLE", "FOREIGN_OWNER_BLOCKED",
    "PROTECTION_RULE", "USER_SHARED", "LAST_MUTEX", "SIMULTANEOUS_PRIORITY",
    "RESET_CLEARS",
)


class MutexTestbenchBackend:
    def __init__(self, layout):
        self._layout = layout
        self._template = Path(__file__).parent / "templates/tb_mutex_selfcheck.vhd.tpl"

    @staticmethod
    def metadata_spec(plan):
        inputs, outputs = [], []
        for index in range(plan.num_interfaces):
            prefix = f"S{index}_AXI_"
            inputs.extend((
                Port(prefix + "ARESETN", scalar=True), Port(prefix + "AWADDR", 32),
                Port(prefix + "AWVALID", scalar=True), Port(prefix + "WDATA", 32),
                Port(prefix + "WSTRB", 4), Port(prefix + "WVALID", scalar=True),
                Port(prefix + "BREADY", scalar=True), Port(prefix + "ARADDR", 32),
                Port(prefix + "ARVALID", scalar=True), Port(prefix + "RREADY", scalar=True),
            ))
            outputs.extend((
                Port(prefix + "AWREADY", scalar=True), Port(prefix + "WREADY", scalar=True),
                Port(prefix + "BRESP", 2), Port(prefix + "BVALID", scalar=True),
                Port(prefix + "ARREADY", scalar=True), Port(prefix + "RDATA", 32),
                Port(prefix + "RRESP", 2), Port(prefix + "RVALID", scalar=True),
            ))
        settings = {
            "C_NUM_AXI": plan.num_interfaces,
            "C_NUM_MUTEX": plan.num_mutexes,
            "C_ENABLE_USER": int(plan.enable_user),
            "C_ENABLE_HW_PROT": int(plan.hardware_protection),
            "C_ASYNC_CLKS": 0,
        }
        models = {
            **settings, "C_OWNER_ID_WIDTH": 8, "C_NUM_SYNC_FF": 2,
            **{f"C_S{i}_AXI_ADDR_WIDTH": 32 for i in range(plan.num_interfaces)},
            **{f"C_S{i}_AXI_DATA_WIDTH": 32 for i in range(plan.num_interfaces)},
        }
        return CycleSpec(
            inputs=tuple(inputs), outputs=tuple(outputs), settings=settings,
            model_parameters=models, model_factory=lambda: None,
            clock="S0_AXI_ACLK",
            clock_aliases=tuple(f"S{i}_AXI_ACLK" for i in range(1, plan.num_interfaces)),
        )

    @staticmethod
    def _port_map(count):
        rows = []
        mappings = {
            "ACLK": "aclk", "ARESETN": "aresetn", "AWADDR": "awaddr",
            "AWVALID": "awvalid", "AWREADY": "awready", "WDATA": "wdata",
            "WSTRB": "wstrb", "WVALID": "wvalid", "WREADY": "wready",
            "BRESP": "bresp", "BVALID": "bvalid", "BREADY": "bready",
            "ARADDR": "araddr", "ARVALID": "arvalid", "ARREADY": "arready",
            "RDATA": "rdata", "RRESP": "rresp", "RVALID": "rvalid",
            "RREADY": "rready",
        }
        for index in range(count):
            for suffix, signal in mappings.items():
                actual = "aclk" if suffix == "ACLK" else f"{signal}({index})"
                rows.append(f"      S{index}_AXI_{suffix} => {actual}")
        return ",\n".join(rows)

    @staticmethod
    def _all_port_calls(count, operation):
        return "\n".join(
            f"    {operation}({index});" for index in range(count)
        )

    def generate(self, case):
        run = self._layout.case_run_dir(case)
        plan = MutexPlan.from_parameters(case.parameters)
        spec = self.metadata_spec(plan)
        xci_path, metadata = load_metadata(run, spec, "mutex", "2.1")
        model = MutexModel(plan.num_interfaces, plan.num_mutexes,
                           plan.enable_user, plan.hardware_protection)
        model.write_mutex(0, 0, 0x25)
        model.write_mutex(1, 0, 0x24)
        protection_value = model.read_mutex(0, 0)
        paths = {
            "state_plan": run / "vectors/state_plan.json",
            "expected_output": run / "vectors/expected_output.txt",
            "actual_output": run / "outputs/actual_output.txt",
            "testbench": run / "tb/tb_mutex_selfcheck.vhd",
        }
        for directory in (run / "vectors", run / "outputs", run / "tb"):
            directory.mkdir(parents=True, exist_ok=True)
        paths["state_plan"].write_text(json.dumps(plan.as_dict(), indent=2) + "\n")
        paths["expected_output"].write_text("\n".join(EXPECTED_EVENTS) + "\n")
        paths["actual_output"].unlink(missing_ok=True)
        paths["testbench"].write_text(Template(self._template.read_text()).substitute(
            interface_count=plan.num_interfaces,
            last_interface=plan.num_interfaces - 1,
            last_mutex_address=(plan.num_mutexes - 1) * 256,
            multiple_mutexes="true" if plan.num_mutexes > 1 else "false",
            protection_value=f'{protection_value:08X}',
            user_enabled="true" if plan.enable_user else "false",
            port_map=self._port_map(plan.num_interfaces),
            initial_setup=(
                "\n".join((
                    "    axi_write(0, 0, x\"00000000\");",
                    f"    axi_write(0, {(plan.num_mutexes - 1) * 256}, x\"00000000\");",
                    "    if C_USER_ENABLED then axi_write(0, 4, x\"00000000\"); end if;",
                )) if plan.num_mutexes > 1 else ""
            ),
            reset_read_calls=self._all_port_calls(plan.num_interfaces, "check_initial_port"),
            visible_read_calls=self._all_port_calls(plan.num_interfaces, "check_owner_port"),
            competition_drives="\n".join(
                f"    awaddr({i}) <= (others => '0'); wdata({i}) <= std_logic_vector(to_unsigned({2*i+3}, 32));\n"
                f"    wstrb({i}) <= (others => '1'); awvalid({i}) <= '1'; wvalid({i}) <= '1'; bready({i}) <= '1';"
                for i in range(plan.num_interfaces)),
            actual_path=str(paths["actual_output"].resolve()).replace('"', '""'),
        ))
        manifest_path = run / "manifest.json"
        manifest = {
            "schema_version": 1, "case_id": case.case_id, "ip_type": case.ip_type,
            "vendor": case.vendor, "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {**case.verification.as_dict(), "total_vectors": len(EXPECTED_EVENTS),
                             "reference_contract": plan.as_dict()},
            "generated_ip": metadata,
            "artifacts": {"xci": str(xci_path.resolve()),
                          **{name: str(path.resolve()) for name, path in paths.items()}},
            "artifact_sha256": {"xci": sha256_file(xci_path),
                                **{name: sha256_file(path) for name, path in paths.items()
                                   if name != "actual_output"}},
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        return TestbenchArtifacts(
            testbench_path=paths["testbench"], input_path=paths["state_plan"],
            expected_path=paths["expected_output"], actual_path=paths["actual_output"],
            manifest_path=manifest_path, vector_count=len(EXPECTED_EVENTS),
            metrics={"checked_interfaces": plan.num_interfaces,
                     "checked_mutexes": min(plan.num_mutexes, 2),
                     "reference_contract": plan.as_dict()},
        )
