"""Coordinate the ESS charge-voltage state machine."""

from __future__ import annotations

import logging
import math
from typing import Optional

from essmanager.dbus_service import DBusService
from essmanager.state_machine import (
    SettingsData,
    StateMachine,
    StateResult,
)
from essmanager.victron_settings import VictronSettings
from essmanager.victron_system import VictronSystem


class EssManager:
    """Coordinate system readings, settings and DVCC voltage control."""

    def __init__(
        self,
        dbus_service: DBusService,
        victron_system: VictronSystem,
        victron_settings: VictronSettings,
        state_machine: Optional[StateMachine] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._dbus_service = dbus_service
        self._victron_system = victron_system
        self._victron_settings = victron_settings
        self._state_machine = state_machine or StateMachine()
        self._logger = logger or logging.getLogger(__name__)

        self._last_state: Optional[int] = None
        self._last_battery_full: Optional[bool] = None
        self._last_soc_full_timer: Optional[float] = None

    def update(self) -> bool:
        """
        Execute one complete ESS Manager control cycle.

        The Boolean return value makes this method directly usable as a
        GLib timeout callback. Returning True keeps the timer active.
        """

        try:
            settings = self._read_settings()
            system = self._victron_system.read()

            result = self._state_machine.update(
                settings=settings,
                system=system,
            )

            self._apply_state_result(result)
            self._apply_target_charge_voltage(
                result.target_charge_voltage
            )

        except Exception:
            self._logger.exception(
                "ESS Manager control cycle failed"
            )

        return True

    def _read_settings(self) -> SettingsData:
        """Read all persistent settings required by the state machine."""

        return SettingsData(
            enable=bool(self._dbus_service.get_enable()),
            max_soc=float(self._dbus_service.get_max_soc()),
            soc_hysteresis=float(
                self._dbus_service.get_soc_hysteresis()
            ),
            soc_full_voltage=float(
                self._dbus_service.get_soc_full_voltage()
            ),
            soc_full_tail_current=float(
                self._dbus_service.get_soc_full_tail_current()
            ),
            soc_full_wait_time=float(
                self._dbus_service.get_soc_full_wait_time()
            ),
            limit_voltage_idle=float(
                self._dbus_service.get_limit_voltage_idle()
            ),
            limit_voltage_floating=float(
                self._dbus_service.get_limit_voltage_floating()
            ),
            limit_voltage_absorption=float(
                self._dbus_service.get_limit_voltage_absorption()
            ),
        )

    def _apply_state_result(
        self,
        result: StateResult,
    ) -> None:
        """Publish state-machine runtime values on the service D-Bus."""

        state_value = int(result.state)

        if self._last_state != state_value:
            self._logger.info(
                "ESS Manager state changed: %s (%d)",
                result.status,
                state_value,
            )

            self._dbus_service.set_state_and_status(
                state_value,
                result.status,
            )

            self._last_state = state_value

        battery_full = bool(result.battery_full)

        if self._last_battery_full != battery_full:
            self._logger.info(
                "BatteryFull changed: %s",
                battery_full,
            )

            self._dbus_service.set_battery_full(
                battery_full
            )

            self._last_battery_full = battery_full

        self._apply_soc_full_timer(
            result.soc_full_timer
        )

    def _apply_soc_full_timer(
        self,
        timer_minutes: float,
    ) -> None:
        """
        Publish the elapsed full-detection timer.

        The value is rounded to two decimal places, corresponding to
        approximately 0.6 seconds, to avoid insignificant floating-point
        differences.
        """

        timer_minutes = round(float(timer_minutes), 2)

        if self._last_soc_full_timer == timer_minutes:
            return

        self._dbus_service.set_soc_full_timer(
            timer_minutes
        )

        self._last_soc_full_timer = timer_minutes

    def _apply_target_charge_voltage(
        self,
        target_voltage: float,
    ) -> None:
        """
        Apply the requested DVCC maximum charge voltage when necessary.

        The actual value is read from com.victronenergy.settings during
        every control cycle. This ensures that the state machine remains
        authoritative without repeatedly writing the same persistent
        setting.
        """

        target_voltage = self._normalize_voltage(
            target_voltage,
            name="Target charge voltage",
        )

        current_voltage = self._normalize_voltage(
            self._victron_settings.get_max_charge_voltage(),
            name="Current charge voltage",
        )

        if current_voltage == target_voltage:
            return

        self._logger.info(
            "Changing MaxChargeVoltage: %.1f V -> %.1f V",
            current_voltage,
            target_voltage,
        )

        self._victron_settings.set_max_charge_voltage(
            target_voltage
        )

    @staticmethod
    def _normalize_voltage(
        value: float,
        name: str,
    ) -> float:
        """
        Convert and validate a charge-voltage value.

        Voltage settings currently use one decimal place throughout the
        service. Normalizing here also avoids differences caused solely by
        D-Bus numeric types or floating-point representation.
        """

        try:
            voltage = float(value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Invalid {name}: {value!r}"
            ) from exc

        if not math.isfinite(voltage):
            raise RuntimeError(
                f"Non-finite {name}: {value!r}"
            )

        return round(voltage, 1)