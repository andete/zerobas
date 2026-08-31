#!/usr/bin/env python3
r"""D-CLAMPPITCH — WHICH pitch does an edge accidental play?

D-PLAYCORNER measured that `O1 C-` and `O8 B#` are ACCEPTED on both references
(rows c.cflat / c.bsharp), but a screen read cannot say whether the reference
plays the SAME PITCH as this tree's clamp (note 0 = C1 / note 95 = B8).
This is that row, by the playtrace method: trace the PSG per VBLANK on both
machines and compare the (tone_period, amp) note sequence.

Fixtures bracket the clamped note between two ORDINARY notes so a sequence
mismatch is attributable: [D1, C-@O1, D1] and [A8, B#@O8, A8]. If the
reference clamps as we do, the middle period equals C1's / B8's; if it wraps
(C- at O1 -> B of a phantom octave 0, B# at O8 -> C of a phantom octave 9) or
ignores the accidental, the middle period differs and the row says so.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "probes", "basic"))
import basic_probe_playtrace as PT                               # noqa: E402

CASES = [
    ("cflat",  'PLAY"O1L8DC-D"', 300),   # C- at the bottom edge
    ("bsharp", 'PLAY"O8L8AB#A"', 300),   # B# at the top edge
    ("ctl.c1", 'PLAY"O1L8DCD"',  300),   # 🟢 what plain C1 traces as
    ("ctl.b8", 'PLAY"O8L8ABA"',  300),   # 🟢 what plain B8 traces as
    # 🔴 THE EDGE ROWS CANNOT SEPARATE TWO RULES. `C-` at O1 playing B1 fits
    # BOTH "semitone wraps mod 12 inside the octave" AND "borrow the octave,
    # then clamp octave to 1". Mid-octave they part company: mod-12 says
    # `O4 C-` is B4 (period 227) and octave-borrow says B3 (453). Same for
    # `O4 B#`: mod-12 -> C4, borrow -> C5.
    ("mid.cf", 'PLAY"O4L8DC-D"', 300),
    ("mid.bs", 'PLAY"O4L8AB#A"', 300),
    ("ctl.o4", 'PLAY"O4L8DCD"',  300),   # 🟢 plain C4/D4 anchors
    ("ctl.b4", 'PLAY"O4L8ABA"',  300),   # 🟢 plain A4/B4 anchors
]


def main():
    ok = True
    mid = {}
    for lbl, stmt, n in CASES:
        ref = PT.voice_seq(PT.REF_MACHINE, stmt, n, 0)
        zb = PT.voice_seq(PT.ZB_MACHINE, stmt, n, 0)
        good = ref == zb and len(ref) > 0
        ok = ok and good
        mid[lbl] = (ref[1][0] if len(ref) >= 2 else None,
                    zb[1][0] if len(zb) >= 2 else None)
        print(f"{'PASS' if good else 'FAIL':5} {lbl:7} ref={ref}")
        if not good:
            print(f"      {'':7} zb ={zb}")
    # the pitch question, answered in periods rather than pass/fail prose.
    # 🔴 The first cut indexed seq[1] only when len > 2 and printed None for
    # every row: the trace helper DROPS the open-ended trailing segment, so a
    # three-note fixture parses to TWO segments and the middle IS seq[1] of a
    # len >= 2 sequence.
    for edge, ctl in (("cflat", "ctl.c1"), ("bsharp", "ctl.b8"),
                      ("mid.cf", "ctl.b4"), ("mid.bs", "ctl.o4")):
        rp, zp = mid[edge]
        cp = mid[ctl][0]
        rel = ("the plain-note period, octave KEPT" if rp == cp
               else f"NOT the plain note's {cp}")
        print(f"  {edge}: accidental's period ref={rp} zb={zp}  ({rel})")
    print("VERDICT:", "identical sequences on both machines" if ok
          else "🔴 sequences differ -- the clamp rule is NOT the reference's")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
