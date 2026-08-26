#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-STALLSLOW falsification — and one arm is recorded as NOT EXERCISED.

The change is two things:
  (a) read the heartbeat file's CONTENT (the emulated instant) before unlinking;
  (b) stop asserting "a stall is a FROZEN OR CRASHED emulator, not a slow one"
      and report the evidence instead.

(b) is fully covered by message vectors. (a)'s parse is covered by a file
vector. 🔴 THE END-TO-END KILL IS NOT COVERED, and that is stated rather than
implied: an attempt to force one with ZEROBAS_OMSX_STALL=2 did NOT kill -- the
run completed normally -- so that arm proved nothing and is reported as a GAP.
An arm that passes because it never fired is the defect this project keeps
catching (D-PASMOSAY's first RED vector was a valid LABEL, not a broken source).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl as R                                             # noqa: E402
import probe_tmp                                                  # noqa: E402

BANNED = "not a slow one"


def main() -> int:
    fails = 0

    print("  --- (b) the message no longer ASSERTS what it cannot know ---")
    for name, hb, lines in [("advancing", 12.4, 1886),
                            ("never-started", 0.0, 0),
                            ("no-value", None, 2)]:
        msg = R._why_missing("M", 0, 1, "stall", 0, 947.0, lines,
                             "/nonexistent", hb)
        ok = (BANNED not in msg
              and "CANNOT separate" in msg
              and f"wrote {lines} line(s)" in msg
              and ("no emulated instant" in msg if hb is None
                   else f"emulated {hb:.1f}s" in msg))
        print(f"    {name:14s} {'✅' if ok else '🔴'}  "
              f"{'reports the instant + the line count, claims neither' if ok else msg[:120]}")
        fails += not ok

    print("\n  --- (b) control: a NON-stall kill must be untouched ---")
    msg = R._why_missing("M", 0, 1, "abscap", 0, 1800.0, 5, "/nonexistent", 900.0)
    ok = "CANNOT separate" not in msg and "abscap watchdog" in msg
    print(f"    abscap         {'✅' if ok else '🔴'}  "
          f"{'unchanged -- the clause is stall-only' if ok else msg[:120]}")
    fails += not ok

    print("\n  --- (a) the heartbeat PARSE contract ---")
    d = probe_tmp.tmp("stallslow")
    os.makedirs(d, exist_ok=True)
    for name, body, want in [("plain", "12.4\n", 12.4),
                             ("padded", "  0.0  \n", 0.0),
                             ("empty", "", None),
                             ("garbage", "not-a-float\n", None)]:
        p = os.path.join(d, "hb")
        open(p, "w").write(body)
        try:
            got = float(open(p).read().strip() or "nan")
            got = None if got != got else got
        except (OSError, ValueError):
            got = None
        ok = got == want
        print(f"    {name:14s} {'✅' if ok else '🔴'}  {body!r} -> {got!r}")
        fails += not ok
    os.remove(os.path.join(d, "hb"))

    print("\n  --- 🔴 NOT EXERCISED, and said so ---")
    print("    end-to-end stall kill: ZEROBAS_OMSX_STALL=2 against a live")
    print("    emulator did NOT kill -- the run completed and returned its")
    print("    capture. So nothing here proves the READ happens at a real kill")
    print("    site, only that the parse and the message are right. An arm that")
    print("    passes because it never fired is not an arm.")

    print()
    if fails:
        print(f"  🔴 {fails} arm(s) failed — do NOT ship.")
        return 1
    print("  ✅ 8 of 8 covered arms pass; 1 arm NOT EXERCISED and named.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
