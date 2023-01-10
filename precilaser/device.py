from abc import ABC
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Union

import pyvisa


class PrecilaserCommand(Enum):
    ENABLE = b"\x30"
    SET_CURRENT = b"\xa1"
    POWER_STABILIZATION = b"\x47"
    STATUS = b"\x04"


class PrecilaserReturn(Enum):
    ENABLE = b"\x40"
    SET_CURRENT = b"\x41"
    STATUS = b"\x44"


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


class PrecilaserMessageType(Enum):
    COMMAND = auto()
    RETURN = auto()


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


@dataclass(frozen=True)
class SystemStatus:
    status: int
    pd_protection: tuple[bool, ...] = field(init=False)
    temperature_protection: tuple[bool, ...] = field(init=False)
    fault: bool = field(init=False)

    def __post_init__(self):
        pd_protection_bits = [4, 5, 6, 7]
        temperature_protection_bits = [8, 9, 10, 11, 12]

        pd_protection = tuple(
            bool(self.status >> pdb & 1) for pdb in pd_protection_bits
        )
        object.__setattr__(self, "pd_protection", pd_protection)

        temperature_protection = tuple(
            bool(self.status >> tpb & 1) for tpb in temperature_protection_bits
        )
        object.__setattr__(self, "temperature_protection", temperature_protection)

        object.__setattr__(self, "fault", self.status != 0)


@dataclass(frozen=True)
class DriverUnlock:
    driver_unlock: int
    driver_enable_control: tuple[bool, ...] = field(init=False)
    driver_enable_flag: tuple[bool, ...] = field(init=False)
    interlock: bool = field(init=False)

    def __post_init__(self):
        driver_enable_control = tuple(
            bool(self.driver_unlock >> bi & 1) for bi in range(3)
        )
        driver_enable_flag = tuple(
            bool(self.driver_unlock >> bi & 1) for bi in range(3, 6)
        )
        interlock = bool(self.driver_unlock >> 6 & 1)
        object.__setattr__(self, "driver_enable_control", driver_enable_control)
        object.__setattr__(self, "driver_enable_flag", driver_enable_flag)
        object.__setattr__(self, "interlock", interlock)


@dataclass(frozen=True)
class PDStatus:
    status: int
    sampling_enable: bool = field(init=False)
    hardware_protection: bool = field(init=False)
    upper_limit_enabled: bool = field(init=False)
    lower_limit_enabled: bool = field(init=False)
    hardware_protection_event: bool = field(init=False)
    upper_limit_event: bool = field(init=False)
    lower_limit_event: bool = field(init=False)
    fault: bool = field(init=False)

    def __post_init__(self):
        for idf, field in enumerate(self.__dataclass_fields__):
            if field in ["status", "fault"]:
                continue
            idf -= 1
            object.__setattr__(self, field, bool(self.status >> idf & 1))

        object.__setattr__(
            self,
            "fault",
            self.hardware_protection_event
            | self.upper_limit_event
            | self.lower_limit_event,
        )


@dataclass(frozen=True)
class PrecilaserStatus:
    status: int
    endian: str = "big"
    stable: bool = field(init=False)
    system_status: SystemStatus = field(init=False)
    driver_unlock: DriverUnlock = field(init=False)
    driver_current: tuple[float, ...] = field(init=False)
    pd_value: tuple[int, ...] = field(init=False)
    pd_status: tuple[PDStatus, ...] = field(init=False)
    temperatures: tuple[float, ...] = field(init=False)

    def __post_init__(self):
        byte_index = 0
        status_bytes = self.status.to_bytes(64, self.endian)

        # get the stable bit
        object.__setattr__(self, "stable", bool(status_bytes[byte_index]))

        # get the system status
        byte_index = 3
        system_status_int = int.from_bytes(
            status_bytes[byte_index : byte_index + 2], self.endian
        )
        system_status = SystemStatus(system_status_int)
        object.__setattr__(self, "system_status", system_status)

        # get the driver unlock register
        object.__setattr__(self, "driver_unlock", DriverUnlock(status_bytes[4]))

        # get currents in A
        byte_index = 7
        driver_current = tuple(
            int.from_bytes(status_bytes[bi : bi + 2], self.endian) / 100
            for bi in range(byte_index, byte_index + 3 * 2, 2)
        )
        object.__setattr__(self, "driver_current", driver_current)

        # get the pd readout
        byte_index = 28
        pd_value = tuple(
            int.from_bytes(status_bytes[bi : bi + 2], self.endian)
            for bi in range(byte_index, byte_index + 5 * 2, 2)
        )
        object.__setattr__(self, "pd_value", pd_value)

        # get the pd status
        byte_index = 36
        pd_status = tuple(
            PDStatus(int.from_bytes(status_bytes[bi : bi + 1], self.endian))
            for bi in range(byte_index, byte_index + 4)
        )
        object.__setattr__(self, "pd_status", pd_status)

        # get the temperatures in C
        byte_index = 42
        temperatures = tuple(
            int.from_bytes(status_bytes[bi : bi + 2], self.endian) / 100
            for bi in range(byte_index, byte_index + 4 * 2, 2)
        )
        object.__setattr__(self, "temperatures", temperatures)


class AbstractPrecilaserDevice(ABC):
    def __init__(self, resource_name: str):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(
            resource_name=resource_name, baud_rate=115200, write_termination=""
        )

        self.status: PrecilaserStatus(0)

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        if message.command == PrecilaserReturn.STATUS.value:
            self.status = PrecilaserStatus(message.param)
            return message
        else:
            return message

    def _write(self, message: PrecilaserMessage):
        while True:
            if self.instrument.bytes_in_buffer != 0:
                self._handle_message(self._read())
            else:
                break
        self.instrument.write(message.command_bytes)

    def _read(self) -> PrecilaserMessage:
        message = decompose_message(self.instrument.read())
        self._handle_message(message)
        return message

    def _read_until_reply(self, return_command: PrecilaserReturn) -> PrecilaserMessage:
        while True:
            message = self._read()
            if message.command == return_command.value:
                return message


class Amplifier(AbstractPrecilaserDevice):
    def __init__(self, resource_name: str):
        super().__init__(resource_name)

    @property
    def fault(self) -> bool:
        if self.status is not None:
            fault = sum([pds.fault for pds in self.status.pd_status]) != 0
            fault |= self.status.system_status.fault
            return fault
        else:
            return False

    def get_status(self):
        message = PrecilaserMessage(
            PrecilaserCommand.STATUS,
        )
        self._write(message)
        message = self._read()
        return self.status

    def set_current(self, current: float):
        current_int = int(round(current * 100, 0))
        message = PrecilaserMessage(PrecilaserCommand.SET_CURRENT, current_int)
        self._write(message)
        return_message = self._read_until_reply(PrecilaserReturn.SET_CURRENT)

    def enable(self):
        message = PrecilaserMessage(PrecilaserCommand.ENABLE, 0b111)
        self._write(message)

    def disable(self):
        message = PrecilaserMessage(PrecilaserCommand.ENABLE, 0b0)
        self._write(message)
        return


class SHGAmplifier(Amplifier):
    def __init__(self, resource_name: str):
        super().__init__(resource_name)
