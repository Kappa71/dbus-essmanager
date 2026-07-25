"""Charge-voltage state machine for dbus-essmanager."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Callable, Optional


class ChargeState(IntEnum):
    """Operating states exposed through D-Bus."""

    OFF = 0
    CHARGE_ABSORPTION = 1
    CHARGE_IDLE = 2
    CHARGE_ABSORPTION_100 = 3
    CHARGE_FLOATING_100 = 4


STATE_TEXT: dict[ChargeState, str] = {
    ChargeState.OFF: "Off",
    ChargeState.CHARGE_ABSORPTION: "Charge absorption",
    ChargeState.CHARGE_IDLE: "Charge idle",
    ChargeState.CHARGE_ABSORPTION_100: "Charge absorption 100%",
    ChargeState.CHARGE_FLOATING_100: "Charge floating 100%",
}


STATE_DESCRIPTION: dict[ChargeState, str] = {
    ChargeState.OFF: "ESS Manager disabled",
    ChargeState.CHARGE_ABSORPTION: (
        "Charging towards the configured maximum SOC"
    ),
    ChargeState.CHARGE_IDLE: "Configured maximum SOC reached",
    ChargeState.CHARGE_ABSORPTION_100: (
        "Waiting for full-battery detection"
    ),
    ChargeState.CHARGE_FLOATING_100: "Battery full",
}


@dataclass(frozen=True)
class SettingsData:
    """Settings used by the state machine."""

    enable: bool

    max_soc: float
    soc_hysteresis: float

    soc_full_voltage: float
    soc_full_tail_current: float
    soc_full_wait_time: float

    limit_voltage_idle: float
    limit_voltage_floating: float
    limit_voltage_absorption: float


@dataclass(frozen=True)
class SystemData:
    """Battery data read from com.victronenergy.system."""

    battery_soc: float
    battery_voltage: float
    battery_current: float


@dataclass(frozen=True)
class StateResult:
    """Result produced by one state-machine update."""

    state: ChargeState
    battery_full: bool
    soc_full_timer: float
    target_charge_voltage: float

    @property
    def status(self) -> str:
        """Return the human-readable state name."""

        return STATE_TEXT[self.state]

    @property
    def description(self) -> str:
        """Return the extended state description."""

        return STATE_DESCRIPTION[self.state]


class StateMachine:
    """Determine the required DVCC maximum charge voltage."""

    def __init__(
        self,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        """
        Initialize the state machine.

        A custom monotonic clock can be supplied by unit tests.
        """

        self._monotonic = monotonic

        self._current_state = ChargeState.OFF
        self._battery_full = False

        self._soc_full_condition_start: Optional[float] = None
        self._soc_full_timer = 0.0

    @property
    def current_state(self) -> ChargeState:
        """Return the current internal state."""

        return self._current_state

    def reset(self) -> None:
        """Reset all transient state-machine values."""

        self._current_state = ChargeState.OFF
        self._reset_full_detection()

    def update(
        self,
        settings: SettingsData,
        system: SystemData,
    ) -> StateResult:
        """
        Evaluate the inputs and return the requested operating state.

        The state machine does not perform any D-Bus reads or writes.
        """

        if not settings.enable:
            return self._update_disabled()

        if settings.max_soc < 100.0:
            return self._update_limited_soc(
                settings=settings,
                system=system,
            )

        return self._update_full_soc(
            settings=settings,
            system=system,
        )

    def _update_disabled(self) -> StateResult:
        """Handle the disabled state."""

        self._current_state = ChargeState.OFF
        self._reset_full_detection()

        return self._build_result(
            target_charge_voltage=0.0,
        )

    def _update_limited_soc(
        self,
        settings: SettingsData,
        system: SystemData,
    ) -> StateResult:
        """Handle operation with MaxSoc below 100 percent."""

        self._reset_full_detection()

        limited_soc_states = {
            ChargeState.CHARGE_ABSORPTION,
            ChargeState.CHARGE_IDLE,
        }

        if self._current_state not in limited_soc_states:
            if system.battery_soc >= settings.max_soc:
                self._current_state = ChargeState.CHARGE_IDLE
            else:
                self._current_state = ChargeState.CHARGE_ABSORPTION

        elif self._current_state == ChargeState.CHARGE_ABSORPTION:
            if system.battery_soc >= settings.max_soc:
                self._current_state = ChargeState.CHARGE_IDLE

        elif self._current_state == ChargeState.CHARGE_IDLE:
            restart_soc = (
                settings.max_soc
                - settings.soc_hysteresis
            )

            if system.battery_soc <= restart_soc:
                self._current_state = ChargeState.CHARGE_ABSORPTION

        if self._current_state == ChargeState.CHARGE_IDLE:
            target_voltage = settings.limit_voltage_idle
        else:
            target_voltage = settings.limit_voltage_absorption

        return self._build_result(
            target_charge_voltage=target_voltage,
        )

    def _update_full_soc(
        self,
        settings: SettingsData,
        system: SystemData,
    ) -> StateResult:
        """Handle operation with MaxSoc equal to 100 percent."""

        if self._current_state == ChargeState.CHARGE_FLOATING_100:
            return self._update_floating_100(
                settings=settings,
                system=system,
            )

        if self._current_state != ChargeState.CHARGE_ABSORPTION_100:
            self._current_state = ChargeState.CHARGE_ABSORPTION_100
            self._reset_full_detection()

        full_condition = (
            system.battery_voltage >= settings.soc_full_voltage
            and abs(system.battery_current)
            <= settings.soc_full_tail_current
        )

        if not full_condition:
            self._reset_full_detection()

            return self._build_result(
                target_charge_voltage=(
                    settings.limit_voltage_absorption
                ),
            )

        self._update_full_detection_timer()

        if self._soc_full_timer >= settings.soc_full_wait_time:
            self._current_state = ChargeState.CHARGE_FLOATING_100
            self._battery_full = True

            return self._build_result(
                target_charge_voltage=(
                    settings.limit_voltage_floating
                ),
            )

        return self._build_result(
            target_charge_voltage=settings.limit_voltage_absorption,
        )

    def _update_floating_100(
        self,
        settings: SettingsData,
        system: SystemData,
    ) -> StateResult:
        """Handle the floating state after full-battery detection."""

        restart_soc = 100.0 - settings.soc_hysteresis

        if system.battery_soc <= restart_soc:
            self._current_state = ChargeState.CHARGE_ABSORPTION_100
            self._reset_full_detection()

            return self._build_result(
                target_charge_voltage=(
                    settings.limit_voltage_absorption
                ),
            )

        self._battery_full = True

        return self._build_result(
            target_charge_voltage=settings.limit_voltage_floating,
        )

    def _update_full_detection_timer(self) -> None:
        """Start or update the continuous full-condition timer."""

        now = self._monotonic()

        if self._soc_full_condition_start is None:
            self._soc_full_condition_start = now
            self._soc_full_timer = 0.0
            return

        elapsed_seconds = now - self._soc_full_condition_start

        self._soc_full_timer = max(
            0.0,
            elapsed_seconds / 60.0,
        )

    def _reset_full_detection(self) -> None:
        """Reset full-battery detection and its timer."""

        self._battery_full = False
        self._soc_full_condition_start = None
        self._soc_full_timer = 0.0

    def _build_result(
        self,
        target_charge_voltage: float,
    ) -> StateResult:
        """Build an immutable result from the current internal values."""

        return StateResult(
            state=self._current_state,
            battery_full=self._battery_full,
            soc_full_timer=self._soc_full_timer,
            target_charge_voltage=float(target_charge_voltage),
        )