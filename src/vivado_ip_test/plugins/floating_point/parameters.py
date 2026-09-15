from vivado_ip_test.plugins.base import PluginError


ALL_OPERATIONS = ("ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "SQRT", "COMPARE", "FIX_TO_FLT",
    "FLT_TO_FIX", "FLT_TO_FLT", "RECIP", "RECIP_SQRT", "ABSOLUTE", "LOGARITHM", "EXPONENTIAL",
    "FMA", "FMS", "UNFUSED_MULTIPLY_ADD", "UNFUSED_MULTIPLY_SUB", "UNFUSED_MULTIPLY_ACCUMULATOR_A",
    "UNFUSED_MULTIPLY_ACCUMULATOR_S", "ACCUMULATOR_A", "ACCUMULATOR_S", "ACCUMULATOR_PRIMITIVE_A",
    "ACCUMULATOR_PRIMITIVE_S")


def validate_format(exponent, fraction, floating):
    if floating:
        if not 4 <= exponent <= 16 or not 4 <= fraction <= 64 or exponent < (fraction + 2).bit_length() + 1:
            raise PluginError("Floating point exponent does not support the requested precision")
    elif not 4 <= exponent + fraction <= 64:
        raise PluginError("Fixed point total width must be between 4 and 64")
