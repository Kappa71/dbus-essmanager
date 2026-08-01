# dbus-essmanager

A lightweight D-Bus service for Venus OS that extends Victron ESS with
configurable battery charging strategies.

The service automatically controls the DVCC Maximum Charge Voltage Limit based on
battery state, configurable charge limits and user-defined charging policies.

Designed for battery systems using Victron DVCC while remaining fully compatible with the standard Victron ecosystem.

## Screenshots

### Home Assistant

![Home Assistant](docs/images/home-assistant-device.png)

### D-Bus service

![D-Bus](docs/images/dbus-spy.png)

---

## Quick Start

### Option 1 – Clone the repository (requires Git)

```bash
git clone https://github.com/<username>/dbus-essmanager.git
cd dbus-essmanager

chmod +x install.sh
./install.sh
```

### Option 2 – Manual installation

Download the latest project archive from GitHub and copy the
`dbus-essmanager` directory to:

```text
/data/dbus-essmanager
```

Then connect to the Venus OS shell and run:

```bash
cd /data/dbus-essmanager

chmod +x install.sh
./install.sh
```

The installer:

- registers the runit service
- enables automatic startup after reboot
- starts **dbus-essmanager** immediately

Configuration can then be adjusted through D-Bus, MQTT or Home Assistant
(using MQTT Discovery).

---

Warning

This software modifies the Victron DVCC Maximum Charge Voltage Limit automatically.
It is intended for users who understand the implications of custom battery charging parameters.
Always verify your battery manufacturer's recommended charging limits.

## Requirements

- Venus OS v3.60 or later
- DVCC enabled
- MQTT enabled (required for Home Assistant MQTT Discovery)

## Features

- Native D-Bus service
- Persistent settings stored by `com.victronenergy.settings`
- Automatic DVCC Maximum Charge Voltage Limit management
- Configurable maximum battery SOC
- Automatic full-battery detection
- Automatic transition between:
  - Charge absorption
  - Charge floating
  - Charge idle
- Configurable:
  - absorption voltage
  - floating voltage
  - idle voltage
  - full-battery detection voltage
  - tail current
  - validation time
  - SOC hysteresis
- MQTT support through the standard Venus MQTT broker
- Home Assistant MQTT Discovery
- No modifications required to Victron services
- Very low CPU and memory usage

---

## How it works

The service continuously monitors:

- Battery SOC
- Battery voltage
- Battery current

and automatically updates the DVCC Maximum Charge Voltage Limit according to the
configured charging strategy.

When the battery reaches the configured full conditions:

- voltage above threshold
- current below tail current
- condition maintained for the configured time

the DVCC voltage is reduced to the configured Floating Voltage.

When the SOC later drops below the restart threshold, charging automatically
returns to Absorption Voltage.

If the user limits the maximum SOC below 100%, the service automatically
switches between:

Charge Absorption → Charge Idle

without performing full-battery detection.

Max SOC = 100%

Absorption
      │
      │ Full voltage reached
      │ Tail current reached
      │ Wait time elapsed
      ▼
Floating
      │
      │ SOC < 100 % - Hysteresis
      ▼
Absorption


Max SOC < 100%

Absorption
      │
      │ SOC >= Max SOC
      ▼
Idle
      │
      │ SOC <= Max SOC - Hysteresis
      ▼
Absorption


Install:

```bash
chmod +x install.sh
./install.sh
```

The installer:

- installs the runit service
- enables automatic startup after reboot
- registers itself in `rc.local`

The service starts automatically.

---

## Updating

Simply replace the project files and run:

```bash
./install.sh
```

---

## Uninstall

Keep settings:

```bash
./uninstall.sh
```

Remove everything including persistent settings:

```bash
./uninstall.sh --purge
```

## Configuration

The service is configured through `config.ini`.

Example:

```ini
[DEFAULT]
Logging=INFO
DeviceInstance=250
```

### Logging

Defines the logging level.

Supported values are:

| Value | Description |
|--------|-------------|
| DEBUG | Verbose output intended for development and troubleshooting |
| INFO | Normal operation (recommended) |
| WARNING | Only warnings and errors |
| ERROR | Errors only |

The default value is:

```ini
Logging=INFO
```

---

### DeviceInstance

Defines the D-Bus DeviceInstance used by the service.

```ini
DeviceInstance=250
```

The default value is **250**.

If multiple instances of **dbus-essmanager** are running on the same Venus OS system, each service must use a unique DeviceInstance.

In normal installations no changes are required.

## Logging

The service writes its log through the standard Venus OS runit logging system.

The current log can be viewed with:

```bash
tail -f /data/log/dbus-essmanager/current
```

or

```bash
cat /data/log/dbus-essmanager/current
```

When running manually:

```bash
python3 main.py
```

the log is printed directly to the terminal.

---

## Charging settings

The service exposes the following configurable parameters.

### Enable

Enables or disables all dbus-essmanager functionality.

When disabled, the service does not modify the Victron DVCC Maximum Charge
Voltage.

---

### Maximum SOC

Defines the maximum battery State of Charge.

- **100 %** enables normal charging with full-battery detection.
- **Below 100 %** the battery is kept around the configured SOC by switching
  between **Absorption Voltage** and **Idle Voltage**.

---

### SOC Hysteresis

Defines how much the battery SOC must decrease before charging resumes.

Example:

- Maximum SOC = 80 %
- Hysteresis = 3 %

Charging restarts when the battery reaches **77 % SOC**.

---

### SOC Full Voltage

Minimum battery voltage required before full-battery detection can begin.

The battery voltage must remain above this threshold while the charging current
is below the configured Tail Current.

---

### SOC Full Tail Current

Maximum charging current required to consider the battery fully charged.


---

### SOC Full Wait Time

Time that the full-charge conditions must remain continuously satisfied before
the battery is considered fully charged.

---

### Absorption Voltage

DVCC Maximum Charge Voltage Limit applied during normal charging.

This is typically the battery manufacturer's recommended absorption voltage.

---

### Floating Voltage

DVCC Maximum Charge Voltage Limit applied after the battery has been detected as
fully charged.

This lower voltage reduces battery stress while keeping the battery full.

---

### Idle Voltage

DVCC Maximum Charge Voltage Limit applied when the configured Maximum SOC has been
reached (Maximum SOC < 100%).

This effectively stops further charging while still allowing the battery to
power the ESS system.

---

### Voltage value of 0 V

For all DVCC voltage settings (**Absorption**, **Floating** and **Idle**):

Setting a value of **0 V** disables the charge-voltage override for that
operating state.

This allows another DVCC-compatible device (typically the battery BMS) to
control the charging voltage without limitation from **dbus-essmanager**.

---

## MQTT

The service uses the standard Venus MQTT topics.

Persistent settings can be modified directly through the standard Venus MQTT broker using the following topics:

```
W/<portal-id>/settings/0/Settings/EssManager/...
```

Example:

```json
{
  "value": 90
}
```

---

## Home Assistant

The service publishes Home Assistant MQTT Discovery information automatically.

No YAML configuration is required.

After installation the following entities are created automatically:

- Enable
- Maximum SOC
- Charge voltages
- Full battery detection settings
- Battery full
- State
- Status
- Connected
- Full timer

---
## Home Assistant Integration (optional)

`dbus-essmanager` supports automatic Home Assistant entity creation through
MQTT Discovery.

The service publishes MQTT Discovery messages to the Venus OS MQTT broker.


---
### Using the Home Assistant Mosquitto broker

> **Note**
>
> The following configuration is only required when Home Assistant uses its
> own Mosquitto broker.
>
> If Home Assistant connects directly to the Venus OS MQTT broker, the bridge
> configuration is not required.

#### 1. Enable custom Mosquitto configuration

In the Home Assistant Mosquitto Broker add-on configuration, enable the custom
configuration folder.

The bridge configuration files are stored in:

```text
/share/mosquitto/
```

Create the following file:

```text
/share/mosquitto/victron-essmanager.conf
```

#### 2. Add the bridge configuration

Use the following configuration:

```conf
connection_messages true

connection victron_essmanager
address <venus-ip-address>:1883

remote_username <venus-mqtt-username>
remote_password <venus-mqtt-password>

clientid ha_victron_essmanager_bridge

start_type automatic
try_private false
cleansession true
notifications false
bridge_protocol_version mqttv311

# Values published by Venus OS to Home Assistant
topic N/<portal-id>/essmanager/<device-instance>/# in 0

# Home Assistant MQTT Discovery published by dbus-essmanager
topic homeassistant/device/dbus_essmanager_<device-instance>/# in 0

# Commands and requests sent from Home Assistant to Venus OS
topic W/<portal-id>/essmanager/<device-instance>/# out 0
topic R/<portal-id>/essmanager/<device-instance>/# out 0
topic R/<portal-id>/keepalive out 0
```

Replace the following placeholders:

| Placeholder | Description |
|---|---|
| `<venus-ip-address>` | IP address of the Venus OS device |
| `<venus-mqtt-username>` | MQTT username configured on Venus OS |
| `<venus-mqtt-password>` | MQTT password configured on Venus OS |
| `<portal-id>` | VRM Portal ID used in the Venus MQTT topics |
| `<device-instance>` | `DeviceInstance` configured in `config.ini`, default `250` |

Example topic structure:

```text
N/<portal-id>/essmanager/<device-instance>/Settings/MaxSoc
W/<portal-id>/essmanager/<device-instance>/Settings/MaxSoc
```

The Home Assistant discovery topic is:

```text
homeassistant/device/dbus_essmanager_<device-instance>/config
```

#### 3. Restart the Mosquitto Broker add-on

After saving the file, restart the Home Assistant Mosquitto Broker add-on.

Its log should show that the custom file has been loaded and that the bridge
has connected to the Venus OS MQTT broker.

#### 4. Add the Venus MQTT keepalive automations

Venus OS only republishes its MQTT values while the MQTT keepalive mechanism is
active.

Replace `<portal-id>` in both automations.

##### Initial refresh

```yaml
alias: ESS Manager MQTT - Initial refresh
mode: single

triggers:
  - trigger: homeassistant
    event: start

actions:
  - delay: "00:00:10"

  - action: mqtt.publish
    data:
      topic: R/<portal-id>/keepalive
      payload: ""
```

##### Periodic keepalive

```yaml
alias: ESS Manager MQTT - Keepalive
mode: single

triggers:
  - trigger: time_pattern
    seconds: "/30"

actions:
  - action: mqtt.publish
    data:
      topic: R/<portal-id>/keepalive
      payload: '{"keepalive-options":["suppress-republish"]}'
```

The initial refresh requests all current Venus MQTT values after Home Assistant
starts.

The periodic keepalive keeps the Venus MQTT publication active without forcing
a complete republish every 30 seconds.

---

## Service Architecture

```
                main.py
                    │
                    ▼
             EssManager
                    │
      ┌─────────────┼──────────────┐
      ▼             ▼              ▼
 DBusService   VictronSystem   VictronSettings
      ▲
      │
      ▼
 StateMachine
```

### Responsibilities

**EssManager**

Coordinates the complete control loop.

Reads:

- battery values
- configuration

Runs the state machine.

Publishes runtime values.

Updates the Victron DVCC settings.

---

**StateMachine**

Contains all charging logic.

Does **not** access D-Bus.

Pure decision engine.

---

**DBusService**

Exposes:

- persistent settings
- runtime values

Handles:

- validation
- persistence
- D-Bus communication

---

**VictronSystem**

Reads battery information from:

```
com.victronenergy.system
```

---

**VictronSettings**

Reads and writes:

```
Settings/SystemSetup/MaxChargeVoltage
Settings/SystemSetup/MaxChargeCurrent
```

---

## D-Bus interface

### Runtime paths

```
/BatteryFull
/SocFullTimer
/State
/Status
```

### Service settings

```
/Settings/Enable
/Settings/MaxSoc
/Settings/SocHysteresis
/Settings/SocFullVoltage
/Settings/SocFullTailCurrent
/Settings/SocFullWaitTime
/Settings/LimitVoltageIdle
/Settings/LimitVoltageFloating
/Settings/LimitVoltageAbsorption
```

### Persistent settings

```
/Settings/EssManager/Enable
/Settings/EssManager/MaxSoc
/Settings/EssManager/SocHysteresis
/Settings/EssManager/SocFullVoltage
/Settings/EssManager/SocFullTailCurrent
/Settings/EssManager/SocFullWaitTime
/Settings/EssManager/LimitVoltageIdle
/Settings/EssManager/LimitVoltageFloating
/Settings/EssManager/LimitVoltageAbsorption
```


---

## Development

Run without installing the service:

```bash
python3 main.py
```

Run through runit:

```bash
./service/run
```

Reset all persistent settings:

```bash
./reset-settings.sh
```

