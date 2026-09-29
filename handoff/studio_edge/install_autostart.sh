#!/usr/bin/env bash
# Install Myra edge: boot autostart (systemd --user) + keep 06:15 morning restart cron.
set -eu
EDGE=/home/james/studio-edge
UNIT_DIR=/home/james/.config/systemd/user
mkdir -p "$UNIT_DIR" "$EDGE/scripts"

cat >"$UNIT_DIR/studio-edge.service" <<'EOF'
[Unit]
Description=Myra Studio Edge (wake / STT / TTS)
After=network-online.target sound.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/james/studio-edge
Environment=HOME=/home/james
ExecStart=/home/james/studio-edge-venv/bin/python -u -m studio_edge.main
Restart=on-failure
RestartSec=5
StandardOutput=append:/tmp/myra.log
StandardError=append:/tmp/myra.log

[Install]
WantedBy=default.target
EOF

# Morning restart script (clears stale ALSA / hung backends)
cat >"$EDGE/scripts/morning_edge_restart.sh" <<'EOF'
#!/usr/bin/env bash
set -eu
exec bash /home/james/studio-edge/restart_edge.sh >>/tmp/myra-morning-restart.log 2>&1
EOF
chmod +x "$EDGE/scripts/morning_edge_restart.sh" "$EDGE/restart_edge.sh"

# Cron at 06:15 America/Denver — Pi clock should be local
EXISTING=$(crontab -l 2>/dev/null || true)
FILTERED=$(printf '%s\n' "$EXISTING" | grep -v 'morning_edge_restart' || true)
printf '%s\n%s\n' "$FILTERED" "15 6 * * * $EDGE/scripts/morning_edge_restart.sh" | crontab -
echo "cron:"
crontab -l

systemctl --user daemon-reload
systemctl --user enable studio-edge.service
# Linger so user services start at boot without graphical login
loginctl enable-linger james 2>/dev/null || true
echo "systemd user unit enabled: studio-edge.service"
systemctl --user is-enabled studio-edge.service || true
