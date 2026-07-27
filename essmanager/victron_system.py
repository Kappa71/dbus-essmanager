"""Read runtime battery values from the Victron system service."""

from __future__ import annotations

import logging
import math
from typing import Dict, Optional

import dbus

from essmanager.state_machine import SystemData
class DBusValueUnavailableError(RuntimeError):
    """Raised when a D-Bus value is temporarily unavailable."""


SYSTEM_SERVICE = "com.victronenergy.system"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"

BATTERY_SOC_PATH = "/Dc/Battery/Soc"
BATTERY_VOLTAGE_PATH = "/Dc/Battery/Voltage"
BATTERY_CURRENT_PATH = "/Dc/Battery/Current"
PORTAL_ID_PATH = "/Serial"


class VictronSystem:
    """Read runtime system values exposed by com.victronenergy.system."""

    def __init__(
        self,
        bus: Optional[dbus.Bus] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._bus = bus or dbus.SystemBus()
        self._logger = logger or logging.getLogger(__name__)

        # Cache the D-Bus interfaces because these paths are read
        # repeatedly during the one-second control loop.
        self._bus_items: Dict[str, dbus.Interface] = {}

    def _get_bus_item(self, path: str) -> dbus.Interface:
        """Return a cached D-Bus interface for the requested path."""

        item = self._bus_items.get(path)

        if item is not None:
            return item

        try:
            dbus_object = self._bus.get_object(
                SYSTEM_SERVICE,
                path,
            )

            item = dbus.Interface(
                dbus_object,
                dbus_interface=BUS_ITEM_INTERFACE,
            )
        except dbus.DBusException as exc:
            raise RuntimeError(
                f"Unable to access D-Bus path "
                f"{SYSTEM_SERVICE}{path}: {exc}"
            ) from exc

        self._bus_items[path] = item

        return item

    def _get_float_value(
        self,
        path: str,
        name: str,
        unit: str,
    ) -> float:
        """Read and validate a floating-point runtime value."""

        item = self._get_bus_item(path)

        try:
            raw_value = item.GetValue()
        except dbus.DBusException as exc:
            raise RuntimeError(
                f"Unable to read {name} from D-Bus path "
                f"{SYSTEM_SERVICE}{path}: {exc}"
            ) from exc

        if raw_value is None:
            raise DBusValueUnavailableError(
                f"{name} is unavailable on D-Bus path "
                f"{SYSTEM_SERVICE}{path}"
            )

        # Venus OS represents a temporarily unavailable value as an empty dbus.Array.
        if isinstance(raw_value, dbus.Array) and len(raw_value) == 0:
            raise DBusValueUnavailableError(
                f"{name} is temporarily unavailable on D-Bus path "
                f"{SYSTEM_SERVICE}{path}"
            )

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Invalid {name} value received from D-Bus path "
                f"{SYSTEM_SERVICE}{path}: {raw_value!r}"
            ) from exc

        if not math.isfinite(value):
            raise RuntimeError(
                f"Non-finite {name} value received from D-Bus path "
                f"{SYSTEM_SERVICE}{path}: {raw_value!r}"
            )

        self._logger.debug(
            "Read %s from D-Bus: %.1f %s",
            name,
            value,
            unit,
        )

        return value

    def get_battery_soc(self) -> float:
        """
        Return the battery SOC selected by the Victron system.

        The value is expressed as a percentage from 0.0 to 100.0.
        """

        return self._get_float_value(
            path=BATTERY_SOC_PATH,
            name="Battery SOC",
            unit="%",
        )

    def get_battery_voltage(self) -> float:
        """Return the system battery voltage in volts."""

        return self._get_float_value(
            path=BATTERY_VOLTAGE_PATH,
            name="Battery voltage",
            unit="V",
        )

    def get_battery_current(self) -> float:
        """
        Return the system battery current in amperes.

        The sign follows the convention exposed by
        com.victronenergy.system.
        """

        return self._get_float_value(
            path=BATTERY_CURRENT_PATH,
            name="Battery current",
            unit="A",
        )

    def read(self) -> SystemData:
        """
        Read all battery values required by the state machine.

        Raises RuntimeError if one of the required values is unavailable
        or invalid. A partial SystemData object is never returned.
        """

        return SystemData(
            battery_soc=self.get_battery_soc(),
            battery_voltage=self.get_battery_voltage(),
            battery_current=self.get_battery_current(),
        )

    def get_portal_id(self) -> str:
        """
        Return the VRM Portal ID used by dbus-flashmq in MQTT topics.
        """

        item = self._get_bus_item(PORTAL_ID_PATH)
        value = item.GetValue()

        # An empty dbus.Array indicates that the value is temporarily
        # unavailable.
        if isinstance(value, dbus.Array) and len(value) == 0:
            raise DBusValueUnavailableError(
                "Portal ID is temporarily unavailable"
            )

        portal_id = str(value).strip()

        if not portal_id:
            raise DBusValueUnavailableError(
                "Portal ID is temporarily unavailable"
            )

        return portal_id