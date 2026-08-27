#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The boot banner — the one thing in this tree no other gate can see.

🔴 EVERY PROBE PROGRAM IN THIS REPO OPENS WITH `CLS`, WHICH WIPES THE STARTUP
HEADER. So `show_title` could stop printing entirely and all 41 gates would stay
green. That is not hypothetical: D-MISSOP funded its 5 B fix by PROMOTING
`basic/title.asm` out of page 1 into the low region, i.e. the one thing the
change could plausibly break was the one thing nothing read.

This runs NO `CLS` anywhere and asserts the header is still above the prompt.

TWO ASSERTIONS, AND THE SECOND IS WHAT KEEPS THE FIRST HONEST:

  BANNER   both header lines are on screen.
  MARKER   a fenced `[...]` the program printed itself. Without it, a machine
           that never booted -- or a capture that never happened -- looks
           exactly like a banner that stopped printing, and the gate would
           report the apparatus as the feature
           [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

So: marker present + banner present -> PASS. Marker present + banner absent ->
RED, the real finding. Marker ABSENT -> rc 2, instrument fault, never a verdict.

⚠️ SUBJECT-ONLY BY CONSTRUCTION. The header text is zerobas's own (`sub/title.asm`
via `basic/title-body.inc`); the references print their own different banner, so
there is nothing to differentiate against. This gate asserts that OUR text is
present, not that it matches anyone.

Usage:  python3 probes/basic/basic_probe_banner.py --gate
"""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl                                                  # noqa: E402

ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
BODY = os.path.join(ROOT, "basic", "title-body.inc")


def expected() -> list[str]:
    """The header lines, read out of the SOURCE rather than pinned here.

    🎯 A COPY OF THE TEXT IN THIS FILE WOULD ROT THE DAY THE BANNER CHANGES, and
    the gate would then fail for the wrong reason -- or worse, be "fixed" by
    editing the expectation to match whatever it now prints, which is a gate
    that asserts nothing."""
    out = []
    for m in re.finditer(r'db\s+"([^"]+)"', open(BODY).read()):
        s = m.group(1).strip()
        if s:
            out.append(s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.parse_args()

    want = expected()
    if not want:
        print(f"INSTRUMENT FAULT: no header strings parsed out of "
              f"{os.path.relpath(BODY, ROOT)} -- the expectation would be empty "
              f"and every run would pass.")
        return 2
    caps = omsx_repl.run_cases(ZB, [("direct", ['10 PRINT"[";7;0;"]"', "RUN"])],
                               batch=False, boot=8.0, step=3.0, cap_gap=8.0,
                               timeout=300.0)
    scr = caps[0] or ""
    marker = omsx_repl.result_span_after_echo(caps[0], "RUN")
    print(f"banner gate — {len(want)} header line(s) expected, read from "
          f"{os.path.relpath(BODY, ROOT)}")
    for w in want:
        print(f"  {'PRESENT' if w in scr else '🔴 ABSENT'}  {w!r}")
    print(f"  marker {marker!r}")

    if marker is None or not marker.strip():
        print("\nINSTRUMENT FAULT (rc 2): the program's own marker never "
              "printed, so the machine did not reach the prompt or the capture "
              "did not happen. A missing banner is indistinguishable from a "
              "missing run, and this is NOT a verdict about the banner.")
        return 2
    missing = [w for w in want if w not in scr]
    if missing:
        print(f"\n🔴 FAIL: the marker printed but {len(missing)} header line(s) "
              f"are GONE: {missing}. `show_title` stopped reaching the screen, "
              f"and no other gate in this tree would have noticed.")
        return 1
    print("\nbanner: PASS — the startup header survives to the prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
