import time

from .amplifier import SHGAmplifier


def wait_until_shg_temperature_stable(
    amplifier: SHGAmplifier,
    temperature_setpoint: float,
    temp_stable: float = 0.02,
    time_stable: float = 5,
    timeout: float = 200,
) -> None:
    """
    Utility function to wait until the SHG temperature is stable to within temp_stable
    [C] for at least time_stable [s].

    Args:
        amplifier (SHGAmplifier): precilaser shg amplifier interface
        temperature_setpoint (float): temperature setpoint [C]
        temp_stable (float, optional): temperature stability range [C]. Defaults to 0.02
        time_stable (float, optional): time [s] to stay within temperature stability
                                        range. Defaults to 5.
        timeout (float, optional): timeout [s]. Defaults to 200.

    Raises:
        TimeoutError: raises a TimeoutError if the wait time exceeds timout
    """
    tstart = time.time()
    time_temp_stable = 0
    while True:
        temperature = amplifier.shg_temperature
        if abs(temperature - temperature_setpoint) < temp_stable:
            if time_temp_stable == 0:
                time_temp_stable = time.time()
            elif time.time() - time_temp_stable > time_stable:
                break
        else:
            time_temp_stable = 0
        if time.time() - tstart > timeout:
            raise TimeoutError(
                "SHG crystal temperature stabilization wait time exceeded the preset"
                f" limit of {timeout} seconds"
            )
        time.sleep(0.3)
