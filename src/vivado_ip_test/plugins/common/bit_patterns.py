def bit_identity_frames(ports):
    """Distinguish each physical input bit with logarithmically many patterns."""
    width = sum(port.width for port in ports)
    if not width:
        return
    mask = (1 << width)-1

    def frame(value):
        result, offset = {}, 0
        for port in ports:
            result[port.name] = (value >> offset) & port.limit
            offset += port.width
        return result

    yield frame(0)
    yield frame(mask)
    for bit in range((width-1).bit_length()):
        block = 1 << bit
        period = "0" * block + "1" * block
        pattern = int((period * ((width+len(period)-1)//len(period)))[:width][::-1], 2)
        yield frame(pattern)
        yield frame(mask ^ pattern)
