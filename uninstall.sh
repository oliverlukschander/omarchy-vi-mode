#!/usr/bin/bash
set -euo pipefail

_self=${BASH_SOURCE[0]}
if [[ $_self != /* ]]; then
  _self=${PWD%/}/$_self
fi
PLUGIN_DIR=${_self%/*}
PYTHON=/usr/bin/python3
SUDO=/usr/bin/sudo
KEYD=/usr/bin/keyd
SYSTEMCTL=/usr/bin/systemctl
OMARCHY=/usr/bin/omarchy

echo "Removing Omarchy Vi Mode keyd mapping"

if [[ ! -x $PYTHON ]]; then
  echo "Missing $PYTHON" >&2
  exit 1
fi

run() {
  local timeout=$1 max=$2
  shift 2
  "$PYTHON" -I "$PLUGIN_DIR/scripts/run.py" --timeout "$timeout" --max-stdout "$max" --max-stderr "$max" -- "$@"
}

py() {
  run 15 1048576 "$PYTHON" -I "$@"
}

have_sudo() {
  "$SUDO" -n true >/dev/null 2>&1
}

ensure_sudo() {
  if have_sudo; then
    return 0
  fi
  if [[ ! -t 0 || ! -t 2 ]]; then
    echo "sudo needs a terminal to ask for your password." >&2
    echo "Run: $PLUGIN_DIR/uninstall.sh" >&2
    exit 1
  fi
  echo "Updating /etc/keyd and libinput quirks needs root. sudo will ask for your password."
  "$SUDO" -v
}

as_root() {
  ensure_sudo
  "$SUDO" "$PYTHON" -I "$@"
}

reload_keyd() {
  have_sudo || return 0
  "$SUDO" -n "$KEYD" reload >/dev/null 2>&1 || \
    "$SUDO" -n "$SYSTEMCTL" restart keyd >/dev/null 2>&1 || true
}

# Drop our Hyprland resize toggle first (no sudo). Leaves the separate
# Vi Resize plugin's toggle alone if that plugin is still installed.
py "$PLUGIN_DIR/scripts/apply.py" unhypr || true

target=""
set +e
wildcard=$(py "$PLUGIN_DIR/scripts/keyd_conf.py" find)
find_rc=$?
set -e
if [[ $find_rc -eq 0 ]]; then
  target=$wildcard
elif [[ $find_rc -eq 2 ]]; then
  target=""
else
  exit "$find_rc"
fi

if [[ -n $target ]]; then
  tmp=$(py "$PLUGIN_DIR/scripts/keyd_conf.py" uninstall-body "$target")
  if [[ -n ${tmp:-} ]]; then
    echo "Keeping other plugins' keyd blocks in $target"
    as_root "$PLUGIN_DIR/scripts/keyd_conf.py" install "$tmp" "$target"
    reload_keyd
  else
    echo "No other keyd blocks remain; removing $target"
    as_root "$PLUGIN_DIR/scripts/keyd_conf.py" remove "$target"
    if [[ -d /etc/keyd ]] && ! compgen -G "/etc/keyd/*.conf" >/dev/null; then
      echo "No other keyd configs remain; stopping keyd"
      ensure_sudo
      "$SUDO" "$SYSTEMCTL" disable --now keyd 2>/dev/null || true
    else
      reload_keyd
    fi
  fi
fi

quirks_tmp=$(py "$PLUGIN_DIR/scripts/libinput_quirks.py" uninstall-body)
if [[ -n ${quirks_tmp:-} ]]; then
  echo "Keeping other libinput quirks in /etc/libinput/local-overrides.quirks"
  as_root "$PLUGIN_DIR/scripts/libinput_quirks.py" install "$quirks_tmp"
else
  echo "Removing Vi Mode libinput disable-while-typing quirk"
  as_root "$PLUGIN_DIR/scripts/libinput_quirks.py" remove
fi

py "$PLUGIN_DIR/scripts/menu.py" uninstall
if [[ -x $OMARCHY ]]; then
  run 5 65536 "$OMARCHY" menu refresh >/dev/null || true
fi

echo "Vi Mode mapping removed. Caps Lock is back to the compositor unless another plugin remaps it."
echo "Omarchy still uses Caps as compose unless you changed kb_options."
echo "Settings in ~/.config/omarchy/oliverlukschander.vi-mode.json were kept."
