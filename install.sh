#!/bin/sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

chmod +x "$SCRIPT_DIR/service/run"

ln -sf "$SCRIPT_DIR/service" /service/dbus-essmanager

echo "dbus-essmanager installed"