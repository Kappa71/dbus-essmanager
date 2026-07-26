#!/bin/sh

SERVICE_NAME="dbus-essmanager"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_LINK="/service/$SERVICE_NAME"
RC_LOCAL="/data/rc.local"
INSTALL_COMMAND="$SCRIPT_DIR/install.sh"

# Remove the runit service symlink.
rm -f "$SERVICE_LINK"

# Remove this install script from rc.local.
if [ -f "$RC_LOCAL" ]; then
    sed -i "\|^$INSTALL_COMMAND$|d" "$RC_LOCAL"
fi

echo "$SERVICE_NAME removed"