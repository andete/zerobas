#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""nodiskverbs-acceptance (D-NODISKVERBS) -- the file verbs on a DISKLESS
machine, as on the VG-8020: a device-less name is the cassette's (where the
verb has a cassette face), a drive name is refused.

`10 REM` + `20 ON ERROR GOTO 90` + `30 <stmt>`; the handler prints `[E <ERR>
<ERL>]`, a statement that returns prints `[OK]`; `load error` on the screen is
its own reading (ours alone prints it, and it RETURNS). Fresh boot per row, no
tape: rows that would WAIT for a tape (LOAD / MERGE / BLOAD / RUN of a
device-less name) are not asked, and FILES / KILL / NAME of a device-less
name are nodisk-acceptance's rows already (h.files / h.kill / h.name). A reference with no reading is reported per
row and the sweep goes on.

    python3 -u probes/basic/basic_probe_nodiskverbs.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

REF, OURS = "Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK")
CASES = {
    "save": 'SAVE "X"',
    "savecas": 'SAVE "CAS:X"',
    "bsave": 'BSAVE "X",&HC000,&HC010',
    "loadd": 'LOAD "A:X"',
    "merged": 'MERGE "A:X"',
    "bloadd": 'BLOAD "A:X"',
    "rund": 'RUN "A:X"',
    "saved": 'SAVE "A:X"',
    "bsaved": 'BSAVE "A:X",&HC000,&HC010',
    "killd": 'KILL "A:X"',
}


def reading(machine, stmt):
    prog = ["NEW", "10 REM", "20 ON ERROR GOTO 90", f"30 {stmt}", '40 PRINT"[OK]":END',
            '90 PRINT"[E";ERR;ERL;"]":END', "RUN"]
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0,
                              reset=("CLS",))[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    if "load error" in scr.lower():
        return "load error"
    m = re.findall(r"\[(OK|E[^\]]*)\]", scr)
    if m:
        return " ".join(m[-1].split())
    return "ENDED" if re.search(r"\bRUN (Ok|ZB)\b", scr) else None


def main():
    bad = faults = 0
    only = sys.argv[1:]
    for case, stmt in CASES.items():
        if only and case not in only:
            continue
        r, z = reading(REF, stmt), reading(OURS, stmt)
        if r is None:
            faults += 1
            print(f"NOREF {case:8} {REF} gave no reading; ours {z!r}", flush=True)
            continue
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:8} {r!r:12} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not (bad or faults) else 'FAIL'}: the diskless file verbs as on the "
          f"VG-8020 ({bad} divergence(s), {faults} row(s) the reference did not answer)")
    return 2 if faults else (1 if bad else 0)


if __name__ == "__main__":
    sys.exit(main())
