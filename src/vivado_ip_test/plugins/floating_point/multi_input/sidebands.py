def result_frame(value, frame, p, flags=None):
    output = {'tdata': value}
    selected = [name for name in ('underflow', 'overflow', 'invalid_op', 'divide_by_zero')
                if p.get('has_' + name, False)]
    user = sum(int(flags[name]) << i for i, name in enumerate(selected))
    offset = len(selected)
    lasts = []
    for lane in ('a', 'b', 'c', 'operation'):
        width = p.get(f'{lane}_user_width', 0)
        if width:
            user |= frame[f'{lane}_tuser'] << offset
            offset += width
        if p.get(f'has_{lane}_last', False):
            lasts.append(frame[f'{lane}_tlast'])
    if offset:
        output['tuser'] = user
    if lasts:
        mode = p['last_mode']
        output['tlast'] = (int(any(lasts)) if mode == 'Or' else int(all(lasts)) if mode == 'And'
                           else frame[f'{mode.lower()}_tlast'])
    return output
