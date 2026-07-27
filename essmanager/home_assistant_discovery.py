import json
import logging
import subprocess
from typing import Any, Dict, Optional


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

        components: Dict[str, Dict[str, Any]] = {}

        components["enable"] = self._switch_component(
            name="Enable",
            unique_id="ess_manager_enable",
            default_entity_id="switch.ess_manager_enable",
            path="Settings/Enable",
        )

        components["maximum_soc"] = self._integer_number_component(
            name="Maximum SOC",
            unique_id="ess_manager_max_soc",
            default_entity_id="number.ess_manager_max_soc",
            path="Settings/MaxSoc",
            minimum=10,
            maximum=100,
            mode="slider",
            unit="%",
            entity_category=None,
        )

        components["soc_hysteresis"] = self._integer_number_component(
            name="SOC Hysteresis",
            unique_id="ess_manager_soc_hysteresis",
            default_entity_id="number.ess_manager_soc_hysteresis",
            path="Settings/SocHysteresis",
            minimum=1,
            maximum=50,
            mode="box",
            unit="%",
        )

        components["soc_full_voltage"] = self._float_number_component(
            name="SOC Full voltage",
            unique_id="ess_manager_soc_full_voltage",
            default_entity_id="number.ess_manager_soc_full_voltage",
            path="Settings/SocFullVoltage",
            minimum=48.0,
            maximum=60.0,
            step=0.1,
            unit="V",
        )

        components["soc_full_tail_current"] = (
            self._integer_number_component(
                name="SOC Full Tail current",
                unique_id="ess_manager_soc_full_tail_current",
                default_entity_id=(
                    "number.ess_manager_soc_full_tail_current"
                ),
                path="Settings/SocFullTailCurrent",
                minimum=0,
                maximum=100,
                mode="box",
                unit="A",
            )
        )

        components["soc_full_wait_time"] = (
            self._integer_number_component(
                name="SOC Full Wait time",
                unique_id="ess_manager_soc_full_wait_time",
                default_entity_id=(
                    "number.ess_manager_soc_full_wait_time"
                ),
                path="Settings/SocFullWaitTime",
                minimum=0,
                maximum=1440,
                mode="box",
                unit="min",
            )
        )

        components["limit_voltage_idle"] = (
            self._float_number_component(
                name="ESS Idle voltage",
                unique_id="ess_manager_limit_voltage_idle",
                default_entity_id=(
                    "number.ess_manager_limit_voltage_idle"
                ),
                path="Settings/LimitVoltageIdle",
                minimum=48.0,
                maximum=60.0,
                step=0.1,
                unit="V",
            )
        )

        components["limit_voltage_floating"] = (
            self._float_number_component(
                name="ESS Floating voltage",
                unique_id="ess_manager_limit_voltage_floating",
                default_entity_id=(
                    "number.ess_manager_limit_voltage_floating"
                ),
                path="Settings/LimitVoltageFloating",
                minimum=48.0,
                maximum=60.0,
                step=0.1,
                unit="V",
            )
        )

        components["limit_voltage_absorption"] = (
            self._float_number_component(
                name="ESS Absorption voltage",
                unique_id="ess_manager_limit_voltage_absorption",
                default_entity_id=(
                    "number.ess_manager_limit_voltage_absorption"
                ),
                path="Settings/LimitVoltageAbsorption",
                minimum=48.0,
                maximum=60.0,
                step=0.1,
                unit="V",
            )
        )

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

    def _integer_number_component(
        self,
        name: str,
        unique_id: str,
        default_entity_id: str,
        path: str,
        minimum: int,
        maximum: int,
        mode: str,
        unit: str,
        entity_category: Optional[str] = "config",
    ) -> Dict[str, Any]:
        component: Dict[str, Any] = {
            "platform": "number",
            "name": name,
            "unique_id": unique_id,
            "default_entity_id": default_entity_id,
            "state_topic": self._read_topic(path),
            "command_topic": self._write_topic(path),
            "value_template": "{{ value_json.value | int }}",
            "command_template": '{"value":{{ value | int }}}',
            "min": minimum,
            "max": maximum,
            "step": 1,
            "mode": mode,
            "unit_of_measurement": unit,
        }

        if entity_category is not None:
            component["entity_category"] = entity_category

        return component

    def _float_number_component(
        self,
        name: str,
        unique_id: str,
        default_entity_id: str,
        path: str,
        minimum: float,
        maximum: float,
        step: float,
        unit: str,
    ) -> Dict[str, Any]:
        return {
            "platform": "number",
            "name": name,
            "unique_id": unique_id,
            "default_entity_id": default_entity_id,
            "state_topic": self._read_topic(path),
            "command_topic": self._write_topic(path),
            "value_template": "{{ value_json.value | float }}",
            "command_template": '{"value":{{ value | float }}}',
            "min": minimum,
            "max": maximum,
            "step": step,
            "mode": "box",
            "unit_of_measurement": unit,
            "entity_category": "config",
        }

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