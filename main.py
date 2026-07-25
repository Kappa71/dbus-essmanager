"""Main entry point for dbus-essmanager."""

from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from essmanager.settings import Settings
from essmanager.logger import setup_logger
from essmanager.dbus_service import DBusService
from essmanager.ess_manager import EssManager
from essmanager.state_machine import StateMachine
from essmanager.victron_settings import VictronSettings
from essmanager.victron_system import VictronSystem


LOOP_INTERVAL_SECONDS = 1


def main() -> None:
    """Start the dbus-essmanager service and control loop."""

    settings = Settings()
    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    # Connect the main loop to the D-Bus system bus.
    # This must happen before any D-Bus connections are created.
    DBusGMainLoop(set_as_default=True)

    service = DBusService(
        settings.device_instance,
        logger=logger,
    )

    victron_settings = VictronSettings(
        logger=logger,
    )

    victron_system = VictronSystem(
        logger=logger,
    )

    state_machine = StateMachine()

    ess_manager = EssManager(
        dbus_service=service,
        victron_system=victron_system,
        victron_settings=victron_settings,
        state_machine=state_machine,
        logger=logger,
    )

    logger.info("Service registered")

    # Initial diagnostic readings.
    # MaxChargeCurrent is only read and logged; it is not modified by
    # dbus-essmanager.
    try:
        max_charge_voltage = (
            victron_settings.get_max_charge_voltage()
        )
        max_charge_current = (
            victron_settings.get_max_charge_current()
        )

        logger.info(
            "Current DVCC limits: %.1f V, %.1f A",
            max_charge_voltage,
            max_charge_current,
        )

        system_data = victron_system.read()

        logger.info(
            "Battery status: SOC %.1f %%, "
            "voltage %.1f V, current %.1f A",
            system_data.battery_soc,
            system_data.battery_voltage,
            system_data.battery_current,
        )

    except Exception:
        logger.exception(
            "Unable to read initial Victron values"
        )

    # Execute the first control cycle immediately instead of waiting
    # for the first GLib timeout.
    ess_manager.update()

    # EssManager.update() returns True, which keeps the GLib timer active.
    GLib.timeout_add_seconds(
        LOOP_INTERVAL_SECONDS,
        ess_manager.update,
    )

    logger.info(
        "ESS Manager control loop started with interval %d s",
        LOOP_INTERVAL_SECONDS,
    )

    mainloop = GLib.MainLoop()

    try:
        mainloop.run()

    except KeyboardInterrupt:
        logger.info("Stopping dbus-essmanager")


if __name__ == "__main__":
    main()