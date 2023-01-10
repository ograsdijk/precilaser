from enum import Enum, auto


class PrecilaserCommand(Enum):
    ENABLE = b"\x30"
    SET_CURRENT = b"\xa1"
    POWER_STABILIZATION = b"\x47"
    STATUS = b"\x04"


class PrecilaserReturn(Enum):
    ENABLE = b"\x40"
    SET_CURRENT = b"\x41"
    STATUS = b"\x44"


class PrecilaserMessageType(Enum):
    COMMAND = auto()
    RETURN = auto()
