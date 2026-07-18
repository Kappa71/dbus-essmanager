from essmanager import victron_settings
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from essmanager.settings import Settings
from essmanager.logger import setup_logger
from essmanager.dbus_service import DBusService
from essmanager.victron_settings import VictronSettings
from essmanager.victron_system import VictronSystem


def main():
    settings = Settings()
    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    # Connect the main loop to the D-Bus system bus. This must 
    # happen before any D-Bus connections are created.
    DBusGMainLoop(set_as_default=True)

    service = DBusService(settings.device_instance)

    victron_settings = VictronSettings(logger=logger)
    victron_system = VictronSystem(logger=logger)

    max_charge_voltage = victron_settings.get_max_charge_voltage()
    max_charge_current = victron_settings.get_max_charge_current()

    logger.info(
        "Current DVCC limits: %.1f V, %.1f A",
        max_charge_voltage,
        max_charge_current,
    )
    #max_charge_voltage = 52.1
    #max_charge_current = 0
    #victron_settings.set_max_charge_voltage(max_charge_voltage)
    #victron_settings.set_max_charge_current(max_charge_current)

    battery_soc = victron_system.get_battery_soc()
    battery_voltage = victron_system.get_battery_voltage()
    battery_current = victron_system.get_battery_current()

    logger.info(
        "Battery status: SOC %.1f %%, voltage %.1f V, current %.1f A",
        battery_soc,
        battery_voltage,
        battery_current,
    )

    logger.info("Service registered")

    mainloop = GLib.MainLoop()

    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("Stopping dbus-essmanager")


if __name__ == "__main__":
    main()