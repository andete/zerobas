#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-PAINTRAMCLASH (Joost 2026-11-20: "use the reference's own cells"): WHERE does each machine keep OUTDLP's held
$01 -- a graphic character's header to a printer that is not an MSX one (NTMSXP $F417 not 0), held back for the next
byte (docs/bios/OUTDLP.md R-OD-PRN)? zerobas keeps it in GRP_HDR bit 1. Black box: NTMSXP := 1, then a USR stub
`ld a,1 / call $014D / ret` (OUTDLP with $01: held, nothing sent, so no printer is needed), or not; two program
lengths each. The program then loops and $F380-$FFFF is read by the debugger. A cell that differs in BOTH held cases
from BOTH others is a candidate. No ROM byte is read.
    python3 -u scratchpad/outdlphold_probe.py > scratchpad/OUTDLPHOLD_run1.out"""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl, probe_sides  # noqa: E402

STUB = "FOR I=0 TO 5:POKE &HD000+I,VAL(\"&H\"+MID$(\"3E01CD4D01C9\",2*I+1,2)):NEXT:DEFUSR=&HD000:POKE &HF417,1"
CASES = {"none": STUB, "none2": STUB + ":Z=1:Z=2:Z=3",
         "held": STUB + ":X=USR(0)", "held2": STUB + ":Z=1:Z=2:Z=3:X=USR(0)"}
BASE, LEN = 0xF380, 0x10000 - 0xF380 - 1
for side in sys.argv[1:] or ("vg8020", "cf3300", "zb"):
    m = probe_sides.MACHINES[side]
    d = {}
    for name, line in CASES.items():
        prog = ["10 " + line, "20 GOTO 20", "RUN"]
        h = omsx_repl.run_batch(m["machine"], [("direct", prog)], boot=m["boot"], reset=m["reset"],
                                capture=("mem_abs", [(BASE, LEN)]))[0] or ""
        d[name] = bytes.fromhex(h) if len(h) == 2 * LEN else None
        print(f"{side:7} {name:6} {'ok' if d[name] else '<no dump>'}")
    if not all(d.values()):
        continue
    for i in range(LEN):
        h1, h2, n1, n2 = d["held"][i], d["held2"][i], d["none"][i], d["none2"][i]
        if h1 not in (n1, n2) and h2 not in (n1, n2):
            print(f"  ${BASE + i:04X}: held {h1:02X} held2 {h2:02X} none {n1:02X} none2 {n2:02X}")
