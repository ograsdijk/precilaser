from .device import AbstractPrecilaserDevice
from .enums import PrecilaserDeviceType, PrecilaserCommand
from .status import SeedStatus


class Seed(AbstractPrecilaserDevice):
    def __init__(
        self,
        resource_name: str,
        address: int,
        header: bytes = b"P",
        terminator: bytes = b"\r\n",
        check_start: int = 1,
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.SEED,
    ):
        super().__init__(
            resource_name, address, header, terminator, check_start, device_type
        )

    @property
    def status(self) -> SeedStatus:
        message = self._generate_message(PrecilaserCommand.SEED_STATUS)
        self._write(message)
        message = self._read()
        return SeedStatus(message.param, self.endian)

    @property
    def temperature_setpoint(self) -> float:
        return self.status.temperature_set

    @temperature_setpoint.setter
    def temperature_setpoint(self, temperature: float):
        param = int(temperature * 1_000)
        # do not save to eeprom, i.e. add a zero to the end
        param = param << 1
        message = self._generate_message(PrecilaserCommand.SEED_SET_TEMP, param)
        self._write(message)
        message = self._read()

    @property
    def piezo_voltage(self) -> float:
        return self.status.current_set

    @piezo_voltage.setter
    def piezo_voltage(self, voltage: float):
        assert (
            voltage >= 0 and voltage <= 74
        ), "Piezo voltage cannot exceed 0V-74V range"
        param = int(voltage * 100)
        # do not save to eeprom, i.e. add a zero to the end
        param = param << 1
        message = self._generate_message(PrecilaserCommand.SEED_SET_VOLTAGE, param)
        self._write(message)
        message = self._read()
