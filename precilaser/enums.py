from enum import Enum, auto


class PrecilaserCommand(Enum):
    AMP_ENABLE = b"\x30"
    AMP_SET_CURRENT = b"\xa1"
    AMP_TEC_TEMPERATURE = b"\x47"
    AMP_STATUS = b"\x04"
    SEED_STATUS = b"\xA9"
    SEED_SET_TEMP = b"\xA5"
    SEED_SET_VOLTAGE = b"\xAE"
    SEED_ENABLE = b"\xA8"
    SEED_SERIAL_WAV = b"\xAA"


class PrecilaserReturn(Enum):
    AMP_ENABLE = b"\x40"
    AMP_SET_CURRENT = b"\x41"
    AMP_TEC_TEMPERATURE = b"\x45"
    AMP_STATUS = b"\x44"
    SEED_STATUS = b"\xB7"
    SEED_SET_TEMP = b"\xB3"
    SEED_SET_VOLTAGE = b"\xBE"
    SEED_ENABLE = b"\xB8"
    SEED_SERIAL_WAV = b"\xB0"


class PrecilaserMessageType(Enum):
    COMMAND = auto()
    RETURN = auto()


class PrecilaserDeviceType(Enum):
    AMP = auto()
    SEED = auto()
