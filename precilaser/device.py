from abc import ABC
from typing import Tuple

import pyvisa

from .enums import PrecilaserReturn
from .message import PrecilaserMessage, decompose_message
from .status import PrecilaserStatus


class AbstractPrecilaserDevice(ABC):
    def __init__(
        self, resource_name: str, header: bytes, terminator: bytes, check_start: int
    ):
        self.rm = pyvisa.ResourceManager()
        self.instrument = self.rm.open_resource(
            resource_name=resource_name, baud_rate=115200, write_termination=""
        )
        self.header = header
        self.terminator = terminator
        self.check_start = check_start

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
        message = decompose_message(
            self.instrument.read(), self.header, self.terminator, self.check_start
        )
        self._handle_message(message)
        return message

    def _read_until_reply(self, return_command: PrecilaserReturn) -> PrecilaserMessage:
        while True:
            message = self._read()
            if message.command == return_command.value:
                return message
