#!/bin/bash
# Wrapper for launchd — runs WhatsApp bridge with proper env.
# Template: replace __HOME__ and __NANOBOT_DIR__ before installing to ~/.nanobot/bin/.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin"
export HOME="__HOME__"
export AUTH_DIR="__HOME__/.nanobot/whatsapp-auth"
export BRIDGE_TOKEN="$(cat __HOME__/.nanobot/whatsapp-auth/bridge-token)"
cd __NANOBOT_DIR__/bridge
exec /opt/homebrew/bin/node dist/index.js
