#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FDCMASKED: no FDC operation of a BASIC disk program starts with interrupts masked.

WHY: a hook reaches the disk ROM through an inter-slot call with interrupts OFF. One
that forgot its `ei` (hk_ochk / hk_srcfind until D-FWDWIN, 2026-11-12) ran every FDC
read it made fully masked: 9 of 66 sector operations in L5_files, frame-interrupt gaps
up to 0.139 s (scratchpad/FW5_stack.out -> FW7_stack_ei.out). programs-acceptance's
gap rule sees that only when a gap grows past the reference's; this counts it at the
source. fdc_di_save records the caller's state, so a masked caller here is a masked
transfer.

INSTRUMENT: a PC breakpoint at OUR disk ROM's fdc_di_save (address from build/disk.sym,
slot 3 only) reads the CPU's IFF register at entry -- our own code's address and a CPU
register, nothing of any reference ROM. Each `# @DISK` program of probes/programs runs
on the DISK target through run_programs' own harness (fresh disk image, KEYBUF input).

PASS: every program ENDED, and has at least one fdc_di_save entry (a program that
reached no FDC operation tests nothing -- refused, not passed), and none with IFF 0.

    ZEROBAS_BASIC_MACHINE=... python3 -u probes/disk/disk_probe_fdcmasked.py [PROG ...]
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs as r  # noqa: E402
import probe_tmp  # noqa: E402

MACHINE = os.environ.get("ZEROBAS_BASIC_MACHINE", r.DISK_ZB[0])


def disk_programs():
    d = os.path.join(REPO, "probes", "programs")
    return sorted(f[:-4] for f in os.listdir(d)
                  if f.endswith(".bas") and r.needs_disk(open(os.path.join(d, f)).read()))


def fdc_di_save_addr():
    for line in open(os.path.join(REPO, "build", "disk.sym")):
        p = line.split()
        if len(p) >= 3 and p[0] == "fdc_di_save":
            return int(p[2].rstrip("H"), 16)
    raise SystemExit("fdc_di_save is not in build/disk.sym -- build first")


def run_one(name, addr):
    dump = probe_tmp.tmp(f"fdcmasked_{name}.txt")
    if os.path.exists(dump):
        os.unlink(dump)
    base = r.GAP_TCL
    r.GAP_TCL = base + """
set ::__km [open {%s} w]
proc __fkm {} { puts $::__km "[format %%.4f [machine_info time]] K iff=[reg iff]"; flush $::__km }
debug set_bp 0x%04X {[pc_in_slot 3]} __fkm
""" % (dump, addr)
    try:
        text = open(os.path.join(REPO, "probes", "programs", name + ".bas")).read()
        status, _lpt, _rows = r.run(MACHINE, "fdcmasked_" + name, text, gaps=True)
    finally:
        r.GAP_TCL = base
    rows = open(dump).read().splitlines() if os.path.exists(dump) else []
    k = [x for x in rows if " K iff=" in x]
    masked = [x for x in k if x.split("iff=")[1].strip() in ("0", "00")]
    return status, k, masked


def main():
    names = sys.argv[1:] or disk_programs()
    if not names:
        print("FAIL: no `# @DISK` program in probes/programs -- nothing to measure")
        return 1
    addr = fdc_di_save_addr()
    print(f"fdc_di_save at ${addr:04X}; machine {MACHINE}; programs {' '.join(names)}")
    bad = 0
    for name in names:
        status, k, masked = run_one(name, addr)
        verdict = "ok"
        if not status.startswith("ENDED"):
            verdict = "DID NOT END"
        elif not k:
            verdict = "NO FDC ENTRY (refused: measures nothing)"
        elif masked:
            verdict = "MASKED"
        print(f"  {name:12} {status.split()[0] if status else '?':10} "
              f"fdc_di_save entries {len(k):4}  masked {len(masked):3}  {verdict}")
        for x in masked[:5]:
            print(f"      {x}")
        bad += verdict != "ok"
    if bad:
        print(f"FAIL: {bad} program(s) ran an FDC operation masked, or measured nothing")
        return 1
    print("PASS: every FDC operation of every disk program started with interrupts on")
    return 0


if __name__ == "__main__":
    sys.exit(main())
