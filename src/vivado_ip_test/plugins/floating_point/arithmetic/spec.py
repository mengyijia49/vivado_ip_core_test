from vivado_ip_test.plugins.base import PluginError
from vivado_ip_test.plugins.common.cycle import validate_parameters
from vivado_ip_test.plugins.floating_point.parameters import validate_format
from vivado_ip_test.plugins.floating_point.multi_input.spec import LAST_MODES, build_spec


NATIVE_FORMATS = {(5, 11): 'Half', (8, 24): 'Single', (11, 53): 'Double'}
DSP_USAGE = {'No_Usage': 0, 'Medium_Usage': 1, 'Full_Usage': 2, 'Max_Usage': 3}


def implementation_options(operation, exponent, precision):
    native = NATIVE_FORMATS.get((exponent, precision))
    if operation == 'Add_Subtract':
        if not native:
            return [('Speed_Optimized', 'No_Usage')]
        usages = ('No_Usage', 'Full_Usage') if native == 'Double' else (
                  'No_Usage', 'Medium_Usage', 'Full_Usage')
        return [('Speed_Optimized', usage) for usage in usages] + [('Low_Latency', 'No_Usage')]
    if operation == 'Multiply':
        usages = ('No_Usage', 'Medium_Usage', 'Full_Usage', 'Max_Usage') if native == 'Double' else (
                  'No_Usage', 'Full_Usage', 'Max_Usage')
        return [('Speed_Optimized', usage) for usage in usages] + (
            [('Low_Latency', 'Max_Usage')] if native == 'Double' else [])
    raise PluginError('Unsupported arithmetic operation')


def describe(p):
    rules = {'operation': {'Add_Subtract', 'Multiply'}, 'input_exponent': range(4, 17),
        'input_fraction': range(4, 65), 'optimization': {'Resources', 'Performance'},
        'architecture': {'Speed_Optimized', 'Low_Latency'}, 'mult_usage': DSP_USAGE, 'last_mode': LAST_MODES,
        **{f'{lane}_user_width': range(257) for lane in ('a', 'b', 'operation')},
        **{f'has_{lane}_last': bool for lane in ('a', 'b', 'operation')},
        **{f'has_{name}': bool for name in ('underflow', 'overflow', 'invalid_op')}}
    if p.get('operation') == 'Add_Subtract':
        rules['add_sub_value'] = {'Add', 'Subtract', 'Both'}
    validate_parameters(p, rules)
    e, precision = p['input_exponent'], p['input_fraction']
    validate_format(e, precision, True)
    if (p['architecture'], p['mult_usage']) not in implementation_options(p['operation'], e, precision):
        raise PluginError('Architecture or DSP setting is unsupported or would be rewritten by Vivado')
    operations = {'MULTIPLY'} if p['operation'] == 'Multiply' else (
        {'ADD', 'SUBTRACT'} if p['add_sub_value'] == 'Both' else {p['add_sub_value'].upper()})
    native = NATIVE_FORMATS.get((e, precision), 'Custom')
    settings = {'Operation_Type': p['operation'], 'A_Precision_Type': native, 'Result_Precision_Type': native,
                'C_Optimization': p['architecture'], 'C_Mult_Usage': p['mult_usage']}
    if p['operation'] == 'Add_Subtract':
        settings['Add_Sub_Value'] = p['add_sub_value']
    return build_spec(p, operations, len(operations) == 2, e + precision, precision, settings=settings,
        model={'C_OPTIMIZATION': 1 if p['architecture'] == 'Speed_Optimized' else 2,
               'C_MULT_USAGE': DSP_USAGE[p['mult_usage']]})
