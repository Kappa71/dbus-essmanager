"""Main entry point for dbus-essmanager."""

import time

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from essmanager.dbus_service import DBusService
from essmanager.ess_manager import EssManager
from essmanager.home_assistant_discovery import (
    HomeAssistantDiscovery,
)
from essmanager.logger import setup_logger
from essmanager.settings import Settings
from essmanager.state_machine import StateMachine
from essmanager.victron_settings import VictronSettings
from essmanager.victron_system import VictronSystem


LOOP_INTERVAL_SECONDS = 1
DISCOVERY_RETRY_INTERVAL_SECONDS = 30

SYSTEM_READY_TIMEOUT_SECONDS = 30
SYSTEM_READY_POLL_SECONDS = 1


def wait_for_victron_system(
    victron_system: VictronSystem,
    logger,
) -> None:
    """
    Wait until com.victronenergy.system becomes available.

    During Venus OS startup, dbus-essmanager may start before
    dbus-systemcalc-py has registered com.victronenergy.system.
    """

    deadline = time.monotonic() + SYSTEM_READY_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        try:
            victron_system.get_portal_id()

            logger.info(
                "Victron system service is available"
            )
            return

        except Exception:
            time.sleep(SYSTEM_READY_POLL_SECONDS)

    logger.warning(
        "Victron system service was not available after %d seconds; "
        "starting anyway",
        SYSTEM_READY_TIMEOUT_SECONDS,
    )


def main() -> None:
    """Start the dbus-essmanager service and control loop."""

    settings = Settings()
    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    # Connect the main loop to the D-Bus system bus.
    # This must happen before any D-Bus connections are created.
    DBusGMainLoop(set_as_default=True)

    device_instance = settings.device_instance

    service = DBusService(
        device_instance=device_instance,
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

    logger.info(
        "Service registered with DeviceInstance %d",
        device_instance,
    )

    # Venus OS services are started independently. Wait for
    # com.victronenergy.system before performing the initial reads.
    wait_for_victron_system(
        victron_system=victron_system,
        logger=logger,
    )

    # Publish Home Assistant MQTT discovery information.
    #
    # The callback returns True when publication fails, causing GLib
    # to retry periodically. It returns False after a successful
    # publication, stopping further retries.
    def publish_home_assistant_discovery() -> bool:
        try:
            portal_id = victron_system.get_portal_id()

            discovery = HomeAssistantDiscovery(
                portal_id=portal_id,
                device_instance=device_instance,
                logger=logger,
            )

            discovery.publish()

            logger.info(
                "Home Assistant MQTT discovery active for "
                "Portal ID %s and DeviceInstance %d",
                portal_id,
                device_instance,
            )

            return False

        except Exception:
            logger.exception(
                "Unable to publish Home Assistant MQTT discovery; "
                "retrying in %d seconds",
                DISCOVERY_RETRY_INTERVAL_SECONDS,
            )

            return True

    # Try immediately. If publication fails, schedule periodic retries.
    if publish_home_assistant_discovery():
        GLib.timeout_add_seconds(
            DISCOVERY_RETRY_INTERVAL_SECONDS,
            publish_home_assistant_discovery,
        )

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