#!/usr/bin/env python3
"""Remove the retained Home Assistant MQTT discovery message."""

import sys

from dbus.mainloop.glib import DBusGMainLoop

from essmanager.home_assistant_discovery import (
    HomeAssistantDiscovery,
)
from essmanager.settings import Settings
from essmanager.victron_system import VictronSystem


def main() -> None:
    """Remove Home Assistant discovery for this service instance."""

    # This must happen before creating D-Bus connections.
    DBusGMainLoop(set_as_default=True)

    settings = Settings()

    victron_system = VictronSystem()
    portal_id = victron_system.get_portal_id()

    discovery = HomeAssistantDiscovery(
        portal_id=portal_id,
        device_instance=settings.device_instance,
    )

    discovery.remove()

    print(
        "Home Assistant MQTT discovery removed for "
        f"Portal ID {portal_id}, "
        f"DeviceInstance {settings.device_instance}"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            "Unable to remove Home Assistant MQTT discovery: "
            f"{error}",
            file=sys.stderr,
        )
        raise SystemExit(1)