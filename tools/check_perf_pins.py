#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-PERFPIN — the standing ASYMMETRIC performance check.

`docs/spec-basic-paintvram.md`'s own item proposed it: *"a standing asymmetric
perf check falls out of the same instrument: RED only when an operation is
significantly slower than BOTH references, never when it is faster"*, against
Joost's policy — **faster or comparable is not a worry; significantly SLOWER
is.**

🔴 BUT "SLOWER THAN BOTH REFERENCES" CANNOT BE THE GATE ON ITS OWN, and saying so
is the whole design. `PAINT` is 2× slower TODAY and that is a filed, open TIER 4
item — a gate that simply asserted the policy would be RED on arrival, and a gate
that is red for a known reason teaches nobody anything. So the rule is:

    RED when an operation is slower THAN ITS OWN PINNED BASELINE by more than the
    margin. The reference columns are REPORTED for context and never gate.

That is the asymmetry the policy asks for, made actionable: it cannot fire for
being slow, only for getting SLOWER.

🎯 AND IT EXISTS BECAUSE THE DRIFT ALREADY HAPPENED, MEASURED, WITH NOTHING
WATCHING. D-PAINTSCAN recorded the reverted tree at flood **29.742824** on
2026-08-25. On 2026-09-16 the same deterministic stopwatch reads **30.922748** —
**+4.0 %**, ratio 2.02x -> 2.10x. Nothing in the battery could see it. A pin is
what turns that from an anecdote into a gate.

⚠️ THE STOPWATCH IS EXACT AND DETERMINISTIC, which is what makes a pin legitimate
here at all: the case's own BASIC POKEs a watched cell either side of the
operation and openMSX logs the emulated instant of each write, so the difference
IS the duration and it repeats bit-identically across runs
(`docs/spec-probe-budget.md` §6). A wall-clock timer could not be pinned this
tightly.
⚠️ MARGIN 3 %: above the 0 % the instrument's determinism would allow, so a pin
refresh is not needed for noise, and far below the 4 % drift that went unnoticed.
"""
from __future__ import annotations
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚠️ THE MEASUREMENT IS NOT IN THIS FILE. It is `scratchpad/paint_stopwatch.py`,
# which is OUTSIDE `run_gates.py`'s fingerprinted trees -- so it is named there
# in FINGERPRINT_FILES, and the path is spelled out HERE so the one-hop premise
# check can see the reach. Do not turn this back into a bare `sys.path` join:
# `import paint_stopwatch` on its own is invisible to that check.
sys.path.insert(0, os.path.dirname(os.path.join(ROOT, "scratchpad/paint_stopwatch.py")))
import paint_stopwatch as sw                                       # noqa: E402

MARGIN = 0.03

# label: (pinned zb seconds, when, why this number)
PINS = {
    "paint.flood":  (30.922748, "2026-09-16", "post-D-PAINTSCAN-revert, re-pinned "
                                "after a +4.0% drift from 29.742824 (2026-08-25) "
                                "went unnoticed"),
    "paint.circle": (7.708053,  "2026-09-16", "same run; 7.403163 on 2026-08-25"),
    "circle":       (0.254279,  "2026-09-16", "faster than both references; pinned "
                                "so it cannot quietly stop being"),
    "line":         (0.123786,  "2026-09-16", "faster than both references"),
}


def main() -> int:
    print(f"{'operation':<14} {'vg8020':>11} {'cf3300':>11} {'zb':>11} "
          f"{'pin':>11} {'drift':>8}   verdict")
    bad, unread = [], []
    for label, op in sw.OPS:
        d = {}
        for side in ("vg8020", "cf3300", "zb"):
            dur, marks = sw.measure(side, op)
            d[side] = dur
            if dur is None:
                unread.append(f"{label}/{side}")
        if any(v is None for v in d.values()):
            print(f"{label:<14} {'':>11} {'':>11} {'':>11} {'':>11} {'':>8}   "
                  f"🔴 NO MARKS — not a reading")
            continue
        pin = PINS.get(label)
        best = min(d["vg8020"], d["cf3300"])
        ratio = d["zb"] / best
        if pin is None:
            verdict, drift = "⚠️ UNPINNED", ""
            bad.append(f"{label}: no pin")
        else:
            drift_f = (d["zb"] - pin[0]) / pin[0]
            drift = f"{drift_f:+.1%}"
            if drift_f > MARGIN:
                verdict = f"🔴 SLOWER than its pin ({ratio:.2f}x vs refs)"
                bad.append(f"{label}: {drift} over pin {pin[0]:.6f}")
            elif drift_f < -MARGIN:
                verdict = f"🟢 FASTER than its pin — re-pin it ({ratio:.2f}x)"
            else:
                verdict = f"✅ held ({ratio:.2f}x vs refs)"
        print(f"{label:<14} {d['vg8020']:>11.6f} {d['cf3300']:>11.6f} "
              f"{d['zb']:>11.6f} {pin[0] if pin else 0:>11.6f} {drift:>8}   {verdict}")

    print()
    if unread:
        print(f"🔴 INSTRUMENT FAULT (rc 2): {len(unread)} side(s) produced NO "
              f"MARKS — {', '.join(unread)}. A missing duration is not a fast one.")
        return 2
    if bad:
        print("🔴 PERF PIN(S) BROKEN — an operation got SLOWER than its own "
              "recorded baseline:")
        for b in bad:
            print(f"     {b}")
        print("   The reference columns do NOT gate: this fires only on drift "
              "against the pin, never on being slow.")
        return 1
    print("perf pins: every operation held within "
          f"{MARGIN:.0%} of its pinned baseline.")
    print("  (the reference columns are context — `PAINT` is a filed, open "
          "TIER 4 item at ~2x and this check is not about that)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
