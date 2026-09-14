import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestCase, TestbenchArtifacts
from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.multiplier.metadata import (
    MultiplierMetadata,
    load_multiplier_metadata,
)
from vivado_ip_test.plugins.multiplier.reference import encode_fixed_width
from vivado_ip_test.plugins.multiplier.vectors import generate_vectors
from vivado_ip_test.strategies import StrategyRegistry
from vivado_ip_test.services.stimulus_schedule import build_schedule


class MultiplierTestbenchBackend:
    def __init__(
        self,
        layout: RepositoryLayout,
        strategy_registry: StrategyRegistry,
    ) -> None:
        self._layout = layout
        self._strategy_registry = strategy_registry
        self._template_path = (
            Path(__file__).parent
            / "templates"
            / "tb_multiplier_selfcheck.vhd.tpl"
        )

    def generate(self, case: TestCase) -> TestbenchArtifacts:
        run_dir = self._layout.case_run_dir(case)
        xci_path, metadata = load_multiplier_metadata(run_dir)
        self._validate_metadata(case, metadata)
        vectors, generation = generate_vectors(
            a_width=metadata.a_width,
            b_width=metadata.b_width,
            a_type=metadata.a_type,
            b_type=metadata.b_type,
            output_width=metadata.output_width,
            profile=case.verification,
            strategy_registry=self._strategy_registry,
        )
        schedule = build_schedule(len(vectors), case.verification, can_idle=False)

        tb_dir = run_dir / "tb"
        vector_dir = run_dir / "vectors"
        output_dir = run_dir / "outputs"
        for directory in (tb_dir, vector_dir, output_dir):
            directory.mkdir(parents=True, exist_ok=True)

        input_path = vector_dir / "input_vectors.txt"
        expected_path = vector_dir / "expected_output.txt"
        vector_manifest_path = vector_dir / "vectors.json"
        actual_path = output_dir / "actual_output.txt"
        testbench_path = tb_dir / "tb_multiplier_selfcheck.vhd"
        manifest_path = run_dir / "manifest.json"
        schedule_path = vector_dir / "schedule.json"
        schedule_path.write_text(json.dumps({
            **schedule.metrics(), "timing_mode": case.verification.timing_mode,
            "gaps_before_vector": schedule.gaps,
            "transaction_vector_indices": schedule.transaction_indices,
        }, indent=2) + "\n")

        input_lines = []
        expected_lines = []
        vector_records = []
        for vector in vectors:
            a_bits = self._bits(vector.a, metadata.a_width)
            b_bits = self._bits(vector.b, metadata.b_width)
            output_bits = self._bits(vector.packed_output, metadata.output_width)
            input_lines.append(f"{a_bits} {b_bits}")
            expected_lines.append(output_bits)
            vector_records.append(
                {
                    "a": vector.a,
                    "b": vector.b,
                    "product": vector.product,
                    "packed_output": output_bits,
                }
            )

        input_path.write_text("\n".join(input_lines[index] for index in schedule.transaction_indices) + "\n")
        expected_path.write_text("\n".join(expected_lines[index] for index in schedule.transaction_indices) + "\n")
        vector_manifest_path.write_text(
            json.dumps(vector_records, indent=2, ensure_ascii=False) + "\n"
        )
        if actual_path.exists():
            actual_path.unlink()

        transaction_count = len(schedule.transaction_indices)
        timeout_cycles = schedule.input_cycles + metadata.latency + 20
        testbench_path.write_text(
            Template(self._template_path.read_text()).substitute(
                a_width=metadata.a_width,
                b_width=metadata.b_width,
                output_width=metadata.output_width,
                latency=metadata.latency,
                vector_count=transaction_count,
                timeout_cycles=timeout_cycles,
                input_path=input_path.resolve(),
                expected_path=expected_path.resolve(),
                actual_path=actual_path.resolve(),
            )
        )

        manifest = {
            "schema_version": 1,
            "case_id": case.case_id,
            "ip_type": case.ip_type,
            "vendor": case.vendor,
            "ip_name": case.ip_name,
            "configured_parameters": dict(case.parameters),
            "verification": {
                **case.verification.as_dict(),
                "total_vectors": transaction_count,
                "generation": generation.as_dict(),
                "schedule": schedule.metrics(),
            },
            "generated_ip": metadata.as_dict(),
            "artifacts": {
                "xci": str(xci_path.resolve()),
                "testbench": str(testbench_path.resolve()),
                "input_vectors": str(input_path.resolve()),
                "expected_output": str(expected_path.resolve()),
                "actual_output": str(actual_path.resolve()),
                "schedule": str(schedule_path.resolve()),
            },
            "artifact_sha256": {
                "xci": sha256_file(xci_path),
                "testbench": sha256_file(testbench_path),
                "input_vectors": sha256_file(input_path),
                "expected_output": sha256_file(expected_path),
                "vectors": sha256_file(vector_manifest_path),
                "schedule": sha256_file(schedule_path),
            },
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )

        return TestbenchArtifacts(
            testbench_path=testbench_path,
            input_path=input_path,
            expected_path=expected_path,
            actual_path=actual_path,
            manifest_path=manifest_path,
            vector_count=transaction_count,
            metrics={**generation.as_dict(), **schedule.metrics()},
        )

    @staticmethod
    def _bits(value: int, width: int) -> str:
        return format(encode_fixed_width(value, width), f"0{width}b")

    @staticmethod
    def _validate_metadata(case: TestCase, metadata: MultiplierMetadata) -> None:
        expected = case.parameters
        if metadata.a_width != expected["a_width"]:
            raise PluginError("XCI 的 A 端口位宽与配置不一致")
        if metadata.b_width != expected["b_width"]:
            raise PluginError("XCI 的 B 端口位宽与配置不一致")
        if metadata.a_type != expected["a_type"]:
            raise PluginError("XCI 的 A 端口符号类型与配置不一致")
        if metadata.b_type != expected["b_type"]:
            raise PluginError("XCI 的 B 端口符号类型与配置不一致")
        if metadata.latency != expected["pipeline_stages"]:
            raise PluginError("XCI 的流水线时延与配置不一致")
        if metadata.output_low != 0:
            raise PluginError("当前 Multiplier 后端只支持完整精度输出")
        if metadata.output_width != metadata.a_width + metadata.b_width:
            raise PluginError("Multiplier 输出位宽不是完整乘积位宽")
