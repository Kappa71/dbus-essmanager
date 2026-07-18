import logging
import sys


def setup_logger(level="INFO"):

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.StreamHandler(sys.stdout)

    return logging.getLogger("dbus-essmanager")