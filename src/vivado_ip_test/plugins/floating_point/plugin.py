from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.plugin import StreamIpPlugin
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.floating_point.reference import EXCEPTIONS, expected_transactions
from vivado_ip_test.plugins.floating_point.vectors import prepare_frames
from vivado_ip_test.plugins.floating_point.parameters import ALL_OPERATIONS, validate_format
from vivado_ip_test.plugins.floating_point.accuracy import reciprocal_tolerances, transcendental_tolerances
from vivado_ip_test.plugins.floating_point.compare.spec import describe as describe_compare
from vivado_ip_test.plugins.floating_point.compare.reference import expected_transactions as compare_reference
from vivado_ip_test.plugins.floating_point.compare.vectors import prepare_frames as prepare_compare
from vivado_ip_test.plugins.floating_point.multi_input.testbench import render_testbench as render_operands
from vivado_ip_test.plugins.floating_point.multi_input.timing import independent_gaps
from vivado_ip_test.plugins.floating_point.multi_input.vectors import USER_PATTERN
from vivado_ip_test.plugins.floating_point.arithmetic.spec import describe as describe_arithmetic
from vivado_ip_test.plugins.floating_point.arithmetic.reference import expected_transactions as arithmetic_reference
from vivado_ip_test.plugins.floating_point.arithmetic.vectors import prepare_frames as prepare_arithmetic
from vivado_ip_test.plugins.floating_point.divide.spec import describe as describe_divide
from vivado_ip_test.plugins.floating_point.divide.reference import expected_transactions as divide_reference
from vivado_ip_test.plugins.floating_point.divide.vectors import prepare_frames as prepare_divide
from vivado_ip_test.plugins.floating_point.fma.spec import describe as describe_fma
from vivado_ip_test.plugins.floating_point.fma.reference import expected_transactions as fma_reference
from vivado_ip_test.plugins.floating_point.fma.vectors import prepare_frames as prepare_fma
from vivado_ip_test.plugins.floating_point.reciprocal.spec import describe as describe_reciprocal
from vivado_ip_test.plugins.floating_point.reciprocal.reference import expected_transactions as reciprocal_reference
from vivado_ip_test.plugins.floating_point.reciprocal.vectors import prepare_frames as prepare_reciprocal
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.spec import describe as describe_reciprocal_sqrt
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.reference import expected_transactions as reciprocal_sqrt_reference
from vivado_ip_test.plugins.floating_point.reciprocal_sqrt.vectors import prepare_frames as prepare_reciprocal_sqrt
from vivado_ip_test.plugins.floating_point.transcendental.spec import describe as describe_transcendental
from vivado_ip_test.plugins.floating_point.transcendental.reference import expected_transactions as transcendental_reference
from vivado_ip_test.plugins.floating_point.transcendental.vectors import prepare_frames as prepare_transcendental


OPERATIONS = {"Absolute": "ABSOLUTE", "Float_to_float": "FLT_TO_FLT",
              "Fixed_to_float": "FIX_TO_FLT", "Float_to_fixed": "FLT_TO_FIX", "Square_root": "SQRT"}


class FloatingPointPlugin(StreamIpPlugin):
    ip_type = ip_name = "floating_point"
    version = "7.1"

    def describe(self, p):
        if p.get('operation') == 'Compare':
            return describe_compare(p)
        if p.get('operation') in {'Add_Subtract', 'Multiply'}:
            return describe_arithmetic(p)
        if p.get('operation') == 'Divide':
            return describe_divide(p)
        if p.get('operation') == 'FMA':
            return describe_fma(p)
        if p.get('operation') == 'Reciprocal':
            return describe_reciprocal(p)
        if p.get('operation') == 'Reciprocal_square_root':
            return describe_reciprocal_sqrt(p)
        if p.get('operation') in {'Exponential', 'Logarithm'}:
            return describe_transcendental(p)
        p = {"cycles_per_operation": 1, **p}
        validate_parameters(p, {"operation": OPERATIONS, "input_exponent": range(1, 65),
            "input_fraction": range(65), "output_exponent": range(1, 65), "output_fraction": range(65),
            "input_unsigned": bool, "optimization": {"Resources", "Performance"},
            "has_last": bool, "user_width": range(257),
            "cycles_per_operation": range(1, 66),
            **{"has_" + name: bool for name in EXCEPTIONS}})
        op = p["operation"]
        source_float, target_float = op != "Fixed_to_float", op != "Float_to_fixed"
        ie, ip, oe, oprec = (p[key] for key in
                            ("input_exponent", "input_fraction", "output_exponent", "output_fraction"))
        validate_format(ie, ip, source_float)
        validate_format(oe, oprec, target_float)
        if op == "Fixed_to_float" and oe < (ie + ip + 2).bit_length() + 1:
            raise PluginError("Output exponent is insufficient for fixed point input width")
        if op == "Float_to_fixed" and ie < (oe + oprec + 2).bit_length() + 1:
            raise PluginError("Input exponent is insufficient for fixed point output width")
        if p["input_unsigned"] and (op != "Fixed_to_float" or ip != 0 or ie not in (32, 64)):
            raise PluginError("Unsigned conversion is available only for Uint32 and Uint64 inputs")
        if op in {"Absolute", "Square_root"} and (ie, ip) != (oe, oprec):
            raise PluginError("Absolute value and square root must preserve the input format")
        rate = p["cycles_per_operation"]
        if rate > (ip + 1 if op == "Square_root" else 1):
            raise PluginError("Unsupported cycles per operation for the selected operation and precision")
        allowed = ({"underflow", "overflow"} if op == "Float_to_float" else
                   {"overflow", "invalid_op"} if op == "Float_to_fixed" else
                   {"invalid_op"} if op == "Square_root" else set())
        if any(p["has_" + name] and name not in allowed for name in EXCEPTIONS):
            raise PluginError("This operation does not provide the selected exception flag")
        selected = [name for name in EXCEPTIONS if p["has_" + name]]
        source_width, sink_width = ((ie + ip + 7) // 8) * 8, ((oe + oprec + 7) // 8) * 8
        user_width = p["user_width"] + len(selected)
        source, sink = [Port("tdata", source_width)], [Port("tdata", sink_width)]
        if p["has_last"]:
            source.append(Port("tlast", scalar=True))
            sink.append(Port("tlast", scalar=True))
        if p["user_width"]:
            source.append(Port("tuser", p["user_width"]))
        if user_width:
            sink.append(Port("tuser", user_width))
        settings = {"Operation_Type": op, "A_Precision_Type": f"Uint{ie}" if p["input_unsigned"] else "Custom",
            "C_A_Exponent_Width": ie, "C_A_Fraction_Width": ip, "Result_Precision_Type": "Custom",
            "C_Result_Exponent_Width": oe, "C_Result_Fraction_Width": oprec,
            "Flow_Control": "Blocking", "Axi_Optimize_Goal": p["optimization"], "Has_RESULT_TREADY": True,
            "Maximum_Latency": True, "C_Rate": rate, "Has_ACLKEN": False, "Has_ARESETn": op != "Absolute",
            **{"C_Has_" + name.upper(): p["has_" + name] for name in EXCEPTIONS},
            "C_Has_DIVIDE_BY_ZERO": False, "C_Has_ACCUM_OVERFLOW": False, "C_Has_ACCUM_INPUT_OVERFLOW": False,
            "Has_A_TLAST": p["has_last"], "Has_A_TUSER": bool(p["user_width"]), "A_TUSER_Width": p["user_width"] or 1,
            "Has_B_TLAST": False, "Has_B_TUSER": False, "Has_C_TLAST": False, "Has_C_TUSER": False,
            "Has_OPERATION_TLAST": False, "Has_OPERATION_TUSER": False,
            "RESULT_TLAST_Behv": "Pass_A_TLAST" if p["has_last"] else "Null"}
        model = {**{"C_HAS_" + name: int(name == OPERATIONS[op]) for name in ALL_OPERATIONS},
            "C_A_WIDTH": ie + ip, "C_A_FRACTION_WIDTH": ip,
            "C_RESULT_WIDTH": oe + oprec, "C_RESULT_FRACTION_WIDTH": oprec,
            **{"C_HAS_" + name.upper(): int(p["has_" + name]) for name in EXCEPTIONS},
            "C_HAS_DIVIDE_BY_ZERO": 0, "C_HAS_ACCUM_OVERFLOW": 0, "C_HAS_ACCUM_INPUT_OVERFLOW": 0,
            "C_HAS_ACLKEN": 0, "C_HAS_ARESETN": int(op != "Absolute"), "C_RATE": rate,
            "C_THROTTLE_SCHEME": 1 if p["optimization"] == "Resources" else 2,
            "C_HAS_A_TLAST": int(p["has_last"]), "C_HAS_A_TUSER": int(bool(p["user_width"])),
            "C_HAS_B": 0, "C_HAS_C": 0, "C_HAS_OPERATION": 0,
            "C_HAS_B_TLAST": 0, "C_HAS_B_TUSER": 0, "C_HAS_C_TLAST": 0, "C_HAS_C_TUSER": 0,
            "C_HAS_OPERATION_TLAST": 0, "C_HAS_OPERATION_TUSER": 0,
            "C_HAS_RESULT_TLAST": int(p["has_last"]), "C_HAS_RESULT_TUSER": int(bool(user_width)),
            "C_A_TDATA_WIDTH": source_width, "C_A_TUSER_WIDTH": p["user_width"] or 1,
            "C_RESULT_TDATA_WIDTH": sink_width, "C_RESULT_TUSER_WIDTH": user_width or 1,
            "C_FIXED_DATA_UNSIGNED": int(p["input_unsigned"])}
        version = self._layout.vivado_version
        clocked_absolute = (version not in (None, "unavailable")
                            and tuple(map(int, version.split("."))) >= (2026, 1))
        return StreamSpec(tuple(source), settings, model,
            input_clock=None if op == "Absolute" and not clocked_absolute else "aclk",
            input_reset=None if op == "Absolute" else "aresetn",
            output_payload=tuple(sink), capacity=ie + ip + oe + oprec + 8,
            input_prefix="s_axis_a", output_prefix="m_axis_result", transfer_interval_cycles=rate,
            drain_cycles=max(64, 2 * (ip + rate + 8)) if op == "Square_root" else 64)

    def generate_testbench(self, case):
        spec = self.describe(case.parameters)
        if case.parameters['operation'] == 'Compare':
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: compare_reference(frames, case.parameters),
                prepare=lambda frames: prepare_compare(frames, spec, case.parameters), renderer=render_operands,
                source_timing=lambda schedule, profile: independent_gaps(schedule, profile, spec.input_lane_count),
                reference_contract={'model': 'floating_point_compare:1.0', 'arithmetic': 'integer_order',
                    'denormals': 'signed_zero', 'nan_comparison': 'unordered', 'output_padding': 'zero',
                    'latency_check': 'accepted_operand_order', 'input_barrier': False, 'user_pattern': USER_PATTERN,
                    'operation_coverage': 'all_seven_per_numeric_pair' if spec.input_lane_count == 3 else 'fixed',
                    'operation_padding': 'upper_two_bits_varied', 'drain_cycles': 128})
        if case.parameters['operation'] in {'Add_Subtract', 'Multiply'}:
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: arithmetic_reference(frames, case.parameters),
                prepare=lambda frames: prepare_arithmetic(frames, spec, case.parameters), renderer=render_operands,
                source_timing=lambda schedule, profile: independent_gaps(schedule, profile, spec.input_lane_count),
                reference_contract={'model': 'floating_point_arithmetic:1.0', 'arithmetic': 'integer_exact',
                    'rounding': 'nearest_even', 'denormals': 'signed_zero', 'nan_result': 'pg060_canonical',
                    'underflow_detection': 'after_unbounded_exponent_rounding',
                    'underflow_documentation_conflict': True, 'output_padding': 'sign_extension',
                    'latency_check': 'accepted_operand_order', 'input_barrier': False, 'user_pattern': USER_PATTERN,
                    'operation_coverage': 'add_and_subtract_per_numeric_pair' if spec.input_lane_count == 3 else 'fixed',
                    'operation_padding': 'upper_two_bits_varied' if spec.input_lane_count == 3 else 'no_operation_channel',
                    'cycles_per_operation': 1, 'drain_cycles': 128})
        if case.parameters['operation'] == 'Divide':
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: divide_reference(frames, case.parameters),
                prepare=lambda frames: prepare_divide(frames, spec, case.parameters), renderer=render_operands,
                source_timing=lambda schedule, profile: independent_gaps(schedule, profile, spec.input_lane_count),
                reference_contract={'model': 'floating_point_divide:1.0', 'arithmetic': 'integer_quotient_remainder',
                    'rounding': 'nearest_even', 'denormals': 'signed_zero', 'nan_result': 'pg060_canonical',
                    'underflow_detection': 'after_unbounded_exponent_rounding',
                    'underflow_documentation_conflict': True, 'output_padding': 'sign_extension',
                    'latency_check': 'accepted_operand_order', 'input_barrier': False, 'user_pattern': USER_PATTERN,
                    'cycles_per_operation': spec.transfer_interval_cycles, 'drain_cycles': 128})
        if case.parameters['operation'] == 'FMA':
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: fma_reference(frames, case.parameters),
                prepare=lambda frames: prepare_fma(frames, spec, case.parameters), renderer=render_operands,
                source_timing=lambda schedule, profile: independent_gaps(schedule, profile, spec.input_lane_count),
                reference_contract={'model': 'floating_point_fma:1.0', 'arithmetic': 'exact_product_and_sum',
                    'intermediate_rounding': False, 'rounding': 'nearest_even', 'denormals': 'signed_zero',
                    'nan_result': 'pg060_canonical', 'underflow_detection': 'after_unbounded_exponent_rounding',
                    'output_padding': 'sign_extension', 'latency_check': 'accepted_operand_order',
                    'input_barrier': False, 'user_pattern': USER_PATTERN,
                    'cycles_per_operation': 1, 'drain_cycles': 128})
        if case.parameters['operation'] == 'Reciprocal':
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: reciprocal_reference(frames, case.parameters),
                prepare=lambda frames: prepare_reciprocal(frames, spec, case.parameters),
                tolerances=lambda frames, expected: reciprocal_tolerances(
                    frames, expected, case.parameters),
                reference_contract={'model': 'floating_point_reciprocal:1.0',
                    'arithmetic': 'exact_integer_ratio', 'rounding': 'nearest_even',
                    'denormals': 'signed_zero', 'nan_result': 'pg060_canonical',
                    'underflow_detection': 'after_unbounded_exponent_rounding',
                    'output_padding': 'sign_extension',
                    'latency_check': 'accepted_transaction_order',
                    'accuracy': 'half_exact_single_double_within_one_ulp',
                    'cycles_per_operation': 1, 'drain_cycles': 128})
        if case.parameters['operation'] == 'Reciprocal_square_root':
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: reciprocal_sqrt_reference(frames, case.parameters),
                prepare=lambda frames: prepare_reciprocal_sqrt(frames, spec, case.parameters),
                tolerances=lambda frames, expected: reciprocal_tolerances(
                    frames, expected, case.parameters),
                reference_contract={'model': 'floating_point_reciprocal_sqrt:1.0',
                    'arithmetic': 'exact_squared_midpoint', 'rounding': 'nearest_even',
                    'denormals': 'signed_zero', 'nan_result': 'pg060_canonical',
                    'output_padding': 'sign_extension',
                    'accuracy': 'half_exact_single_double_within_one_ulp',
                    'latency_check': 'accepted_transaction_order',
                    'cycles_per_operation': 1, 'drain_cycles': 256})
        if case.parameters['operation'] in {'Exponential', 'Logarithm'}:
            operation = case.parameters['operation'].lower()
            return self._backend.generate(case, spec, self.ip_name, self.version,
                lambda frames: transcendental_reference(frames, case.parameters),
                prepare=lambda frames: prepare_transcendental(frames, spec, case.parameters),
                tolerances=lambda frames, expected: transcendental_tolerances(
                    frames, expected, case.parameters),
                reference_contract={'model': f'floating_point_{operation}:1.0',
                    'arithmetic': 'decimal_high_precision_stable_encoding',
                    'rounding': 'nearest_even_reference', 'denormals': 'signed_zero',
                    'nan_result': 'pg060_canonical', 'output_padding': 'sign_extension',
                    'accuracy': 'ordinary_finite_within_one_ulp',
                    'latency_check': 'accepted_transaction_order',
                    'cycles_per_operation': 1, 'drain_cycles': 384})
        sqrt_contract = {"model": "floating_point_square_root:1.0", "arithmetic": "integer_exact",
            "rounding": "nearest_even_squared_midpoint", "denormals": "signed_zero",
            "output_padding": "sign_extension", "latency_check": "accepted_transaction_order",
            "dut_clock_present": True, "nan_result": "pg060_canonical",
            "cycles_per_operation": spec.transfer_interval_cycles, "drain_cycles": spec.drain_cycles}
        return self._backend.generate(case, spec, self.ip_name, self.version,
            lambda frames: expected_transactions(frames, case.parameters),
            prepare=lambda frames: prepare_frames(frames, spec, case.parameters),
            reference_contract=sqrt_contract if case.parameters["operation"] == "Square_root" else
                {"model": "floating_point_conversion:1.1", "arithmetic": "integer_exact",
                "rounding": "nearest_even", "denormals": "preserve_for_absolute_otherwise_flush",
                "underflow_detection": "after_unbounded_exponent_rounding",
                "underflow_documentation_conflict": True,
                "output_padding": "sign_extension", "latency_check": "accepted_transaction_order",
                "dut_clock_present": spec.input_clock is not None,
                "nan_result": "pg060_canonical_except_absolute"})
