from enum import Enum, auto


class PrecilaserCommand(Enum):
    AMP_ENABLE = b"\x30"
    AMP_SETCURRENT = b"\xa1"
    AMP_POWER_STABILIZATION = b"\x47"
    AMP_STATUS = b"\x04"
    SEED_QUERY = b"0xA9"
    SEED_SET_TEMP = b"0xA5"
    SEED_SET_VOLTAGE = b"0xAE"


class PrecilaserReturn(Enum):
    AMP_ENABLE = b"\x40"
    AMP_SETCURRENT = b"\x41"
    AMP_POWER_STABILIZATION = b"\x44"
    SEED_QUERY = b"0xB7"
    SEED_SET_TEMP = b"0xB5"
    SEED_SET_VOLTAGE = b"0xBE"


class PrecilaserMessageType(Enum):
    COMMAND = auto()
    RETURN = auto()
