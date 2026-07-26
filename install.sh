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

# Register this install script in rc.local so the service is restored
# automatically after reboot or firmware updates.
if ! grep -Fxq "$INSTALL_COMMAND" "$RC_LOCAL"; then
    if grep -q '^exit 0$' "$RC_LOCAL"; then
        sed -i "\|^exit 0$|i $INSTALL_COMMAND" "$RC_LOCAL"
    else
        echo "$INSTALL_COMMAND" >> "$RC_LOCAL"
    fi
fi

# Wait briefly for runit to detect the service.
WAIT_COUNT=0
while [ ! -e "$SCRIPT_DIR/service/supervise/ok" ] && [ "$WAIT_COUNT" -lt 10 ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Explicitly enable and start the service.
if [ -e "$SCRIPT_DIR/service/supervise/ok" ]; then
    svc -u "$SERVICE_LINK"
else
    echo "Warning: runit did not detect the service within 10 seconds"
fi

echo "$SERVICE_NAME installed"