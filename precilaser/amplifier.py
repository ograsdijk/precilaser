from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserDeviceType, PrecilaserReturn
from .message import PrecilaserMessage, decompose_message
from .status import PrecilaserStatus
from typing import Tuple
from pyvisa import VisaIOError


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

    def _read(self) -> PrecilaserMessage:
        while True:
            try:
                msg = self.instrument.read_bytes(1)
                if msg == self.header:
                    msg += self.instrument.read_bytes(2)
                    if msg == self.header + b'\x00' + self.address.to_bytes(1, self.endian):
                        msg += self.instrument.read_bytes(2)
                        msg += self.instrument.read_bytes(msg[-1] + 4)
                        message = decompose_message(msg, self.address, self.header, self.terminator, self.endian)
                        return message
            except VisaIOError as err:
                if "VI_ERROR_ASRL_OVERRUN" in err.args[0]:
                    continue
                else:
                    raise err

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        # the amplifier sends out a status message at a set time interval,
        # need to check for this message
        if message.command == PrecilaserReturn.AMP_STATUS:
            if message.payload is not None:
                self._status = PrecilaserStatus(message.payload)
            else:
                raise ValueError("no status data bytes retrieved")
            return message
        else:
            return message

    def _read_until_reply(self, return_command: PrecilaserReturn) -> PrecilaserMessage:
        while True:
            message = self._read()
            self._handle_message(message)
            if message.command == return_command:
                return message

    def _read_until_buffer_empty(self) -> None:
        while self.instrument.bytes_in_buffer > 0:
            message = self._read()
            self._handle_message(message)

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
        message = self._read_until_reply(PrecilaserReturn.AMP_STATUS)
        return self._status

    @property
    def current(self) -> float:
        return self.status.driver_current

    @current.setter
    def current(self, current: float):
        current_int = int(round(current * 100, 0))
        message = self._generate_message(
            PrecilaserCommand.AMP_SET_CURRENT, current_int.to_bytes(2, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_SET_CURRENT)

    def enable(self):
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b111.to_bytes(1, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_ENABLE)

    def disable(self):
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b0.to_bytes(1, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_ENABLE)


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
        self._shg_temperature = (0.0, 0.0)

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        # the amplifier sends out a status message at a set time interval,
        # need to check for this message
        if message.command == PrecilaserReturn.AMP_STATUS:
            if message.payload is not None:
                self._status = PrecilaserStatus(message.payload)
            else:
                raise ValueError("no status data bytes retrieved")
            return message
        elif message.command == PrecilaserReturn.AMP_TEC_TEMPERATURE:
            if message.payload is not None:
                self._shg_temperature = (
                    int.from_bytes(message.payload[1:3], 'big')/100,
                    int.from_bytes(message.payload[3:5], 'big')/100
                )
            else:
                raise ValueError("no status data bytes retrieved")
            return message
        else:
            return message

    @property
    def shg_temperature(self) -> Tuple[float, float]:
        self._read_until_buffer_empty()
        return self._shg_temperature
        