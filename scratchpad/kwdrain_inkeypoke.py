#!/usr/bin/env python3
"""🔬 RE-VERIFYING THE LAST BLOCKER ON THE DRAIN. `INKEY$` is filed as needing a
HARNESS change: a key must arrive after the machine consumes `RUN` and before the
statement reads it, and that moment is computed inside `run_cases` from `boot` +
per-line `step`, which a row cannot see — with the D-LATCH/D-LATCH2 races as the
thing such a change must not reopen.

But a key does not have to be TYPED to be waiting. The BIOS type-ahead buffer is
ordinary MSX work area — KEYBUF $FBF0 with the GETPNT/PUTPNT cursors, empty when
equal — and BASIC can POKE it. If a program stuffs one character and then reads
`INKEY$`, the answer is a real keystroke with NO injector timing anywhere.

⚠️ IT MUST BE A STORED PROGRAM, not typed lines: in direct mode the harness
delivers the NEXT line through that very buffer, which would overwrite the
stuffed character and move the cursors. During RUN nothing competes for it.
"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides

PROG = ['10 POKE&HFBF0,65',
        '20 POKE&HF3FA,&HF0:POKE&HF3FB,&HFB',   # GETPNT = $FBF0
        '30 POKE&HF3F8,&HF1:POKE&HF3F9,&HFB',   # PUTPNT = $FBF0+1 -> one key waiting
        '40 A$=INKEY$:PRINT"[";A$;LEN(A$);"]"',
        'RUN']

for side in ("vg8020", "zb"):
    cfg = probe_sides.sides(side)[side]
    caps = omsx_repl.run_cases(cfg["machine"], [("d", list(cfg["reset"]) + PROG)],
                               batch=False, reset=(), boot=cfg["boot"], step=1.0,
                               cap_gap=6.0, timeout=600.0)
    cap = caps[0]
    rows = [cap[r*40:(r+1)*40].rstrip() for r in range(24)] if cap else []
    rows = [r.strip() for r in rows if r.strip()]
    print("%-8s %s" % (side, " | ".join(rows[-4:])))
    sys.stdout.flush()
print()
print("READ IT AS: `[A 1 ]` => a real keystroke reached INKEY$ with no injector")
print("timing at all, and the row is a plain stored row. `[ 0 ]` => the buffer")
print("poke does not reach INKEY$ and the filed harness change stands.")
