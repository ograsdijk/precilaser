from precilaser import Seed

resource_name = "COM6"

dev = Seed(resource_name=resource_name, addresss=100)

print(dev.status)
print(dev.temperature_setpoint)
print(dev.piezo_voltage)
