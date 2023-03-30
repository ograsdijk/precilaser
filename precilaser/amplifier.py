from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserDeviceType, PrecilaserReturn
from .message import PrecilaserMessage
from .status import PrecilaserStatus
from typing import Tuple

def status_handler(message: PrecilaserMessage) -> PrecilaserStatus:
    return PrecilaserStatus(message.payload)

def temperature_handler(message: PrecilaserMessage) -> Tuple[float, float]:
    return (
        int.from_bytes(message.payload[1:3], message.endian) / 100,
        int.from_bytes(message.payload[3:5], message.endian) / 100,
    )

class Amplifier(AbstractPrecilaserDevice):
    def __init__(
        self,
        resource_name: str,
        address: int,
        header: bytes = b"\x50",
        terminator: bytes = b"\x0d\x0a",
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.AMP,
        endian: str = "big",
    ):
        super().__init__(
            resource_name, address, header, terminator, device_type, endian
        )
        self._status = None

        self._message_handling[PrecilaserReturn.AMP_STATUS] = (
            "_status",
            status_handler,
        )

    def _read_until_reply(self, return_command: PrecilaserReturn) -> PrecilaserMessage:
        while True:
            message = self._read()
            if message.command == return_command:
                return message

    def _read_until_buffer_empty(self) -> None:
        while self.instrument.bytes_in_buffer > 0:
            self._read()

    @property
    def fault(self) -> bool:
        if self.status is not None:
            fault = sum([pds.fault for pds in self.status.pd_status]) != 0
            fault |= self.status.system_status.fault
            return fault
        else:
            return False

    @property
    def status(self) -> PrecilaserStatus:
        # message = self._generate_message(PrecilaserCommand.AMP_STATUS)
        # self._write(message)
        self._read_until_buffer_empty()
        self._read_until_reply(PrecilaserReturn.AMP_STATUS)
        return self._status

    @property
    def current(self) -> float:
        return self.status.driver_current

    @current.setter
    def current(self, current: float) -> None:
        current_int = int(round(current * 100, 0))
        message = self._generate_message(
            PrecilaserCommand.AMP_SET_CURRENT, current_int.to_bytes(2, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_SET_CURRENT)

    def enable(self) -> None:
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b111.to_bytes(1, self.endian)
        )
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Enable set ok":
            raise ValueError(f"Amplifier not enabled; {message.payload}")

    def disable(self) -> None:
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b0.to_bytes(1, self.endian)
        )
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Enable set ok":
            raise ValueError(f"Amplifier not disabled; {message.payload}")

    def save(self) -> None:
        message = self._generate_message(PrecilaserCommand.AMP_SAVE, None)
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_SAVE)
        if message.payload != b"ROM saved":
            raise ValueError(f"Values not saved to ROM; {message.payload}")

class SHGAmplifier(Amplifier):
    def __init__(
        self,
        resource_name: str,
        address: int,
        header: bytes = b"\x50",
        terminator: bytes = b"\x0d\x0a",
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.AMP,
        endian: str = "big",
    ):
        super().__init__(
            resource_name, address, header, terminator, device_type, endian
        )
        self._temperatures = (0.0, 0.0)
        self._message_handling[PrecilaserReturn.AMP_TEC_TEMPERATURE] = (
            "_temperatures",
            temperature_handler,
        )

    @property
    def shg_temperature(self) -> float:
        self._read_until_buffer_empty()
        return self._temperatures[1]

    @shg_temperature.setter
    def shg_temperature(self, temperature: float) -> None:
        payload = b"\x00\x02"
        payload += int(temperature * 100).to_bytes(2, self.endian)
        message = self._generate_message(PrecilaserCommand.AMP_TEC_TEMPERATURE, payload)
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_TEC_TEMPERATURE)

    def enable_power_stabilization(self) -> None:
        message = self._generate_message(PrecilaserCommand.AMP_POWER_STAB, b"\x01")
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Stable set ok":
            raise ValueError(f"Power stabilization not enabled: {message.payload}")

    def disable_power_stabilization(self) -> None:
        message = self._generate_message(PrecilaserCommand.AMP_POWER_STAB, b"\x00")
        self._write(message)
        message = self._read_until_reply(PrecilaserReturn.AMP_ENABLE)
        if message.payload != b"Stable set ok":
            raise ValueError(f"Power stabilization not disabled: {message.payload}")
