from precilaser import Seed

resource_name = "COM6"

dev = Seed(resource_name=resource_name, address=100)

print(dev.status)
print("temperature setpoint", dev.temperature_setpoint)
print("piezo voltage", dev.piezo_voltage)

temperature_setpoint = dev.temperature_setpoint

print(f"temperature setpoint is {temperature_setpoint}")
dev.temperature_setpoint = temperature_setpoint + 1
print(
    f"changed temperature setpoint to {temperature_setpoint+1}, device temperature"
    f" setpoint is {dev.temperature_setpoint}"
)

dev.temperature_setpoint = temperature_setpoint
