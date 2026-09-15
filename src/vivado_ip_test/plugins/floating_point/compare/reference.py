from vivado_ip_test.plugins.floating_point.formats import FloatFormat
from vivado_ip_test.plugins.floating_point.multi_input.sidebands import result_frame


COMPARISONS = ('Unordered', 'Less_Than', 'Equal', 'Less_Than_Or_Equal', 'Greater_Than',
               'Not_Equal', 'Greater_Than_Or_Equal', 'Condition_Code', 'Programmable')
OPERATION_CODES = dict(zip((4, 12, 20, 28, 36, 44, 52), COMPARISONS[:7]))
TRUTH_MASKS = dict(zip(COMPARISONS[:7], (8, 2, 1, 3, 4, 14, 5)))


def condition_code(a, b, fmt):
    keys = []
    for bits in (a, b):
        sign, exponent, fraction = fmt.unpack(bits)
        if exponent == fmt.exponent_mask and fraction:
            return 8
        # Biased exponent and fraction are monotonic within one sign.
        magnitude = (exponent << fmt.fraction_bits) | fraction if exponent else 0
        keys.append(-magnitude if sign else magnitude)
    return 1 if keys[0] == keys[1] else 2 if keys[0] < keys[1] else 4


def compare(a, b, fmt, operation, opcode=0):
    condition = condition_code(a, b, fmt)
    if operation == 'Programmable':
        try:
            operation = OPERATION_CODES[opcode & 63]
        except KeyError as exc:
            raise ValueError('Unsupported programmable comparison opcode') from exc
    if operation == 'Condition_Code':
        return condition
    return int(bool(condition & TRUTH_MASKS[operation]))


def expected_transactions(frames, p):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    result = []
    for frame in frames:
        value = compare(frame['a_tdata'], frame['b_tdata'], fmt,
                        p['compare_operation'], frame.get('operation_tdata', 0))
        result.append(result_frame(value, frame, p))
    return result
