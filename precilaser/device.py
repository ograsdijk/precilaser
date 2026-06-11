from abc import ABC
from typing import Callable, Optional

import serial

from .enums import (
    Endian,
    PrecilaserCommand,
    PrecilaserDeviceType,
    PrecilaserMessageType,
    PrecilaserReturn,
)
from .message import PrecilaserMessage, decompose_message


class AbstractPrecilaserDevice(ABC):
    def __init__(
        self,
        port: str,
        address: int,
        header: bytes,
        terminator: bytes,
        device_type: PrecilaserDeviceType,
        endian: Endian,
        timeout: float = 1.0,
    ):
        """
        Generic Precilaser device interface

        Args:
            port (str): serial port, e.g. "COM6" or "/dev/ttyUSB0"
            address (int): device address
            header (bytes): message header
            terminator (bytes): message terminator
            device_type (PrecilaserDeviceType): device type
            endian (str): endian of message payload
            timeout (float): serial read timeout [s]. Defaults to 1.0 s.
        """
        self.instrument = serial.Serial(port=port, baudrate=115200, timeout=timeout)

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
        self.instrument.write(bytes(message.command_bytes))

    def _read_exact(self, n: int) -> bytes:
        """
        Read exactly n bytes from the device, raising on a short read.

        pyserial's read(n) returns up to n bytes, returning fewer (or none) once
        the read timeout elapses. A short read therefore means the device went
        silent mid-frame.

        Args:
            n (int): number of bytes to read

        Raises:
            TimeoutError: if fewer than n bytes are received before the timeout

        Returns:
            bytes: exactly n bytes
        """
        data = self.instrument.read(n)
        if len(data) < n:
            raise TimeoutError(f"expected {n} bytes, received {len(data)}")
        return data

    def _read_single_message(self) -> PrecilaserMessage:
        """
        Read a single message from the Precilaser device

        Raises:
            TimeoutError: if no data is received before the read timeout

        Returns:
            PrecilaserMessage: message
        """
        while True:
            # scan byte-by-byte until the header is found to (re)synchronize
            msg = self.instrument.read(1)
            if len(msg) == 0:
                raise TimeoutError("no data received from device")
            if msg != self.header:
                continue
            msg += self._read_exact(2)
            if msg != self.header + b"\x00" + self.address.to_bytes(1, self.endian):
                continue
            msg += self._read_exact(2)
            msg += self._read_exact(msg[-1] + 4)
            return decompose_message(
                msg, self.address, self.header, self.terminator, self.endian
            )

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

    def close(self) -> None:
        """Close the underlying serial port."""
        self.instrument.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
