#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S10.0: is PARM1's unattributed tail $F71C-$F74B written by anything?

S10 moves zerobas's persistent diskless cells into those 48 bytes (TODO D-WSZERO).
No name covers them in any sym file or in C-BIOS's sources, which is static
evidence only. This runs probes/basic/basic_probe_ramfree.py's own instrument --
fill the span with an offset-keyed pattern, run one workout, count the bytes that
changed -- over ONLY that span, with its rows plus the ones that touch S10's
neighbours and users: a 9-parameter double DEF FN (the reference builds FN
parameter blocks in PARM1 -- its positive control), arrays, an error, ON
INTERVAL, a CRT: channel, a tape BLOAD and SWAP.

    python3 -u scratchpad/s10_parm1_fill.py MACHINE [ROW-SUBSTRING]

MACHINE: C-BIOS_MSX1_EU_REPACK_NODISK / C-BIOS_MSX1_EU_REPACK_DISK /
Philips_VG_8020. ctl.pool reads zerobas's own CTLTOP and is dropped on the
VG-8020; s.files needs the disk and runs only on the disk machine.
PREDICTED, before the run: zerobas reads 0 on every row on both machines,
ctl.poke reads 1; the VG-8020 reads 0 everywhere except n.fn9.
"""
import os, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "basic"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import basic_probe_ramfree as RF                           # noqa: E402
import omsx_repl                                           # noqa: E402
from cas_encode import build_cas                           # noqa: E402

MACHINE = sys.argv[1]
ONLY = sys.argv[2] if len(sys.argv) > 2 else None
RF.ZB_M = MACHINE
RF.declared_spans = lambda: [(0xF71C, 0xF74C)]
EXTRA = [
    ("n.fn9", ["DEFFNA#(A#,B#,C#,D#,E#,F#,G#,H#,I#)=A#+I#",
               "X#=FNA#(1,2,3,4,5,6,7,8,9):DEFFNB(X)=FNA#(X,X,X,X,X,X,X,X,X):Y=FNB(2)"], 120.0, 0, 0, "0"),
    ("n.arr", ["DIM Z(20,3):Z(20,3)=5:X=Z(20,3):ERASE Z"], 90.0, 0, 0, "0"),
    ("n.err", ["ERROR 2"], 90.0, 0, 1, "0"),
    ("n.trap", ["ON INTERVAL=1 GOSUB 1000:INTERVAL ON", "Q8=Q8+1:IF Q8<300 THEN {SELF}",
                "INTERVAL OFF"], 150.0, 0, 0, "0"),
    ("n.chan", ['OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"x":CLOSE'], 90.0, 0, 0, "0"),
    ("n.tape", ['BLOAD"CAS:",R'], 150.0, 0, 0, "0"),
    ("n.swap", ["A=1:B=2:SWAP A,B:DIM V(3):SWAP V(1),V(2)"], 90.0, 0, 0, "0"),
]
rows = RF.CASES + EXTRA
if MACHINE == "Philips_VG_8020":
    rows = [r for r in rows if r[0] != "ctl.pool"]
if "DISK" not in MACHINE or "NODISK" in MACHINE:
    rows = [r for r in rows if r[0] != "s.files"]
RF.CASES = rows
cas = os.path.join(tempfile.mkdtemp(prefix="s10fill_"), "t.cas")
open(cas, "wb").write(build_cas("W", 0xC000, 0xC000, b"\xC9" + b"\xA5" * 255))
_run = omsx_repl.run_cases
omsx_repl.run_cases = lambda m, cases, **kw: _run(m, cases, cassette=cas, **kw)
print(f"machine {MACHINE}")
sys.argv = [sys.argv[0]] + (["--only", ONLY] if ONLY else [])
sys.exit(RF.main())
