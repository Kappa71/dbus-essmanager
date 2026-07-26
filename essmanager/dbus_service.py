import logging
import os
import platform
import sys
from typing import Any, Dict

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


# ---------------------------------------------------------------------------
# Runtime paths exposed by com.victronenergy.essmanager
# ---------------------------------------------------------------------------

BATTERY_FULL_PATH = "/BatteryFull"
SOC_FULL_TIMER_PATH = "/SocFullTimer"
STATE_PATH = "/State"
STATUS_PATH = "/Status"


# ---------------------------------------------------------------------------
# Persistent settings
#
# Each entry contains:
#   path: persistent path in com.victronenergy.settings
#   service_path: path exposed by com.victronenergy.essmanager
#   default: default value used when the setting is first created
#   minimum: minimum accepted value
#   maximum: maximum accepted value
#   value_type: Python type used internally
#   unit: unit used in log messages
# ---------------------------------------------------------------------------

SETTING_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "enable": {
        "path": "/Settings/EssManager/Enable",
        "service_path": "/Settings/Enable",
        "default": 1,
        "minimum": 0,
        "maximum": 1,
        "value_type": int,
        "unit": "",
    },
    "max_soc": {
        "path": "/Settings/EssManager/MaxSoc",
        "service_path": "/Settings/MaxSoc",
        "default": 100,
        "minimum": 10,
        "maximum": 100,
        "value_type": int,
        "unit": "%",
    },
    "soc_hysteresis": {
        "path": "/Settings/EssManager/SocHysteresis",
        "service_path": "/Settings/SocHysteresis",
        "default": 3,
        "minimum": 1,
        "maximum": 50,
        "value_type": int,
        "unit": "%",
    },
    "soc_full_voltage": {
        "path": "/Settings/EssManager/SocFullVoltage",
        "service_path": "/Settings/SocFullVoltage",
        "default": 55.1,
        "minimum": 0.0,
        "maximum": 80.0,
        "value_type": float,
        "unit": "V",
    },
    "soc_full_tail_current": {
        "path": "/Settings/EssManager/SocFullTailCurrent",
        "service_path": "/Settings/SocFullTailCurrent",
        "default": 5,
        "minimum": 0,
        "maximum": 100,
        "value_type": int,
        "unit": "A",
    },
    "soc_full_wait_time": {
        "path": "/Settings/EssManager/SocFullWaitTime",
        "service_path": "/Settings/SocFullWaitTime",
        "default": 30,
        "minimum": 0,
        "maximum": 1440,
        "value_type": int,
        "unit": "min",
    },
    "limit_voltage_idle": {
        "path": "/Settings/EssManager/LimitVoltageIdle",
        "service_path": "/Settings/LimitVoltageIdle",
        "default": 51.2,
        "minimum": 0.0,
        "maximum": 80.0,
        "value_type": float,
        "unit": "V",
    },
    "limit_voltage_floating": {
        "path": "/Settings/EssManager/LimitVoltageFloating",
        "service_path": "/Settings/LimitVoltageFloating",
        "default": 53.6,
        "minimum": 0.0,
        "maximum": 80.0,
        "value_type": float,
        "unit": "V",
    },
    "limit_voltage_absorption": {
        "path": "/Settings/EssManager/LimitVoltageAbsorption",
        "service_path": "/Settings/LimitVoltageAbsorption",
        "default": 55.2,
        "minimum": 0.0,
        "maximum": 80.0,
        "value_type": float,
        "unit": "V",
    },
}


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

        supported_settings = {}

        for setting_name, definition in SETTING_DEFINITIONS.items():
            supported_settings[setting_name] = [
                definition["path"],
                definition["default"],
                definition["minimum"],
                definition["maximum"],
            ]

        self.settings = SettingsDevice(
            bus=self._dbus_conn,
            supportedSettings=supported_settings,
            eventCallback=self._on_persistent_setting_changed,
        )

        self._log_loaded_settings()

    def _log_loaded_settings(self) -> None:
        """Log all persistent settings loaded at startup."""

        self._logger.info(
            "Persistent settings loaded: "
            "Enable=%d, MaxSoc=%d %%, SocHysteresis=%d %%, "
            "SocFullVoltage=%.1f V, SocFullTailCurrent=%d A, "
            "SocFullWaitTime=%d min",
            int(self.get_enable()),
            self.get_max_soc(),
            self.get_soc_hysteresis(),
            self.get_soc_full_voltage(),
            self.get_soc_full_tail_current(),
            self.get_soc_full_wait_time(),
        )

        self._logger.info(
            "Persistent voltage limits loaded: "
            "Idle=%.1f V, Floating=%.1f V, Absorption=%.1f V",
            self.get_limit_voltage_idle(),
            self.get_limit_voltage_floating(),
            self.get_limit_voltage_absorption(),
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

    def _add_essmanager_paths(self) -> None:
        """Add settings and runtime paths specific to dbus-essmanager."""

        for setting_name, definition in SETTING_DEFINITIONS.items():
            self.service.add_path(
                definition["service_path"],
                self._get_setting(setting_name),
                writeable=True,
                onchangecallback=self._create_setting_change_callback(
                    setting_name
                ),
            )

        # Runtime values controlled internally by the state machine.
        self.service.add_path(
            BATTERY_FULL_PATH,
            0,
            writeable=False,
        )

        self.service.add_path(
            SOC_FULL_TIMER_PATH,
            0.0,
            writeable=False,
        )

        self.service.add_path(
            STATE_PATH,
            0,
            writeable=False,
        )

        self.service.add_path(
            STATUS_PATH,
            "Off",
            writeable=False,
        )

    def _create_setting_change_callback(self, setting_name: str):
        """
        Create the callback used when a setting is written through
        com.victronenergy.essmanager.
        """

        def callback(path: str, value: object) -> bool:
            return self._on_service_setting_changed(
                setting_name,
                path,
                value,
            )

        return callback

    def _on_service_setting_changed(
        self,
        setting_name: str,
        path: str,
        value: object,
    ) -> bool:
        """
        Handle writes to settings exposed by the essmanager service.

        Returning True accepts the write.
        Returning False rejects it.
        """

        try:
            normalized_value = self._normalize_setting_value(
                setting_name,
                value,
            )
        except (TypeError, ValueError) as error:
            self._logger.warning(
                "Rejected value %r for %s: %s",
                value,
                path,
                error,
            )
            return False

        current_value = self._get_setting(setting_name)

        if current_value != normalized_value:
            self.settings[setting_name] = normalized_value

            self._logger.info(
                "%s changed through essmanager D-Bus from %s to %s",
                self._setting_display_name(setting_name),
                self._format_setting_value(setting_name, current_value),
                self._format_setting_value(
                    setting_name,
                    normalized_value,
                ),
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

        if setting not in SETTING_DEFINITIONS:
            return

        try:
            normalized_old_value = self._normalize_setting_value(
                setting,
                old_value,
            )
            normalized_new_value = self._normalize_setting_value(
                setting,
                new_value,
            )
        except (TypeError, ValueError) as error:
            self._logger.warning(
                "Invalid persistent value received for %s: %s",
                setting,
                error,
            )
            return

        self._logger.info(
            "Persistent %s changed from %s to %s",
            self._setting_display_name(setting),
            self._format_setting_value(
                setting,
                normalized_old_value,
            ),
            self._format_setting_value(
                setting,
                normalized_new_value,
            ),
        )

        # During SettingsDevice construction the essmanager service
        # paths have not necessarily been created yet.
        if not hasattr(self, "service"):
            return

        service_path = SETTING_DEFINITIONS[setting]["service_path"]

        try:
            current_service_value = self.service[service_path]
        except KeyError:
            return

        try:
            normalized_service_value = self._normalize_setting_value(
                setting,
                current_service_value,
            )
        except (TypeError, ValueError):
            normalized_service_value = None

        if normalized_service_value != normalized_new_value:
            self.service[service_path] = normalized_new_value

    def _normalize_setting_value(
        self,
        setting_name: str,
        value: object,
    ):
        """Convert and validate a setting value."""

        definition = SETTING_DEFINITIONS[setting_name]
        value_type = definition["value_type"]

        if value_type is int:
            numeric_value = float(value)

            if not numeric_value.is_integer():
                raise ValueError(
                    "value must be an integer"
                )

            normalized_value = int(numeric_value)
        else:
            normalized_value = float(value)

        minimum = definition["minimum"]
        maximum = definition["maximum"]

        if not minimum <= normalized_value <= maximum:
            raise ValueError(
                f"value must be between {minimum} and {maximum}"
            )

        return normalized_value

    def _get_setting(self, setting_name: str):
        """Return a normalized persistent setting value."""

        return self._normalize_setting_value(
            setting_name,
            self.settings[setting_name],
        )

    def _set_setting(
        self,
        setting_name: str,
        value: object,
    ) -> None:
        """Validate and persist a setting value."""

        normalized_value = self._normalize_setting_value(
            setting_name,
            value,
        )

        current_value = self._get_setting(setting_name)

        if current_value == normalized_value:
            return

        self.settings[setting_name] = normalized_value

        self._logger.info(
            "%s set internally from %s to %s",
            self._setting_display_name(setting_name),
            self._format_setting_value(setting_name, current_value),
            self._format_setting_value(
                setting_name,
                normalized_value,
            ),
        )

    @staticmethod
    def _setting_display_name(setting_name: str) -> str:
        """Return the public name of a setting."""

        return SETTING_DEFINITIONS[setting_name][
            "service_path"
        ].rsplit("/", 1)[-1]

    @staticmethod
    def _format_setting_value(
        setting_name: str,
        value: object,
    ) -> str:
        """Format a setting value for log messages."""

        definition = SETTING_DEFINITIONS[setting_name]
        unit = definition["unit"]

        if definition["value_type"] is int:
            formatted_value = str(int(value))
        else:
            formatted_value = f"{float(value):.1f}"

        if unit:
            return f"{formatted_value} {unit}"

        return formatted_value

    # ------------------------------------------------------------------
    # Persistent setting getters and setters
    # ------------------------------------------------------------------

    def get_enable(self) -> bool:
        """Return whether ESS Manager control is enabled."""

        return bool(self._get_setting("enable"))

    def set_enable(self, enable: bool) -> None:
        """Enable or disable all ESS Manager functions."""

        self._set_setting(
            "enable",
            1 if enable else 0,
        )

    def get_max_soc(self) -> int:
        """Return the maximum battery SOC."""

        return int(self._get_setting("max_soc"))

    def set_max_soc(self, max_soc: int) -> None:
        """Set and persist the maximum battery SOC."""

        self._set_setting("max_soc", max_soc)

    def get_soc_hysteresis(self) -> int:
        """Return the SOC hysteresis used to restart charging."""

        return int(self._get_setting("soc_hysteresis"))

    def set_soc_hysteresis(self, hysteresis: int) -> None:
        """Set and persist the SOC hysteresis."""

        self._set_setting(
            "soc_hysteresis",
            hysteresis,
        )

    def get_soc_full_voltage(self) -> float:
        """Return the minimum voltage used to detect a full battery."""

        return float(self._get_setting("soc_full_voltage"))

    def set_soc_full_voltage(self, voltage: float) -> None:
        """Set and persist the full-battery voltage threshold."""

        self._set_setting(
            "soc_full_voltage",
            voltage,
        )

    def get_soc_full_tail_current(self) -> int:
        """Return the maximum tail current used to detect full charge."""

        return int(
            self._get_setting("soc_full_tail_current")
        )

    def set_soc_full_tail_current(self, current: int) -> None:
        """Set and persist the full-battery tail-current threshold."""

        self._set_setting(
            "soc_full_tail_current",
            current,
        )

    def get_soc_full_wait_time(self) -> int:
        """Return the full-charge validation time in minutes."""

        return int(
            self._get_setting("soc_full_wait_time")
        )

    def set_soc_full_wait_time(self, wait_time: int) -> None:
        """Set and persist the full-charge validation time."""

        self._set_setting(
            "soc_full_wait_time",
            wait_time,
        )

    def get_limit_voltage_idle(self) -> float:
        """Return the DVCC voltage limit used in ChargeIdle."""

        return float(
            self._get_setting("limit_voltage_idle")
        )

    def set_limit_voltage_idle(self, voltage: float) -> None:
        """Set and persist the idle DVCC voltage limit."""

        self._set_setting(
            "limit_voltage_idle",
            voltage,
        )

    def get_limit_voltage_floating(self) -> float:
        """Return the DVCC voltage limit used in floating state."""

        return float(
            self._get_setting("limit_voltage_floating")
        )

    def set_limit_voltage_floating(self, voltage: float) -> None:
        """Set and persist the floating DVCC voltage limit."""

        self._set_setting(
            "limit_voltage_floating",
            voltage,
        )

    def get_limit_voltage_absorption(self) -> float:
        """Return the DVCC voltage limit used in absorption state."""

        return float(
            self._get_setting("limit_voltage_absorption")
        )

    def set_limit_voltage_absorption(self, voltage: float) -> None:
        """Set and persist the absorption DVCC voltage limit."""

        self._set_setting(
            "limit_voltage_absorption",
            voltage,
        )

    # ------------------------------------------------------------------
    # Runtime state getters and setters
    # ------------------------------------------------------------------

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

    def get_soc_full_timer(self) -> float:
        """Return the current full-charge timer in minutes."""

        return float(
            self.service[SOC_FULL_TIMER_PATH]
        )

    def set_soc_full_timer(self, minutes: float) -> None:
        """
        Update the full-charge timer internally.

        The value is rounded to two decimal places to avoid unnecessary
        D-Bus and MQTT updates caused by very small timing differences.
        """

        new_value = round(max(0.0, float(minutes)), 2)
        current_value = float(
            self.service[SOC_FULL_TIMER_PATH]
        )

        if current_value == new_value:
            return

        self.service[SOC_FULL_TIMER_PATH] = new_value

    def get_state(self) -> int:
        """Return the numeric state-machine state."""

        return int(
            self.service[STATE_PATH]
        )

    def set_state(self, state: int) -> None:
        self.service["/State"] = int(state)

    def get_status(self) -> str:
        """Return the human-readable state-machine status."""

        return str(
            self.service[STATUS_PATH]
        )

    def set_status(self, status: str) -> None:
        self.service["/Status"] = str(status)

    def set_state_and_status(
        self,
        state: int,
        status: str,
    ) -> None:
        """Update both the numeric state and its readable description."""

        self.set_state(state)
        self.set_status(status)