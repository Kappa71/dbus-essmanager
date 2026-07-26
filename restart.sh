#!/bin/sh

SERVICE_NAME="dbus-essmanager"
SERVICE_PATH="/service/$SERVICE_NAME"

if [ ! -e "$SERVICE_PATH" ]; then
    echo "Error: $SERVICE_PATH does not exist"
    exit 1
fi

svc -t "$SERVICE_PATH"