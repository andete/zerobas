#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PLAYXREC -- WHICH MECHANISM does the reference's `X<var>;` nesting use?

D-PLAYX2 walked chains out to 24 levels and found NO ceiling: that says the limit
is not small, not what it IS. `docs/spec-basic-audio-play.md` §7 picked a fixed
8-entry RAM table on that evidence, and the table is the WRONG SHAPE if the
reference recurses on the Z80 stack. This asks the machine, without reading a
byte of its ROM.

  A. SELF-REFERENCE. `A$="XA$;"` is unbounded depth in ONE variable.
       a specific error   -> a bounded structure of some kind
       `Out of memory` 7  -> the BASIC/Z80 STACK ran out
       nothing at all     -> no bound and no guard: it hangs
  B. STACK INTERACTION -- 🎯 THE ROW THAT ACTUALLY SEPARATES THEM, because a
     table and a stack can both end in an error. A chain of 6 that plays at top
     level is run again from inside 80 nested `GOSUB`s. Still plays => the two do
     not share. Raises => they do.

🔴 THE FIRST CUT OF THIS PROBE WAS BROKEN AND ITS OWN CONTROL SAID SO. Line
numbers were hand-counted from list positions, so `ON ERROR GOTO` and `GOSUB`
pointed at the wrong lines: the recursion body was skipped entirely and the B
rows read silence on BOTH the subject and the control. Targets are RESOLVED from
labels here -- `lines()` refuses a jump to a label that does not exist, which is
the failure the first cut could not have caught by inspection.
🔴 AND IT WAS BROKEN A SECOND TIME, BY A LABEL THAT RESOLVED PERFECTLY WELL. The
settle loop was `("w", "T=TIME") / "IF TIME-T<30 THEN @w"` -- so it jumped back to
`T=TIME` and re-read its own start time every iteration, never exiting. `lines()`
refuses an UNRESOLVED label and cannot notice one pointing at the line next door.
Every row that reached the settle hung; the one row that raised BEFORE it was the
only reading in the run, which is a good illustration of how a broken instrument
can still emit something that looks like data.
⚠️ AN EMPTY CAPTURE IS NOT A HANG. `<no reading>` means the window closed. The
self-reference row therefore gets a LONG window and a follow-up that asks whether
the machine is still alive afterwards.
"""
import sys, os
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = ("Philips_VG_8020",)


def lines(seq) -> list[str]:
    """`seq` is (label|None, text) with `@label` standing for that line's number.

    🔴 REFUSES an unresolved `@label`. The first cut of this probe hand-counted
    those numbers and silently pointed a GOSUB past its own loop body."""
    nums = {lab: 10 * (i + 1) for i, (lab, _) in enumerate(seq) if lab}
    out = []
    for i, (_, text) in enumerate(seq):
        for lab, n in nums.items():
            text = text.replace("@" + lab, str(n))
        if "@" in text:
            sys.exit(f"REFUSE: unresolved label in {text!r}; known {sorted(nums)}")
        assert len(text) <= 34, (len(text), text)
        out.append(f"{text}")
    return out


READ = [(None, 'PRINT"<";'), (None, "OUT&HA0,0:PRINT INP(&HA2);"),
        (None, "OUT&HA0,1:PRINT INP(&HA2);"), (None, 'PRINT">":END')]
CHAIN6 = [(None, 'A$="XB$;":B$="XC$;":C$="XD$;"'), (None, 'D$="XE$;":E$="XF$;"'),
          (None, 'F$="O7L1C"')]
ERRL = ("err", 'PRINT"<E";ERR;">":END')


def settle_and_read(head):
    return lines([(None, "ON ERROR GOTO @err")] + head +
                 [(None, "T=TIME"), ("w", "IF TIME-T<30 THEN @w")] + READ + [ERRL])


CASES = [
    # the plain note -- if this is not 53/0 nothing below means anything
    ("c0_ctl_note",   settle_and_read([(None, 'PLAY"O7L1C"')])),
    # one level of X, which TERMINATES: so "it errored" is not the only thing
    # the self-reference row could ever have produced
    ("c1_once",       settle_and_read([(None, 'A$="XB$;":B$="O7L1C"'),
                                       (None, 'PLAY"XA$;"')])),
    # A -- unbounded depth in one variable
    ("c2_selfref",    lines([(None, "ON ERROR GOTO @err"), (None, 'A$="XA$;"'),
                             (None, 'PLAY"XA$;"'),
                             (None, 'PRINT"<RETURNED>":END'), ERRL])),
    # ...and is the machine still alive after it?
    ("c3_alive",      lines([(None, "ON ERROR GOTO @err"), (None, 'A$="XA$;"'),
                             (None, 'PLAY"XA$;"'), (None, 'PRINT"<ALIVE>":END'),
                             ERRL])),
    # B -- the same chain at top level and 80 GOSUBs deep, each with its control
    ("c4_chain_top",  settle_and_read(CHAIN6 + [(None, 'PLAY"XA$;"')])),
    ("c5_chain_deep", lines([(None, "ON ERROR GOTO @err")] + CHAIN6 +
                            [(None, "K=0:GOSUB @rec"), (None, "T=TIME"),
                             ("w", "IF TIME-T<30 THEN @w")] + READ +
                            [ERRL, (None, "END"),
                             ("rec", "K=K+1:IF K<80 THEN GOSUB @rec"),
                             (None, 'IF K=80 THEN PLAY"XA$;"'),
                             (None, "RETURN")])),
    # the control for c5: the SAME 80 GOSUBs, the note played with NO X
    ("c9_ctl_deep",   lines([(None, "ON ERROR GOTO @err"), (None, "REM"),
                             (None, "REM"), (None, "REM"),
                             (None, "K=0:GOSUB @rec"), (None, "T=TIME"),
                             ("w", "IF TIME-T<30 THEN @w")] + READ +
                            [ERRL, (None, "END"),
                             ("rec", "K=K+1:IF K<80 THEN GOSUB @rec"),
                             (None, 'IF K=80 THEN PLAY"O7L1C"'),
                             (None, "RETURN")])),
]


def main() -> int:
    for mach in MACHINES:
        print("===", mach, flush=True)
        specs = [("stored", ls) for _, ls in CASES]
        raws = omsx_repl.run_cases(mach, specs, batch=False, cap_gap=25.0)
        for (name, _), raw in zip(CASES, raws):
            txt = " ".join("".join(raw or "").split())
            r = txt.rfind("RUN")
            tail = txt[r + 3:] if r >= 0 else txt
            i = tail.find("<")
            j = tail.find(">", i + 1)
            cell = (tail[i:j + 1] if i >= 0 and j > i
                    else "<no reading — the window closed, NOT proof of a hang>")
            print(f"  {name:14} {cell!r}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
