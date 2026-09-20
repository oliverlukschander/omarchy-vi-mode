#!/usr/bin/python3
"""Read or write Vi Mode settings. `set` also applies the Hyprland resize toggle."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apply import apply_hypr
from config import dump_status, load_settings, merge_set, parse_set_args, save_settings


def main(argv: list[str]) -> None:
    if len(argv) < 2 or argv[1] in ("get", "status"):
        dump_status()
        return
    if argv[1] == "set":
        updates = parse_set_args(argv[2:])
        if not updates:
            dump_status()
            return
        settings = merge_set(updates)
        if "resize" in updates:
            try:
                apply_hypr(settings)
            except Exception:
                pass
        dump_status()
        return
    if argv[1] == "save-defaults":
        save_settings(load_settings())
        dump_status()
        return
    raise SystemExit("usage: settings.py [get|status|set KEY=VAL ...]")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except SystemExit:
        raise
    except Exception:
        try:
            dump_status()
        except Exception:
            sys.stdout.write(
                '{"keydInstalled":false,"active":false,"configPresent":false,'
                '"navKey":"capslock","swapCapsCtrl":false,"resize":false,'
                '"liveNavKey":"capslock","liveSwapCapsCtrl":false,"liveResize":false,'
                '"dirty":false,"resizeTogglePresent":false,"foreignResizeToggle":false}\n'
            )
        raise SystemExit(0)
