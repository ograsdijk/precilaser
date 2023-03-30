from abc import ABC
from typing import Callable, Optional, cast

import pyvisa
from pyvisa import VisaIOError

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
        """
        Generic Precilaser device interface

        Args:
            resource_name (str): resource name, e.g. com port
            address (int): device address
            header (bytes): message header
            terminator (bytes): message terminator
            device_type (PrecilaserDeviceType): device type
            endian (str): endian of message payload
        """
        self.rm = pyvisa.ResourceManager()
        self.instrument = cast(
            pyvisa.resources.SerialInstrument,
            self.rm.open_resource(
                resource_name=resource_name, baud_rate=115200, write_termination=""
            ),
        )

        self.address = address
        self.header = header
        self.terminator = terminator
        self.device_type = device_type
        self.endian = endian

        # dict with return types that require message handling; the tuple for each
        # return type includes the attr to write to and the transformation function
        self._message_handling: dict[PrecilaserReturn, tuple[str, Callable]] = {}

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        """
        message handling function. Some precilaser devices periodically send status
        updates to the host, which require some message handling to save those results.
        Examples are the SHG crystal temperature and amplifier status

        Args:
            message (PrecilaserMessage): message

        Raises:
            ValueError: raises if the message payload is empty

        Returns:
            PrecilaserMessage: message
        """
        if len(self._message_handling) == 0:
            return message
        else:
            for ret_cmd, (attr, transform) in self._message_handling.items():
                if message.command == ret_cmd:
                    if message.payload is not None:
                        setattr(self, attr, transform(message))
                    else:
                        raise ValueError(f"{ret_cmd.name} no data bytes retrieved")
            return message

    def _write(self, message: PrecilaserMessage):
        """
        Write a message to the Precilaser device

        Args:
            message (PrecilaserMessage): message
        """
        self.instrument.write_raw(bytes(message.command_bytes))  # type: ignore

    def _read_single_message(self) -> PrecilaserMessage:
        """
        Read a single message from the Precilaser device

        Raises:
            err: raise any error that isn't a VI_ERROR_ASRL_OVERRUN

        Returns:
            PrecilaserMessage: message
        """
        while True:
            try:
                msg = self.instrument.read_bytes(1)
                if msg == self.header:
                    msg += self.instrument.read_bytes(2)
                    if msg == self.header + b"\x00" + self.address.to_bytes(
                        1, self.endian
                    ):
                        msg += self.instrument.read_bytes(2)
                        msg += self.instrument.read_bytes(msg[-1] + 4)
                        message = decompose_message(
                            msg, self.address, self.header, self.terminator, self.endian
                        )
                        return message
            except VisaIOError as err:
                if "VI_ERROR_ASRL_OVERRUN" in err.args[0]:
                    continue
                else:
                    raise err

    def _read(self) -> PrecilaserMessage:
        """
        Read and handle a message from a Precilaser device

        Returns:
            PrecilaserMessage: message
        """
        message = self._read_single_message()
        self._handle_message(message)
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
        self, command: PrecilaserCommand, payload: Optional[bytes] = None
    ) -> PrecilaserMessage:
        """
        Generate a message to send to a Precilaser device

        Args:
            command (PrecilaserCommand): command to send
            payload (Optional[bytes], optional): command payload. Defaults to None.

        Returns:
            PrecilaserMessage: message
        """
        message = PrecilaserMessage(
            command=command,
            address=self.address,
            payload=payload,
            header=self.header,
            terminator=self.terminator,
            endian=self.endian,
            type=PrecilaserMessageType.COMMAND,
        )
        return message
