from dataclasses import dataclass, field
from typing import Union

from .enums import PrecilaserCommand, PrecilaserMessageType, PrecilaserReturn


@dataclass
class PrecilaserCommandParamLength:
    ENABLE: int = 1
    SET_CURRENT: int = 2
    POWER_STABILIZATION: int = 1
    STATUS: int = 0


@dataclass
class PrecilaserReturnParamLength:
    ENABLE: int = 13
    SET_CURRENT: int = 2
    POWER_STABILIZATION: int = 1
    STATUS: int = 64


@dataclass(frozen=True)
class PrecilaserMessage:
    command: Union[PrecilaserCommand, PrecilaserReturn]
    param: int
    header: bytes = b"\x50\x00\x00"
    terminator: bytes = b"\x0d\x0a"
    endian: str = "big"
    type: PrecilaserMessageType = PrecilaserMessageType.COMMAND
    command_bytes: bytearray = field(init=False)
    checksum: bytes = field(init=False)
    xor_check: bytes = field(init=False)

    def __post_init__(self):
        command_bytes = bytearray()
        command_bytes += bytearray(self.header)
        command_bytes += bytearray(self.command.value)
        if self.type == PrecilaserMessageType.COMMAND:
            param_byte_length = getattr(PrecilaserCommandParamLength, self.command.name)
        else:
            param_byte_length = getattr(PrecilaserReturnParamLength, self.command.name)
        command_bytes += param_byte_length.to_bytes(1, self.endian)
        command_bytes += self.param.to_bytes(param_byte_length, self.endian)
        checksum = self._checksum(command_bytes[1:])
        command_bytes += checksum
        xor_check = self._xor_check(command_bytes[1:-1])
        command_bytes += xor_check
        command_bytes += self.terminator
        object.__setattr__(self, "command_bytes", command_bytes)
        object.__setattr__(self, "checksum", checksum)
        object.__setattr__(self, "xor_check", xor_check)

    def _checksum(self, data: bytearray) -> bytes:
        checksum_byte = 0
        for b in data:
            checksum_byte += b
        checksum_byte %= 2**8
        return checksum_byte.to_bytes(1, self.endian)

    def _xor_check(self, data: bytearray) -> bytes:
        xor_byte = 0
        for b in data:
            xor_byte = xor_byte ^ b
        return xor_byte.to_bytes(1, self.endian)


def decompose_message(
    message: bytearray,
    header: bytes = b"\x50\x00\x00",
    terminator: bytes = b"\x0d\x0a",
    endian: str = "big",
):
    if message[:3] != header:
        raise ValueError(f"invalid message header {message[:3]}")
    if message[-2:] != terminator:
        raise ValueError(f"invalid message terminator {message[-2:]}")

    ret = PrecilaserReturn(message[3])
    param_length = int.from_bytes(message[4], endian)
    param_bytes = message[5 : 5 + param_length]
    checksum = message[5 + param_length]
    xor_check = message[5 + param_length + 1]
    param = int.from_bytes(param_bytes, endian)
    pm = PrecilaserMessage(ret, param, type=PrecilaserMessageType.RETURN)
    if pm.checksum != checksum:
        raise ValueError(f"invalid message checksum {checksum}")
    if pm.xor_check != xor_check:
        raise ValueError(f"invalid xor check {xor_check}")
    return pm
