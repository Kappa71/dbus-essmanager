import json
import logging
import subprocess
from typing import Any, Dict, Optional

from essmanager.setting_definitions import SETTING_DEFINITIONS


DISCOVERY_PREFIX = "homeassistant"


class HomeAssistantDiscovery:
    """Publish Home Assistant MQTT device discovery information."""

    def __init__(
        self,
        portal_id: str,
        device_instance: int,
        mqtt_host: str = "127.0.0.1",
        mqtt_port: int = 1883,
        mqtt_username: Optional[str] = None,
        mqtt_password: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._portal_id = str(portal_id).strip()
        self._device_instance = int(device_instance)
        self._mqtt_host = mqtt_host
        self._mqtt_port = mqtt_port
        self._mqtt_username = mqtt_username
        self._mqtt_password = mqtt_password
        self._logger = logger or logging.getLogger(__name__)

        self._device_id = (
            f"dbus_essmanager_{self._device_instance}"
        )

        self._read_topic_base = (
            f"N/{self._portal_id}/essmanager/"
            f"{self._device_instance}"
        )

        self._write_topic_base = (
            f"W/{self._portal_id}/essmanager/"
            f"{self._device_instance}"
        )

        self._discovery_topic = (
            f"{DISCOVERY_PREFIX}/device/"
            f"{self._device_id}/config"
        )

    def publish(self) -> None:
        """Publish the retained Home Assistant discovery message."""

        payload = self._build_payload()

        self._publish(
            topic=self._discovery_topic,
            payload=json.dumps(
                payload,
                separators=(",", ":"),
            ),
            retain=True,
        )

        self._logger.info(
            "Home Assistant MQTT discovery published to %s",
            self._discovery_topic,
        )

    def remove(self) -> None:
        """Remove the retained Home Assistant discovery message."""

        self._publish(
            topic=self._discovery_topic,
            payload="",
            retain=True,
        )

        self._logger.info(
            "Home Assistant MQTT discovery removed from %s",
            self._discovery_topic,
        )

    def _build_payload(self) -> Dict[str, Any]:
        """Build the Home Assistant device discovery payload."""

        components = self._build_setting_components()

        components["status"] = {
            "platform": "sensor",
            "name": "Status",
            "unique_id": "ess_manager_status",
            "default_entity_id": "sensor.ess_manager_status",
            "state_topic": self._read_topic("Status"),
            "value_template": "{{ value_json.value }}",
            "icon": "mdi:battery-sync",
        }

        components["state"] = {
            "platform": "sensor",
            "name": "State",
            "unique_id": "ess_manager_state",
            "default_entity_id": "sensor.ess_manager_state",
            "state_topic": self._read_topic("State"),
            "value_template": "{{ value_json.value | int }}",
            "entity_category": "diagnostic",
        }

        components["soc_full_timer"] = {
            "platform": "sensor",
            "name": "SOC full timer",
            "unique_id": "ess_manager_soc_full_timer",
            "default_entity_id": (
                "sensor.ess_manager_soc_full_timer"
            ),
            "state_topic": self._read_topic("SocFullTimer"),
            "value_template": "{{ value_json.value | float }}",
            "unit_of_measurement": "min",
            "state_class": "measurement",
            "entity_category": "diagnostic",
        }

        components["battery_full"] = {
            "platform": "binary_sensor",
            "name": "Battery full",
            "unique_id": "ess_manager_battery_full",
            "default_entity_id": (
                "binary_sensor.ess_manager_battery_full"
            ),
            "state_topic": self._read_topic("BatteryFull"),
            "value_template": "{{ value_json.value | int }}",
            "payload_on": "1",
            "payload_off": "0",
        }

        components["connected"] = {
            "platform": "binary_sensor",
            "name": "Connected",
            "unique_id": "ess_manager_connected",
            "default_entity_id": (
                "binary_sensor.ess_manager_connected"
            ),
            "state_topic": self._read_topic("Connected"),
            "value_template": "{{ value_json.value | int }}",
            "payload_on": "1",
            "payload_off": "0",
            "device_class": "connectivity",
            "entity_category": "diagnostic",
        }

        return {
            "device": {
                "identifiers": [self._device_id],
                "name": "ESS Manager",
                "manufacturer": "dbus-essmanager",
                "model": "Venus OS D-Bus service",
                "model_id": "dbus-essmanager",
            },
            "origin": {
                "name": "dbus-essmanager",
            },
            "components": components,
        }

    def _build_setting_components(
        self,
    ) -> Dict[str, Dict[str, Any]]:
        """Build discovery components from shared setting definitions."""

        components: Dict[str, Dict[str, Any]] = {}

        for setting_name, definition in SETTING_DEFINITIONS.items():
            home_assistant = definition.get("home_assistant")

            if home_assistant is None:
                continue

            platform = home_assistant["platform"]
            path = definition["service_path"].lstrip("/")

            if platform == "switch":
                component = self._switch_component(
                    name=home_assistant["name"],
                    unique_id=home_assistant["unique_id"],
                    default_entity_id=(
                        home_assistant["default_entity_id"]
                    ),
                    path=path,
                )
            elif platform == "number":
                component = self._number_component(
                    definition=definition,
                    home_assistant=home_assistant,
                    path=path,
                )
            else:
                raise ValueError(
                    "Unsupported Home Assistant platform "
                    f"{platform!r} for setting {setting_name!r}"
                )

            components[setting_name] = component

        return components

    def _switch_component(
        self,
        name: str,
        unique_id: str,
        default_entity_id: str,
        path: str,
    ) -> Dict[str, Any]:
        return {
            "platform": "switch",
            "name": name,
            "unique_id": unique_id,
            "default_entity_id": default_entity_id,
            "state_topic": self._read_topic(path),
            "command_topic": self._write_topic(path),
            "value_template": "{{ value_json.value | int }}",
            "state_on": "1",
            "state_off": "0",
            "payload_on": '{"value":1}',
            "payload_off": '{"value":0}',
            "optimistic": False,
        }

    def _number_component(
        self,
        definition: Dict[str, Any],
        home_assistant: Dict[str, Any],
        path: str,
    ) -> Dict[str, Any]:
        """Build an integer or floating-point number component."""

        value_type = definition["value_type"]

        if value_type is int:
            value_filter = "int"
            default_step: Any = 1
        elif value_type is float:
            value_filter = "float"
            default_step = 0.1
        else:
            raise ValueError(
                "Unsupported value_type "
                f"{value_type!r} for path {definition['service_path']!r}"
            )

        component: Dict[str, Any] = {
            "platform": "number",
            "name": home_assistant["name"],
            "unique_id": home_assistant["unique_id"],
            "default_entity_id": (
                home_assistant["default_entity_id"]
            ),
            "state_topic": self._read_topic(path),
            "command_topic": self._write_topic(path),
            "value_template": (
                f"{{{{ value_json.value | {value_filter} }}}}"
            ),
            "command_template": (
                '{"value":{{ value | '
                f"{value_filter}"
                ' }}}'
            ),
            "min": definition["minimum"],
            "max": definition["maximum"],
            "step": home_assistant.get("step", default_step),
            "mode": home_assistant.get("mode", "box"),
            "unit_of_measurement": definition["unit"],
        }

        entity_category = home_assistant.get(
            "entity_category",
            "config",
        )

        if entity_category is not None:
            component["entity_category"] = entity_category

        return component

    def _read_topic(self, path: str) -> str:
        return f"{self._read_topic_base}/{path}"

    def _write_topic(self, path: str) -> str:
        return f"{self._write_topic_base}/{path}"

    def _publish(
        self,
        topic: str,
        payload: str,
        retain: bool,
    ) -> None:
        command = [
            "mosquitto_pub",
            "-h",
            self._mqtt_host,
            "-p",
            str(self._mqtt_port),
            "-t",
            topic,
            "-m",
            payload,
        ]

        if retain:
            command.append("-r")

        if self._mqtt_username:
            command.extend(["-u", self._mqtt_username])

        if self._mqtt_password:
            command.extend(["-P", self._mqtt_password])

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as error:
            raise RuntimeError(
                "mosquitto_pub is not installed"
            ) from error
        except subprocess.CalledProcessError as error:
            message = error.stderr.strip() or str(error)

            raise RuntimeError(
                f"MQTT discovery publish failed: {message}"
            ) from error