from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserReturn
from .message import PrecilaserMessage


class Amplifier(AbstractPrecilaserDevice):
    def __init__(
        self,
        resource_name: str,
        header: bytes = b"\x50\x00\x00",
        terminator: bytes = b"\x0d\x0a",
        check_start: int = 5,
    ):
        super().__init__(resource_name, header, terminator, check_start)

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
            PrecilaserCommand.AMP_STATUS,
        )
        self._write(message)
        message = self._read()
        return self.status

    def set_current(self, current: float):
        current_int = int(round(current * 100, 0))
        message = PrecilaserMessage(PrecilaserCommand.AMP_SETCURRENT, current_int)
        self._write(message)
        return_message = self._read_until_reply(PrecilaserReturn.SET_CURRENT)

    def enable(self):
        message = PrecilaserMessage(PrecilaserCommand.AMP_ENABLE, 0b111)
        self._write(message)

    def disable(self):
        message = PrecilaserMessage(PrecilaserCommand.AMP_ENABLE, 0b0)
        self._write(message)
        return


class SHGAmplifier(Amplifier):
    def __init__(
        self,
        resource_name: str,
        header: bytes = b"\x50\x00\x00",
        terminator: bytes = b"\x0d\x0a",
        check_start: int = 5,
    ):
        super().__init__(resource_name, header, terminator, check_start)
