## Planned features

- [ ] D-Bus service
- [ ] MQTT integration
- [ ] Max SoC limit
- [ ] Automatic charge voltage management
- [ ] Configurable hysteresis
- [ ] Persistent settings

Commands:
chmod +x install.sh
chmod +x service/run
Install:
./install.sh

ls -l /service/dbus-essmanager

Dovresti vedere un link simbolico verso:
/data/dbus-essmanager/service
Start service
svc -u /service/dbus-essmanager
Stop service:
svc -d /service/dbus-essmanager
check service:
svstat /service/dbus-essmanager

run program without service:
python3 main.py

run manually the service:
./service/run

Percorsi risultanti

In com.victronenergy.essmanager vedrai:

/Settings/Enable
/Settings/MaxSoc
/Settings/SocHysteresis
/Settings/SocFullVoltage
/Settings/SocFullTailCurrent
/Settings/SocFullWaitTime
/Settings/LimitVoltageIdle
/Settings/LimitVoltageFloating
/Settings/LimitVoltageAbsorption

/BatteryFull
/SocFullTimer
/State
/Status

I corrispondenti percorsi persistenti saranno:

/Settings/EssManager/Enable
/Settings/EssManager/MaxSoc
/Settings/EssManager/SocHysteresis
/Settings/EssManager/SocFullVoltage
/Settings/EssManager/SocFullTailCurrent
/Settings/EssManager/SocFullWaitTime
/Settings/EssManager/LimitVoltageIdle
/Settings/EssManager/LimitVoltageFloating
/Settings/EssManager/LimitVoltageAbsorption

Per esempio, la modifica MQTT di Enable userà:

W/<portal-id>/settings/0/Settings/EssManager/Enable

con:

{"value": 0}


Architettura definitiva
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
EssManager

È l'orchestratore.

Ad ogni ciclo (es. ogni secondo):

system = victron_system.read()

settings = dbus_service.read_settings()

result = state_machine.update(
    settings=settings,
    system=system,
)

dbus_service.apply(result)

victron_settings.set_max_charge_voltage(
    result.target_charge_voltage
)

Quindi EssManager non contiene alcuna logica, coordina soltanto gli oggetti.
