from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import Port, validate_parameters
from vivado_ip_test.plugins.common.stream.spec import StreamSpec
from vivado_ip_test.plugins.floating_point.parameters import ALL_OPERATIONS


NATIVE_FORMATS = {(5, 11): 'Half', (8, 24): 'Single', (11, 53): 'Double'}


def describe(p):
    validate_parameters(p, {'operation': {'Reciprocal_square_root'},
        'input_exponent': range(5, 12), 'input_fraction': range(11, 54),
        'output_exponent': range(5, 12), 'output_fraction': range(11, 54),
        'optimization': {'Resources', 'Performance'}, 'has_last': bool, 'user_width': range(257),
        'has_underflow': bool, 'has_overflow': bool, 'has_invalid_op': bool,
        'has_divide_by_zero': bool})
    if p['has_underflow'] or p['has_overflow']:
        raise PluginError('Reciprocal square root does not provide UNDERFLOW or OVERFLOW flags')
    source_format = NATIVE_FORMATS.get((p['input_exponent'], p['input_fraction']))
    result_format = NATIVE_FORMATS.get((p['output_exponent'], p['output_fraction']))
    if source_format is None or result_format is None:
        raise PluginError('Reciprocal square root supports only native Half, Single, and Double formats')
    if source_format != result_format:
        raise PluginError('Reciprocal square root mixed formats are not supported by this behavioral test')
    input_width = p['input_exponent'] + p['input_fraction']
    output_width = p['output_exponent'] + p['output_fraction']
    input_wire = ((input_width + 7) // 8) * 8
    output_wire = ((output_width + 7) // 8) * 8
    selected = [name for name in ('invalid_op', 'divide_by_zero') if p['has_' + name]]
    result_user_width = p['user_width'] + len(selected)
    source = [Port('tdata', input_wire)]
    sink = [Port('tdata', output_wire)]
    if p['has_last']:
        source.append(Port('tlast', scalar=True))
        sink.append(Port('tlast', scalar=True))
    if p['user_width']:
        source.append(Port('tuser', p['user_width']))
    if result_user_width:
        sink.append(Port('tuser', result_user_width))
    settings = {'Operation_Type': 'Rec_Square_Root', 'A_Precision_Type': source_format,
        'C_A_Exponent_Width': p['input_exponent'], 'C_A_Fraction_Width': p['input_fraction'],
        'Result_Precision_Type': result_format, 'C_Result_Exponent_Width': p['output_exponent'],
        'C_Result_Fraction_Width': p['output_fraction'], 'Flow_Control': 'Blocking',
        'Axi_Optimize_Goal': p['optimization'], 'Has_RESULT_TREADY': True,
        'Maximum_Latency': True, 'C_Rate': 1, 'C_Optimization': 'Speed_Optimized',
        'Has_ACLKEN': False, 'Has_ARESETn': True,
        'C_Has_UNDERFLOW': False, 'C_Has_OVERFLOW': False,
        'C_Has_INVALID_OP': p['has_invalid_op'],
        'C_Has_DIVIDE_BY_ZERO': p['has_divide_by_zero'],
        'C_Has_ACCUM_OVERFLOW': False, 'C_Has_ACCUM_INPUT_OVERFLOW': False,
        'Has_A_TLAST': p['has_last'], 'Has_A_TUSER': bool(p['user_width']),
        'A_TUSER_Width': p['user_width'] or 1, 'Has_B_TLAST': False, 'Has_B_TUSER': False,
        'Has_C_TLAST': False, 'Has_C_TUSER': False,
        'Has_OPERATION_TLAST': False, 'Has_OPERATION_TUSER': False,
        'RESULT_TLAST_Behv': 'Pass_A_TLAST' if p['has_last'] else 'Null'}
    model = {**{f'C_HAS_{name}': int(name == 'RECIP_SQRT') for name in ALL_OPERATIONS},
        'C_A_WIDTH': input_width, 'C_A_FRACTION_WIDTH': p['input_fraction'],
        'C_RESULT_WIDTH': output_width, 'C_RESULT_FRACTION_WIDTH': p['output_fraction'],
        'C_OPTIMIZATION': 1, 'C_MULT_USAGE': 0 if source_format == 'Half' else 2, 'C_RATE': 1,
        'C_HAS_UNDERFLOW': 0, 'C_HAS_OVERFLOW': 0,
        'C_HAS_INVALID_OP': int(p['has_invalid_op']),
        'C_HAS_DIVIDE_BY_ZERO': int(p['has_divide_by_zero']),
        'C_HAS_ACCUM_OVERFLOW': 0, 'C_HAS_ACCUM_INPUT_OVERFLOW': 0,
        'C_HAS_ACLKEN': 0, 'C_HAS_ARESETN': 1, 'C_FIXED_DATA_UNSIGNED': 0,
        'C_THROTTLE_SCHEME': 1 if p['optimization'] == 'Resources' else 2,
        'C_HAS_A_TLAST': int(p['has_last']), 'C_HAS_A_TUSER': int(bool(p['user_width'])),
        'C_A_TDATA_WIDTH': input_wire, 'C_A_TUSER_WIDTH': p['user_width'] or 1,
        'C_HAS_B': 0, 'C_HAS_C': 0, 'C_HAS_OPERATION': 0,
        'C_HAS_B_TLAST': 0, 'C_HAS_B_TUSER': 0, 'C_HAS_C_TLAST': 0, 'C_HAS_C_TUSER': 0,
        'C_HAS_OPERATION_TLAST': 0, 'C_HAS_OPERATION_TUSER': 0,
        'C_HAS_RESULT_TLAST': int(p['has_last']), 'C_HAS_RESULT_TUSER': int(bool(result_user_width)),
        'C_RESULT_TDATA_WIDTH': output_wire, 'C_RESULT_TUSER_WIDTH': result_user_width or 1}
    return StreamSpec(tuple(source), settings, model, output_payload=tuple(sink),
        input_prefix='s_axis_a', output_prefix='m_axis_result', capacity=128, drain_cycles=256)
