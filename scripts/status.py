#!/usr/bin/python3
"""Bounded status probe for the Vi Mode bar widget."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import dump_status


def main() -> None:
    dump_status()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.stdout.write(
            '{"keydInstalled":false,"active":false,"configPresent":false,'
            '"navKey":"capslock","swapCapsCtrl":false,"resize":false,'
            '"liveNavKey":"capslock","liveSwapCapsCtrl":false,"liveResize":false,'
            '"dirty":false,"resizeTogglePresent":false,"foreignResizeToggle":false}\n'
        )
        raise SystemExit(0)
