def checksum(data: bytearray) -> int:
    checksum = 0
    for b in data:
        checksum += b
    checksum %= 2**8
    return checksum


def xor_check(data: bytearray) -> int:
    xor = 0
    for b in data:
        xor = xor ^ b
    return xor
