from precilaser.enums import PrecilaserCommand, PrecilaserMessageType
from precilaser.message import (
    PrecilaserCommandParamLength,
    PrecilaserMessage,
    decompose_message,
)


def test_PrecilaserMessage():
    for command in [PrecilaserCommand.AMP_SET_CURRENT]:
        value = int(1.5 * 100)

        param_length = getattr(PrecilaserCommandParamLength, command.name)

        message = PrecilaserMessage(command, value, 0, b"\x50", b"\x0d\x0a")
        assert message.header == b"\x50"
        assert message.terminator == b"\x0d\x0a"
        assert message.param == value
        assert message.command == command
        assert message.type == PrecilaserMessageType.COMMAND
        assert message.checksum == 57
        assert message.xor_check == 53

        assert len(message.payload) == param_length
        assert int.from_bytes(message.payload, "big") == value


def test_decompose_message():
    command_bytes = b"P"  # header
    command_bytes += b"\x00\x64"  # host and slave address
    command_bytes += b"\xB3"  # command byte
    command_bytes += b"\x04"  # nr bytes in payload
    command_bytes += (25_000).to_bytes(2, "big")  # part 1 of payload
    command_bytes += (25_025).to_bytes(2, "big")  # part 2 of payload
    command_bytes += b"\x46"  # checksum
    command_bytes += b"\xBA"  # xor check
    command_bytes += b"\r\n"  # terminator

    message = decompose_message(
        message=command_bytes,
        address=100,
        header=b"P",
        terminator=b"\r\n",
        endian="big",
    )

    assert message.address == 100
    assert message.payload == (25_000).to_bytes(2, "big") + (25_025).to_bytes(2, "big")
    assert message.param == 1638425025
    assert message.param.to_bytes(4, "big") == (25_000).to_bytes(2, "big") + (
        25_025
    ).to_bytes(2, "big")
    assert message.type == PrecilaserMessageType.RETURN
    assert message.xor_check == 186
    assert message.checksum == 70
