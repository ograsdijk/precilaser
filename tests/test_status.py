from precilaser.enums import PrecilaserMessageType, PrecilaserReturn
from precilaser.message import PrecilaserMessage, PrecilaserReturnParamLength
from precilaser.status import PrecilaserStatus, SeedStatus


def test_PrecilaserStatus():
    # testing with a random number
    message = PrecilaserMessage(
        PrecilaserReturn.AMP_STATUS,
        address=100,
        payload=(
            5151256923390522315301251121412425192132412421581125251212512558390258
        ).to_bytes(PrecilaserReturnParamLength.AMP_STATUS, "big"),
        header=b"P",
        terminator=b"\r\n",
        endian="big",
        type=PrecilaserMessageType.RETURN,
    )
    status = PrecilaserStatus(message.payload)
    assert status.stable is False
    assert status.system_status.pd_protection == (False, False, False, False)
    assert status.system_status.temperature_protection == (
        False,
        False,
        False,
        False,
        False,
    )
    assert status.system_status.fault is False
    assert status.driver_unlock.driver_enable_control == (False, False, False)
    assert status.driver_unlock.driver_enable_flag == (False, False, False)
    assert status.driver_unlock.interlock is False
    assert status.driver_current == (0.0, 0.0, 0.0)
    assert status.pd_value == (0, 0, 0, 191, 4635)
    assert status.pd_status[0].sampling_enable is False
    assert status.pd_status[0].hardware_protection is True
    assert status.pd_status[0].upper_limit_enabled is False
    assert status.pd_status[0].lower_limit_enabled is False
    assert status.pd_status[0].hardware_protection_event is True
    assert status.pd_status[0].upper_limit_event is False
    assert status.pd_status[0].lower_limit_event is False
    assert status.pd_status[0].fault is True
    assert status.temperatures == (320.74, 589.83, 219.19, 421.14)


def test_SeedStatus():
    message_bytes = (
        b"P\x00d\xb7(a\xa8a\xa8\x01\xf4\x00\x00\x00\x00\x00\x00\x00\x00\x00a\xc9\x00a"
        b"\xff\x00\x00\x00\x00\x16\x00\x00\x03R\x0b\x00\xa5\xd2y\x00\x00\x00\x01\x00"
        b"\x00;{\r\n"
    )
    payload_bytes = message_bytes[5 : 5 + PrecilaserReturnParamLength.SEED_STATUS]
    status = SeedStatus(payload_bytes, endian="big")
    assert status.temperature_act == 25.087
    assert status.temperature_diode == 25.033
    assert status.temperature_set == 25.0
    assert status.current_set == 500
    assert status.current_act == 22
    assert status.piezo_voltage == 0
    assert status.wavelength == 1086.7321
    assert status.power == 1
    assert status.emission is False
    assert status.run_hours == 850
    assert status.run_minutes == 11

    # testing with a random number
    message = PrecilaserMessage(
        PrecilaserReturn.SEED_STATUS,
        address=100,
        payload=(
            5151256923390522315301251121412425192132412421581125251212512558390258
        ).to_bytes(PrecilaserReturnParamLength.SEED_STATUS, "big"),
        header=b"P",
        terminator=b"\r\n",
        endian="big",
        type=PrecilaserMessageType.RETURN,
    )
    status = SeedStatus(message.payload, endian="big")
    assert status.temperature_act == 32.074
    assert status.temperature_diode == 29.145
    assert status.temperature_set == 0
    assert status.current_set == 0
    assert status.current_act == 40868
    assert status.piezo_voltage == 227.58
    assert status.wavelength == 108406.0632
    assert status.power == 8225
    assert status.emission is True
