import pytest

from precilaser.enums import PrecilaserCommand, PrecilaserMessageType
from precilaser.message import (
    PrecilaserCommandParamLength,
    PrecilaserMessage,
    decompose_message,
)


def _valid_return_frame() -> bytes:
    command_bytes = b"P"  # header
    command_bytes += b"\x00\x64"  # host and slave address
    command_bytes += b"\xb3"  # command byte
    command_bytes += b"\x04"  # nr bytes in payload
    command_bytes += (25_000).to_bytes(2, "big")  # part 1 of payload
    command_bytes += (25_025).to_bytes(2, "big")  # part 2 of payload
    command_bytes += b"\x46"  # checksum
    command_bytes += b"\xba"  # xor check
    command_bytes += b"\r\n"  # terminator
    return command_bytes


def test_PrecilaserMessage():
    for command in [PrecilaserCommand.AMP_SET_CURRENT]:
        value = int(1.5 * 100)
        param_length = getattr(PrecilaserCommandParamLength, command.name)
        payload = value.to_bytes(param_length, "big")

        message = PrecilaserMessage(
            command, address=0, payload=payload, header=b"\x50", terminator=b"\x0d\x0a"
        )
        assert message.header == b"\x50"
        assert message.terminator == b"\x0d\x0a"
        assert message.payload == payload
        assert message.command == command
        assert message.type == PrecilaserMessageType.COMMAND
        assert message.checksum == 57
        assert message.xor_check == 53

        assert len(message.payload) == param_length
        assert int.from_bytes(message.payload, "big") == value


def test_decompose_message():
    command_bytes = b"P"  # header
    command_bytes += b"\x00\x64"  # host and slave address
    command_bytes += b"\xb3"  # command byte
    command_bytes += b"\x04"  # nr bytes in payload
    command_bytes += (25_000).to_bytes(2, "big")  # part 1 of payload
    command_bytes += (25_025).to_bytes(2, "big")  # part 2 of payload
    command_bytes += b"\x46"  # checksum
    command_bytes += b"\xba"  # xor check
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
    assert int.from_bytes(message.payload, "big") == 1638425025
    assert message.type == PrecilaserMessageType.RETURN
    assert message.xor_check == 186
    assert message.checksum == 70


def _decompose(frame: bytes):
    return decompose_message(
        message=frame,
        address=100,
        header=b"P",
        terminator=b"\r\n",
        endian="big",
    )


def test_decompose_message_invalid_header():
    frame = b"X" + _valid_return_frame()[1:]
    with pytest.raises(ValueError, match="invalid message header"):
        _decompose(frame)


def test_decompose_message_invalid_terminator():
    frame = _valid_return_frame()[:-2] + b"\x00\x00"
    with pytest.raises(ValueError, match="invalid message terminator"):
        _decompose(frame)


def test_decompose_message_invalid_checksum():
    # corrupt the checksum byte (4th from the end)
    frame = bytearray(_valid_return_frame())
    frame[-4] ^= 0xFF
    # regression: this branch used to raise TypeError instead of ValueError
    with pytest.raises(ValueError, match="invalid message checksum"):
        _decompose(bytes(frame))


def test_decompose_message_invalid_xor():
    # corrupt the xor byte (3rd from the end)
    frame = bytearray(_valid_return_frame())
    frame[-3] ^= 0xFF
    with pytest.raises(ValueError, match="invalid xor check"):
        _decompose(bytes(frame))
