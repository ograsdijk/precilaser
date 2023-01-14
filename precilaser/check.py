def checksum(data: bytes) -> int:
    checksum = 0
    for b in data:
        checksum += b
    checksum %= 2**8
    return checksum


def xor_check(data: bytes) -> int:
    xor = 0
    for b in data:
        xor = xor ^ b
    return xor
