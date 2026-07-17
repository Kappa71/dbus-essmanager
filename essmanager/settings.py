import configparser
import os


class Settings:
    def __init__(self):
        self.config = configparser.ConfigParser()

        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config.ini"
        )

        self.config.read(config_path)

        self.logging = self.config.get(
            "DEFAULT",
            "Logging",
            fallback="INFO"
        )

        self.device_instance = self.config.getint(
            "DEFAULT",
            "DeviceInstance",
            fallback=250
        )