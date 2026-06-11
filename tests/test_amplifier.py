import pytest

from precilaser.amplifier import status_handler, temperature_handler
from precilaser.enums import PrecilaserMessageType, PrecilaserReturn
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
