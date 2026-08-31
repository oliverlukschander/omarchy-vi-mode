#!/usr/bin/env bash
set -euo pipefail

keyd_installed=false
keyd_active=false
config_present=false

if pacman -Q keyd &>/dev/null; then
  keyd_installed=true
fi
if systemctl is-active --quiet keyd; then
  keyd_active=true
fi
if [[ -f /etc/keyd/omarchy-vi-mode.conf ]]; then
  config_present=true
fi

printf '{"keydInstalled":%s,"active":%s,"configPresent":%s}\n' \
  "$keyd_installed" "$keyd_active" "$config_present"
