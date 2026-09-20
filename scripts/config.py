#!/usr/bin/python3
"""Vi Mode settings, keyd generation, and live-config inference."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from safe_file import atomic_write, read_text

PLUGIN_ID = "oliverlukschander.vi-mode"
NAV_KEYS = ("capslock", "control")
DEFAULTS = {
    "navKey": "capslock",
    "swapCapsCtrl": False,
    "resize": False,
}

BEGIN_RE = re.compile(r"^# BEGIN (.+)$")
END_RE = re.compile(r"^# END (.+)$")
STRIP_BLOCKS = {"oliverlukschander.vi-resize"}
ASSIGN_RE = re.compile(r"^([A-Za-z0-9_]+)\s*=\s*(.+)$")


def plugin_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def _state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))


def settings_path() -> Path:
    return _config_home() / "omarchy" / f"{PLUGIN_ID}.json"


def resize_toggle_path() -> Path:
    return _state_home() / "omarchy" / "toggles" / "hypr" / "oliverlukschander-vi-mode-resize.lua"


def foreign_resize_toggle_path() -> Path:
    return _state_home() / "omarchy" / "toggles" / "hypr" / "oliverlukschander-vi-resize.lua"


def keyd_target() -> Path:
    return Path("/etc/keyd/omarchy-vi-mode.conf")


def _coerce(raw: dict) -> dict:
    nav = raw.get("navKey", DEFAULTS["navKey"])
    if nav not in NAV_KEYS:
        nav = DEFAULTS["navKey"]
    return {
        "navKey": nav,
        "swapCapsCtrl": bool(raw.get("swapCapsCtrl", DEFAULTS["swapCapsCtrl"])),
        "resize": bool(raw.get("resize", DEFAULTS["resize"])),
    }


def load_settings(*, infer_if_missing: bool = True) -> dict:
    path = settings_path()
    try:
        text = read_text(path)
    except SystemExit:
        text = ""
    if text.strip():
        try:
            data = json.loads(text)
        except ValueError:
            data = {}
        if isinstance(data, dict):
            return _coerce(data)
    if infer_if_missing:
        live = infer_live()
        if live is not None:
            return live
    return dict(DEFAULTS)


def save_settings(settings: dict) -> dict:
    data = _coerce(settings)
    atomic_write(settings_path(), json.dumps(data, indent=2) + "\n")
    return data


def merge_set(updates: dict) -> dict:
    current = load_settings()
    current.update(updates)
    return save_settings(current)


def parse_set_args(args: list[str]) -> dict:
    updates: dict = {}
    for arg in args:
        if "=" not in arg:
            raise SystemExit(f"expected KEY=VAL, got {arg!r}")
        key, val = arg.split("=", 1)
        if key == "navKey":
            if val not in NAV_KEYS:
                raise SystemExit(f"navKey must be capslock or control, got {val!r}")
            updates["navKey"] = val
        elif key in ("swapCapsCtrl", "resize"):
            if val not in ("true", "false", "1", "0"):
                raise SystemExit(f"{key} must be true or false, got {val!r}")
            updates[key] = val in ("true", "1")
        else:
            raise SystemExit(f"unknown setting {key!r}")
    return updates


def split_managed(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (non-managed body, [(block_id, block_text including markers)])."""
    body: list[str] = []
    blocks: list[tuple[str, str]] = []
    current_id: str | None = None
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        begin = BEGIN_RE.match(stripped)
        if begin and current_id is None:
            current_id = begin.group(1)
            current = [line]
            continue
        if current_id is not None:
            current.append(line)
            if stripped == f"# END {current_id}":
                blocks.append((current_id, "".join(current)))
                current_id = None
                current = []
            continue
        body.append(line)
    if current_id is not None:
        body.extend(current)
    return "".join(body), blocks


def preserved_blocks(text: str) -> list[str]:
    _body, blocks = split_managed(text)
    return [block for ident, block in blocks if ident not in STRIP_BLOCKS]


def compose_keyd(generated: str, blocks: list[str]) -> str:
    body = generated.rstrip() + "\n"
    extras = [block.strip("\n") for block in blocks if block.strip()]
    if extras:
        body += "\n" + "\n\n".join(extras) + "\n"
    return body


def _hjkl(action: dict[str, str]) -> list[str]:
    return [f"{key} = {action[key]}" for key in ("h", "j", "k", "l")]


def _arrows() -> dict[str, str]:
    return {"h": "left", "j": "down", "k": "up", "l": "right"}


def _shifted(prefix: str) -> dict[str, str]:
    arrows = _arrows()
    return {key: f"{prefix}{arrows[key]}" for key in arrows}


def _meta_shift() -> dict[str, str]:
    return {"h": "M-S-h", "j": "M-S-j", "k": "M-S-k", "l": "M-S-l"}


def generate(settings: dict | None = None) -> str:
    cfg = _coerce(settings or DEFAULTS)
    nav = cfg["navKey"]
    swap = cfg["swapCapsCtrl"]
    resize = cfg["resize"]
    mod = "Ctrl" if nav == "control" else "Caps Lock"
    lines = [
        "# Omarchy Vi Mode",
        f"# Generated from {settings_path()}",
        f"# Arrow layer: {mod}"
        + ("; Caps Lock and Left Ctrl swapped" if swap else "")
        + ("; resize on Shift+hjkl" if resize else ""),
        "# Other plugins may append # BEGIN / # END blocks below.",
        "",
        "[ids]",
        "*",
        "",
    ]

    main: list[str] = []
    if nav == "capslock":
        main.append("capslock = layer(nav)")
        if swap:
            main.append("leftcontrol = capslock")
    elif swap:
        main.append("capslock = leftcontrol")
        main.append("leftcontrol = capslock")

    if main:
        lines.append("[main]")
        lines.extend(main)
        lines.append("")

    shift_map = _meta_shift() if resize else _shifted("S-")
    word_map = _shifted("C-")
    word_shift_map = _shifted("C-S-")

    if nav == "capslock":
        lines.append("[nav]")
        lines.extend(_hjkl(_arrows()))
        lines.append("")
        lines.append("[nav+shift]")
        lines.extend(_hjkl(shift_map))
        lines.append("")
        lines.append("[nav+control]")
        lines.extend(_hjkl(word_map))
        lines.append("")
        lines.append("[nav+control+shift]")
        lines.extend(_hjkl(word_shift_map))
        lines.append("")
    else:
        lines.append("[control]")
        lines.extend(_hjkl(_arrows()))
        lines.append("")
        lines.append("[control+shift]")
        lines.extend(_hjkl(shift_map))
        lines.append("")
        lines.append("[control+alt]")
        lines.extend(_hjkl(word_map))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _assignments(section: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in section.splitlines():
        match = ASSIGN_RE.match(line.strip())
        if match:
            out[match.group(1)] = match.group(2).strip()
    return out


def _sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]") and not stripped.startswith("[ids]"):
            if current is not None:
                sections[current] = "\n".join(buf)
            current = stripped[1:-1]
            buf = []
            continue
        if current is not None:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf)
    return sections


def infer_from_text(text: str) -> dict | None:
    if not text.strip():
        return None
    secs = _sections(text)
    main = _assignments(secs.get("main", ""))
    nav = "capslock"
    if main.get("capslock") == "layer(nav)":
        nav = "capslock"
    elif "h = left" in secs.get("control", ""):
        nav = "control"
    swap = main.get("capslock") == "leftcontrol" or main.get("leftcontrol") == "capslock"
    resize = "M-S-h" in text
    return {"navKey": nav, "swapCapsCtrl": swap, "resize": resize}


def read_keyd(path: Path | None = None) -> str:
    target = path or keyd_target()
    try:
        return read_text(target, owner=0)
    except SystemExit:
        return ""


def infer_live(path: Path | None = None) -> dict | None:
    return infer_from_text(read_keyd(path))


def _file_exists(path: Path) -> bool:
    try:
        read_text(path)
        return True
    except SystemExit:
        return False
    except OSError:
        return False


def status_dict() -> dict:
    desired = load_settings()
    live = infer_live()
    keyd_text = read_keyd()
    config_present = bool(keyd_text.strip())
    if live is None:
        live = dict(DEFAULTS)
        live_ok = False
    else:
        live_ok = True
    dirty = config_present and live_ok and live != desired
    return {
        "keydInstalled": os.path.isfile("/usr/bin/keyd"),
        "active": _service_active("keyd"),
        "configPresent": config_present,
        "navKey": desired["navKey"],
        "swapCapsCtrl": desired["swapCapsCtrl"],
        "resize": desired["resize"],
        "liveNavKey": live["navKey"],
        "liveSwapCapsCtrl": live["swapCapsCtrl"],
        "liveResize": live["resize"],
        "dirty": dirty,
        "resizeTogglePresent": _file_exists(resize_toggle_path()),
        "foreignResizeToggle": _file_exists(foreign_resize_toggle_path()),
    }


def _service_active(name: str) -> bool:
    try:
        import subprocess

        proc = subprocess.run(
            ["/usr/bin/systemctl", "is-active", "--quiet", name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return proc.returncode == 0
    except OSError:
        return False


def dump_status() -> None:
    sys.stdout.write(json.dumps(status_dict(), separators=(",", ":")) + "\n")
