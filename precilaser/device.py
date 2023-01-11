from abc import ABC
from typing import Optional

import pyvisa

from .enums import (
    PrecilaserCommand,
    PrecilaserDeviceType,
    PrecilaserMessageType,
    PrecilaserReturn,
)
from .message import PrecilaserMessage, decompose_message


class AbstractPrecilaserDevice(ABC):
    def __init__(
        self,
        resource_name: str,
        address: int,
        header: bytes,
        terminator: bytes,
        device_type: PrecilaserDeviceType,
        endian: str,
    ):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(
            resource_name=resource_name, baud_rate=115200, write_termination=""
        )

        self.address = address
        self.header = header
        self.terminator = terminator
        self.device_type = device_type
        self.endian = endian

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        return message

    def _write(self, message: PrecilaserMessage):
        while True:
            if self.instrument.bytes_in_buffer != 0:
                self._handle_message(self._read())
            else:
                break
        self.instrument.write_raw(bytes(message.command_bytes))

    def _read(self) -> PrecilaserMessage:
        message = decompose_message(
            self.instrument.read_raw(),
            self.address,
            self.header,
            self.terminator,
            self.endian,
        )
        self._handle_message(message)
        return message

    def _read_until_reply(self, return_command: PrecilaserReturn) -> PrecilaserMessage:
        while True:
            message = self._read()
            if message.command == return_command.value:
                return message

    def _check_write_return(
        self, data: bytes, value: int, value_name: Optional[str] = None
    ):
        if int.from_bytes(data, self.endian) != value:
            error_str = (
                f"not set to requested value: {value} !="
                f" {int.from_bytes(data, self.endian)}"
            )
            if value_name is not None:
                error_str = f"{value_name} {error_str}"
            raise ValueError(error_str)
        return

    def _generate_message(
        self, command: PrecilaserCommand, param: Optional[int] = None
    ) -> PrecilaserMessage:
        message = PrecilaserMessage(
            command,
            param,
            self.address,
            self.header,
            self.terminator,
            self.endian,
            PrecilaserMessageType.COMMAND,
        )
        return message
