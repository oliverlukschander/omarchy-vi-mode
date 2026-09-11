#!/usr/bin/env python3
"""Add or remove the Setup → Vi Mode row in the user Omarchy menu."""

from __future__ import annotations

import os
import stat
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
MAX_BYTES = 1_048_576


def _die(msg: str) -> None:
    raise SystemExit(msg)


def _owned_by_us(st: os.stat_result) -> bool:
    return st.st_uid == os.getuid()


def _ensure_parent(path: Path) -> None:
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    st = os.lstat(parent)
    if stat.S_ISLNK(st.st_mode):
        _die(f"refusing symlink parent: {parent}")
    if not stat.S_ISDIR(st.st_mode):
        _die(f"parent is not a directory: {parent}")
    if not _owned_by_us(st):
        _die(f"parent not owned by current user: {parent}")


def _read(path: Path) -> str:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return "{\n}\n"
    except OSError as exc:
        _die(f"refusing to read {path}: {exc}")
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            _die(f"refusing non-regular file: {path}")
        if not _owned_by_us(st):
            _die(f"file not owned by current user: {path}")
        if st.st_size > MAX_BYTES:
            _die(f"file too large ({st.st_size} bytes): {path}")
        data = os.read(fd, MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            _die(f"file too large: {path}")
        return data.decode()
    finally:
        os.close(fd)


def _atomic_write(path: Path, text: str) -> None:
    data = text.encode()
    if len(data) > MAX_BYTES:
        _die("refusing to write oversized menu file")
    _ensure_parent(path)
    existing = None
    try:
        existing = os.lstat(path)
    except FileNotFoundError:
        pass
    if existing is not None:
        if stat.S_ISLNK(existing.st_mode) or not stat.S_ISREG(existing.st_mode):
            _die(f"refusing non-regular file: {path}")
        if not _owned_by_us(existing):
            _die(f"file not owned by current user: {path}")
    tmp_path = path.parent / f".{path.name}.{os.getpid()}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = -1
    try:
        fd = os.open(tmp_path, flags, 0o600)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not _owned_by_us(st):
            _die(f"refusing temp file {tmp_path}")
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.replace(tmp_path, path)
        landed = os.lstat(path)
        if stat.S_ISLNK(landed.st_mode) or not stat.S_ISREG(landed.st_mode):
            _die(f"rename did not land on a regular file: {path}")
        if not _owned_by_us(landed):
            _die(f"renamed file not owned by current user: {path}")
    except Exception:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def _with_row(text: str) -> str:
    if MARKER in text:
        return text
    idx = text.rfind("}")
    if idx == -1:
        return "{\n" + ROW + "}\n"
    return text[:idx] + ROW + text[idx:]


def _without_row(text: str) -> str:
    return "".join(line for line in text.splitlines(keepends=True) if MARKER not in line)


def install() -> None:
    _ensure_parent(MENU)
    _atomic_write(MENU, _with_row(_read(MENU)))


def uninstall() -> None:
    try:
        st = os.lstat(MENU)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        _die(f"refusing non-regular file: {MENU}")
    _atomic_write(MENU, _without_row(_read(MENU)))


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    if action == "uninstall":
        uninstall()
    else:
        install()
