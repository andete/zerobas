#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PAINTRAMCLASH, STRPTR (Joost 2026-11-20: "use the cells the reference uses"): where does each machine keep the
pointer to the current string result's descriptor? zerobas: STRPTR ($F954). The Microsoft-BASIC answer would be DAC+2
($F7F8, VALTYP 3). Black box: one string assignment per case, then the program loops and $F380-$FFFF is read by the
debugger; then, for each case, which 2-byte cells hold an address that points AT a descriptor [len][addr] whose len
is the result's length and whose addr points at the result's bytes. No ROM byte is read.
    python3 -u scratchpad/strptr_probe.py > scratchpad/STRPTR_run1.out"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

CASES = {"cat":   ('A$="AB"+"CDE"', b"ABCDE"),
         "left":  ('A$=LEFT$("WXYZQ",3)', b"WXY"),
         "lit":   ('A$="HELLO!"', b"HELLO!"),
         "chr":   ('A$=CHR$(65)+CHR$(66)+CHR$(67)+CHR$(68)', b"ABCD")}
BASE, LEN = 0x8000, 0x10000 - 0x8000 - 1           # strings live below $F380: dump from $8000
for side in sys.argv[1:] or ("vg8020", "cf3300", "zb"):
    m = probe_sides.MACHINES[side]
    for name, (stmt, want) in CASES.items():
        prog = ["10 " + stmt, "20 GOTO 20", "RUN"]   # nothing numeric after it: DAC stays the string's
        h = omsx_repl.run_batch(m["machine"], [("direct", prog)], boot=m["boot"], reset=m["reset"],
                                capture=("mem_abs", [(BASE, LEN)]))[0] or ""
        if len(h) != 2 * LEN:
            print(f"{side:7} {name:5} <no dump>")
            continue
        mem = bytes.fromhex(h)
        rd = lambda a: mem[a - BASE] if BASE <= a < BASE + LEN else None
        rw = lambda a: (rd(a) | (rd(a + 1) << 8)) if rd(a) is not None and rd(a + 1) is not None else None
        hits = []
        for c in range(0xF380, 0xFFFE):              # a work-area cell pointing at a matching descriptor
            d = rw(c)
            if d is None or rd(d) != len(want):
                continue
            s = rw(d + 1)
            if s is not None and all(rd(s + i) == want[i] for i in range(len(want))):
                hits.append(f"${c:04X}->${d:04X}")
        print(f"{side:7} {name:5} {' '.join(hits) if hits else '-'}")
