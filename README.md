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
