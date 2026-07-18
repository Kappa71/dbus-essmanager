import logging
import os
import platform
import sys

try:
    import dbus
except ImportError:
    raise ImportError(
        "The 'dbus' module is available only on Venus OS or Linux "
        "with python3-dbus installed."
    )

from essmanager import constants


sys.path.insert(
    1,
    "/opt/victronenergy/dbus-systemcalc-py/ext/velib_python",
)

from settingsdevice import SettingsDevice
from vedbus import VeDbusService


# Paths exposed by com.victronenergy.essmanager
MAX_SOC_PATH = "/Settings/MaxSoc"
BATTERY_FULL_PATH = "/BatteryFull"

# Persistent path exposed by com.victronenergy.settings
PERSISTENT_MAX_SOC_PATH = "/Settings/EssManager/MaxSoc"

DEFAULT_MAX_SOC = 100.0
MIN_MAX_SOC = 10.0
MAX_MAX_SOC = 100.0


class DBusService:
    """D-Bus interface exposed by dbus-essmanager."""

    def __init__(self, device_instance, logger=None):
        self._logger = logger or logging.getLogger(__name__)

        self._dbus_conn = (
            dbus.SessionBus()
            if "DBUS_SESSION_BUS_ADDRESS" in os.environ
            else dbus.SystemBus(private=True)
        )

        self._register_persistent_settings()

        self.service = VeDbusService(
            constants.SERVICE_NAME,
            bus=self._dbus_conn,
            register=False,
        )

        self._add_management_paths(device_instance)
        self._add_essmanager_paths()

        self.service.register()

    def _register_persistent_settings(self) -> None:
        """
        Register settings stored persistently by
        com.victronenergy.settings.
        """

        supported_settings = {
            "max_soc": [
                PERSISTENT_MAX_SOC_PATH,
                DEFAULT_MAX_SOC,
                MIN_MAX_SOC,
                MAX_MAX_SOC,
            ],
        }

        self.settings = SettingsDevice(
            bus=self._dbus_conn,
            supportedSettings=supported_settings,
            eventCallback=self._on_persistent_setting_changed,
        )

        self._logger.info(
            "Persistent MaxSoc loaded: %.1f %%",
            self.get_max_soc(),
        )

    def _add_management_paths(self, device_instance: int) -> None:
        """Add the standard Victron management paths."""

        self.service.add_path(
            "/DeviceInstance",
            device_instance,
        )

        self.service.add_path(
            "/Mgmt/ProcessName",
            __file__,
        )

        self.service.add_path(
            "/Mgmt/ProcessVersion",
            "Python " + platform.python_version(),
        )

        self.service.add_path(
            "/ProductId",
            constants.PRODUCT_ID,
        )

        self.service.add_path(
            "/ProductName",
            constants.PRODUCT_NAME,
        )

        self.service.add_path(
            "/Connected",
            1,
        )

        self.service.add_path(
            "/State",
            0,
        )

    def _add_essmanager_paths(self) -> None:
        """Add paths specific to dbus-essmanager."""

        self.service.add_path(
            MAX_SOC_PATH,
            self.get_max_soc(),
            writeable=True,
            onchangecallback=self._on_max_soc_changed,
        )

        self.service.add_path(
            BATTERY_FULL_PATH,
            0,
            writeable=False,
        )

    def _on_max_soc_changed(self, path: str, value: object) -> bool:
        """
        Handle a write to /Settings/MaxSoc on the essmanager service.

        Returning True accepts the D-Bus write.
        Returning False rejects it.
        """

        try:
            max_soc = float(value)
        except (TypeError, ValueError):
            self._logger.warning(
                "Rejected invalid MaxSoc value: %r",
                value,
            )
            return False

        if not MIN_MAX_SOC <= max_soc <= MAX_MAX_SOC:
            self._logger.warning(
                "Rejected MaxSoc %.1f %%: value must be between "
                "%.1f and %.1f %%",
                max_soc,
                MIN_MAX_SOC,
                MAX_MAX_SOC,
            )
            return False

        current_value = self.get_max_soc()

        if current_value != max_soc:
            self.settings["max_soc"] = max_soc

            self._logger.info(
                "MaxSoc changed through essmanager D-Bus to %.1f %%",
                max_soc,
            )

        return True

    def _on_persistent_setting_changed(
        self,
        setting: str,
        old_value: object,
        new_value: object,
    ) -> None:
        """
        Handle changes received from com.victronenergy.settings.

        This includes changes made through MQTT, D-Bus or another
        external client.
        """

        if setting != "max_soc":
            return

        max_soc = float(new_value)

        self._logger.info(
            "Persistent MaxSoc changed from %.1f %% to %.1f %%",
            float(old_value),
            max_soc,
        )

        # During SettingsDevice construction the essmanager service
        # paths have not necessarily been created yet.
        if not hasattr(self, "service"):
            return

        try:
            current_service_value = float(
                self.service[MAX_SOC_PATH]
            )
        except KeyError:
            return

        if current_service_value != max_soc:
            self.service[MAX_SOC_PATH] = max_soc

    def get_max_soc(self) -> float:
        """Return the persistent maximum SOC setting."""

        return float(self.settings["max_soc"])

    def set_max_soc(self, max_soc: float) -> None:
        """
        Set and persist the maximum SOC.

        This method is intended for internal application use.
        """

        max_soc = float(max_soc)

        if not MIN_MAX_SOC <= max_soc <= MAX_MAX_SOC:
            raise ValueError(
                f"MaxSoc must be between {MIN_MAX_SOC:.1f} and "
                f"{MAX_MAX_SOC:.1f} %, received {max_soc}"
            )

        current_value = self.get_max_soc()

        if current_value == max_soc:
            return

        self.settings["max_soc"] = max_soc

        self._logger.info(
            "MaxSoc set internally to %.1f %%",
            max_soc,
        )

    def get_battery_full(self) -> bool:
        """Return the current BatteryFull state."""

        return bool(
            int(self.service[BATTERY_FULL_PATH])
        )

    def set_battery_full(self, battery_full: bool) -> None:
        """
        Update BatteryFull internally.

        The D-Bus path remains read-only for external clients.
        """

        new_value = 1 if battery_full else 0
        current_value = int(
            self.service[BATTERY_FULL_PATH]
        )

        if current_value == new_value:
            return

        self.service[BATTERY_FULL_PATH] = new_value

        self._logger.info(
            "BatteryFull changed to %s",
            battery_full,
        )