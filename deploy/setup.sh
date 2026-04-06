#!/bin/bash
# Deploy PoE Hub Bot to VPS
set -e

echo "=== Setting up PoE Hub Bot ==="

cd /opt/poe-hub-bot

# Create venv and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy service file
cp deploy/poe-hub-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable poe-hub-bot
systemctl start poe-hub-bot

echo "=== Done! Check status with: systemctl status poe-hub-bot ==="
echo "=== Logs: journalctl -u poe-hub-bot -f ==="
