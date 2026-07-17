try:
    from gi.repository import GLib
except ImportError:
    raise ImportError(
        "GLib is not available. This application must run on Venus OS."
    )

from essmanager.dbus_service import DBusService

from essmanager.settings import Settings
from essmanager.logger import setup_logger
from essmanager.dbus_service import DBusService


def main():

    settings = Settings()

    logger = setup_logger(settings.logging)

    logger.info("Starting dbus-essmanager")

    service = DBusService()

    logger.info("Service registered")

    loop = GLib.MainLoop()

    loop.run()


if __name__ == "__main__":
    main()