#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""loadtail-acceptance (D-LOADTAIL) -- a LOAD / RUN whose option is not one
the verb takes is a TRAPPABLE Syntax error, on disk and on cassette.

`10 REM` + `20 ON ERROR GOTO 90` + `30 <stmt>`; the handler prints
`[E <ERR> <ERL>]`, a statement that returns prints `[OK]`.

  disk_lq    LOAD "X.BAS",Q        CF-3300: 2 in 30
  disk_ls    LOAD "X.BAS",S        CF-3300: measured here first
  disk_runq  RUN "A",5             CF-3300: 2 in 30
  disk_lrmiss LOAD "NOSUCH.BAS",R  the control: 53 in 30 on both
  cas_lq     LOAD "CAS:X",Q        VG-8020 (diskless): 2 in 30
  cas_runq   RUN "CAS:X",5         VG-8020: 2 in 30

Fresh boot (and disk copy) per row. Exit 0 all agree; 1 a divergence; 2 a
reference gave no reading.

    python3 -u probes/disk/disk_probe_loadtail.py [case ...]
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
TAPE = ("Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = {"disk_lq": (DISK, 'LOAD "X.BAS",Q'), "disk_ls": (DISK, 'LOAD "X.BAS",S'),
         "disk_runq": (DISK, 'RUN "A",5'), "disk_lrmiss": (DISK, 'LOAD "NOSUCH.BAS",R'),
         "cas_lq": (TAPE, 'LOAD "CAS:X",Q'), "cas_runq": (TAPE, 'RUN "CAS:X",5')}


def reading(machine, arg, disk):
    prog = ["NEW", "10 REM", "20 ON ERROR GOTO 90", f"30 {arg}", '40 PRINT"[OK]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    kw = dict(reset=("CLS",))
    if disk:
        dsk = probe_tmp.tmp(f"loadtail_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    m = re.findall(r"\[(OK|E[^\]]*)\]", scr)
    if m:
        return " ".join(m[-1].split())
    # a LOAD that completes inside a program returns to the PROMPT
    return "ENDED" if re.search(r"\bRUN (Ok|ZB)\b", scr) else None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, ((ref, ours), arg) in CASES.items():
        if only and case not in only:
            continue
        disk = ref.startswith("National")
        r, z = reading(ref, arg, disk), reading(ours, arg, disk)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:8} {ref[:12]:12} {r!r:12} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: LOAD / RUN's option tail as on the references ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
