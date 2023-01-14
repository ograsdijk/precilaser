from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserDeviceType, PrecilaserReturn
from .message import PrecilaserMessage
from .status import PrecilaserStatus


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

    def _handle_message(self, message: PrecilaserMessage) -> PrecilaserMessage:
        # the amplifier sends out a status message at a set time interval,
        # need to check for this message
        if message.command == PrecilaserReturn.AMP_STATUS.value:
            if message.payload is not None:
                self.status = PrecilaserStatus(message.payload)
            else:
                raise ValueError("no status data bytes retrieved")
            return message
        else:
            return message

    @property
    def fault(self) -> bool:
        if self.status is not None:
            fault = sum([pds.fault for pds in self.status.pd_status]) != 0
            fault |= self.status.system_status.fault
            return fault
        else:
            return False

    def get_status(self) -> PrecilaserStatus:
        message = self._generate_message(PrecilaserCommand.AMP_STATUS)
        self._write(message)
        message = self._read()
        return self.status

    def set_current(self, current: float):
        current_int = int(round(current * 100, 0))
        message = self._generate_message(
            PrecilaserCommand.AMP_SET_CURRENT, current_int.to_bytes(2, self.endian)
        )
        self._write(message)
        self._read_until_reply(PrecilaserReturn.AMP_SET_CURRENT)

    def enable(self):
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b111.to_bytes(3, self.endian)
        )
        self._write(message)

    def disable(self):
        message = self._generate_message(
            PrecilaserCommand.AMP_ENABLE, 0b0.to_bytes(3, self.endian)
        )
        self._write(message)
        return


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
