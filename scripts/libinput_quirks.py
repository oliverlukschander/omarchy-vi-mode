#!/usr/bin/python3
"""Mark keyd's virtual keyboard as internal for libinput DWT.

keyd grabs the laptop keyboard and types through "keyd virtual keyboard",
which libinput treats as USB/external, so disable-while-typing never fires.
The only supported way to declare that uinput device as the laptop keyboard
is /etc/libinput/local-overrides.quirks.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import PLUGIN_ID, split_managed
from safe_file import MAX_BYTES, atomic_write, die, read_text

QUIRKS_DIR = Path("/etc/libinput")
QUIRKS_PATH = QUIRKS_DIR / "local-overrides.quirks"
SECTION = "[keyd virtual keyboard]"
MATCH_NAME = "MatchName=keyd virtual keyboard"
ATTR_INTERNAL = "AttrKeyboardIntegration=internal"


def _cache_path() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return cache / "omarchy-vi-mode" / "libinput.quirks.new"


def managed_block() -> str:
    return (
        f"# BEGIN {PLUGIN_ID}\n"
        f"{SECTION}\n"
        "MatchUdevType=keyboard\n"
        f"{MATCH_NAME}\n"
        f"{ATTR_INTERNAL}\n"
        f"# END {PLUGIN_ID}\n"
    )


def _only_comments_or_blank(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return False
    return True


def _is_our_keyd_section(blob: str) -> bool:
    return MATCH_NAME in blob and ATTR_INTERNAL in blob


def strip_unmarked_keyd_section(text: str) -> str:
    """Drop an unmarked [keyd virtual keyboard] internal section (pre-2.0.1)."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip() == SECTION:
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("["):
                j += 1
            blob = "".join(lines[i:j])
            if _is_our_keyd_section(blob):
                i = j
                continue
            out.extend(lines[i:j])
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "".join(out)


def _parts_without_ours(text: str) -> list[str]:
    body, blocks = split_managed(text)
    body = strip_unmarked_keyd_section(body)
    if _only_comments_or_blank(body):
        body = ""
    parts = []
    if body.strip():
        parts.append(body.strip("\n"))
    for ident, block in blocks:
        if ident == PLUGIN_ID:
            continue
        if block.strip():
            parts.append(block.strip("\n"))
    return parts


def merge_quirks(current: str) -> str:
    parts = _parts_without_ours(current)
    parts.append(managed_block().strip("\n"))
    return "\n\n".join(parts) + "\n"


def uninstall_quirks(current: str) -> str:
    parts = _parts_without_ours(current)
    if not parts:
        return ""
    return "\n\n".join(parts) + "\n"


def _read_quirks() -> str:
    return read_text(QUIRKS_PATH, missing="", owner=0)


def _write_temp(text: str) -> Path:
    dest = _cache_path()
    if len(text.encode()) > MAX_BYTES:
        die("refusing oversized libinput quirks replacement")
    atomic_write(dest, text)
    return dest


def _require_root_sudo_uid() -> int:
    if os.geteuid() != 0:
        die("libinput quirks install must run as root")
    sudo_uid = os.environ.get("SUDO_UID")
    if not sudo_uid or not sudo_uid.isdigit() or int(sudo_uid) <= 0:
        die("refusing install without SUDO_UID")
    return int(sudo_uid)


def _ensure_quirks_dir() -> None:
    """Create /etc/libinput as 0755. safe_file's create_parent uses 0700."""
    parent = os.open("/etc", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        try:
            os.mkdir("libinput", 0o755, dir_fd=parent)
        except FileExistsError:
            pass
        fd = os.open(
            "libinput",
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        try:
            st = os.fstat(fd)
            if not stat.S_ISDIR(st.st_mode):
                die("refusing /etc/libinput: not a directory")
            if st.st_uid != 0:
                die("refusing /etc/libinput: not root-owned")
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def cmd_prepare() -> None:
    tmp = _write_temp(merge_quirks(_read_quirks()))
    sys.stdout.write(f"{tmp}\n")


def cmd_uninstall_body() -> None:
    leftover = uninstall_quirks(_read_quirks())
    if not leftover.strip():
        sys.stdout.write("\n")
        return
    tmp = _write_temp(leftover)
    sys.stdout.write(f"{tmp}\n")


def cmd_install(src: Path) -> None:
    sudo_uid = _require_root_sudo_uid()
    _ensure_quirks_dir()
    text = read_text(src, owner=sudo_uid)
    atomic_write(QUIRKS_PATH, text, create_parent=False, owner=0, mode=0o644)


def cmd_remove() -> None:
    _require_root_sudo_uid()
    parent = os.open(str(QUIRKS_DIR), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        try:
            os.unlink(QUIRKS_PATH.name, dir_fd=parent)
        except FileNotFoundError:
            return
    finally:
        os.close(parent)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        die("usage: libinput_quirks.py prepare|uninstall-body|install TMP|remove")
    action = argv[1]
    if action == "prepare" and len(argv) == 2:
        cmd_prepare()
    elif action == "uninstall-body" and len(argv) == 2:
        cmd_uninstall_body()
    elif action == "install" and len(argv) == 3:
        cmd_install(Path(argv[2]))
    elif action == "remove" and len(argv) == 2:
        cmd_remove()
    else:
        die("usage: libinput_quirks.py prepare|uninstall-body|install TMP|remove")


if __name__ == "__main__":
    main(sys.argv)
