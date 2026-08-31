#!/usr/bin/env bash
set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_DST="/etc/keyd/omarchy-vi-mode.conf"

echo "Removing Omarchy Vi Mode keyd mapping"

if [[ -f "$CONF_DST" ]]; then
  sudo rm -f "$CONF_DST"
fi

if [[ -d /etc/keyd ]] && ! compgen -G "/etc/keyd/*.conf" >/dev/null; then
  echo "No other keyd configs remain; stopping keyd"
  sudo systemctl disable --now keyd 2>/dev/null || true
elif systemctl is-active --quiet keyd; then
  sudo keyd reload 2>/dev/null || sudo systemctl restart keyd
fi

python3 "$PLUGIN_DIR/scripts/menu.py" uninstall
omarchy menu refresh >/dev/null 2>&1 || true

echo "Vi Mode mapping removed. Caps Lock is back to the compositor."
echo "Omarchy still uses Caps as compose unless you changed kb_options."
