from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop

from essmanager.settings import Settings
from essmanager.logger import setup_logger
from essmanager.dbus_service import DBusService


def main():
    settings = Settings()
    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    # Collega D-Bus al main loop GLib.
    # Deve avvenire prima della creazione di qualsiasi connessione D-Bus.
    DBusGMainLoop(set_as_default=True)

    service = DBusService(settings.device_instance)

    logger.info("Service registered")

    mainloop = GLib.MainLoop()

    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("Stopping dbus-essmanager")


if __name__ == "__main__":
    main()