# Precilaser

[![Python versions on PyPI](https://img.shields.io/pypi/pyversions/precilaser.svg)](https://pypi.python.org/pypi/precilaser/)
[![Precilaser version on PyPI](https://img.shields.io/pypi/v/precilaser.svg "Precilaser on PyPI")](https://pypi.python.org/pypi/precilaser/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

 Python interface for precilaser devices

Implements a python interface using pyvisa for 3 Precilaser devices:
* Precilaser Fiber DFB
* Precilaser Amplifier
* Precilaser SHG Amplifier

## Installation
`pip install precilaser` or install directly from source.

## Implemented Functionality
### Precilaser Fiber DFB
* `status`  
  retrieve the laser status, in a dataclass (with some of the boilerplate code removed; see `status.py` for more detail):
  ```Python
    @dataclass
    class SeedStatus:
      status_bytes: bytes
      endian: str
      temperature_set: float # grating temperature setpoint [C]
      temperature_act: float # grating temperature [C]
      temperature_diode: float # [C]
      current_set: int # [mA]
      current_act : int # [mA]
      wavelength: float # [nm]
      piezo_voltage: float # [V]
      emission: bool
      power: int
      run_hours: int
      run_minutes: int
  ```
* `temperature_setpoint`  
  get or set the grating temperature in C
* `piezo_voltage`  
  get or set the piezo voltage, from 0 V to 5 V
* `_get_serial_wavelength_params`  
  retrieve the parameters required to reconstruct the wavelength from the grating temperature
* `wavelength`  
  calculate the wavelength from the retrieved parameters and the grating temperature

### Precilaser Amplifier
* `status`  
  retrieve the amplifier status, in a dataclass (with some of the boilerplate code removed; see `status.py` for more detail):
  ```Python
  @dataclass
  class AmplifierStatus:
    status_bytes: bytes
    endian: str
    stable: bool
    system_status: SystemStatus
    driver_unlock: DriverUnlock
    driver_current: Tuple[float, ...]
    pd_value: Tuple[int, ...] # internal photodiode values in arb. units
    pd_status: Tuple[PDStatus, ...]
    temperatures: Tuple[float] # internal temperatures of amplifier stages etc.

  @dataclass
  class SystemStatus:
    status: int
    pd_protection: Tuple[bool, ...]
    temperature_protection: Tuple[bool, ...]
    fault: bool

  @dataclass
  class DriverUnlock:
    driver_unlock: int
    driver_enable_control: Tuple[bool, ...]
    driver_enable_flag: Tuple[bool, ...]
    interlock: bool # true if the interlock is ok

  @dataclass
  class PDStatus:
    status: int
    sampling_enable: bool
    hardware_protection: bool
    upper_limit_enabled: bool
    lower_limit_enabled: bool
    hardware_protection_event: bool
    upper_limit_event: bool
    lower_limit_event: bool
    fault: bool
  ```
* `current`  
  get or set the amplifier current [A]
* `enable()`  
  enable the amplifier
* `disable()`  
  disable the amplifier
* `save()`
  save amplifier settings to ROM
* `enable_power_stabilization()`  
  enable power stabilization mode; varies the amplifier current to keep the output power constant
* `disable_power_stabilization()`
  disable power stabilization mode

### Precilaser Amplifier
A subclass of the `Amplifier`, includes all `Amplifier` functionality plus additionally:
* `shg_temperature`
  get or set the shg crystal temperature [C]

## Example
```Python

from precilaser import SHGAmplifier

amp = SHGAmplifier("COM50", address = 0)

# change the SHG crystal temperature
amp.shg_temperature = 73.15