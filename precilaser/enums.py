from enum import Enum, auto
from typing import Literal

# byte order accepted by int.to_bytes / int.from_bytes
Endian = Literal["little", "big"]


class PrecilaserCommand(Enum):
    AMP_ENABLE = b"\x30"
    AMP_SET_CURRENT = b"\xa1"
    AMP_POWER_STAB = b"\x47"
    AMP_TEC_TEMPERATURE = b"\x87"
    AMP_STATUS = b"\x04"
    AMP_SAVE = b"\x8e"
    SEED_STATUS = b"\xa9"
    SEED_SET_TEMP = b"\xa5"
    SEED_SET_VOLTAGE = b"\xae"
    SEED_ENABLE = b"\xa8"
    SEED_SERIAL_WAV = b"\xaa"


class PrecilaserReturn(Enum):
    AMP_ENABLE = b"\x40"
    AMP_SET_CURRENT = b"\x41"
    AMP_POWER_STAB = b"I"
    AMP_TEC_TEMPERATURE = b"\x45"
    AMP_STATUS = b"\x44"
    AMP_SAVE = b"N"
    SEED_STATUS = b"\xb7"
    SEED_SET_TEMP = b"\xb3"
    SEED_SET_VOLTAGE = b"\xbe"
    SEED_ENABLE = b"\xb8"
    SEED_SERIAL_WAV = b"\xb0"


class PrecilaserMessageType(Enum):
    COMMAND = auto()
    RETURN = auto()


class PrecilaserDeviceType(Enum):
    AMP = auto()
    SEED = auto()
