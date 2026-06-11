from precilaser.check import checksum, xor_check


def test_checksum_sums_modulo_256():
    assert checksum(b"") == 0
    assert checksum(b"\x01\x02\x03") == 6
    # wraps around at 2**8
    assert checksum(b"\xff\x01") == 0
    assert checksum(b"\xff\xff") == 254


def test_xor_check():
    assert xor_check(b"") == 0
    assert xor_check(b"\x0f\xf0") == 0xFF
    # a value xored with itself cancels out
    assert xor_check(b"\xab\xab") == 0
    assert xor_check(b"\x01\x02\x04") == 0x07
