import hashlib

from vivado_ip_test.plugins.floating_point.formats import FloatFormat


USER_PATTERN = 'walking_bits_and_full_width_tags:1.0'


def user_tag(index, lane, width):
    limit = (1 << width) - 1
    walk = 1 << ((index // 8 + lane * 31) % width)
    phase = index % 8
    if phase == 0:
        return limit
    if phase == 1:
        return walk
    if phase == 2:
        return limit ^ walk
    if phase == 3:
        return 0
    seed = f'{USER_PATTERN}:{index}:{lane}'.encode('ascii')
    return int.from_bytes(hashlib.sha256(seed).digest(), 'big') & limit


def prefixed_frames(frames, spec, p, pairs):
    fmt = FloatFormat(p['input_exponent'], p['input_fraction'])
    padding = (1 << spec.lanes[0][1][0].width) - (1 << fmt.width)
    pads = (0, padding) if padding else (0,)
    base = {port.name: 0 for port in spec.payload}
    prefix = []
    for a, b in pairs:
        for a_pad in pads:
            for b_pad in pads:
                row = {**base, 'a_tdata': a | a_pad, 'b_tdata': b | b_pad}
                for lane_index, (lane, ports) in enumerate(spec.lanes):
                    for port in ports:
                        if port.name == 'tuser':
                            row[f'{lane}_tuser'] = user_tag(len(prefix), lane_index, port.width)
                prefix.append(row)
    return prefix + [{**base, **frame} for frame in frames]
