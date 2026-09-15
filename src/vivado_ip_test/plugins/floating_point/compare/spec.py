from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.floating_point.parameters import validate_format
from vivado_ip_test.plugins.floating_point.compare.reference import COMPARISONS
from vivado_ip_test.plugins.floating_point.multi_input.spec import LAST_MODES, build_spec


def describe(p):
    validate_parameters(p, {'operation': {'Compare'}, 'input_exponent': range(4, 17),
        'input_fraction': range(4, 65), 'compare_operation': COMPARISONS,
        'optimization': {'Resources', 'Performance'}, 'last_mode': LAST_MODES,
        **{f'{lane}_user_width': range(257) for lane in ('a', 'b', 'operation')},
        **{f'has_{lane}_last': bool for lane in ('a', 'b', 'operation')}})
    validate_format(p['input_exponent'], p['input_fraction'], True)
    return build_spec(p, {'COMPARE'}, p['compare_operation'] == 'Programmable',
        4 if p['compare_operation'] == 'Condition_Code' else 1,
        settings={'Operation_Type': 'Compare', 'C_Compare_Operation': p['compare_operation']},
        model={'C_COMPARE_OPERATION': COMPARISONS.index(p['compare_operation'])})
