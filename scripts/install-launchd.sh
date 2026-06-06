#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install-launchd.sh — Instala los servicios launchd para nanobot.
#
# Crea:
#   ~/.nanobot/venv/               — venv fuera de ~/Desktop (evita TCC)
#   ~/.nanobot/bin/run-bridge.sh   — wrapper para bridge
#   ~/.nanobot/bin/run-gateway.sh  — wrapper para gateway
#   ~/Library/LaunchAgents/com.nanobot.bridge.plist
#   ~/Library/LaunchAgents/com.nanobot.gateway.plist
#
# Uso:
#   ./scripts/install-launchd.sh          # instala y arranca
#   ./scripts/install-launchd.sh --start  # igual (default)
#   ./scripts/install-launchd.sh --no-start  # solo instala, no arranca
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

# ── Detectar NANOBOT_DIR ─────────────────────────────────────────────────────
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$_SCRIPT_DIR/../pyproject.toml" ]]; then
  NANOBOT_DIR="$(cd "$_SCRIPT_DIR/.." && pwd)"
elif [[ -n "${NANOBOT_DIR:-}" ]] && [[ -f "$NANOBOT_DIR/pyproject.toml" ]]; then
  true  # use env var
else
  echo "ERROR: No se pudo detectar NANOBOT_DIR." >&2
  exit 1
fi

START=1
for arg in "$@"; do
  [[ "$arg" == "--no-start" ]] && START=0
done

echo "📦 Instalando launchd services para nanobot"
echo "   NANOBOT_DIR: $NANOBOT_DIR"
echo "   HOME:        $HOME"
echo

# ── 1. Crear venv fuera de ~/Desktop (TCC-free) ─────────────────────────────
echo "▶ Creando venv en ~/.nanobot/venv ..."
LAUNCHD_VENV="$HOME/.nanobot/venv"

if [[ ! -f "$LAUNCHD_VENV/bin/python3" ]]; then
  PYTHON_CMD="python3.12"
  if ! command -v "$PYTHON_CMD" &>/dev/null; then
    PYTHON_CMD="python3"
  fi
  "$PYTHON_CMD" -m venv "$LAUNCHD_VENV"
  "$LAUNCHD_VENV/bin/pip" install --upgrade pip --quiet 2>&1 | tail -1
fi

echo "▶ Instalando nanobot en launchd venv ..."
"$LAUNCHD_VENV/bin/pip" install "$NANOBOT_DIR" --quiet 2>&1 | tail -3
# Extras que nanobot necesita pero no están en install_requires
"$LAUNCHD_VENV/bin/pip" install anthropic matrix-nio mistune "nh3>=0.2.17,<1.0.0" assemblyai firecrawl-py --quiet 2>&1 | tail -3
echo "✅ Venv listo"

# ── 2. Instalar wrapper scripts ──────────────────────────────────────────────
echo "▶ Instalando wrapper scripts en ~/.nanobot/bin/ ..."
mkdir -p "$HOME/.nanobot/bin"

sed -e "s|__HOME__|$HOME|g" -e "s|__NANOBOT_DIR__|$NANOBOT_DIR|g" \
  "$NANOBOT_DIR/scripts/run-bridge.sh" > "$HOME/.nanobot/bin/run-bridge.sh"
chmod +x "$HOME/.nanobot/bin/run-bridge.sh"

sed -e "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/run-gateway.sh" > "$HOME/.nanobot/bin/run-gateway.sh"
chmod +x "$HOME/.nanobot/bin/run-gateway.sh"
echo "✅ Wrappers instalados"

# ── 3. Instalar plists ───────────────────────────────────────────────────────
echo "▶ Instalando plists en ~/Library/LaunchAgents/ ..."
mkdir -p "$HOME/Library/LaunchAgents"

# Unload if already loaded
launchctl unload "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.nanobot.bridge.plist" 2>/dev/null || true

sed "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/com.nanobot.bridge.plist" > "$HOME/Library/LaunchAgents/com.nanobot.bridge.plist"

sed "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/com.nanobot.gateway.plist" > "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist"
echo "✅ Plists instalados"

# ── 4. Arrancar (opcional) ───────────────────────────────────────────────────
if [[ $START -eq 1 ]]; then
  echo "▶ Arrancando servicios ..."
  # Kill orphans
  pkill -f "nanobot gateway" 2>/dev/null || true
  pkill -f "node.*bridge/dist/index.js" 2>/dev/null || true
  STALE=$(lsof -ti :3001 2>/dev/null || true)
  [[ -n "$STALE" ]] && kill "$STALE" 2>/dev/null || true
  sleep 1

  launchctl load "$HOME/Library/LaunchAgents/com.nanobot.bridge.plist"
  sleep 3
  launchctl load "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist"
  sleep 5

  B_PID=$(launchctl list com.nanobot.bridge 2>/dev/null | grep '"PID"' | grep -o '[0-9]*' || echo "?")
  G_PID=$(launchctl list com.nanobot.gateway 2>/dev/null | grep '"PID"' | grep -o '[0-9]*' || echo "?")
  echo "✅ Bridge PID: $B_PID"
  echo "✅ Gateway PID: $G_PID"
fi

echo
echo "══════════════════════════════════════════════"
echo "  launchd services instalados"
echo "  Auto-restart: ON (KeepAlive)"
echo "  Auto-start at login: ON (RunAtLoad)"
echo ""
echo "  Gestión:"
echo "    nanobot-restart              # restart con tests + sync venv"
echo "    launchctl unload ~/Library/LaunchAgents/com.nanobot.*.plist  # stop"
echo "    launchctl load   ~/Library/LaunchAgents/com.nanobot.*.plist  # start"
echo "══════════════════════════════════════════════"
