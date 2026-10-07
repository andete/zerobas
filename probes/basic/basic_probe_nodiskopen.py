#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""nodiskopen-acceptance (D-NODISKOPEN) -- on a DISKLESS machine a device-less
OPEN name is the cassette's, and the cassette's unsupported forms are refused
as the VG-8020 refuses them.

`10 REM` + `20 ON ERROR GOTO 90` + `30 <stmt>`; the handler prints `[E <ERR>
<ERL>]`, a statement that returns prints `[OK]`. Fresh boot per row, no tape.

  out       OPEN "X" FOR OUTPUT AS #1:PRINT #1,"A":CLOSE    VG-8020: no error
  two       OPEN "X" FOR OUTPUT AS #1:OPEN "CAS:Y" FOR OUTPUT AS #2
            -- the DISCRIMINATOR: if "X" is the cassette, this answers exactly
            as `twocas` does
  twocas    OPEN "CAS:X" FOR OUTPUT AS #1:OPEN "CAS:Y" FOR OUTPUT AS #2
  rand      OPEN "X" AS #1                                   VG-8020: 56
  casrand   OPEN "CAS:X" AS #1
  casapp    OPEN "CAS:X" FOR APPEND AS #1
  app       OPEN "X" FOR APPEND AS #1
  drive     OPEN "A:X" FOR OUTPUT AS #1    a drive name on a machine with no drive
  casfoo    OPEN "CAS:X" FOR FOO AS #1     separates "APPEND is 56" from "anything
                                           but INPUT/OUTPUT after FOR is 56"
  casjunk   OPEN "CAS:X" FOO               separates "no FOR is 56" from "only AS
                                           is 56"
  dcasrand  OPEN "CAS:X" AS #1             | the same two cassette refusals on the
  dcasapp   OPEN "CAS:X" FOR APPEND AS #1  | CF-3300 (the code serves both targets)

Exit 0 all agree; 1 a divergence; 2 a reference gave no reading.

    python3 -u probes/basic/basic_probe_nodiskopen.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

TAPE = ("Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK"))
DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
ON_DISK = {"dcasrand", "dcasapp"}      # the cassette's refusals on the DISK machine too
CASES = {
    "out": 'OPEN "X" FOR OUTPUT AS #1:PRINT #1,"A":CLOSE',
    "two": 'OPEN "X" FOR OUTPUT AS #1:OPEN "CAS:Y" FOR OUTPUT AS #2',
    "twocas": 'OPEN "CAS:X" FOR OUTPUT AS #1:OPEN "CAS:Y" FOR OUTPUT AS #2',
    "rand": 'OPEN "X" AS #1',
    "casrand": 'OPEN "CAS:X" AS #1',
    "casapp": 'OPEN "CAS:X" FOR APPEND AS #1',
    "app": 'OPEN "X" FOR APPEND AS #1',
    "drive": 'OPEN "A:X" FOR OUTPUT AS #1',
    "casfoo": 'OPEN "CAS:X" FOR FOO AS #1',
    "casjunk": 'OPEN "CAS:X" FOO',
    "dcasrand": 'OPEN "CAS:X" AS #1',
    "dcasapp": 'OPEN "CAS:X" FOR APPEND AS #1',
}


def reading(machine, stmt, disk=False):
    prog = ["NEW", "10 REM", "20 ON ERROR GOTO 90", f"30 {stmt}", '40 PRINT"[OK]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    kw = dict(reset=("CLS",))
    if disk:
        import shutil
        import probe_tmp
        dsk = probe_tmp.tmp(f"nodiskopen_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    m = re.findall(r"\[(OK|E[^\]]*)\]", scr)
    return " ".join(m[-1].split()) if m else None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, stmt in CASES.items():
        if only and case not in only:
            continue
        disk = case in ON_DISK
        ref, ours = DISK if disk else TAPE
        r, z = reading(ref, stmt, disk), reading(ours, stmt, disk)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:8} {r!r:12} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: a diskless OPEN as on the VG-8020 ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
