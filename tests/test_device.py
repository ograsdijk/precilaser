import pytest

import precilaser.device
from precilaser.enums import (
    PrecilaserCommand,
    PrecilaserMessageType,
    PrecilaserReturn,
)
from precilaser.message import PrecilaserMessage
from precilaser.seed import Seed


class FakeSerial:
    """Minimal stand-in for serial.Serial used to drive the device read/write code."""

    def __init__(self, rx: bytes = b"", **kwargs):
        self._rx = bytearray(rx)
        self.written = bytearray()
        self.closed = False
        self.is_open = True

    def read(self, n: int = 1) -> bytes:
        # like pyserial: return up to n bytes, fewer if the (fake) buffer runs dry
        chunk = bytes(self._rx[:n])
        del self._rx[:n]
        return chunk

    def write(self, data: bytes) -> int:
        self.written += data
        return len(data)

    @property
    def in_waiting(self) -> int:
        return len(self._rx)

    def close(self) -> None:
        self.closed = True
        self.is_open = False


def _return_frame(payload: bytes = b"\x01\xf4") -> bytes:
    """A valid SEED_SET_VOLTAGE return frame (header P, address 100, 2-byte payload)."""
    msg = PrecilaserMessage(
        command=PrecilaserReturn.SEED_SET_VOLTAGE,
        address=100,
        payload=payload,
        header=b"P",
        terminator=b"\r\n",
        endian="big",
        type=PrecilaserMessageType.RETURN,
    )
    return bytes(msg.command_bytes)


def _make_seed(monkeypatch, rx: bytes = b"") -> tuple:
    fake = FakeSerial(rx)
    monkeypatch.setattr(precilaser.device.serial, "Serial", lambda **kw: fake)
    dev = Seed(port="COMTEST", address=100)
    return dev, fake


def test_read_single_message_parses_frame(monkeypatch):
    payload = b"\x01\xf4"
    dev, _ = _make_seed(monkeypatch, _return_frame(payload))
    message = dev._read_single_message()
    assert message.command == PrecilaserReturn.SEED_SET_VOLTAGE
    assert message.payload == payload
    assert message.address == 100


def test_read_single_message_resyncs_past_garbage(monkeypatch):
    # leading bytes that are not the header should be skipped
    dev, _ = _make_seed(monkeypatch, b"\xaa\xbb\xcc" + _return_frame())
    message = dev._read_single_message()
    assert message.payload == b"\x01\xf4"


def test_read_single_message_timeout_on_no_data(monkeypatch):
    dev, _ = _make_seed(monkeypatch, b"")
    with pytest.raises(TimeoutError, match="no data received"):
        dev._read_single_message()


def test_read_exact_raises_on_short_read(monkeypatch):
    dev, _ = _make_seed(monkeypatch, b"\x01\x02\x03")
    with pytest.raises(TimeoutError, match="expected 5 bytes, received 3"):
        dev._read_exact(5)


def test_read_exact_returns_requested_bytes(monkeypatch):
    dev, _ = _make_seed(monkeypatch, b"\x01\x02\x03\x04\x05")
    assert dev._read_exact(3) == b"\x01\x02\x03"


def test_write_sends_command_bytes(monkeypatch):
    dev, fake = _make_seed(monkeypatch)
    msg = dev._generate_message(PrecilaserCommand.SEED_STATUS)
    dev._write(msg)
    assert bytes(fake.written) == bytes(msg.command_bytes)


def test_check_write_return_ok(monkeypatch):
    dev, _ = _make_seed(monkeypatch)
    # 0x01f4 == 500, big endian -> no exception
    dev._check_write_return(b"\x01\xf4", 500)


def test_check_write_return_mismatch_raises(monkeypatch):
    dev, _ = _make_seed(monkeypatch)
    with pytest.raises(ValueError, match="piezo voltage"):
        dev._check_write_return(b"\x00\x00", 500, "piezo voltage")


def test_close(monkeypatch):
    dev, fake = _make_seed(monkeypatch)
    dev.close()
    assert fake.closed is True


def test_context_manager_closes_port(monkeypatch):
    fake = FakeSerial()
    monkeypatch.setattr(precilaser.device.serial, "Serial", lambda **kw: fake)
    with Seed(port="COMTEST", address=100) as dev:
        assert dev.instrument is fake
        assert fake.closed is False
    assert fake.closed is True
