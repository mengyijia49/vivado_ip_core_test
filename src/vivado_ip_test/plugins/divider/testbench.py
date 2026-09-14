import json
from pathlib import Path
from string import Template

from vivado_ip_test.domain import TestCase, TestbenchArtifacts
from vivado_ip_test.infrastructure import RepositoryLayout, sha256_file
from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.divider.metadata import (
    DividerMetadata,
    load_divider_metadata,
)
from vivado_ip_test.plugins.divider.reference import encode_fixed_width
from vivado_ip_test.plugins.divider.vectors import generate_vectors
from vivado_ip_test.strategies import StrategyRegistry
from vivado_ip_test.services.stimulus_schedule import build_schedule


class DividerTestbenchBackend:
    def __init__(
        self,
        layout: RepositoryLayout,
        strategy_registry: StrategyRegistry,
    ) -> None:
        self._layout = layout
        self._strategy_registry = strategy_registry
        self._template_path = (
            Path(__file__).parent / "templates" / "tb_divider_selfcheck.vhd.tpl"
        )

    def generate(self, case: TestCase) -> TestbenchArtifacts:
        run_dir = self._layout.case_run_dir(case)
        xci_path, metadata = load_divider_metadata(run_dir)
        self._validate_metadata(case, metadata)

        vectors, generation = generate_vectors(
            dividend_width=metadata.dividend_width,
            divisor_width=metadata.divisor_width,
            operand_sign=metadata.operand_sign,
            profile=case.verification,
            strategy_registry=self._strategy_registry,
        )
        schedule = build_schedule(len(vectors), case.verification, can_idle=True)
        tb_dir = run_dir / "tb"
        vector_dir = run_dir / "vectors"
        output_dir = run_dir / "outputs"
        for directory in (tb_dir, vector_dir, output_dir):
            directory.mkdir(parents=True, exist_ok=True)

        input_path = vector_dir / "input_vectors.txt"
        expected_path = vector_dir / "expected_output.txt"
        vector_manifest_path = vector_dir / "vectors.json"
        actual_path = output_dir / "actual_output.txt"
        testbench_path = tb_dir / "tb_divider_selfcheck.vhd"
        manifest_path = run_dir / "manifest.json"
        schedule_path = vector_dir / "schedule.json"
        gaps_path = vector_dir / "gaps.txt"
        gaps_path.write_text("\n".join(map(str, schedule.gaps)) + "\n")
        schedule_path.write_text(json.dumps({
            **schedule.metrics(), "timing_mode": case.verification.timing_mode,
            "gaps_before_vector": schedule.gaps,
            "transaction_vector_indices": schedule.transaction_indices,
        }, indent=2) + "\n")

        input_lines = []
        expected_lines = []
        vector_records = []
        for vector in vectors:
            dividend_bits = self._bits(vector.dividend, metadata.dividend_width)
            divisor_bits = self._bits(vector.divisor, metadata.divisor_width)
            output_bits = self._bits(vector.packed_output, metadata.dout_width)
            input_lines.append(f"{dividend_bits} {divisor_bits}")
            expected_lines.append(output_bits)
            vector_records.append(
                {
                    "dividend": vector.dividend,
                    "divisor": vector.divisor,
                    "quotient": vector.quotient,
                    "remainder": vector.remainder,
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

        timeout_cycles = schedule.input_cycles + 2 * metadata.latency + 100
        template = Template(self._template_path.read_text())
        testbench_path.write_text(
            template.substitute(
                dividend_width=metadata.dividend_width,
                divisor_width=metadata.divisor_width,
                dout_width=metadata.dout_width,
                latency=metadata.latency,
                gaps_path=gaps_path.resolve(),
                vector_count=len(vectors),
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
                "total_vectors": len(vectors),
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
                "gaps": sha256_file(gaps_path),
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
            vector_count=len(vectors),
            metrics={**generation.as_dict(), **schedule.metrics()},
        )

    @staticmethod
    def _bits(value: int, width: int) -> str:
        encoded = encode_fixed_width(value, width)
        return format(encoded, f"0{width}b")

    @staticmethod
    def _validate_metadata(
        case: TestCase,
        metadata: DividerMetadata,
    ) -> None:
        expected_dividend = case.parameters["dividend_width"]
        expected_divisor = case.parameters["divisor_width"]
        expected_sign = case.parameters["operand_sign"]
        if metadata.dividend_width != expected_dividend:
            raise PluginError("XCI 被除数位宽与配置不一致")
        if metadata.divisor_width != expected_divisor:
            raise PluginError("XCI 除数位宽与配置不一致")
        if metadata.operand_sign != expected_sign:
            raise PluginError("XCI 符号类型与配置不一致")
        if metadata.dout_width != metadata.dividend_width + metadata.divisor_width:
            raise PluginError("当前 Divider 后端不支持带填充位的输出布局")
