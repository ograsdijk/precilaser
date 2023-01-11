from dataclasses import dataclass, field
from typing import Optional, Union

from .check import checksum, xor_check
from .enums import PrecilaserCommand, PrecilaserMessageType, PrecilaserReturn


@dataclass
class PrecilaserCommandParamLength:
    AMP_ENABLE: int = 1
    AMP_SET_CURRENT: int = 2
    AMP_POWER_STABILIZATION: int = 1
    AMP_STATUS: int = 0
    SEED_STATUS: int = 0
    SEED_SET_TEMP: int = 3
    SEED_SET_VOLTAGE: int = 3


@dataclass
class PrecilaserReturnParamLength:
    AMP_ENABLE: int = 13
    AMP_SET_CURRENT: int = 2
    AMP_POWER_STABILIZATION: int = 1
    AMP_STATUS: int = 64
    SEED_STATUS: int = 40
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
    payload: Optional[bytearray] = field(init=False)
    command_bytes: bytearray = field(init=False)
    checksum: bytes = field(init=False)
    xor_check: bytes = field(init=False)

    def __post_init__(self):
        command_bytes = bytearray()
        command_bytes += bytearray(self.header)
        command_bytes += bytearray(b"\x00")
        command_bytes += self.address.to_bytes(1, self.endian)
        command_bytes += bytearray(self.command.value)

        if self.type == PrecilaserMessageType.COMMAND:
            param_byte_length = getattr(PrecilaserCommandParamLength, self.command.name)
        else:
            param_byte_length = getattr(PrecilaserReturnParamLength, self.command.name)

        command_bytes += param_byte_length.to_bytes(1, self.endian)
        if self.param is not None:
            command_bytes += self.param.to_bytes(param_byte_length, self.endian)

        sum = checksum(command_bytes[1:])
        xor = xor_check(command_bytes[1:])

        command_bytes += sum.to_bytes(1, self.endian)
        command_bytes += xor.to_bytes(1, self.endian)
        command_bytes += self.terminator
        object.__setattr__(
            self,
            "payload",
            command_bytes[5 : 5 + param_byte_length]
            if self.param is not None
            else None,
        )
        object.__setattr__(self, "command_bytes", command_bytes)
        object.__setattr__(self, "checksum", sum)
        object.__setattr__(self, "xor_check", xor)


def decompose_message(
    message: bytearray,
    address: int,
    header: bytes,
    terminator: bytes,
    endian: str,
):
    if message[: len(header)] != header:
        raise ValueError(f"invalid message header {message[:len(header)]}")
    if message[-len(terminator) :] != terminator:
        raise ValueError(f"invalid message terminator {message[-len(terminator):]}")

    ret = PrecilaserReturn(message[3].to_bytes(1, endian))
    param_length = message[4]
    param_bytes = message[5 : 5 + param_length]
    checksum = message[-4]
    xor_check = message[-3]
    param = int.from_bytes(param_bytes, endian)
    pm = PrecilaserMessage(
        command=ret,
        param=param,
        address=address,
        header=header,
        terminator=terminator,
        endian=endian,
        type=PrecilaserMessageType.RETURN,
    )
    if pm.checksum != checksum:
        raise ValueError(f"invalid message checksum {checksum} != {pm.checksum}")
    if pm.xor_check != xor_check:
        raise ValueError(f"invalid xor check {xor_check} != {pm.xor_check}")
    return pm
