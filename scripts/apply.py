#!/usr/bin/python3
"""Apply Vi Mode settings to Hyprland (no sudo) and prepare the keyd file."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import foreign_resize_toggle_path, load_settings, plugin_dir, resize_toggle_path
from run import run
from safe_file import copy_file, die, read_text, remove_file


def _present(path: Path) -> bool:
    try:
        read_text(path)
        return True
    except SystemExit:
        return False

HYPRCTL = "/usr/bin/hyprctl"
HYPR_SRC = plugin_dir() / "hypr" / "vi-resize.lua"


def _reload_hypr() -> None:
    if os.path.isfile(HYPRCTL) and os.access(HYPRCTL, os.X_OK):
        run([HYPRCTL, "reload"], timeout=5, max_stdout=65536, max_stderr=65536)


def apply_hypr(settings: dict | None = None) -> None:
    cfg = settings or load_settings()
    dest = resize_toggle_path()
    if cfg["resize"]:
        if _present(foreign_resize_toggle_path()):
            # Separate Vi Resize plugin already owns SUPER + SHIFT + hjkl.
            remove_file(dest)
        else:
            if not HYPR_SRC.is_file():
                die(f"missing {HYPR_SRC}")
            copy_file(HYPR_SRC, dest)
    else:
        remove_file(dest)
    _reload_hypr()


def remove_hypr() -> None:
    remove_file(resize_toggle_path())
    _reload_hypr()


def main(argv: list[str]) -> None:
    if len(argv) == 2 and argv[1] == "hypr":
        apply_hypr()
        return
    if len(argv) == 2 and argv[1] == "unhypr":
        remove_hypr()
        return
    die("usage: apply.py hypr|unhypr")


if __name__ == "__main__":
    main(sys.argv)
