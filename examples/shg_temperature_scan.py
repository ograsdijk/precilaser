import csv
import datetime
import time

import asciichartpy as acp
import matplotlib.pyplot as plt
import numpy as np
import pyvisa
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from precilaser import SHGAmplifier
from precilaser.utils import wait_until_shg_temperature_stable

amp_com_port = "COM50"
power_meter = "USB0::0x1313::0x8078::P0020445::INSTR"  # Thorlabs PM100D
scan_range = 4  # scan range in celcius to scan around the current setpoint
dt = 10
points = 101

measurement_time = (
    datetime.datetime.now()
    .isoformat(timespec="seconds")
    .replace(":", "_")
    .replace("-", "_")
)


def get_panel(data, title, height=15, format="{:>2.2f}"):
    return Panel(acp.plot(data, {"height": height, "format": format}), title=title)


class TaskSpeed(ProgressColumn):
    def render(self, task):
        if task.speed is None:
            return ""
        elif task.speed >= 0.1:
            return f"{( task.speed or 0 ):.1f}/s"
        else:
            return f"{( 1 / task.speed or 0):.1f} s/i"


progress = Progress(
    SpinnerColumn(),
    TextColumn("{task.description} : {task.fields[value]}", justify="right"),
    BarColumn(bar_width=None),
    TaskProgressColumn(show_speed=True),
    TaskSpeed(),
    TextColumn("{task.completed} of {task.total}"),
    "•",
    TimeElapsedColumn(),
    TimeRemainingColumn(),
)
panel = Panel("")
group = Group(panel, progress)

console = Console()

amp = SHGAmplifier("COM50", address=0)

# Thorlabs PM100D power meter, probably works with any of the Thorlabs power meters.
rm = pyvisa.ResourceManager()
pm = rm.open_resource(power_meter, read_termination="\n")

pm.write("SENS:CORR:WAV 543.5")
pm.write("SENS:CORR:BEAM 1.3")

time.sleep(1)
amp._read_until_buffer_empty()
amp.status
current_temperature_setpoint = amp.shg_temperature

# enable amplifier
console.print("Enabling the amplifier", end="\r")
amp.enable()


# give the amplifier some time to finish starting up and going to the first temperature
amp.shg_temperature = current_temperature_setpoint - scan_range / 2
wait_until_shg_temperature_stable(
    amp, current_temperature_setpoint - scan_range / 2, progress=True
)

amp.current = 5

data = []
with Live(group, refresh_per_second=10) as live:
    task = progress.add_task("[red] Scanning SHG temperature", total=points, value=None)
    for T in np.linspace(
        current_temperature_setpoint - scan_range / 2,
        current_temperature_setpoint + scan_range / 2,
        points,
    ):
        amp.shg_temperature = T
        wait_until_shg_temperature_stable(amp, T, time_stable=2, progress=False)
        power = float(pm.query("MEAS:POW?")) * 1000
        data.append((T, amp.shg_temperature, power))
        progress.update(task, advance=1, value=f"{T:>2.2f} C")
        s, x, y = zip(*data)
        group.renderables[0] = get_panel(y, title="SHG power")

amp.disable()
amp.shg_temperature = current_temperature_setpoint

xsetpoint, x, y = zip(*data)

# write data to csv
with open(f"shg_temperature_scan_{measurement_time}.csv", "w", newline="") as csv_file:
    writer = csv.writer(csv_file, delimiter=",")
    writer.writerow(
        ["SHG temperature setpoint [C]", "SHG temperature [C]", "output power [mW]"]
    )
    for d in data:
        writer.writerow(d)

fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(x, y, ".-", lw=2, ms=12)
ax.set_xlabel("temperature [C]")
ax.set_ylabel("power [mW]")
ax.grid(True)

plt.show()
