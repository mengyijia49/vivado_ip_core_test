from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext


PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286")


def decode_signed(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def _sin_cos(angle, precision):
    with localcontext() as context:
        context.prec = precision
        angle = +angle
        square = angle * angle
        sine = sine_term = angle
        cosine = cosine_term = Decimal(1)
        threshold = Decimal(10) ** (-(precision - 12))
        for index in range(1, precision + 8):
            sine_term *= -square / Decimal((2 * index) * (2 * index + 1))
            cosine_term *= -square / Decimal((2 * index - 1) * (2 * index))
            sine += sine_term
            cosine += cosine_term
            if abs(sine_term) < threshold and abs(cosine_term) < threshold:
                return +cosine, +sine
    raise ArithmeticError("CORDIC trigonometric reference did not converge")


def _quantize(value, width, rounding):
    scaled = value * (1 << (width - 2))
    if rounding == "Truncate":
        return int(scaled.to_integral_value(rounding=ROUND_FLOOR))
    if rounding == "Round_Pos_Inf":
        return int((scaled + Decimal("0.5")).to_integral_value(rounding=ROUND_FLOOR))
    if rounding == "Round_Pos_Neg_Inf":
        adjusted = scaled + (Decimal("0.5") if scaled >= 0 else Decimal("-0.5"))
        mode = ROUND_FLOOR if scaled >= 0 else ROUND_CEILING
        return int(adjusted.to_integral_value(rounding=mode))
    return int(scaled.to_integral_value(rounding=ROUND_HALF_EVEN))


def calculate(value, parameters, precision=180):
    width = parameters["input_width"]
    phase = Decimal(decode_signed(value, width)) / (1 << (width - 3))
    angle = phase * PI if parameters["phase_format"] == "Scaled_Radians" else phase
    cosine, sine = _sin_cos(angle, precision)
    output_width = parameters["output_width"]
    return (_quantize(cosine, output_width, parameters["rounding"]),
            _quantize(sine, output_width, parameters["rounding"]))


def _pack_field(value, width):
    padded = ((width + 7) // 8) * 8
    return value & ((1 << padded) - 1), padded


def expected_transactions(frames, parameters):
    result = []
    for frame in frames:
        low = calculate(frame["tdata"], parameters, 140)
        high = calculate(frame["tdata"], parameters, 220)
        if low != high:
            raise ArithmeticError("CORDIC trigonometric reference did not stabilize")
        cosine, field_width = _pack_field(high[0], parameters["output_width"])
        sine, _ = _pack_field(high[1], parameters["output_width"])
        output = {"tdata": cosine | (sine << field_width)}
        if parameters["has_last"]:
            output["tlast"] = frame["tlast"]
        if parameters["user_width"]:
            output["tuser"] = frame["tuser"]
        result.append(output)
    return result


def tolerances(frames, expected, parameters):
    field_width = ((parameters["output_width"] + 7) // 8) * 8
    for output in expected:
        row = {name: 0 for name in output}
        row["tdata"] = 2 | (2 << field_width)
        yield row
