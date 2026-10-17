#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-GOSUBOOM -- a GOSUB near the memory edge, and what a trapped overflow leaves.

WHY THIS EXISTS. Head over Heels lowers HIMEM with its own CLEAR and then GOSUBs
with ~671 B free; zerobas answered `Out of memory`, because it kept 768 B clear
below every control frame (CTL_FRAME_MARGIN, D-STACKFLOOR). The VG-8020 refuses a
frame only with ~130 B left. The 768 existed so a program could go on evaluating
with every frame still standing after a TRAPPED overflow -- and the reference does
not keep them standing: it EMPTIES its stack on that overflow (scratchpad/
gosubedge_probe.out). zerobas now does too, and the margin is 256.

Each row is a program; the VG-8020's printed lines are the oracle, compared as text:
  edge   CLEAR 200,&H97FF, a DIM sized to leave ~650 B of FRE(0), then GOSUB:
         the reference returns; 768 refused it (Head over Heels' shape)
  ret    a trapped GOSUB recursion overflow, then RETURN in the handler:
         `RETURN without GOSUB` on the reference (the frames are gone); zerobas
         looped for ever when they stood
  one    a trapped ERROR inside ONE GOSUB, RESUME, RETURN: the frame is KEPT on
         both (only the out-of-memory overflow empties the stack)
  for    the same overflow by FOR nesting in a recursion: ERR 7, and NEXT in the
         handler finds no FOR (`NEXT without FOR`). ⚠️ NOT a witness for the
         emptying: the overflow lands on a GOSUB push, so the newest frame is a
         GOSUB and NEXT answers the same whether the frames below stand or not
         (knife K-GO2 left it SAME, scratchpad/gosuboom_knife.out); `ret` is.

    python3 -u probes/basic/basic_probe_gosuboom.py [--gate] [--only ROW]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import omsx_repl  # noqa: E402

VG = "Philips_VG_8020"
ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"

ROWS = {
    "edge": ["NEW", "10 CLEAR 200,&H97FF:N=INT((FRE(0)-650)/8):DIM A(N)",
             '20 GOSUB 100:PRINT"[OK]":END', "100 RETURN", "RUN"],
    "ret": ["NEW", "10 CLEAR 200:ON ERROR GOTO 100:D=0", "20 D=D+1:GOSUB 20",
            '100 PRINT"[R";ERR;"]":RETURN', "RUN"],
    "one": ["NEW", "10 ON ERROR GOTO 100", '20 GOSUB 50:PRINT"[BACK]":END', "50 ERROR 5",
            "60 RETURN", "100 RESUME 60", "RUN"],
    "for": ["NEW", "10 CLEAR 200:ON ERROR GOTO 100:D=0", "20 D=D+1:FOR I=1 TO 2:GOSUB 20",
            '100 PRINT"[F";ERR;"]":NEXT', "RUN"],
}


def read(machine, prog):
    scr = omsx_repl.run_cases(machine, [("direct", prog)], batch=False,
                              reset=("", "SCREEN 0:WIDTH 40"), step=3.0, run_gap=60.0)[0]
    # 30 -> 60 s (2026-10-17): with the 7-byte GOSUB frame `ret` recurses to ~4070
    # frames before Out of memory, and zerobas had not printed by 30 s (an empty
    # reading, not a divergence: scratchpad/gosubedge_7b.out reads it at 60 s).
    if not scr:
        return None
    lines = [scr[i:i + 40].strip() for i in range(0, len(scr), 40)]
    return " | ".join(x for x in lines
                      if x.startswith("[") or "rror" in x or "without" in x or "memory" in x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", action="store_true")
    ap.add_argument("--only")
    args = ap.parse_args()
    bad, blind = [], []
    for name, prog in ROWS.items():
        if args.only and args.only != name:
            continue
        vg, zb = read(VG, prog), read(ZB, prog)
        if not vg:
            blind.append(name)
        verdict = "SAME" if vg and vg == zb else "DIVERGES"
        if vg and vg != zb:
            bad.append(name)
        print(f"ROW {name:5} VG=[{vg}] ZB=[{zb}] {verdict}", flush=True)
    if blind:
        print(f"INSTRUMENT FAULT: no VG-8020 reading on {blind}")
        return 2
    print("PASS" if not bad else f"FAIL: {bad}")
    return 1 if bad and args.gate else 0


if __name__ == "__main__":
    sys.exit(main())
