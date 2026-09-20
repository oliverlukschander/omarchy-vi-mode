#!/usr/bin/python3
"""Merge tests for the libinput DWT quirks file. No sudo, no live /etc file."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from libinput_quirks import (
    MATCH_NAME,
    PLUGIN_ID,
    managed_block,
    merge_quirks,
    strip_unmarked_keyd_section,
    uninstall_quirks,
)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")


def test_empty_installs_managed_block() -> None:
    out = merge_quirks("")
    _assert(out == managed_block(), "empty becomes managed block")
    _assert(out.startswith(f"# BEGIN {PLUGIN_ID}\n"), "opens managed block")
    _assert(out.endswith(f"# END {PLUGIN_ID}\n"), "closes managed block")
    _assert(MATCH_NAME in out, "matches keyd virtual keyboard")
    _assert("AttrKeyboardIntegration=internal" in out, "marks internal")


def test_replaces_pre_2_0_1_unmarked_file() -> None:
    current = (
        "# Local override: keyd virtual keyboard is the laptop keyboard for DWT.\n"
        "# keyd grabs Apple MTP keyboard, so those key events never reach libinput.\n"
        "[keyd virtual keyboard]\n"
        "MatchUdevType=keyboard\n"
        "MatchName=keyd virtual keyboard\n"
        "AttrKeyboardIntegration=internal\n"
    )
    stripped = strip_unmarked_keyd_section(current)
    _assert("[keyd virtual keyboard]" not in stripped, "unmarked section removed")
    out = merge_quirks(current)
    _assert(out.count("[keyd virtual keyboard]") == 1, "no duplicate section")
    _assert(f"# BEGIN {PLUGIN_ID}" in out, "now marked")
    _assert("Local override:" not in out, "stale comments dropped")


def test_keeps_other_quirks() -> None:
    current = (
        "[Some Other Device]\n"
        "MatchName=Other\n"
        "AttrKeyboardIntegration=internal\n"
    )
    out = merge_quirks(current)
    _assert("[Some Other Device]" in out, "kept foreign section")
    _assert(f"# BEGIN {PLUGIN_ID}" in out, "added ours")
    _assert(out.index("[Some Other Device]") < out.index(f"# BEGIN {PLUGIN_ID}"), "ours last")


def test_replaces_existing_managed_block() -> None:
    current = (
        "[Keep Me]\n"
        "MatchName=keep\n"
        "\n"
        + managed_block()
        + "\n[Also Keep]\nMatchName=also\n"
    )
    out = merge_quirks(current)
    _assert(out.count(f"# BEGIN {PLUGIN_ID}") == 1, "one managed block")
    _assert("[Keep Me]" in out and "[Also Keep]" in out, "kept neighbors")
    leftover = uninstall_quirks(current)
    _assert(f"# BEGIN {PLUGIN_ID}" not in leftover, "uninstall drops ours")
    _assert("[Keep Me]" in leftover and "[Also Keep]" in leftover, "uninstall keeps others")


def test_uninstall_only_ours_is_empty() -> None:
    _assert(uninstall_quirks(managed_block()) == "", "delete file when only ours")
    _assert(uninstall_quirks("") == "", "missing file")
    unmarked = (
        "[keyd virtual keyboard]\n"
        "MatchUdevType=keyboard\n"
        "MatchName=keyd virtual keyboard\n"
        "AttrKeyboardIntegration=internal\n"
    )
    _assert(uninstall_quirks(unmarked) == "", "unmarked-only file deleted")


def test_does_not_strip_unrelated_keyd_section() -> None:
    current = (
        "[keyd virtual keyboard]\n"
        "MatchName=something else\n"
        "AttrKeyboardIntegration=external\n"
    )
    out = strip_unmarked_keyd_section(current)
    _assert("something else" in out, "foreign keyd section kept")


def main() -> None:
    tests = [
        test_empty_installs_managed_block,
        test_replaces_pre_2_0_1_unmarked_file,
        test_keeps_other_quirks,
        test_replaces_existing_managed_block,
        test_uninstall_only_ours_is_empty,
        test_does_not_strip_unrelated_keyd_section,
    ]
    for test in tests:
        test()
        print(f"ok  {test.__name__}")
    print(f"passed {len(tests)}")


if __name__ == "__main__":
    main()
