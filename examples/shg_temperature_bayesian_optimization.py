import time

import numpy as np
import pyvisa
from ax import optimize

from precilaser import SHGAmplifier
from precilaser.utils import wait_until_shg_temperature_stable

amp_com_port = "COM50"
power_meter = "USB0::0x1313::0x8078::P0020445::INSTR"  # Thorlabs PM100D
scan_range = 4  # scan range in celcius to scan around the current setpoint
trials = 25

amp = SHGAmplifier(amp_com_port, address=0)
rm = pyvisa.ResourceManager()
pm = rm.open_resource(power_meter, read_termination="\n")

# configure power meter
pm.write("SENS:CORR:WAV 543.5")
pm.write("SENS:CORR:BEAM 1.3")

time.sleep(1)
amp._read_until_buffer_empty()

amp.enable()
amp.current = 5


def eval_function(parametrization: dict[str, float]):
    try:
        amp._read_until_buffer_empty()
    except Exception:
        pass

    temperature = parametrization.get("temperature")
    amp.shg_temperature = temperature
    wait_until_shg_temperature_stable(amp, temperature, progress=True)
    powers = []
    for _ in range(5):
        powers.append(pm.query("MEAS:POW?"))
        time.sleep(0.2)

    return {"shg power": (np.mean(powers), np.std(powers))}


best_parameters, best_values, experiment, model = optimize(
    parameters=[
        {
            "name": "temperature",
            "type": "range",
            "bounds": [
                amp.shg_temperature - scan_range / 2,
                amp.shg_temperature + scan_range / 2,
            ],
        }
    ],
    evaluation_function=eval_function,
    minimize=False,
)

amp.current = 0
amp.disable()

print(best_parameters, best_values)
