#!/usr/bin/env python3
"""What does sentinel CAPTURE actually save? Measured, not assumed.

The differential (sentinel_screen_diff.py) says the readout is unchanged. That
makes adoption SAFE; it does not make it WORTH IT. Adoption costs a `POKE` in
every program of a fidelity gate, so the saving has to be measured before the
edit -- the D-PAINTSCAN lesson.

Reports, per case: wall, and the emulated instant the capture actually happened
(the sentinel's own timestamp vs the budget's scheduled one).
"""
from __future__ import annotations
import os, sys, time
ROOT = "/Users/joost/projects/zerobas"
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import omsx_repl                                                   # noqa: E402
import basic_probe_graphics as g                                   # noqa: E402

MARK = 0xE000
CASES = [
    ("flood",       ["PAINT(128,96),15"], [(128, 96), (129, 96)]),
    ("circle_fill", ["CIRCLE(128,96),40:PAINT(128,96),15"], [(128, 96), (10, 10)]),
    ("errpath",     ["ONERRORGOTO90", "CIRCLE(50,50),"], [(30, 50)]),
]


def prog(setup, pts, poke):
    lines = g.paint_points_prog(setup, pts)
    if poke:
        lines[-1] = lines[-1].replace(":END", f":POKE&H{MARK:04X},255:END")
    return lines


def one(machine, lines, sentinel):
    so: dict = {}
    kw = dict(batch=False, run_gap=g.PAINT_STEP, cap_gap=g.PAINT_CAP_GAP,
              timeout=g.PAINT_TIMEOUT, settle_out=so)
    if sentinel:
        kw.update(sentinel=(MARK, 255), sentinel_capture=True)
    t = time.monotonic()
    omsx_repl.run_cases(machine, [("stored", lines)], **kw)
    return time.monotonic() - t, so


def main():
    print(f"{'case':<13} {'side':<5} {'fixed wall':>11} {'sentinel wall':>14} "
          f"{'captured at':>12} {'budget':>8}")
    tf = ts = 0.0
    for label, setup, pts in CASES:
        for side, machine in (("ref", g.REF), ("zb", g.ZB)):
            wf, _ = one(machine, prog(setup, pts, False), False)
            ws, so = one(machine, prog(setup, pts, True), True)
            tf += wf; ts += ws
            fired = so.get("sentinel", {}).get(0)
            fb = so.get("fallback", {}).get(0)
            at = f"{fired:.2f}s" if fired else (f"fallback {fb:.1f}s" if fb else "?")
            print(f"{label:<13} {side:<5} {wf:>10.2f}s {ws:>13.2f}s "
                  f"{at:>12} {g.PAINT_STEP:>7.0f}s")
    print(f"\n  total: fixed {tf:.2f}s -> sentinel {ts:.2f}s "
          f"({100*(tf-ts)/tf:+.0f}%)")
    print("  ⚠️ wall here carries the host's periodic stall (TODO.md), so a small "
          "difference is NOT resolvable; the 'captured at' column is the "
          "deterministic one.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
