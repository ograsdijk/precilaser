from typing import Optional, Tuple

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
        self.serial: Optional[bytes] = None
        self.wavelength_params: Optional[Tuple[int, ...]] = None

    def _set_value(
        self,
        value: int,
        command: PrecilaserCommand,
        nbytes: int = 2,
        save: bool = False,
    ):
        param_bytes = value.to_bytes(nbytes, self.endian)
        if save:
            param_bytes += b"1"
        else:
            param_bytes += b"0"
        param = int.from_bytes(param_bytes, self.endian)
        message = self._generate_message(command, param)
        self._write(message)
        return

    @property
    def status(self) -> SeedStatus:
        message = self._generate_message(PrecilaserCommand.SEED_STATUS)
        self._write(message)
        message = self._read()
        if message.param is not None:
            return SeedStatus(message.param, self.endian)
        else:
            raise ValueError("no status data bytes retrieved")

    @property
    def temperature_setpoint(self) -> float:
        return self.status.temperature_set

    @temperature_setpoint.setter
    def temperature_setpoint(self, temperature: float):
        setpoint = int(temperature * 1_000)
        self._set_value(setpoint, PrecilaserCommand.SEED_SET_TEMP)
        message = self._read()
        self._check_write_return(message.payload[:2], setpoint, "temperature setpoint")

    @property
    def piezo_voltage(self) -> float:
        return self.status.piezo_voltage

    @piezo_voltage.setter
    def piezo_voltage(self, voltage: float):
        assert (
            voltage >= 0 and voltage <= 74
        ), "Piezo voltage cannot exceed 0V-74V range"
        setpoint = int(voltage * 100)
        self._set_value(setpoint, PrecilaserCommand.SEED_SET_VOLTAGE)
        message = self._read()
        self._check_write_return(message.payload[:2], setpoint, "piezo voltage")

    def enable(self):
        self._set_value(True, PrecilaserCommand.SEED_ENABLE)
        message = self._read()
        self._check_write_return(message.payload, True, "enable laser")

    def disable(self):
        self._set_value(False, PrecilaserCommand.SEED_ENABLE)
        message = self._read()
        self._check_write_return(message.payload, False, "disable laser")

    def _get_serial_wavelength_params(self):
        message = self._generate_message(PrecilaserCommand.SEED_SERIAL_WAV)
        self._write(message)
        message = self._read()
        self.serial = message.payload[16:24]
        parameter_bytes = message.payload[25 : 25 + 64]
        self.wavelength_params = [
            int.from_bytes(parameter_bytes[i], self.endian) for i in range(6)
        ]

    @property
    def wavelength(self) -> float:
        status = self.status
        temp_grating_act = status.temperature_act
        assert (
            self.wavelength_params is not None
        ), "Wavelength parameters not loaded from device"
        parameter = self.wavelength_params
        wavelength = ((parameter[0] << 8) | parameter[1]) * temp_grating_act / 10000 + (
            parameter[2] << 24
            | parameter[3] << 16
            | ((parameter[4] << 8) | parameter[5])
        )
        return wavelength / 1_000
