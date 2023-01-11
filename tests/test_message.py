from precilaser.message import PrecilaserMessage
from precilaser.enums import (
    PrecilaserCommand,
    PrecilaserMessageType,
    PrecilaserReturn
)

def test_precilaser_message():
    current = int(1.5*100)
    message = PrecilaserMessage(
        PrecilaserCommand.AMP_SET_CURRENT, current, 0, b"\x50", b"\x0d\x0a"
    )
