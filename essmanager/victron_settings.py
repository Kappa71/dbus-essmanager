import logging
from typing import Optional

import dbus


SETTINGS_SERVICE = "com.victronenergy.settings"
MAX_CHARGE_VOLTAGE_PATH = "/Settings/SystemSetup/MaxChargeVoltage"
BUS_ITEM_INTERFACE = "com.victronenergy.BusItem"


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

    def get_max_charge_voltage(self) -> float:
        """Return the configured DVCC maximum charge voltage."""

        item = self._get_bus_item(MAX_CHARGE_VOLTAGE_PATH)
        value = item.GetValue()

        voltage = float(value)

        self._logger.debug(
            "Read MaxChargeVoltage from D-Bus: %.1f V",
            voltage,
        )

        return voltage

    def set_max_charge_voltage(self, voltage: float) -> None:
        """
        Set the DVCC maximum charge voltage.

        A value of 0.0 disables the maximum charge voltage override.
        """

        voltage = float(voltage)

        if not 0.0 <= voltage <= 80.0:
            raise ValueError(
                f"MaxChargeVoltage must be between 0.0 and 80.0 V, "
                f"received {voltage}"
            )

        item = self._get_bus_item(MAX_CHARGE_VOLTAGE_PATH)

        result = int(
            item.SetValue(
                dbus.Double(voltage)
            )
        )

        if result != 0:
            raise RuntimeError(
                f"D-Bus rejected MaxChargeVoltage={voltage:.1f} V "
                f"with result code {result}"
            )

        # Read back the setting so that successful SetValue alone is
        # not mistaken for a verified write.
        actual_voltage = self.get_max_charge_voltage()

        if actual_voltage != voltage:
            raise RuntimeError(
                f"MaxChargeVoltage verification failed: "
                f"requested {voltage:.1f} V, "
                f"read back {actual_voltage:.1f} V"
            )

        self._logger.info(
            "MaxChargeVoltage set to %.1f V",
            actual_voltage,
        )