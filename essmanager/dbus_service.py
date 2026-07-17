try:
    import dbus
except ImportError:
    raise ImportError(
        "The 'dbus' module is available only on Venus OS or Linux with python3-dbus installed."
    )
import os
import platform
import sys
from essmanager import constants

sys.path.insert(
    1,
    "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
)

from vedbus import VeDbusService


class DBusService:

    def __init__(self, constants):

        dbus_conn = (
            dbus.SessionBus()
            if "DBUS_SESSION_BUS_ADDRESS" in os.environ
            else dbus.SystemBus(private=True)
        )

        self.service = VeDbusService(
            constants.SERVICE_NAME,
            bus=dbus_conn,
            register=False
        )

        self.service.add_path("/Mgmt/ProcessName", __file__)
        self.service.add_path(
            "/Mgmt/ProcessVersion",
            "Python " + platform.python_version()
        )

        self.service.add_path("/DeviceInstance", constants.DEVICE_INSTANCE)
        self.service.add_path("/ProductId", constants.PRODUCT_ID)
        self.service.add_path("/ProductName", constants.PRODUCT_NAME)

        self.service.add_path("/Connected", 1)

        self.service.add_path("/State", 0)

        self.service.register()