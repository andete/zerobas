#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S10: move the persistent diskless cells into PARM1's tail $F71C-$F73F.
Anchored on each equate's NAME, refuses unless the old value matches exactly once."""
import re, sys
p = "basic/sysvars.inc"
L = open(p).read().split("\n")
MOVES = [("FCH_ACTIVE", "$EEBE", "$F733"), ("FCH_MODES", "$EE3D", "$F71C"),
         ("DIRECTF", "$EFC1", "$F73C"), ("ERRRESUME", "$EFC4", "$F73E"),
         ("ARL_GETBYTE", "$EF3B", "$F72E"), ("CAS_BUFP", "$EFF5", "$F730"),
         ("CONTVALID", "$EF41", "$F736"), ("CAL_CNT", "$EF56", "$F737"),
         ("CAL_NEEDFILL", "$EF57", "$F738"), ("CAL_SAVE", "$EF58", "$F739"),
         ("CAS_WCNT", "$EF58", "$F739"), ("FCH_NUM", "$EF64", "$F73A"),
         ("FCH_MODE", "$EF65", "$F73B"), ("RL_AUTO", "$EE75", "$F732"),
         ("CSR_ADDR", "$EEEA", "$F72C"), ("CSR_CHAR", "$EEEC", "$F734"),
         ("CSR_ON", "$EEED", "$F735"), ("PRMWANT", "$F0AA", "$F73D")]
for name, old, new in MOVES:
    hits = [i for i, l in enumerate(L) if re.match(rf"{name}\s+equ\s+", l)]
    if len(hits) != 1:
        sys.exit(f"anchor {name}: {len(hits)} hits")
    i = hits[0]
    m = re.match(rf"({name}\s+equ\s+)(\S+)(.*)$", L[i])
    if m.group(2) != old:
        sys.exit(f"{name}: value {m.group(2)} != {old}")
    L[i] = m.group(1) + new + m.group(3)
    if name == "FCH_MODES":
        L[i] = L[i].replace("($EE3D..$EE4C)", "($F71C..$F72B)")
    L.insert(i + 1, "                                ; D-WSZERO S10: PARM1's unattributed tail (was " + old + ")")
s = "\n".join(L)
a = "SL_CEIL         equ     $F71A   ; store_line: the ceiling a store stays below (2 B)\n"
if s.count(a) != 1:
    sys.exit("SL_CEIL anchor")
s = s.replace(a, a + """; 🏗️ D-WSZERO S10 (2026-10-15): $F71C..$F73F is the PERSISTENT diskless set --
; FCH_MODES, CSR_*, ARL_GETBYTE, CAS_BUFP, RL_AUTO, FCH_ACTIVE, CONTVALID, CAL_*,
; FCH_NUM / FCH_MODE, DIRECTF, PRMWANT, ERRRESUME -- the cells a loader's NEXT
; statements read after a load over $ECF8..$F37F. PARM1's tail: the reference
; writes it only during a DEF FN call (46 B under a 9-parameter double FN, 0 under
; every other workout; zerobas never, its FN frame is at $F74C up --
; scratchpad/s10_parm1_fill_*.out). RULE: only state zerobas keeps between
; statements goes here; transient scratch would collide with nothing today but
; is what the reference's own use of the block looks like.
; FREE-RAM $F740..$F74C  PARM1's last 12 B, idle (D-WSZERO S10)
""")
open(p, "w").write(s)
w = "tools/ram-width-allow.txt"
t = open(w).read()
for line in ("basic CAL_CNT overruns\n", "basic CAL_SAVE/CAS_WCNT disputed\n"):
    if t.count(line) != 1:
        sys.exit(f"allow: {line!r}")
    t = t.replace(line, "")
open(w, "w").write(t)
print("ok", len(MOVES))
