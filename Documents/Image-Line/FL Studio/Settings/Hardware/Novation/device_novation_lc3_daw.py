# name=Novation Launch Control 3 DAW
# supportedHardwareIds=00 20 29 57 01 00 01,00 20 29 58 01 00 01,00 20 29 59 01 00 01,00 20 29 5A 01 00 01,00 20 29 5B 01 00 01,00 20 29 5C 01 00 01,00 20 29 5D 01 00 01,00 20 29 5E 01 00 01
from script.constants import DeviceId
from script.device_adapters.fl_to_application_adapter import (
    add_fl_callbacks_to_namespace,
    make_fl_to_application_adapter,
)

device_id = DeviceId.LaunchControl3
fl_to_application_adapter = make_fl_to_application_adapter(device_id)
add_fl_callbacks_to_namespace(globals(), fl_to_application_adapter)
