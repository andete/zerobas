#!/usr/bin/env python3
r"""D-PUTTIME — how long does a `PUT` actually take, and does the cost RISE?

D-PUT3SLOW (2026-09-02) withdrew the "third PUT hangs untrappably" claim: every
reading behind it was taken at a 2.5 s step, and at 5 s they all pass with the
correct answers. What it left owed is the number itself -- the cost was BOUNDED
(>2.5 s, <5 s for a three-write sequence) and never measured, and one question
was explicitly left open:

  ⚠️ "A CLAIM I AM NOT MAKING: that the third PUT is individually slower. 1 and
     2 pass at 2.5 s and 3 does not, but the harness types at fixed intervals,
     so three writes of ~2.4 s each overrun CUMULATIVELY with none of them
     growing. Flat-vs-rising is UNMEASURED."

🎯 `TIME` SETTLES IT FROM INSIDE THE MACHINE. It is the 50/60 Hz JIFFY counter,
so the emulator's own timeline is read directly and the harness's step drops out
of the measurement entirely -- the thing that produced the wrong answer for two
days is no longer in the loop. Deltas between consecutive reads give the cost of
each individual write.

🔴 PREDICTIONS:
  P1  On the CF-3300 the three deltas are roughly EQUAL -- rewriting one record
      is the same work every time. This is the control that makes any zb shape
      mean something.
  P2  On zerobas they are LARGER than the CF-3300's. Known from D-PUT3SLOW
      (zb needs >2.5 s where the reference needs <2.5 s), so a null here would
      mean the fixture is wrong, not that the defect vanished.
  P3  The open one: FLAT or RISING on zb. Rising implicates something that grows
      per write; flat means every PUT is simply expensive and "the third" was
      only ever the harness's cumulative overrun. D-PUT3SLOW refuted the one
      mechanism proposed for rising (no cluster leak: DSKF reads 706/706/706),
      so flat is the prediction -- and it is the one I have been wrong about
      before in this exact area.

⚠️ `TIME` IS A WORD AND WRAPS AT 65536 JIFFIES (~18 min at 60 Hz); nothing here
runs anywhere near that. Reads are taken into VARIABLES first and printed at the
END, so the PRINT itself is outside every interval being measured.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
for s in ("zb", "cf3300"):
    F.SIDES[s] = dict(F.SIDES[s], step=STEP)

OPEN = ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']

CASES = [
    # 🟢 CONTROL: the same four reads with NO PUT between them. Whatever this
    # prints is the floor -- the cost of TIME itself plus a bare statement --
    # and every subject delta must be read against it, not against zero.
    ("t.ctl",  "dsk", OPEN + ['TIME=0', 'A=TIME', 'B=TIME', 'C=TIME', 'D=TIME',
                              'PRINT"[";A;B;C;D;"]"']),
    # THE SUBJECT: one read before, and one after each of three writes.
    ("t.put3", "dsk", OPEN + ['TIME=0', 'A=TIME',
                              'PUT#1,1', 'B=TIME',
                              'PUT#1,1', 'C=TIME',
                              'PUT#1,1', 'D=TIME',
                              'PRINT"[";A;B;C;D;"]"']),
    # 🎯 AND A FOURTH AND FIFTH WRITE, because "rising" is a claim about a
    # SEQUENCE and three points is a thin sequence to fit a shape to.
    ("t.put5", "dsk", OPEN + ['TIME=0', 'A=TIME',
                              'PUT#1,1', 'B=TIME',
                              'PUT#1,1', 'C=TIME',
                              'PUT#1,1', 'D=TIME',
                              'PUT#1,1', 'E=TIME',
                              'PUT#1,1', 'F=TIME',
                              'PRINT"[";A;B;C;D;E;F;"]"']),
    # 🟢 CONTROL: a GET ladder. GETs are known fine at the default step, so if
    # these deltas are ALSO large the subject is "disk I/O", not "PUT".
    ("t.get3", "dsk", OPEN + ['PUT#1,1', 'TIME=0', 'A=TIME',
                              'GET#1,1', 'B=TIME',
                              'GET#1,1', 'C=TIME',
                              'GET#1,1', 'D=TIME',
                              'PRINT"[";A;B;C;D;"]"']),
    # 🔴 IS `TIME` EVEN ABLE TO SEE DISK WORK? MSX disk routines run with
    # INTERRUPTS DISABLED, and `TIME` counts VDP interrupts -- so jiffies
    # elapsed inside DSKIO are not merely uncounted, they never happen. If so
    # this whole probe measures everything EXCEPT the thing it was built for,
    # and the tiny numbers above are an artefact rather than a result.
    # The discriminator: a pure-CPU busy loop, interrupts ON, of a length that
    # obviously costs real time. If THAT shows many jiffies while three PUTs
    # show one or two, `TIME` is blind to disk I/O and no per-PUT number can be
    # read from it. [[apparatus-is-part-of-the-measurement]]
    ("v.cpu",  "dsk", OPEN + ['TIME=0', 'A=TIME',
                              'FOR I=1 TO 2000:NEXT', 'B=TIME',
                              'FOR I=1 TO 2000:NEXT', 'C=TIME',
                              'PRINT"[";A;B;C;"]"']),
    # and the same busy loop with a PUT in the middle, so both are on ONE
    # timeline and no cross-run comparison is needed.
    ("v.mix",  "dsk", OPEN + ['TIME=0', 'A=TIME',
                              'FOR I=1 TO 2000:NEXT', 'B=TIME',
                              'PUT#1,1', 'C=TIME',
                              'FOR I=1 TO 2000:NEXT', 'D=TIME',
                              'PRINT"[";A;B;C;D;"]"']),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\nstep={STEP}s   values are JIFFIES (60 Hz), cumulative from TIME=0")
print(f"{'row':<{w}}  " + "  ".join(f"{s:>30}" for s in sides))
for label, _, _ in CASES:
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>30}" for s in sides))
print("\nread: consecutive DIFFERENCES are the per-operation cost. Equal deltas\n"
      "      = flat; growing deltas = something grows per write.")
