# Vi Mode

System-wide Caps Lock + hjkl arrow keys for Omarchy 4.

There is no first-party Omarchy plugin for this. Hyprland keybinds can only
move windows. Real arrow keys in every app (editors, browsers, terminals)
have to be injected below the compositor. This plugin uses [keyd](https://github.com/rvaiya/keyd),
the same tool the Omarchy community already uses to remap Caps Lock.

- Caps Lock as Caps Lock is off
- Hold Caps + `h` / `j` / `k` / `l` → left / down / up / right
- Shift and Ctrl still work the way they do with real arrows

`omarchy plugin add` never runs install hooks or sudo, so the mapping is
applied by `install.sh`.

## Install

Both steps are required — `omarchy plugin add` cannot run sudo.

```sh
omarchy plugin add https://github.com/YOUR_GITHUB_USER/omarchy-vi-mode.git --enable
~/.config/omarchy/plugins/oliverlukschander.vi-mode/install.sh
```

`install.sh` asks for sudo: it installs `keyd`, writes `/etc/keyd/omarchy-vi-mode.conf`,
and enables the `keyd` service.

Click the  icon in the bar, or *Setup → Vi Mode* in the Omarchy menu, and
use **Install mapping** if you would rather run that from a floating terminal.

## Usage

Hold Caps Lock and press:

| Keys | Sends |
| --- | --- |
| `h` `j` `k` `l` | Left, down, up, right |
| Shift + `hjkl` | Select |
| Ctrl + `hjkl` | Jump by word |

Tap Caps Lock does nothing. Both Shift keys together still toggles real Caps Lock
(Omarchy's default `shift:both_capslock_cancel`).

Omarchy's CapsLock compose emoji shortcuts (`CapsLock M S` and friends) stop
working because Caps is no longer the compose key. `Super + Ctrl + E` still
opens the emoji picker.

## Remove

```sh
~/.config/omarchy/plugins/oliverlukschander.vi-mode/uninstall.sh
omarchy plugin remove oliverlukschander.vi-mode
```

Run the uninstaller first. Removing the plugin folder also deletes the
uninstaller.

## Why keyd

- Official keyd example is Caps + hjkl as arrows
- Works on Wayland, in GTK/Qt apps, terminals, and the lock screen
- Omarchy discussions and writeups already use keyd for Caps remaps
  ([#1383](https://github.com/basecamp/omarchy/discussions/1383),
  [sudomarchy](https://sudomarchy.com/posts/keyd-capslock-escape-app-launcher))

XKB (`omarchy-modifier-keys`) can turn Caps into Control or Escape, but it
cannot make Caps + hjkl send arrow keys.
