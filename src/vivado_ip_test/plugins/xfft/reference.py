import cmath
import math


def signed_value(value, width):
    value &= (1 << width) - 1
    return value - (1 << width) if value & (1 << (width - 1)) else value


def padded_width(width):
    return ((width + 7) // 8) * 8


def output_width(input_width, transform_length):
    return input_width + int(math.log2(transform_length)) + 1


def unpack_complex(value, width):
    lane = padded_width(width)
    mask = (1 << width) - 1
    return (signed_value(value & mask, width),
            signed_value((value >> lane) & mask, width))


def pack_complex(real, imag, width):
    lane = padded_width(width)
    mask = (1 << width) - 1
    lane_mask = (1 << lane) - 1

    def encoded(value):
        raw = value & mask
        if value < 0:
            raw |= lane_mask ^ mask
        return raw

    return encoded(real) | (encoded(imag) << lane)


def bit_reverse(value, width):
    result = 0
    for _ in range(width):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def integer_dft(samples, forward):
    length = len(samples)
    sign = -1 if forward else 1
    max_component = max((max(abs(real), abs(imag)) for real, imag in samples), default=0)
    tolerance = max(1e-7, length * max_component * 1e-13)
    if tolerance >= 0.25:
        raise ValueError("FFT 参考计算精度不足以确认整数结果")
    transformed = []
    for frequency in range(length):
        total = 0j
        for time, (real, imag) in enumerate(samples):
            angle = sign * 2 * math.pi * frequency * time / length
            total += complex(real, imag) * cmath.exp(1j * angle)
        rounded_real = round(total.real)
        rounded_imag = round(total.imag)
        if (abs(total.real - rounded_real) > tolerance
                or abs(total.imag - rounded_imag) > tolerance):
            raise ValueError("FFT 定向输入没有得到精确整数结果")
        transformed.append((rounded_real, rounded_imag))
    return transformed


def expected_transactions(frames, parameters):
    length = parameters["transform_length"]
    if not frames or len(frames) % length:
        raise ValueError("FFT 输入必须由完整帧组成")
    width = parameters["input_width"]
    result_width = output_width(width, length)
    index_width = int(math.log2(length))
    expected = []
    for start in range(0, len(frames), length):
        frame = frames[start:start + length]
        if any(item["tlast"] != int(index == length - 1)
               for index, item in enumerate(frame)):
            raise ValueError("FFT 输入 TLAST 位置错误")
        samples = [unpack_complex(item["tdata"], width) for item in frame]
        transformed = integer_dft(samples, parameters["direction"] == "forward")
        order = list(range(length))
        if parameters["output_ordering"] == "bit_reversed_order":
            order = [bit_reverse(index, index_width) for index in order]
        for position, frequency in enumerate(order):
            real, imag = transformed[frequency]
            expected.append({
                "tdata": pack_complex(real, imag, result_width),
                "tuser": frequency,
                "tlast": int(position == length - 1),
            })
    return expected
