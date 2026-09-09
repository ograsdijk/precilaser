import time
from typing import Optional, Tuple

from .device import AbstractPrecilaserDevice
from .enums import Endian, PrecilaserCommand, PrecilaserDeviceType, PrecilaserReturn
from .message import PrecilaserMessage
from .status import AmplifierStatus

# The Precilaser Amplifiers send out periodic messages with the laser status and in the
# case of the SHG amplifier also the TEC temperatures. This happens roughly every
# 300 ms, which means the serial buffer can fill up quickly. Some additional functions
# such as _read_until_buffer_empty and read_until_reply had to be added to account for
# this.
#
# Because the device is never quiet, the pyserial read timeout only fires when the
# device goes silent; it cannot bound a loop in which every read succeeds. Both loops
# below therefore carry their own wall-clock deadline, so waiting for a reply that
# never arrives raises instead of spinning forever.


# Wall-clock bound for the read loops [s]. A reply follows the write immediately, so
# the only legitimate wait is on the status frames already in flight (~300 ms each);
# 2 s leaves ample margin while still failing well inside typical caller timeouts.
DEFAULT_REPLY_TIMEOUT = 2.0


def status_handler(message: PrecilaserMessage) -> AmplifierStatus:
    """
    Message handler for receiving the status message from the amplifier.

    Args:
        message (PrecilaserMessage): message with the status payload

    Raises:
        ValueError: Raise if the payload is empty

    Returns:
        AmplifierStatus: laser status dataclass
    """
    if message.payload is None:
        raise ValueError("No status bytes retrieved")
    return AmplifierStatus(message.payload)


def temperature_handler(message: PrecilaserMessage) -> Tuple[float, float]:
    """
    Message handler for receiving the TEC temperatures

    Args:
        message (PrecilaserMessage): message with the temperature payload

    Raises:
        ValueError: raise if the payload is empty

    Returns:
        Tuple[float, float]: tec temperatures
    """
    if message.payload is None:
        raise ValueError("No TEC temperature bytes retrieved")
    return (
        int.from_bytes(message.payload[1:3], message.endian) / 100,
        int.from_bytes(message.payload[3:5], message.endian) / 100,
    )


class Amplifier(AbstractPrecilaserDevice):
    def __init__(
        self,
        port: str,
        address: int,
        header: bytes = b"\x50",
        terminator: bytes = b"\x0d\x0a",
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.AMP,
        endian: Endian = "big",
        timeout: float = 1.0,
    ):
        super().__init__(
            port, address, header, terminator, device_type, endian, timeout
        )
        # Precilaser amplifiers return a status message periodically; when a status
        # message is retrieved, _handle_message ensures the message payload is
        # transformed to a PrecilaserStatus and written to _status
        self._message_handling[PrecilaserReturn.AMP_STATUS] = (
            "_status",
            status_handler,
        )

        self._status: Optional[AmplifierStatus] = None

    def _read_until_reply(
        self,
        return_command: PrecilaserReturn,
        timeout: float = DEFAULT_REPLY_TIMEOUT,
    ) -> PrecilaserMessage:
        """
        Retrieve messages from the device until a message with the return code matching
        return_command is retrieved.

        The amplifier interleaves unsolicited status frames with command replies on the
        same stream, so non-matching frames are discarded here; their payloads are still
        cached by _handle_message.

        Args:
            return_command (PrecilaserReturn): message command to wait for
            timeout (float): wall-clock bound on the whole loop [s]. Defaults to
                DEFAULT_REPLY_TIMEOUT.

        Raises:
            TimeoutError: if no matching message is retrieved within timeout

        Returns:
            PrecilaserMessage: Message matching the return command
        """
        deadline = time.monotonic() + timeout
        while True:
            # checked before each read so the terminator-resync path below, which can
            # loop without consuming a whole frame, is bounded as well
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"no {return_command.name} reply received within {timeout} s"
                )
            try:
                message = self._read()
            except ValueError as error:
                # when the buffer is full a partial message can lead to a invalid
                # message terminator error
                if "invalid message terminator" in error.args[0]:
                    continue
                else:
                    raise error
            if message.command == return_command:
                return message

    def _read_until_buffer_empty(self, timeout: float = DEFAULT_REPLY_TIMEOUT) -> None:
        """
        Retrieve messages from the device until the serial buffer is empty.

        Args:
            timeout (float): wall-clock bound on the whole loop [s]. Defaults to
                DEFAULT_REPLY_TIMEOUT.

        Raises:
            TimeoutError: if the buffer has not drained within timeout, i.e. the device
                produces frames at least as fast as they are read
        """
        deadline = time.monotonic() + timeout
        while self.instrument.in_waiting > 0:
            if time.monotonic() > deadline:
                raise TimeoutError(f"serial buffer did not drain within {timeout} s")
            try:
                self._read()
            except ValueError as error:
                # when the buffer is full a partial message can lead to a invalid
                # message terminator error
                if "invalid message terminator" in error.args[0]:
                    continue
                else:
                    raise error

    @property
    def fault(self) -> bool:
        if self.status is not None:
            fault = sum([pds.fault for pds in self.status.pd_status]) != 0
            fault |= self.status.system_status.fault
            return fault
        else:
            return False

    @property
    def status(self) -> AmplifierStatus:
        # message = self._generate_message(PrecilaserCommand.AMP_STATUS)
        # self._write(message)
        self._read_until_buffer_empty()
        self._read_until_reply(PrecilaserReturn.AMP_STATUS)
        if self._status is None:
            raise ValueError("No status retrieved")
        return self._status

    @property
    def current(self) -> Tuple[float, ...]:
        """
        Amplifier current [A] of all stages

        Returns:
            Tuple[float, ...]: amplifier current [A] of all stages
        """
        self._read_until_buffer_empty()
        return self.status.driver_current

    @current.setter
    def current(self, current: float) -> None:
        """
        Set the amplifier current

        Args:
            current (float): current [A]
        """
        current_int = int(round(current * 100, 0))
        message = self._generate_message(
            PrecilaserCommand.AMP_SET_CURRENT, current_int.to_bytes(2, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_SET_CURRENT)

    def enable(self) -> None:
        """
        Enable amplifier

        Raises:
            ValueError: raises if the amplifier isn't enabled
        """
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b111.to_bytes(1, self.endian)
        )
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Enable set ok":
            raise ValueError(f"Amplifier not enabled; {message.payload!r}")

    def disable(self) -> None:
        """
        Disable amplifier

        Raises:
            ValueError: raises if the amplifier isn't disabled
        """
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b0.to_bytes(1, self.endian)
        )
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Enable set ok":
            raise ValueError(f"Amplifier not disabled; {message.payload!r}")

    def save(self) -> None:
        """
        Save settings to ROM

        Raises:
            ValueError: raises if settings aren't saved
        """
        message = self._generate_message(PrecilaserCommand.AMP_SAVE, None)
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_SAVE)
        if message.payload != b"ROM saved":
            raise ValueError(f"Values not saved to ROM; {message.payload!r}")

    def enable_power_stabilization(self) -> None:
        """
        Enable power stabilization

        Raises:
            ValueError: raises if power stabilization isn't enabled
        """
        message = self._generate_message(PrecilaserCommand.AMP_POWER_STAB, b"\x01")
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_POWER_STAB)
        if message.payload != b"Stable set ok":
            raise ValueError(f"Power stabilization not enabled: {message.payload!r}")

    def disable_power_stabilization(self) -> None:
        """
        Disable power stabilization

        Raises:
            ValueError: raises if power stabilization isn't disabled
        """
        message = self._generate_message(PrecilaserCommand.AMP_POWER_STAB, b"\x00")
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_POWER_STAB)
        if message.payload != b"Stable set ok":
            raise ValueError(f"Power stabilization not disabled: {message.payload!r}")


class SHGAmplifier(Amplifier):
    def __init__(
        self,
        port: str,
        address: int,
        header: bytes = b"\x50",
        terminator: bytes = b"\x0d\x0a",  # '\r\n'
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.AMP,
        endian: Endian = "big",
        timeout: float = 1.0,
    ):
        super().__init__(
            port, address, header, terminator, device_type, endian, timeout
        )
        # Precilaser SHG amplifiers return a TEC temperature message periodically; when
        # a TEC temperature message is retrieved, _handle_message ensures the message
        # payload is transformed to a tuple[float, float] and written to _temperatures
        self._message_handling[PrecilaserReturn.AMP_TEC_TEMPERATURE] = (
            "_temperatures",
            temperature_handler,
        )
        self._temperatures = (0.0, 0.0)

    @property
    def shg_temperature(self) -> float:
        """
        Temperature [C] of the SHG crystal

        Returns:
            float: crystal temperature [C]
        """
        self._read_until_buffer_empty()
        return self._temperatures[1]

    @shg_temperature.setter
    def shg_temperature(self, temperature: float) -> None:
        """
        Set the SHG crystal temperature [C]

        Args:
            temperature (float): crystal temperature [C]
        """
        payload = b"\x00\x02"
        payload += int(temperature * 100).to_bytes(2, self.endian)
        message = self._generate_message(PrecilaserCommand.AMP_TEC_TEMPERATURE, payload)
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_TEC_TEMPERATURE)
