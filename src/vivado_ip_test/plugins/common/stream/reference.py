def transparent_stream(frames):
    """The three transparent IPs preserve each accepted payload and its order."""
    return [dict(frame) for frame in frames]
