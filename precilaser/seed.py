from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserDeviceType
from .status import SeedStatus


class Seed(AbstractPrecilaserDevice):
    def __init__(
        self,
        resource_name: str,
        address: int,
        header: bytes = b"P",
        terminator: bytes = b"\r\n",
        device_type: PrecilaserDeviceType = PrecilaserDeviceType.SEED,
        endian: str = "big",
    ):
        super().__init__(
            resource_name, address, header, terminator, device_type, endian
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
        param_bytes = param.to_bytes(2, self.endian)
        param_bytes += b"0"
        param = int.from_bytes(param_bytes, self.endian)
        message = self._generate_message(PrecilaserCommand.SEED_SET_TEMP, param)
        self._write(message)
        message = self._read()
        assert int.from_bytes(message.command_bytes[5:7], self.endian) == int(
            temperature * 1_000
        ), "temperature setpoint not set to requested value"

    @property
    def piezo_voltage(self) -> float:
        return self.status.piezo_voltage

    @piezo_voltage.setter
    def piezo_voltage(self, voltage: float):
        assert (
            voltage >= 0 and voltage <= 74
        ), "Piezo voltage cannot exceed 0V-74V range"
        param = int(voltage * 100)
        # do not save to eeprom, i.e. add a zero to the end
        param_bytes = param.to_bytes(2, self.endian)
        param_bytes += b"0"
        param = int.from_bytes(param_bytes, "big")
        message = self._generate_message(PrecilaserCommand.SEED_SET_VOLTAGE, param)
        self._write(message)
        message = self._read()
        assert int.from_bytes(message.command_bytes[5:7], self.endian) == int(
            voltage * 100
        ), "piezo voltage not set to requested value"
