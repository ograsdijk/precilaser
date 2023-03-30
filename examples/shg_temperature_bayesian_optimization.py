import time
from typing import Dict

import numpy as np
import pyvisa
from ax import optimize

from precilaser import SHGAmplifier
from precilaser.utils import wait_until_shg_temperature_stable

amp_com_port = "COM50"
power_meter = "USB0::0x1313::0x8078::P0020445::INSTR"  # Thorlabs PM100D
scan_range = 4  # scan range in celcius to scan around the current setpoint
total_trials = 25

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


def eval_function(parametrization: Dict[str, float]):
    while amp.instrument.bytes_in_buffer > 0:
        try:
            amp._read_until_buffer_empty()
        except Exception:
            pass

    temperature = parametrization.get("temperature")
    amp.shg_temperature = temperature
    wait_until_shg_temperature_stable(amp, temperature, timeout = 300, progress=True)

    powers = []
    for _ in range(5):
        powers.append(float(pm.query("MEAS:POW?")))
        time.sleep(0.2)

    return (np.mean(powers), np.std(powers))

current_temperature = amp.shg_temperature

try:
    best_parameters, best_values, experiment, model = optimize(
        parameters=[
            {
                "name": "temperature",
                "type": "range",
                "bounds": [
                    current_temperature - scan_range / 2,
                    current_temperature + scan_range / 2,
                ],
            }
        ],
        evaluation_function=eval_function,
        minimize=False,
        total_trials=total_trials
    )
except TimeoutError as e:
    amp.current = 0
    amp.disable()
    raise e
finally:
    amp.current = 0
    amp.disable()

print(best_parameters, best_values)

data = experiment.fetch_data()
powers = data.df['mean'] * 1e3
powers_err = data.df['sem'] * 1e3
temperatures = [val.parameters['temperature'] for val in experiment.arms_by_name.values()]


fig, ax = plt.subplots(figsize = (8,5))
ax.errorbar(x = temperatures, y = powers, yerr = powers_err, fmt = '.', ms = 10)

ax.set_xlabel("temperature [C]")
ax.set_ylabel("power [mW]")
ax.grid(True)

fig, ax = plt.subplots(figsize = (8,5))
ax.plot(np.arange(1,len(powers)+1), powers, lw = 2)
ax.set_xlabel("trial [#]")
ax.set_ylabel("power [mW]")
ax.grid(True)

plt.show()
