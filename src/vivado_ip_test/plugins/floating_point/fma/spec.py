from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.floating_point.multi_input.spec import LAST_MODES, build_spec


NATIVE_FORMATS = {(5, 11): 'Half', (8, 24): 'Single', (11, 53): 'Double'}
DSP_USAGE = {'Medium_Usage': 1, 'Full_Usage': 2}


def describe(p):
    validate_parameters(p, {
        'operation': {'FMA'}, 'input_exponent': range(5, 12), 'input_fraction': range(11, 54),
        'optimization': {'Resources', 'Performance'}, 'mult_usage': DSP_USAGE,
        'last_mode': LAST_MODES,
        **{f'{lane}_user_width': range(257) for lane in ('a', 'b', 'c', 'operation')},
        **{f'has_{lane}_last': bool for lane in ('a', 'b', 'c', 'operation')},
        **{f'has_{name}': bool for name in ('underflow', 'overflow', 'invalid_op')},
    })
    key = p['input_exponent'], p['input_fraction']
    if key not in NATIVE_FORMATS:
        raise PluginError('FMA currently supports only native half, single, and double formats')
    native = NATIVE_FORMATS[key]
    return build_spec(
        p, {'FMA', 'FMS'}, True, sum(key), p['input_fraction'], data_lanes=('a', 'b', 'c'),
        settings={'Operation_Type': 'FMA', 'A_Precision_Type': native,
                  'Result_Precision_Type': native, 'C_Optimization': 'Speed_Optimized',
                  'C_Mult_Usage': p['mult_usage']},
        model={'C_OPTIMIZATION': 1, 'C_MULT_USAGE': DSP_USAGE[p['mult_usage']]})
