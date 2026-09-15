from vivado_ip_test.plugins.common.stream.bytes import expected_bytes


def expected_transactions(frames, source_payload):
    return expected_bytes(frames, source_payload)
