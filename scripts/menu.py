#!/usr/bin/env python3
"""Add or remove the Setup → Vi Mode row in the user Omarchy menu."""

from __future__ import annotations

import sys
from pathlib import Path

MENU = Path.home() / ".config/omarchy/extensions/omarchy-menu.jsonc"
MARKER = '"setup.vi-mode"'
ROW = (
    '  "setup.vi-mode": {'
    '"icon":"",'
    '"label":"Vi Mode",'
    '"description":"System-wide Caps + hjkl arrows",'
    '"action":"omarchy-shell shell summon oliverlukschander.vi-mode \'{}\'",'
    '"checked":"systemctl is-active --quiet keyd && test -f /etc/keyd/omarchy-vi-mode.conf"'
    "},\n"
)


def install() -> None:
    MENU.parent.mkdir(parents=True, exist_ok=True)
    text = MENU.read_text() if MENU.exists() else "{\n}\n"
    if MARKER in text:
        return
    idx = text.rfind("}")
    if idx == -1:
        text = "{\n" + ROW + "}\n"
    else:
        text = text[:idx] + ROW + text[idx:]
    MENU.write_text(text)


def uninstall() -> None:
    if not MENU.exists():
        return
    lines = MENU.read_text().splitlines(keepends=True)
    kept = [line for line in lines if MARKER not in line]
    MENU.write_text("".join(kept))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    if action == "uninstall":
        uninstall()
    else:
        install()
