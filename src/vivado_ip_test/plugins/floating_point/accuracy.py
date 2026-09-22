from vivado_ip_test.plugins.floating_point.formats import FloatFormat


def reciprocal_tolerances(frames, expected, p):
    """Apply the PG060 one-ULP allowance only to ordinary Single/Double results."""
    source = FloatFormat(p['input_exponent'], p['input_fraction'])
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    for frame, output in zip(frames, expected):
        _, input_exponent, _ = source.unpack(frame['tdata'])
        _, output_exponent, _ = target.unpack(output['tdata'])
        allow_one_ulp = (target.width in (32, 64)
                         and 0 < input_exponent < source.exponent_mask
                         and 0 < output_exponent < target.exponent_mask)
        yield {name: int(allow_one_ulp) if name == 'tdata' else 0 for name in output}


def transcendental_tolerances(frames, expected, p):
    """PG060 permits one ULP for ordinary finite logarithm and exponential results."""
    target = FloatFormat(p['output_exponent'], p['output_fraction'])
    for output in expected:
        _, output_exponent, _ = target.unpack(output['tdata'])
        allow_one_ulp = 0 < output_exponent < target.exponent_mask
        yield {name: int(allow_one_ulp) if name == 'tdata' else 0 for name in output}
