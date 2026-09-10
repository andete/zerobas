#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-OPEN2 rig — a breakpoint on fch_ctx_addr with a RAM dump at every hit.

docs/spec-basic-open2.md §3c located the spurious ERR 2 of a second concurrent
disk OPEN to fch_save_active's surviving part, fch_ctx_addr (the strheap tenant's
op 18, "channel block address"), and named the next measurement itself: *"a
breakpoint on the second fch_ctx_addr with a register/RAM dump"*. This is that
rig: openMSX Tcl `debug probe set_bp` on the routine's address (from the reloc
sym, never typed), logging FCH_ACTIVE / MAXF / SH_LEN / SH_PTR / SH_ERR / the
pool floor cells and the Z80 registers at each hit, for a program that opens two
disk channels and traps the error.
"""
from __future__ import annotations
import os, re, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)   # chokepoint ROOT rule: never a hardcoded path
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402

def sym(name):
    for line in open(os.path.join(REPO, "build", "basic-reloc.sym"), encoding="utf-8", errors="replace"):
        m = re.match(rf"{name}\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if m: return int(m.group(1), 16)
    raise SystemExit(f"no symbol {name}")

CELLS = {"FCH_ACTIVE": 0xE012, "MAXF": 0xE011, "SH_OP": 0xE36D, "POOLSIZE": 0xE232}
PROG = ["10 ON ERROR GOTO 90", "15 MAXFILES=2",
        '20 OPEN"TEST.BIN"AS #1 LEN=128', '25 OPEN"PROG.BIN"AS #2 LEN=128',
        '30 PRINT"[O2 OK]":END', '90 PRINT"[O2 ERR";ERR;"AT";ERL;"]":END', "RUN"]

def main() -> int:
    bp = sym("fch_ctx_addr"); log = probe_tmp.tmp("open2_rig.log")
    cells = " ".join(f"{k}=[debug read memory 0x{v:04X}]" for k, v in CELLS.items())
    prologue = (
        f'set ::f [open "{log}" w]\n'
        f'debug set_bp 0x{bp:04X} {{}} {{\n'      # an ADDRESS breakpoint: the per-instruction probe with a PC condition ran ~1000x slower and the stall watchdog killed the boot
        f'  puts $::f "hit PC=[format %04X [reg PC]] A=[reg A] E=[reg E] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] SP=[format %04X [reg SP]] {cells}"\n'
        f'  flush $::f }}\n')
    cfg = probe_sides.sides("zb")["zb"]
    dsk = probe_tmp.tmp("open2_rig.dsk"); shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    cap = omsx_repl.run_cases(cfg["machine"], [("o2", PROG)], batch=False, boot=cfg["boot"],
                              reset=cfg["reset"], diska=dsk, prologue=(prologue,), run_gap=30.0)[0] or ""
    i = cap.rfind("[O2"); j = cap.find("]", i + 1)
    print("face:", cap[i:j + 1] if i >= 0 and j > 0 else "<NO FENCE> " + cap[-120:])
    print("=== hits on fch_ctx_addr:")
    try:
        for line in open(log, encoding="utf-8"): print("  " + line.rstrip())
    except OSError:
        print("  (no log -- the breakpoint never fired, or the prologue did not run)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
