from precilaser import Seed

port = "COM6"

# using the device as a context manager guarantees the serial port is closed on exit
with Seed(port=port, address=100) as dev:
    print(dev.status)
    print("temperature setpoint", dev.temperature_setpoint)
    print("piezo voltage", dev.piezo_voltage)

    temperature_setpoint = dev.temperature_setpoint

    print(f"temperature setpoint is {temperature_setpoint}")
    dev.temperature_setpoint = temperature_setpoint + 1
    print(
        f"changed temperature setpoint to {temperature_setpoint + 1}, device"
        f" temperature setpoint is {dev.temperature_setpoint}"
    )

    dev.temperature_setpoint = temperature_setpoint
