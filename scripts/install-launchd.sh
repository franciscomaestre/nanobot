#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install-launchd.sh — Instala los servicios launchd para nanobot.
#
# WhatsApp usa neonize (in-process, dentro del gateway) — ya NO hay bridge Node.
#
# Crea:
#   ~/.nanobot/venv/                — venv fuera de ~/Desktop (evita TCC)
#   ~/.nanobot/bin/run-gateway.sh   — wrapper para gateway (canales + agente + WhatsApp neonize)
#   ~/.nanobot/bin/run-serve.sh     — wrapper para serve (API OpenAI-compatible)
#   ~/Library/LaunchAgents/com.nanobot.gateway.plist
#   ~/Library/LaunchAgents/com.nanobot.serve.plist
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

echo "📦 Instalando launchd services para nanobot (WhatsApp via neonize, sin bridge)"
echo "   NANOBOT_DIR: $NANOBOT_DIR"
echo "   HOME:        $HOME"
echo

# ── 0. Dependencia nativa para neonize (python-magic → libmagic) ─────────────
if ! brew list libmagic &>/dev/null; then
  echo "▶ Instalando libmagic (requerido por neonize) ..."
  brew install libmagic 2>&1 | tail -2
fi

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

echo "▶ Instalando nanobot[whatsapp] en launchd venv ..."
# El extra [whatsapp] trae neonize + segno (QR) para el canal de WhatsApp in-process
"$LAUNCHD_VENV/bin/pip" install "$NANOBOT_DIR[whatsapp]" --quiet 2>&1 | tail -3
# Extras que nanobot necesita pero no están en install_requires
"$LAUNCHD_VENV/bin/pip" install anthropic matrix-nio mistune "nh3>=0.2.17,<1.0.0" assemblyai firecrawl-py --quiet 2>&1 | tail -3
echo "✅ Venv listo"

# ── 2. Instalar wrapper scripts ──────────────────────────────────────────────
echo "▶ Instalando wrapper scripts en ~/.nanobot/bin/ ..."
mkdir -p "$HOME/.nanobot/bin"

sed -e "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/run-gateway.sh" > "$HOME/.nanobot/bin/run-gateway.sh"
chmod +x "$HOME/.nanobot/bin/run-gateway.sh"

sed -e "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/run-serve.sh" > "$HOME/.nanobot/bin/run-serve.sh"
chmod +x "$HOME/.nanobot/bin/run-serve.sh"

# Limpiar wrapper obsoleto del bridge (neonize ya no lo usa)
rm -f "$HOME/.nanobot/bin/run-bridge.sh" 2>/dev/null || true
echo "✅ Wrappers instalados"

# ── 3. Instalar plists ───────────────────────────────────────────────────────
echo "▶ Instalando plists en ~/Library/LaunchAgents/ ..."
mkdir -p "$HOME/Library/LaunchAgents"

# Unload if already loaded
launchctl unload "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist" 2>/dev/null || true
launchctl unload "$HOME/Library/LaunchAgents/com.nanobot.serve.plist" 2>/dev/null || true
# Limpiar el plist obsoleto del bridge, si quedó de una instalación previa
launchctl unload "$HOME/Library/LaunchAgents/com.nanobot.bridge.plist" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.nanobot.bridge.plist" 2>/dev/null || true

sed "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/com.nanobot.gateway.plist" > "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist"

sed "s|__HOME__|$HOME|g" \
  "$NANOBOT_DIR/scripts/com.nanobot.serve.plist" > "$HOME/Library/LaunchAgents/com.nanobot.serve.plist"
echo "✅ Plists instalados"

# ── 4. Arrancar (opcional) ───────────────────────────────────────────────────
if [[ $START -eq 1 ]]; then
  echo "▶ Arrancando servicios ..."
  # Kill orphans
  pkill -f "nanobot gateway" 2>/dev/null || true
  pkill -f "nanobot serve" 2>/dev/null || true
  sleep 1

  launchctl load "$HOME/Library/LaunchAgents/com.nanobot.serve.plist"
  sleep 2
  launchctl load "$HOME/Library/LaunchAgents/com.nanobot.gateway.plist"
  sleep 5

  S_PID=$(launchctl list com.nanobot.serve 2>/dev/null | grep '"PID"' | grep -o '[0-9]*' || echo "?")
  G_PID=$(launchctl list com.nanobot.gateway 2>/dev/null | grep '"PID"' | grep -o '[0-9]*' || echo "?")
  echo "✅ Serve PID: $S_PID"
  echo "✅ Gateway PID: $G_PID"
fi

echo
echo "══════════════════════════════════════════════"
echo "  launchd services instalados"
echo "  WhatsApp:            neonize (in-process)"
echo "  Auto-restart:        ON (KeepAlive)"
echo "  Auto-start at login: ON (RunAtLoad)"
echo ""
echo "  Gestión:"
echo "    nanobot-restart              # restart con tests + sync venv"
echo "    launchctl unload ~/Library/LaunchAgents/com.nanobot.*.plist  # stop"
echo "    launchctl load   ~/Library/LaunchAgents/com.nanobot.*.plist  # start"
echo "══════════════════════════════════════════════"
