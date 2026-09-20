#!/usr/bin/python3
"""Generator tests for Vi Mode keyd output. No sudo, no live keyd file."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import compose_keyd, generate, infer_from_text, preserved_blocks, split_managed


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def test_default_matches_caps_nav() -> None:
    text = generate({"navKey": "capslock", "swapCapsCtrl": False, "resize": False})
    _assert("capslock = layer(nav)" in text, "default Caps layer")
    _assert("leftcontrol" not in text, "no swap remap")
    _assert("[nav]" in text, "nav section")
    _assert("[control]" not in text.split("[nav]")[0] or "[control]\n" not in text, "no control overlay")
    _assert("h = left" in text, "arrows")
    _assert("h = S-left" in text, "select")
    _assert("h = C-left" in text, "word jump")
    _assert("M-S-h" not in text, "no resize")
    _assert("[control]\n" not in text, "ctrl layer unused")


def test_caps_resize() -> None:
    text = generate({"navKey": "capslock", "swapCapsCtrl": False, "resize": True})
    _assert("[nav+shift]" in text, "nav+shift present")
    _assert("h = M-S-h" in text, "resize chord")
    _assert("h = S-left" not in text, "select replaced")


def test_caps_swap() -> None:
    text = generate({"navKey": "capslock", "swapCapsCtrl": True, "resize": False})
    _assert("capslock = layer(nav)" in text, "caps stays the layer")
    _assert("leftcontrol = capslock" in text, "ctrl becomes caps")
    _assert("capslock = leftcontrol" not in text, "caps is not swapped away")


def test_ctrl_nav() -> None:
    text = generate({"navKey": "control", "swapCapsCtrl": False, "resize": False})
    _assert("[main]" not in text, "no main remaps")
    _assert("[control]" in text, "control overlay")
    _assert("h = left" in text, "ctrl+hjkl arrows")
    _assert("[control+shift]" in text, "shift composite")
    _assert("[control+alt]" in text, "word jump")
    _assert("layer(nav)" not in text, "caps not a layer")


def test_ctrl_swap() -> None:
    text = generate({"navKey": "control", "swapCapsCtrl": True, "resize": False})
    _assert("capslock = leftcontrol" in text, "caps becomes ctrl")
    _assert("leftcontrol = capslock" in text, "ctrl becomes caps")
    _assert("[control]" in text, "control overlay")


def test_ctrl_swap_resize() -> None:
    text = generate({"navKey": "control", "swapCapsCtrl": True, "resize": True})
    _assert("h = M-S-h" in text, "resize on control+shift")
    _assert("[control+shift]" in text, "composite after control")
    live = infer_from_text(text)
    _assert(live == {"navKey": "control", "swapCapsCtrl": True, "resize": True}, f"infer {live}")


def test_infer_legacy_with_resize_block() -> None:
    text = """[ids]
*

[main]
capslock = layer(nav)

[nav]
h = left

[nav+shift]
h = S-left

# BEGIN oliverlukschander.vi-resize
[nav+shift]
h = M-S-h
# END oliverlukschander.vi-resize
"""
    live = infer_from_text(text)
    _assert(live == {"navKey": "capslock", "swapCapsCtrl": False, "resize": True}, f"infer {live}")


def test_preserve_mac_option_strip_resize() -> None:
    current = """[ids]
*

[main]
capslock = layer(nav)

# BEGIN oliverlukschander.mac-option
[alt]
u = macro(iso-level3-shift+u)
# END oliverlukschander.mac-option

# BEGIN oliverlukschander.vi-resize
[nav+shift]
h = M-S-h
# END oliverlukschander.vi-resize
"""
    blocks = preserved_blocks(current)
    _assert(len(blocks) == 1, f"kept {len(blocks)} blocks")
    _assert("mac-option" in blocks[0], "kept mac-option")
    _assert("vi-resize" not in blocks[0], "stripped vi-resize")
    composed = compose_keyd(generate({"navKey": "capslock", "swapCapsCtrl": False, "resize": True}), blocks)
    _assert("BEGIN oliverlukschander.mac-option" in composed, "mac-option survives compose")
    _assert("BEGIN oliverlukschander.vi-resize" not in composed, "resize block not re-added")
    _assert("h = M-S-h" in composed, "resize lives in generated body")


def test_unclosed_block_stays_in_body() -> None:
    body, blocks = split_managed("# BEGIN dangling\nfoo = bar\n")
    _assert(not blocks, "unclosed block is not managed")
    _assert("BEGIN dangling" in body, "unclosed block remains body")


def main() -> None:
    tests = [
        test_default_matches_caps_nav,
        test_caps_resize,
        test_caps_swap,
        test_ctrl_nav,
        test_ctrl_swap,
        test_ctrl_swap_resize,
        test_infer_legacy_with_resize_block,
        test_preserve_mac_option_strip_resize,
        test_unclosed_block_stays_in_body,
    ]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"passed {len(tests)}")


if __name__ == "__main__":
    main()
