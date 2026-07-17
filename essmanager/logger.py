import logging


def setup_logger(level="INFO"):

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    return logging.getLogger("dbus-essmanager")