#!/usr/bin/python3
"""Omarchy-menu checked/action helper. Invoked as an absolute python3 -I command."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from run import closed_env
from safe_file import read_text

PLUGIN_ID = "oliverlukschander.vi-mode"
OMARCHY_SHELL = "/usr/bin/omarchy-shell"
KEYD_CONF = Path("/etc/keyd/omarchy-vi-mode.conf")


def checked() -> int:
    try:
        read_text(KEYD_CONF, owner=0)
    except SystemExit:
        return 1
    return 0


def action(payload: str) -> None:
    if "\x00" in payload:
        raise SystemExit("illegal payload")
    if not os.path.isfile(OMARCHY_SHELL) or not os.access(OMARCHY_SHELL, os.X_OK):
        raise SystemExit(f"missing {OMARCHY_SHELL}")
    os.execve(
        OMARCHY_SHELL,
        [OMARCHY_SHELL, "shell", "summon", PLUGIN_ID, payload],
        closed_env(),
    )


def main(argv: list[str]) -> None:
    if len(argv) >= 2 and argv[1] == "checked":
        raise SystemExit(checked())
    if len(argv) >= 2 and argv[1] == "action":
        payload = argv[2] if len(argv) > 2 else "{}"
        action(payload)
        raise SystemExit("execve failed")
    raise SystemExit("usage: menu_host.py checked | action [payload]")


if __name__ == "__main__":
    main(sys.argv)
