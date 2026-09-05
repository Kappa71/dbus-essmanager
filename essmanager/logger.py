import logging
import sys


def setup_logger(level="INFO"):

    logger = logging.getLogger("dbus-essmanager")

    log_level = getattr(
        logging,
        level.upper(),
    )

    logger.setLevel(log_level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)

        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(message)s"
            )
        )

        logger.addHandler(handler)

    logger.propagate = False

    return logger