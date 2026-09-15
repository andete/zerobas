#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-NODISKGAP: WHICH hook slot is `FIELD`'s?  Un-claim one and see who notices.

`scratchpad/hookscan_probe.py` found the CF-3300's disk ROM claims 27 hook cells
and that 14 of them have no equate in `basic/sysvars.inc`. `FIELD` needs a
disk-presence gate (it has none, so a diskless build answers the CHANNEL's error
where the reference answers Illegal function call) and its slot is one of those
fourteen.

THE METHOD: a claimed hook holds `F7 <slot> <lo> <hi> C9`; an UNCLAIMED one is a
bare `RET`. So `POKE <cell>,201` un-claims it on the reference, live, and the verb
that then starts answering ERR 5 owns that cell. Black-box: a POKE and a reading.

\U0001f534 TWO CONTROLS, AND BOTH CAN FAIL:
  ctrl_none   poke NOTHING -- `FIELD#1,2 AS A$` must still read ERR 59. If the
              act of running the program changes the answer, nothing below counts.
  ctrl_file   poke `H_FILE $FE7B`, a slot we have ALREADY named, and run `FILES`.
              It must flip ERR 70 -> ERR 5. This is the one that proves the
              METHOD; without it a flip in an unnamed slot proves nothing.
  ctrl_cross  poke that same `H_FILE` and run `FIELD`. It must NOT flip -- if
              un-claiming any hook broke every verb, a "hit" would be meaningless.

⚠️ A POKE IS STICKY FOR THE WHOLE BOOT, so every case gets its own machine
(`batch=False`) and no set is ever reused.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF = "National_CF-3300"
REF_KW = dict(boot=14.0, reset=("", "SCREEN 0"))

H_FILE = 65147                                  # $FE7B, already named
# the 14 claimed cells basic/sysvars.inc does not name, in address order
UNNAMED = [65007, 65057, 65062, 65067, 65102, 65112, 65117, 65122,
           65137, 65142, 65152, 65157, 65162, 65177]
FIELD = "FIELD#1,2 AS A$"


def prog(pokes, stmt):
    b = [None] + ["POKE %d,201" % a for a in pokes] + \
        [stmt, 'PRINT"<X>":END', 'PRINT"<E";ERR;">":END']
    b[0] = "ON ERROR GOTO %d" % (10 * len(b))
    return b


# ROUND 1 (2026-09-15) ran exactly this and the three controls all behaved:
#   ctrl_none  ERR 59   unchanged -- running the program does not move the answer
#   ctrl_file  ERR  5   FILES flipped when ITS OWN named hook was un-claimed
#   ctrl_cross ERR 59   and FIELD did NOT move when FILES's hook went -- so a hit
#                       is SPECIFIC, not "un-claiming anything breaks everything"
#   setA       ERR  5   <- FIELD's slot is in the first seven
#   setB       ERR 59
# ROUND 2 asks the seven ONE AT A TIME rather than bisecting again: seven boots
# against three rounds of two, and it also answers whether MORE THAN ONE slot
# matters, which a bisect would hide.
ROUND1 = [
    ("ctrl_none",  prog([], FIELD)),            # must stay ERR 59
    ("ctrl_file",  prog([H_FILE], "FILES")),    # must flip 70 -> 5
    ("ctrl_cross", prog([H_FILE], FIELD)),      # must NOT flip
    ("setA",       prog(UNNAMED[:7], FIELD)),
    ("setB",       prog(UNNAMED[7:], FIELD)),
]
ROUND2 = [("ctrl_none", prog([], FIELD))] + \
         [("$%04X" % a, prog([a], FIELD)) for a in UNNAMED[:7]]
# ROUND 2 ANSWERED IT: $FE2B and ONLY $FE2B flips FIELD. The other six read 59,
# the control read 59, so the slot is FIELD's and nothing else in that half
# matters.
H_FIELD = 0xFE2B

# ROUND 3 -- `LSET` and `RSET` have the SAME diskless hole (the diskless VG-8020
# answers ERR 5, this tree and the CF-3300 both RUN them), so they need slots too.
# 🔴 `GET` and `PUT` DO NOT: all three machines answer 59, so there is nothing
# to gate and no slot to look for. Measuring that first is what keeps this round
# to two verbs instead of five.
# ⚠️ `MERGE` IS NOT MEASURABLE WITH THIS INSTRUMENT AT ALL -- it merges into the
# RUNNING PROGRAM, so it destroys the probe that asks the question; the VG-8020
# cell came back with no fence. That is an apparatus limit, not a reading.
LSET = 'LSET A$="X"'
REST = [a for a in UNNAMED if a != H_FIELD]
ROUND3 = [("ctrl_none", prog([], LSET))] + \
         [("$%04X" % a, prog([a], LSET)) for a in REST]
# ROUND 3 ANSWERED IT: $FE21 and only $FE21 flips LSET.
H_LSET = 0xFE21

# ROUND 4 -- RSET. ⚠️ $FE26 is the cell right after LSET's and the obvious
# guess; it is asked here ALONGSIDE every other remaining candidate rather than
# on its own, because a guess that happens to be right still has not excluded
# anything.
RSET = 'RSET A$="X"'
REST2 = [a for a in UNNAMED if a not in (H_FIELD, H_LSET)]
ROUND4 = [("ctrl_none", prog([], RSET))] + \
         [("$%04X" % a, prog([a], RSET)) for a in REST2]
CASES = (ROUND4 if "--round4" in sys.argv else
         ROUND3 if "--round3" in sys.argv else
         ROUND2 if "--round2" in sys.argv else ROUND1)


def read(raw):
    t = " ".join("".join(raw or "").split())
    r = t.rfind("RUN")                          # the fence is in the LISTING too
    tail = t[r + 3:] if r >= 0 else t
    i = tail.find("<")
    j = tail.find(">", i + 1) if i >= 0 else -1
    return tail[i:j + 1] if i >= 0 and j > i else "?" + tail[:50]


def main() -> int:
    raws = omsx_repl.run_cases(REF, [("stored", l) for _, l in CASES],
                               batch=False, cap_gap=8.0, **REF_KW)
    for (name, lines), raw in zip(CASES, raws):
        print(f"  {name:11} {read(raw)!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
