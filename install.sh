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
PACMAN=/usr/bin/pacman

echo "Omarchy Vi Mode"
echo "Caps or Ctrl + hjkl arrows. Optional Caps/Ctrl swap and window resize."
echo

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

# Do not wrap sudo in timeout(1). timeout starts a new process group, so sudo
# cannot read a password from the TTY; a 30s deadline also kills a slow prompt.
have_sudo() {
  "$SUDO" -n true >/dev/null 2>&1
}

ensure_sudo() {
  if have_sudo; then
    return 0
  fi
  if [[ ! -t 0 || ! -t 2 ]]; then
    echo "sudo needs a terminal to ask for your password." >&2
    echo "Run: $PLUGIN_DIR/install.sh" >&2
    exit 1
  fi
  echo "Writing /etc/keyd and libinput quirks needs root. sudo will ask for your password."
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

if [[ -x $PACMAN ]] && ! "$PACMAN" -Q keyd &>/dev/null; then
  echo "Installing keyd..."
  if [[ -x $OMARCHY ]]; then
    "$OMARCHY" pkg add keyd
  else
    echo "keyd is not installed. Install it, then re-run $PLUGIN_DIR/install.sh" >&2
    exit 1
  fi
fi

py "$PLUGIN_DIR/scripts/apply.py" hypr
echo "Applied Hyprland resize toggle from current settings."

target=""
set +e
wildcard=$(py "$PLUGIN_DIR/scripts/keyd_conf.py" find)
find_rc=$?
set -e
if [[ $find_rc -eq 0 ]]; then
  target=$wildcard
elif [[ $find_rc -eq 2 ]]; then
  target=/etc/keyd/omarchy-vi-mode.conf
  echo "No keyd wildcard config yet; writing $target"
else
  exit "$find_rc"
fi

echo "Writing $target (keeps other plugins' # BEGIN / # END blocks)"
tmp=$(py "$PLUGIN_DIR/scripts/keyd_conf.py" prepare "$target")
as_root "$PLUGIN_DIR/scripts/keyd_conf.py" install "$tmp" "$target"

had_dwt=0
if grep -qF "# BEGIN oliverlukschander.vi-mode" /etc/libinput/local-overrides.quirks 2>/dev/null; then
  had_dwt=1
fi
echo "Writing /etc/libinput/local-overrides.quirks (keyd counts as the laptop keyboard)"
quirks_tmp=$(py "$PLUGIN_DIR/scripts/libinput_quirks.py" prepare)
as_root "$PLUGIN_DIR/scripts/libinput_quirks.py" install "$quirks_tmp"

echo "Enabling keyd"
ensure_sudo
"$SUDO" "$SYSTEMCTL" enable --now keyd
reload_keyd

py "$PLUGIN_DIR/scripts/menu.py" install
if [[ -x $OMARCHY ]]; then
  run 5 65536 "$OMARCHY" menu refresh >/dev/null || true
fi

echo
"$PYTHON" -I "$PLUGIN_DIR/scripts/settings.py" get | "$PYTHON" -I -c '
import json, sys
s = json.load(sys.stdin)
mod = "Ctrl" if s.get("navKey") == "control" else "Caps"
print(f"Ready. Hold {mod} and press:")
print("  h  left")
print("  j  down")
print("  k  up")
print("  l  right")
if s.get("resize"):
    print()
    print(f"{mod} + Shift + hjkl resizes the window (also SUPER + SHIFT + hjkl).")
else:
    print()
    print("Shift still works as it does with real arrows (select).")
if s.get("swapCapsCtrl"):
    print("Caps Lock and Left Ctrl are swapped (the arrow-layer key is unchanged).")
print()
print("Omarchy CapsLock compose emojis only work if Caps Lock is not the arrow layer.")
print("Use Super + Ctrl + E for the emoji picker. Both Shift keys together still toggles real Caps Lock.")
'
if [[ $had_dwt -eq 0 ]]; then
  echo
  echo "Log out once so the touchpad is ignored while typing (libinput reloads on login)."
fi
