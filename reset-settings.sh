#!/bin/sh

SERVICE_NAME="dbus-essmanager"
SERVICE_PATH="/service/$SERVICE_NAME"

# Stop the service before removing its persistent settings.
if [ -e "$SERVICE_PATH" ]; then
    svc -d "$SERVICE_PATH"
fi

# Remove all persistent settings created by dbus-essmanager.
dbus -y com.victronenergy.settings /Settings RemoveSettings \
'%["EssManager/Enable","EssManager/MaxSoc","EssManager/SocHysteresis","EssManager/SocFullVoltage","EssManager/SocFullTailCurrent","EssManager/SocFullWaitTime","EssManager/LimitVoltageIdle","EssManager/LimitVoltageFloating","EssManager/LimitVoltageAbsorption"]'

RESULT=$?

if [ "$RESULT" -ne 0 ]; then
    echo "Failed to remove persistent settings"
    exit "$RESULT"
fi

echo "Persistent settings removed"