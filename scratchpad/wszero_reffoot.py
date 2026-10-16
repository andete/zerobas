#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO after S13's refusal (Joost, 2026-10-16: "investigate what the
references do"): WHERE does the VG-8020 keep the state of the jobs zerobas's last
window cells do? scratchpad/ramfoot_probe.py's instrument (a write watch over
$E001-$FFFF inside a POKE-marked window; stack writes classified away; the
background and the interrupt's own cells removed; RAM addresses and SP only -- no
ROM byte, no PC), with cases for the string-heap tenant's parameter block SH_*
(concatenation, MID$ as function and statement, INSTR, STRING$, SPACE$, RIGHT$,
CHR$, VAL, a string compare, the string GC) and WSRC_TYP (mixed-type widening).
For each case it prints EVERY published cell ($F380 up) each machine writes, so a
same-job home can be read off the reference's own row.
PREDICTED, before the run: the reference's string ops write DSCTMP ($F698),
TEMPPT ($F678) / TEMPST ($F67A..), FRETOP ($F69B) and DAC ($F7F6..); the mixed
op writes DAC / ARG and VALTYP ($F663).
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import ramfoot_probe as RF                                  # noqa: E402

RF.ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
RF.CASES = [
    ("ctl", ""), ("pos", "POKE&HE001,7"),
    ("isr", "X7=TIME:FOR J7=1 TO 2:J7=1-(TIME<>X7):NEXT"),
    ("cat", 'A$="AB":B$=A$+"CD"'),
    ("mid", 'A$=MID$("ABCDE",2,2)'),
    ("midst", 'A$="ABCDE":MID$(A$,2)="XY"'),
    ("instr", 'X=INSTR("ABCD","C")'),
    ("string", "A$=STRING$(5,65)"),
    ("space", "A$=SPACE$(3)"),
    ("right", 'A$=RIGHT$("ABC",1)'),
    ("chr", "A$=CHR$(65)"),
    ("val", 'X=VAL("12.5")'),
    ("strcmp", 'X=("AB"<"AC")'),
    ("gc", 'X=FRE("")'),
    ("mixint", "A%=2:X=A%+1.5"),
    ("mixdbl", "A#=1#:B=A#*2"),
]


def main():
    nm = RF.names()
    res = {"ref": RF.run(RF.REF, 8.0), "zb": RF.run(RF.ZB, 8.0)}
    keys = [k for k, _ in RF.CASES]
    for side, r in res.items():
        if sorted(r) != list(range(len(RF.CASES))):
            print(f"REFUSE: {side} tagged windows {sorted(r)}")
            return 2
        if RF.MARK + 1 not in r[keys.index("pos")]["cells"]:
            print(f"REFUSE: {side}: the positive control saw nothing")
            return 2
    ctl = {s: RF.split_stack(res[s][0])[0] for s in res}
    isr = {}
    for s in res:
        w = res[s][keys.index("isr")]
        if not w.get("ticks"):
            print(f"REFUSE: {s}: the isr control saw no interrupt")
            return 2
        isr[s] = RF.isr_cells(w, RF.split_stack(w)[0])
    for i, (k, op) in enumerate(RF.CASES):
        if k in ("ctl", "pos", "isr"):
            continue
        print(f"=== {k}: {op}")
        for s in res:
            win = res[s][i]
            if not win.get("closed"):
                print(f"  {s}: UNCLOSED")
                continue
            c = RF.split_stack(win)[0] - ctl[s] - isr[s]
            print(f"  {s} std  : {RF.fmt({a for a in c if a >= RF.STD}, nm)}")
            print(f"  {s} below: {RF.fmt({a for a in c if a < RF.STD}, nm)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
