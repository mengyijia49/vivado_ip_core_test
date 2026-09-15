from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.floating_point.parameters import validate_format
from vivado_ip_test.plugins.floating_point.multi_input.spec import LAST_MODES, build_spec


def describe(p):
    validate_parameters(p, {'operation': {'Divide'}, 'input_exponent': range(4, 17),
        'input_fraction': range(4, 65), 'cycles_per_operation': range(1, 67),
        'optimization': {'Resources', 'Performance'}, 'last_mode': LAST_MODES,
        **{f'{lane}_user_width': range(257) for lane in ('a', 'b', 'operation')},
        **{f'has_{lane}_last': bool for lane in ('a', 'b', 'operation')},
        **{f'has_{name}': bool for name in ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')}})
    e, precision, rate = p['input_exponent'], p['input_fraction'], p['cycles_per_operation']
    validate_format(e, precision, True)
    if rate > precision + 2:
        raise PluginError('Divide cycles per operation cannot exceed precision + 2')
    return build_spec(p, {'DIVIDE'}, False, e + precision, precision, rate=rate,
        settings={'Operation_Type': 'Divide', 'Result_Precision_Type': 'Custom',
                  'C_Optimization': 'Speed_Optimized', 'C_Mult_Usage': 'No_Usage'},
        model={'C_OPTIMIZATION': 1, 'C_MULT_USAGE': 0})
