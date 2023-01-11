from dataclasses import dataclass, field
from typing import Union, Tuple, Optional

from .enums import (
    PrecilaserCommand,
    PrecilaserMessageType,
    PrecilaserReturn
)


@dataclass
class PrecilaserCommandParamLength:
    AMP_ENABLE: int = 1
    AMP_SET_CURRENT: int = 2
    AMP_POWER_STABILIZATION: int = 1
    AMP_STATUS: int = 0
    SEED_QUERY: int = 0
    SEED_SET_TEMP: int = 3
    SEED_SET_VOLTAGE: int = 3


@dataclass
class PrecilaserReturnParamLength:
    AMP_ENABLE: int = 13
    AMP_SET_CURRENT: int = 2
    AMP_POWER_STABILIZATION: int = 1
    AMP_STATUS: int = 64
    SEED_QUERY: int = 40
    SEED_SET_TEMP: int = 4
    SEED_SET_VOLTAGE: int = 2


@dataclass(frozen=True)
class PrecilaserMessage:
    command: Union[PrecilaserCommand, PrecilaserReturn]
    param: Optional[int]
    address: int
    header: bytes
    terminator: bytes
    endian: str = "big"
    type: PrecilaserMessageType = PrecilaserMessageType.COMMAND
    command_bytes: bytearray = field(init=False)
    checksum: bytes = field(init=False)
    xor_check: bytes = field(init=False)

    def __post_init__(self):
        command_bytes = bytearray()
        command_bytes += bytearray(self.header)
        command_bytes += self.address.to_bytes(1, self.endian)
        command_bytes += bytearray(b"\x00")
        command_bytes += bytearray(self.command.value)
        if self.type == PrecilaserMessageType.COMMAND:
            param_byte_length = getattr(PrecilaserCommandParamLength, self.command.name)
        else:
            param_byte_length = getattr(PrecilaserReturnParamLength, self.command.name)
        command_bytes += param_byte_length.to_bytes(1, self.endian)
        if self.param is not None:
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
    address: int,
    header: bytes,
    terminator: bytes,
    endian: str,
    check_start: int
):
    if message[: len(header)] != header:
        raise ValueError(f"invalid message header {message[:len(header)]}")
    if message[-len(terminator) :] != terminator:
        raise ValueError(f"invalid message terminator {message[-len(terminator):]}")

    ret = PrecilaserReturn(message[3])
    param_length = int.from_bytes(message[4], endian)
    param_bytes = message[check_start : check_start + param_length]
    checksum = message[check_start + param_length]
    xor_check = message[check_start + param_length + 1]
    param = int.from_bytes(param_bytes, endian)
    pm = PrecilaserMessage(
        ret,
        param,
        address,
        header,
        terminator,
        endian,
        check_start,
        type=PrecilaserMessageType.RETURN,
    )
    if pm.checksum != checksum:
        raise ValueError(f"invalid message checksum {checksum}")
    if pm.xor_check != xor_check:
        raise ValueError(f"invalid xor check {xor_check}")
    return pm
