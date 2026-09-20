#!/usr/bin/python3
"""Prepare and atomically install the Vi Mode keyd config.

Unprivileged actions read a root-owned /etc/keyd/*.conf, keep other plugins'
# BEGIN / # END blocks, replace the Vi Mode body, and print a temp path.
The privileged `install` action (sudo) is the only writer of the system file.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import compose_keyd, generate, load_settings, preserved_blocks
from safe_file import MAX_BYTES, atomic_write, die, read_text

KEYD_DIR = Path("/etc/keyd")
CONF_NAME = re.compile(r"^[A-Za-z0-9._-]+\.conf$")
DEFAULT_NAME = "omarchy-vi-mode.conf"


def _cache_path() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return cache / "omarchy-vi-mode" / "keyd.conf.new"


def _has_wildcard(text: str) -> bool:
    return any(line.strip() == "*" for line in text.splitlines())


def _read_keyd(path: Path) -> str:
    return read_text(path, owner=0)


def _list_conf_names() -> list[str]:
    try:
        names = os.listdir(str(KEYD_DIR))
    except OSError:
        return []
    return [name for name in names if CONF_NAME.match(name)]


def find_wildcard() -> Path | None:
    names = sorted(_list_conf_names(), key=lambda n: (n != DEFAULT_NAME, n))
    for name in names:
        path = KEYD_DIR / name
        try:
            text = _read_keyd(path)
        except SystemExit:
            continue
        if _has_wildcard(text):
            return path
    return None


def default_target() -> Path:
    return KEYD_DIR / DEFAULT_NAME


def _write_temp(text: str) -> Path:
    dest = _cache_path()
    if len(text.encode()) > MAX_BYTES:
        die("refusing oversized keyd replacement")
    atomic_write(dest, text)
    return dest


def _replacement(current: str, settings: dict | None = None) -> str:
    return compose_keyd(generate(settings or load_settings()), preserved_blocks(current))


def cmd_find() -> None:
    path = find_wildcard()
    if path is None:
        raise SystemExit(2)
    sys.stdout.write(f"{path}\n")


def cmd_prepare(target: Path) -> None:
    try:
        current = _read_keyd(target)
    except SystemExit:
        current = ""
    tmp = _write_temp(_replacement(current))
    sys.stdout.write(f"{tmp}\n")


def cmd_uninstall_body(target: Path) -> None:
    """Keep other plugins' managed blocks; drop the Vi Mode body."""
    try:
        current = _read_keyd(target)
    except SystemExit:
        sys.stdout.write("\n")
        return
    blocks = preserved_blocks(current)
    if not blocks:
        sys.stdout.write("\n")
        return
    text = compose_keyd("[ids]\n*\n", blocks)
    tmp = _write_temp(text)
    sys.stdout.write(f"{tmp}\n")


def _require_keyd_target(path: Path) -> None:
    if path.parent != KEYD_DIR or not CONF_NAME.match(path.name):
        die(f"refusing keyd target: {path}")


def cmd_install(src: Path, dest: Path) -> None:
    if os.geteuid() != 0:
        die("keyd install must run as root")
    sudo_uid = os.environ.get("SUDO_UID")
    if not sudo_uid or not sudo_uid.isdigit() or int(sudo_uid) <= 0:
        die("refusing install without SUDO_UID")
    _require_keyd_target(dest)
    text = read_text(src, owner=int(sudo_uid))
    atomic_write(dest, text, create_parent=False, owner=0, mode=0o644)


def cmd_remove(dest: Path) -> None:
    if os.geteuid() != 0:
        die("keyd remove must run as root")
    sudo_uid = os.environ.get("SUDO_UID")
    if not sudo_uid or not sudo_uid.isdigit() or int(sudo_uid) <= 0:
        die("refusing remove without SUDO_UID")
    _require_keyd_target(dest)
    parent = os.open(str(KEYD_DIR), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        try:
            os.unlink(dest.name, dir_fd=parent)
        except FileNotFoundError:
            return
    finally:
        os.close(parent)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        die(
            "usage: keyd_conf.py find|prepare TARGET|uninstall-body TARGET|"
            "install TMP TARGET|remove TARGET"
        )
    action = argv[1]
    if action == "find" and len(argv) == 2:
        cmd_find()
    elif action == "prepare" and len(argv) == 3:
        cmd_prepare(Path(argv[2]))
    elif action == "uninstall-body" and len(argv) == 3:
        cmd_uninstall_body(Path(argv[2]))
    elif action == "install" and len(argv) == 4:
        cmd_install(Path(argv[2]), Path(argv[3]))
    elif action == "remove" and len(argv) == 3:
        cmd_remove(Path(argv[2]))
    else:
        die(
            "usage: keyd_conf.py find|prepare TARGET|uninstall-body TARGET|"
            "install TMP TARGET|remove TARGET"
        )


if __name__ == "__main__":
    main(sys.argv)
