import logging
from typing import Optional

import dbus


SETTINGS_SERVICE = "com.victronenergy.settings"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"

MAX_CHARGE_VOLTAGE_PATH = "/Settings/SystemSetup/MaxChargeVoltage"
MAX_CHARGE_CURRENT_PATH = "/Settings/SystemSetup/MaxChargeCurrent"


class VictronSettings:
    """Read and write settings exposed by com.victronenergy.settings."""

    def __init__(
        self,
        bus: Optional[dbus.Bus] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._bus = bus or dbus.SystemBus()
        self._logger = logger or logging.getLogger(__name__)

    def _get_bus_item(self, path: str) -> dbus.Interface:
        dbus_object = self._bus.get_object(
            SETTINGS_SERVICE,
            path,
        )

        return dbus.Interface(
            dbus_object,
            dbus_interface=BUS_ITEM_INTERFACE,
        )

    def _get_float_setting(
        self,
        path: str,
        name: str,
        unit: str,
    ) -> float:
        """Read a floating-point setting from D-Bus."""

        item = self._get_bus_item(path)
        value = float(item.GetValue())

        self._logger.debug(
            "Read %s from D-Bus: %.1f %s",
            name,
            value,
            unit,
        )

        return value

    def _set_float_setting(
        self,
        path: str,
        name: str,
        value: float,
        minimum: float,
        maximum: float,
        unit: str,
    ) -> None:
        """Write and verify a floating-point setting on D-Bus."""

        value = float(value)

        if not minimum <= value <= maximum:
            raise ValueError(
                f"{name} must be between {minimum:.1f} and "
                f"{maximum:.1f} {unit}, received {value}"
            )

        item = self._get_bus_item(path)

        result = int(
            item.SetValue(
                dbus.Double(value)
            )
        )

        if result != 0:
            raise RuntimeError(
                f"D-Bus rejected {name}={value:.1f} {unit} "
                f"with result code {result}"
            )

        actual_value = self._get_float_setting(
            path=path,
            name=name,
            unit=unit,
        )

        if actual_value != value:
            raise RuntimeError(
                f"{name} verification failed: "
                f"requested {value:.1f} {unit}, "
                f"read back {actual_value:.1f} {unit}"
            )

        self._logger.info(
            "%s set to %.1f %s",
            name,
            actual_value,
            unit,
        )

    def get_max_charge_voltage(self) -> float:
        """Return the configured DVCC maximum charge voltage."""

        return self._get_float_setting(
            path=MAX_CHARGE_VOLTAGE_PATH,
            name="MaxChargeVoltage",
            unit="V",
        )

    def set_max_charge_voltage(self, voltage: float) -> None:
        """
        Set the DVCC maximum charge voltage.

        A value of 0.0 disables the maximum charge voltage override.
        """

        self._set_float_setting(
            path=MAX_CHARGE_VOLTAGE_PATH,
            name="MaxChargeVoltage",
            value=voltage,
            minimum=0.0,
            maximum=80.0,
            unit="V",
        )

    def get_max_charge_current(self) -> float:
        """Return the configured DVCC maximum charge current."""

        return self._get_float_setting(
            path=MAX_CHARGE_CURRENT_PATH,
            name="MaxChargeCurrent",
            unit="A",
        )

    def set_max_charge_current(self, current: float) -> None:
        """
        Set the DVCC maximum charge current.

        A value of 0.0 disables the maximum charge current override.
        """

        self._set_float_setting(
            path=MAX_CHARGE_CURRENT_PATH,
            name="MaxChargeCurrent",
            value=current,
            minimum=0.0,
            maximum=1000.0,
            unit="A",
        )