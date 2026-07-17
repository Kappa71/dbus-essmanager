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