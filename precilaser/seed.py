from typing import Optional, Tuple

import time

from .device import AbstractPrecilaserDevice
from .enums import PrecilaserCommand, PrecilaserDeviceType, PrecilaserReturn
from .status import SeedStatus, AmplifierStatus

from .amplifier import status_handler


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

    def __exit__(self):
        self.rm.close()

    def _set_value(
        self,
        value: int,
        command: PrecilaserCommand,
        nbytes: int = 2,
        save: bool = False,
    ):
        payload = value.to_bytes(nbytes, self.endian)
        if save:
            payload += b"1"
        else:
            payload += b"0"
        message = self._generate_message(command, payload)
        self._write(message)
        return

    @property
    def status(self) -> SeedStatus:
        message = self._generate_message(PrecilaserCommand.SEED_STATUS)
        self._write(message)
        message = self._read()
        if message.payload is not None:
            return SeedStatus(message.payload, self.endian)
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
        if message.payload is not None:
            self._check_write_return(
                message.payload[:2], setpoint, "temperature setpoint"
            )
        else:
            raise ValueError(f"not set to requested value: {setpoint}")

    @property
    def piezo_voltage(self) -> float:
        return self.status.piezo_voltage

    @piezo_voltage.setter
    def piezo_voltage(self, voltage: float):
        assert voltage >= 0 and voltage <= 74, (
            "Piezo voltage cannot exceed 0V-74V range"
        )
        setpoint = int(voltage * 100)
        self._set_value(setpoint, PrecilaserCommand.SEED_SET_VOLTAGE)
        message = self._read()
        if message.payload is not None:
            self._check_write_return(message.payload[:2], setpoint, "piezo voltage")
        else:
            raise ValueError(f"not set to requested value: {setpoint}")

    def _get_serial_wavelength_params(self):
        message = self._generate_message(PrecilaserCommand.SEED_SERIAL_WAV)
        self._write(message)
        message = self._read()
        self.serial = message.payload[16:24]
        parameter_bytes = message.payload[25 : 25 + 64]
        self.wavelength_params = [parameter_bytes[i] for i in range(6)]

    @property
    def wavelength(self) -> float:
        status = self.status
        temp_grating_act = status.temperature_act * 1_000
        assert self.wavelength_params is not None, (
            "Wavelength parameters not loaded from device"
        )
        parameter = self.wavelength_params
        wavelength = (
            (parameter[0] << 8) | parameter[1]
        ) * temp_grating_act / 10_000 + (
            parameter[2] << 24
            | parameter[3] << 16
            | ((parameter[4] << 8) | parameter[5])
        )
        # manual states / 1_000 but this yields an incorrect wavelength
        return wavelength / 10_000

    @wavelength.setter
    def wavelength(self, wavelength: float):
        status = self.status
        assert self.wavelength_params is not None, (
            "Wavelength parameters not loaded from device"
        )
        parameter = self.wavelength_params
        temp_grating_act = (
            (
                wavelength * 10_000
                - (
                    parameter[2] << 24
                    | parameter[3] << 16
                    | ((parameter[4] << 8) | parameter[5])
                )
            )
            * 10_000
            / ((parameter[0] << 8) | parameter[1])
        )
        temp_set = temp_grating_act / 1_000
        self.temperature_setpoint = temp_set


class SeedControl(AbstractPrecilaserDevice):
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
        self.serial: bytes | None = None
        self.wavelength_params: tuple[int, ...] | None = None
        self._message_handling[PrecilaserReturn.AMP_STATUS] = (
            "_status",
            status_handler,
        )

    def enable(self) -> None:
        """Enables the seed.

        Raises:
            ValueError: if the seed has not been enabled
        """
        self._set_value(1, PrecilaserCommand.ENABLE, nbytes=1)
        message = self._read_until_reply(PrecilaserReturn.ENABLE)
        if message.payload != b"Enable set ok":
            raise ValueError("emission not enabled")

    def disable(self) -> None:
        """Disables the seed.

        Raises:
            ValueError: if the seed has not been disabled
        """
        self._set_value(0, PrecilaserCommand.ENABLE, nbytes=1)
        message = self._read_until_reply(PrecilaserReturn.ENABLE)
        # The laser's answer is the same for disable / enable
        if message.payload != b"Enable set ok":
            raise ValueError("emission not disabled")

    def _set_value(
        self,
        value: int,
        command: PrecilaserCommand,
        nbytes: int = 2,
    ) -> None:
        """Sets a value by writing on the seed.

        Args:
            value: The desired value
            command: The command associated to the value to write
            nbytes: The number of bytes the value should take
        """
        # Unlike the seed comm port there is no "save" parameter here
        payload = value.to_bytes(nbytes, self.endian)
        message = self._generate_message(command, payload)

        self._write(message)

    # The control port of the seed is actually a small amplifier according to Precilaser.
    # Which is why some commands from Amplifier are reused.
    @property
    def status(self) -> AmplifierStatus:
        """Reads the buffer until a status is encountered.
        The seed returns it regularly and it's handled by status_handler

        Returns:
            The updated status
        Raises:
            ValueError: if the status is None
        """
        self._read_until_reply(PrecilaserReturn.AMP_STATUS)
        if self._status is None:
            raise ValueError("No status retrieved")
        return self._status

    @property
    def current(self) -> float:
        """Amplifier current [A] of all stages.

        Returns:
            amplifier current [A] of all stages
        """
        self._read_until_reply(PrecilaserReturn.AMP_STATUS)
        return sum(self.status.driver_current)

    @current.setter
    def current(self, current: float) -> None:
        """Set the amplifier current.

        Args:
            current (float): current [A]
        """
        current_int = int(round(current * 100, 0))
        self._set_value(current_int, PrecilaserCommand.SET_CURRENT)
        self._read_until_reply(PrecilaserReturn.SET_CURRENT)

    def set_current_down(self, current: int) -> None:
        """Sets the current down on the amplifier.

        Args:
            current: The desired current
        Raises:
            ValueError: if the current is not set correctly
        """
        if current >= self.current:
            raise ValueError("Actual current cannot be lower than current setting")
        while self.current > current:
            if self.current - 1 <= current:
                self.current = current
                break
            self.current = self.current - 1
            time.sleep(10)

        if self.current != current:
            raise ValueError("Current setting was not set correctly.")

    def set_current_up(self, current: int) -> None:
        """Sets the current up on the amplifier.

        Args:
            current: the desired current
        Raises:
            ValueError: If the current is not set correctly
        """
        while self.current < current:
            if self.current + 1 >= current:
                self.current = current
                break
            self.current = self.current + 1
            time.sleep(10)

        if self.current != current:
            raise ValueError("Current setting was not set correctly.")
