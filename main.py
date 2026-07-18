from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from essmanager.settings import Settings
from essmanager.logger import setup_logger
from essmanager.dbus_service import DBusService
from essmanager.victron_settings import VictronSettings


def main():
    settings = Settings()
    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    # Connect the main loop to the D-Bus system bus. This must 
    # happen before any D-Bus connections are created.
    DBusGMainLoop(set_as_default=True)

    service = DBusService(settings.device_instance)

    victron_settings = VictronSettings(logger=logger)

    max_charge_voltage = victron_settings.get_max_charge_voltage()

    logger.info(
        "Current MaxChargeVoltage: %.1f V",
        max_charge_voltage,
    )


    #max_charge_voltage = 55.1
    #victron_settings.set_max_charge_voltage(max_charge_voltage)

    logger.info("Service registered")

    mainloop = GLib.MainLoop()

    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("Stopping dbus-essmanager")


if __name__ == "__main__":
    main()