#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-STOPSEED -- is the case `ex_stop`'s deleted edge seed would protect REACHABLE?

🔴 WHY. `docs/spec-traps-t1-stop-reslice.md` deletes `ex_stop`/`es_set`'s edge
seed, and gives TWO reasons. The first -- *"122 fires vs the seeded build's 1"*
-- was REFUTED by D-STOPRELATCH: the 122 comes from the reference's per-frame
shadow release and has nothing to do with seeding, so that row never tested the
seed. The spec itself says so and TODO carries the residual.

⚠️ THE SECOND REASON IS THE ONE NOBODY HAS RUN, and it is the load-bearing one:

    "The case a seed would protect (key held across the enable) is unreachable
     for STOP anyway: with the entry OFF or suspended, a held Ctrl-STOP breaks
     the program at the line boundary *before* `STOP ON` runs."

That is a REACHABILITY claim about our own ROM, and it is testable without
building a seeded variant -- which is why this probe exists rather than an A/B.

🎯 THE SEPARATING CASE IS THE WORD "LINE". If the break is checked at a LINE
boundary, then putting `STOP ON` on the SAME LINE as the delay leaves no
boundary between them, the enable executes with the key still down, and the
protected case IS reachable. If the check is per STATEMENT, it is not.

  BOUNDARY   20 FOR..NEXT      / 30 STOP ON      -- a line boundary between them
  SAMELINE   20 FOR..NEXT:STOP ON:<mark>         -- none

`RAN` ($D002) is the reading: it is poked immediately AFTER `STOP ON`, so
`ran=1` means the enable executed and `ran=0` means the program broke first.

🔴 THIS PROBE CANNOT USE `rearmsens_probe.gate()`, AND THE REASON IS THE POINT.
That helper REFUSES any trial with `ran != 1`, because for its question an
un-armed trial is invalid. Here `ran` IS the subject, so the shared gate would
refuse exactly the interesting outcome. A precondition in one experiment is a
finding in another.

    python3 -u scratchpad/stopseed_probe.py [--selftest]
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))

import probe_tmp  # noqa: E402,F401  -- module level; see check_temp_root
import basic_probe_stop_trap as ST          # noqa: E402

# \u26a0\ufe0f THE MACHINE NAMES COME FROM THE SHARED PROBE, NOT FROM A LITERAL --
# a typo here would boot a different machine and the readings would still look
# like readings.
ZB = ST.ZB_MACHINE
# ⚠️ THREE PHASES, NOT ONE. D-REARMSENS's whole finding was that a single
# key-down schedule produced a spike that read like a property.
PHASES = (0.300, 0.315, 0.330)
HOLD = 25.0          # key stays DOWN across the enable and the second delay
N = 6000             # the delay the press lands inside (~2.4 s on the reference)


def prog_boundary(n=N):
    """`STOP ON` on its OWN line: a line boundary sits before it."""
    return [ST.CLR, "10 ON STOP GOSUB 100",
            f"20 FORI=1TO{n}:NEXT",
            "30 STOP ON",
            "35 POKE&HD002,1",
            f"40 FORI=1TO{n}:NEXT",
            "50 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1", "106 RETURN"]


def prog_sameline(n=N):
    """`STOP ON` on the SAME line as the delay: no boundary between them."""
    return [ST.CLR, "10 ON STOP GOSUB 100",
            f"20 FORI=1TO{n}:NEXT:STOP ON:POKE&HD002,1",
            f"40 FORI=1TO{n}:NEXT",
            "50 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1", "106 RETURN"]


def prog_armed(n=N):
    """POSITIVE CONTROL: armed BEFORE the delay, so the same press in the same
    window must FIRE. Without this, `ran=0` cannot be told from a press that
    never reached the machine at all."""
    return [ST.CLR, "10 ON STOP GOSUB 100", "20 STOP ON", "25 POKE&HD002,1",
            f"30 FORI=1TO{n}:NEXT",
            "50 POKE&HD003,1:END",
            "100 POKE&HD000,PEEK(&HD000)+1", "106 RETURN"]


def reading(rs):
    """-> dict or None. Unlike the shared gate, `ran` is REPORTED, not required.
    A trial is still invalid if it crashed or was captured mid-run (`done` 0)."""
    if not rs or any(r is None for r in rs):
        return None
    if any(r.get("done") != 1 for r in rs):
        return None
    return {"ran": sorted({r.get("ran") for r in rs}),
            "flag": sorted({r.get("flag") for r in rs})}


def verdict(boundary, sameline):
    """The three outcomes this probe can produce, named before the run."""
    if boundary is None or sameline is None:
        return "REFUSED (a batch was not a datum)"
    if sameline["ran"] == [0] and boundary["ran"] == [0]:
        return ("UNREACHABLE — the enable never executed on either shape, so "
                "the spec's reachability argument HOLDS and the seed protects "
                "nothing")
    if sameline["ran"] == [1] and boundary["ran"] == [0]:
        return ("REACHABLE ON ONE LINE — the break is checked at a LINE "
                "boundary, so `STOP ON` DID execute under a held key. The "
                "spec's reachability argument is WRONG and the seed's case "
                "exists")
    return (f"MIXED — boundary ran={boundary['ran']}, sameline "
            f"ran={sameline['ran']}; neither clean outcome, read the trials")


def selftest():
    """Pure-helper arms with the negative controls. Without them, 'the verdict
    printed' is equally what a verdict function that ignores its input prints."""
    fails = 0

    def arm(label, cond):
        nonlocal fails
        if not cond:
            print(f"  selftest: FAIL {label}")
            fails += 1

    arm("a crashed trial is not a datum", reading([None]) is None)
    arm("an empty batch is not a datum", reading([]) is None)
    arm("a mid-run capture (done=0) is not a datum",
        reading([{"ran": 1, "done": 0, "flag": 0}]) is None)
    # 🔴 THE ARM THIS PROBE EXISTS FOR: ran=0 must be a READING, not a refusal.
    r = reading([{"ran": 0, "done": 1, "flag": 0}])
    arm("ran=0 is REPORTED, not refused (the shared gate would refuse it)",
        r is not None and r["ran"] == [0])
    arm("ran varying across phases is kept as a set, not collapsed",
        reading([{"ran": 0, "done": 1, "flag": 0},
                 {"ran": 1, "done": 1, "flag": 0}])["ran"] == [0, 1])
    b0 = {"ran": [0], "flag": [0]}
    s0 = {"ran": [0], "flag": [0]}
    s1 = {"ran": [1], "flag": [0]}
    arm("both un-run -> UNREACHABLE", verdict(b0, s0).startswith("UNREACHABLE"))
    arm("same-line runs, boundary does not -> REACHABLE",
        verdict(b0, s1).startswith("REACHABLE"))
    arm("NEGATIVE: boundary ALSO running is MIXED, not REACHABLE",
        verdict({"ran": [1], "flag": [0]}, s1).startswith("MIXED"))
    arm("NEGATIVE: a refused batch cannot produce a verdict",
        verdict(None, s1).startswith("REFUSED"))
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def batch(tag, prog):
    rs = []
    for dn in PHASES:
        r = ST.run(ZB, prog, [(dn, dn + HOLD)], deadline=300.0, timeout=240)
        rs.append(r)
        print(f"    {tag} phase {dn:.3f}: {r}", flush=True)
    return reading(rs)


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    print("D-STOPSEED: is the seed's protected case reachable?\n")
    ctl = batch("CONTROL armed-first", prog_armed())
    print(f"  CONTROL (armed before the delay): {ctl}")
    if ctl is None or ctl["flag"] == [0]:
        print("\n🔴 INSTRUMENT FAULT: the positive control did not FIRE, so the "
              "press is not reaching the machine in this window. Every `ran=0` "
              "below would be unreadable — a press that never lands looks "
              "exactly like a break that happened.")
        return 2
    b = batch("BOUNDARY", prog_boundary())
    print(f"  BOUNDARY (STOP ON on its own line): {b}")
    s = batch("SAMELINE", prog_sameline())
    print(f"  SAMELINE (STOP ON after the delay, same line): {s}")
    print("\nVERDICT:", verdict(b, s))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
