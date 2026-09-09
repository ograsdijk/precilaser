import pytest

import precilaser.device
from precilaser.amplifier import SHGAmplifier, status_handler, temperature_handler
from precilaser.enums import (
    PrecilaserCommand,
    PrecilaserMessageType,
    PrecilaserReturn,
)
from precilaser.message import PrecilaserMessage, PrecilaserReturnParamLength
from precilaser.status import AmplifierStatus


def _return_message(command, payload):
    return PrecilaserMessage(
        command=command,
        address=100,
        payload=payload,
        header=b"P",
        terminator=b"\r\n",
        endian="big",
        type=PrecilaserMessageType.RETURN,
    )


def test_status_handler_returns_amplifier_status():
    payload = (
        5151256923390522315301251121412425192132412421581125251212512558390258
    ).to_bytes(PrecilaserReturnParamLength.AMP_STATUS, "big")
    message = _return_message(PrecilaserReturn.AMP_STATUS, payload)
    status = status_handler(message)
    assert isinstance(status, AmplifierStatus)
    # spot-check a parsed field against test_status expectations
    assert status.driver_current == (0.0, 0.0, 0.0)


def test_status_handler_raises_on_empty_payload():
    message = _return_message(PrecilaserReturn.AMP_STATUS, None)
    with pytest.raises(ValueError, match="No status bytes retrieved"):
        status_handler(message)


def test_temperature_handler_parses_two_temperatures():
    payload = (
        b"\x00"
        + (1234).to_bytes(2, "big")
        + (5678).to_bytes(2, "big")
        + bytes(PrecilaserReturnParamLength.AMP_TEC_TEMPERATURE - 5)
    )
    message = _return_message(PrecilaserReturn.AMP_TEC_TEMPERATURE, payload)
    assert temperature_handler(message) == (12.34, 56.78)


def test_temperature_handler_raises_on_empty_payload():
    message = _return_message(PrecilaserReturn.AMP_TEC_TEMPERATURE, None)
    with pytest.raises(ValueError, match="No TEC temperature bytes retrieved"):
        temperature_handler(message)


class FakeAmpSerial:
    """Fake serial port replaying return frames, optionally repeating them forever.

    Repeating models the real amplifier, which broadcasts a status frame every ~300 ms
    and so never lets a read time out on silence.
    """

    def __init__(self, frames: bytes = b"", repeat: bool = False, **kwargs):
        self._frames = frames
        self._repeat = repeat
        self._rx = bytearray(frames)
        self.written = bytearray()

    def read(self, n: int = 1) -> bytes:
        if self._repeat and len(self._rx) < n:
            self._rx += self._frames
        chunk = bytes(self._rx[:n])
        del self._rx[:n]
        return chunk

    def write(self, data: bytes) -> int:
        self.written += data
        return len(data)

    @property
    def in_waiting(self) -> int:
        # a repeating device is never done broadcasting, so the buffer never reads empty
        if self._repeat and not self._rx:
            self._rx += self._frames
        return len(self._rx)

    def close(self) -> None:
        pass


def _frame(command: PrecilaserReturn, payload: bytes) -> bytes:
    return bytes(_return_message(command, payload).command_bytes)


def _command_bytes(command: PrecilaserCommand, payload: bytes) -> bytes:
    message = PrecilaserMessage(
        command=command,
        address=100,
        payload=payload,
        header=b"P",
        terminator=bytes([13, 10]),
        endian="big",
        type=PrecilaserMessageType.COMMAND,
    )
    return bytes(message.command_bytes)


def _make_amp(monkeypatch, frames: bytes = b"", repeat: bool = False):
    fake = FakeAmpSerial(frames, repeat)
    monkeypatch.setattr(precilaser.device.serial, "Serial", lambda **kw: fake)
    return SHGAmplifier(port="COMTEST", address=100), fake


# the frame the amplifier actually returns for AMP_POWER_STAB, and the AMP_ENABLE frame
# that arrives on the same stream and must not be mistaken for it
_STAB_OK = _frame(PrecilaserReturn.AMP_POWER_STAB, b"Stable set ok")
_ENABLE_OK = _frame(PrecilaserReturn.AMP_ENABLE, b"Enable set ok")


def test_enable_power_stabilization_waits_for_power_stab_reply(monkeypatch):
    amp, fake = _make_amp(monkeypatch, _ENABLE_OK + _STAB_OK)
    amp.enable_power_stabilization()
    assert bytes(fake.written) == _command_bytes(
        PrecilaserCommand.AMP_POWER_STAB, bytes([1])
    )


def test_disable_power_stabilization_waits_for_power_stab_reply(monkeypatch):
    amp, fake = _make_amp(monkeypatch, _ENABLE_OK + _STAB_OK)
    amp.disable_power_stabilization()
    assert bytes(fake.written) == _command_bytes(
        PrecilaserCommand.AMP_POWER_STAB, bytes([0])
    )


def test_power_stabilization_raises_on_unexpected_payload(monkeypatch):
    amp, _ = _make_amp(
        monkeypatch, _frame(PrecilaserReturn.AMP_POWER_STAB, b"Stable set no")
    )
    with pytest.raises(ValueError, match="Power stabilization not enabled"):
        amp.enable_power_stabilization()


def test_read_until_reply_skips_non_matching_frames(monkeypatch):
    amp, _ = _make_amp(monkeypatch, _ENABLE_OK + _ENABLE_OK + _STAB_OK)
    message = amp._read_until_reply(PrecilaserReturn.AMP_POWER_STAB)
    assert message.command == PrecilaserReturn.AMP_POWER_STAB
    assert message.payload == b"Stable set ok"


def test_read_until_reply_times_out_while_device_keeps_talking(monkeypatch):
    # endless non-matching traffic: the pyserial read timeout never fires, so only the
    # loop deadline can end this
    amp, _ = _make_amp(monkeypatch, _ENABLE_OK, repeat=True)
    with pytest.raises(TimeoutError, match="no AMP_POWER_STAB reply"):
        amp._read_until_reply(PrecilaserReturn.AMP_POWER_STAB, timeout=0.05)


def test_read_until_buffer_empty_times_out_on_endless_stream(monkeypatch):
    amp, _ = _make_amp(monkeypatch, _ENABLE_OK, repeat=True)
    with pytest.raises(TimeoutError, match="did not drain"):
        amp._read_until_buffer_empty(timeout=0.05)


def test_read_until_buffer_empty_returns_once_drained(monkeypatch):
    amp, fake = _make_amp(monkeypatch, _ENABLE_OK + _STAB_OK)
    amp._read_until_buffer_empty()
    assert fake.in_waiting == 0
