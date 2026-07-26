#!/bin/sh

SERVICE_NAME="dbus-essmanager"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_LINK="/service/$SERVICE_NAME"
RC_LOCAL="/data/rc.local"
INSTALL_COMMAND="$SCRIPT_DIR/install.sh"
PURGE_SETTINGS=false

if [ "$1" = "--purge" ]; then
    PURGE_SETTINGS=true
elif [ -n "$1" ]; then
    echo "Usage: $0 [--purge]"
    exit 1
fi

# Stop the service before removing it.
if [ -e "$SERVICE_LINK" ]; then
    svc -d "$SERVICE_LINK"
fi

# Optionally remove all persistent settings.
if [ "$PURGE_SETTINGS" = true ]; then
    "$SCRIPT_DIR/reset-settings.sh"

    if [ "$?" -ne 0 ]; then
        echo "Persistent settings could not be removed"
        exit 1
    fi
fi

# Remove the runit service symlink.
rm -f "$SERVICE_LINK"

# Remove this install script from rc.local.
if [ -f "$RC_LOCAL" ]; then
    sed -i "\|^$INSTALL_COMMAND$|d" "$RC_LOCAL"
fi

echo "$SERVICE_NAME removed"

if [ "$PURGE_SETTINGS" = false ]; then
    echo "Persistent settings preserved"
    echo "Use '$0 --purge' to remove them"
fi