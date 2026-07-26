#!/bin/sh

SERVICE_NAME="dbus-essmanager"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_LINK="/service/$SERVICE_NAME"
RC_LOCAL="/data/rc.local"
INSTALL_COMMAND="$SCRIPT_DIR/install.sh"

# Verify that the required service files exist.
if [ ! -f "$SCRIPT_DIR/service/run" ]; then
    echo "Error: $SCRIPT_DIR/service/run not found"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/service/log/run" ]; then
    echo "Error: $SCRIPT_DIR/service/log/run not found"
    exit 1
fi

# Set executable permissions.
chmod 755 "$SCRIPT_DIR/uninstall.sh"
chmod 755 "$SCRIPT_DIR/restart.sh"
chmod 755 "$SCRIPT_DIR/reset-settings.sh"
chmod 755 "$SCRIPT_DIR/service/run"
chmod 755 "$SCRIPT_DIR/service/log/run"

# Create or update the runit service symlink.
ln -sfn "$SCRIPT_DIR/service" "$SERVICE_LINK"

# Create rc.local if it does not already exist.
if [ ! -f "$RC_LOCAL" ]; then
    cat > "$RC_LOCAL" <<'EOF'
#!/bin/sh

EOF
fi

chmod 755 "$RC_LOCAL"

# Register this install script in rc.local so the service
# is automatically reinstalled after reboot or firmware updates.
if ! grep -Fxq "$INSTALL_COMMAND" "$RC_LOCAL"; then
    if grep -q '^exit 0$' "$RC_LOCAL"; then
        sed -i "\|^exit 0$|i $INSTALL_COMMAND" "$RC_LOCAL"
    else
        echo "$INSTALL_COMMAND" >> "$RC_LOCAL"
    fi
fi

echo "$SERVICE_NAME installed"