import logging
from typing import Optional

import dbus


SYSTEM_SERVICE = "com.victronenergy.system"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"

BATTERY_SOC_PATH = "/Dc/Battery/Soc"
BATTERY_VOLTAGE_PATH = "/Dc/Battery/Voltage"
BATTERY_CURRENT_PATH = "/Dc/Battery/Current"


class VictronSystem:
    """Read runtime system values exposed by com.victronenergy.system."""

    def __init__(
        self,
        bus: Optional[dbus.Bus] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._bus = bus or dbus.SystemBus()
        self._logger = logger or logging.getLogger(__name__)

    def _get_bus_item(self, path: str) -> dbus.Interface:
        dbus_object = self._bus.get_object(
            SYSTEM_SERVICE,
            path,
        )

        return dbus.Interface(
            dbus_object,
            dbus_interface=BUS_ITEM_INTERFACE,
        )

    def _get_float_value(
        self,
        path: str,
        name: str,
        unit: str,
    ) -> float:
        """Read a floating-point runtime value from D-Bus."""

        item = self._get_bus_item(path)
        raw_value = item.GetValue()

        if raw_value is None:
            raise RuntimeError(
                f"{name} is unavailable on D-Bus path {path}"
            )

        try:
            value = float(raw_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Invalid {name} value received from D-Bus path "
                f"{path}: {raw_value!r}"
            ) from exc

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