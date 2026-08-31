#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_SRC="$PLUGIN_DIR/keyd/omarchy-vi-mode.conf"
CONF_DST="/etc/keyd/omarchy-vi-mode.conf"

echo "Omarchy Vi Mode"
echo "Caps Lock is disabled. Hold Caps + h/j/k/l for arrow keys."
echo

if ! pacman -Q keyd &>/dev/null; then
  echo "Installing keyd..."
  omarchy pkg add keyd
fi

echo "Writing $CONF_DST"
sudo install -Dm644 "$CONF_SRC" "$CONF_DST"

echo "Enabling keyd"
sudo systemctl enable --now keyd
sudo keyd reload 2>/dev/null || true

python3 "$PLUGIN_DIR/scripts/menu.py" install
omarchy menu refresh >/dev/null 2>&1 || true

echo
echo "Ready. Hold Caps Lock and press:"
echo "  h  left"
echo "  j  down"
echo "  k  up"
echo "  l  right"
echo
echo "Shift / Ctrl still work as they do with real arrows (select, jump by word)."
echo
echo "Omarchy's CapsLock compose emoji shortcuts no longer fire."
echo "Use Super + Ctrl + E for the emoji picker instead."
echo "Both Shift keys together still toggles real Caps Lock."
