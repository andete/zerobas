#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""tapetail-acceptance (D-TAPETAIL) -- the cassette save verbs' bad tails are
TRAPPABLE errors on the diskless VG-8020, not our print-and-return `load error`.

`10 REM` + `20 ON ERROR GOTO 90` + `30 <stmt>`; the handler prints `[E <ERR>
<ERL>]`, a statement that returns prints `[OK]`; `load error` on the screen is
its own reading (ours alone prints it, and it RETURNS -- a row could otherwise
agree for the wrong reason). No tape: a tape save completes without one.

  bsaves    BSAVE "CAS:X",&HC000,&HC010,S     on the DISKLESS VG-8020 there is no
                                              `,S` flag: S is a VARIABLE (the exec)
  bsavesx   BSAVE "CAS:X",&HC000,&HC010,SX    likewise SX
  dbsaves   the `bsaves` statement on the CF-3300, whose Disk BASIC owns `,S`
  bsavesbig  S=70000 first: a VARIABLE exec overflows (6), the FLAG ignores S
  dbsavesbig    and saves -- the DISCRIMINATOR `OK` alone cannot be
  dbsavebig  a DISK BSAVE's exec 70000 (the exec is typed as an address now)
  dbsavestr  a DISK BSAVE's exec "A"   -- both read whether T.BIN was CREATED
                                          (F/N), the error alone being deferred
  savejunk  SAVE "CAS:X" Q                    junk after the name
  csavespd  CSAVE "X",3                       a speed that is not 1 or 2
  csavejunk CSAVE "X",1,2                     junk after the speed
  csaveok   CSAVE "X",2                       the control: saves

Fresh boot per row. Exit 0 all agree; 1 a divergence; 2 a reference gave no
reading.

    python3 -u probes/basic/basic_probe_tapetail.py [case ...]
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402

TAPE = ("Philips_VG_8020", os.environ.get("ZEROBAS_NODISK_MACHINE", "C-BIOS_MSX1_EU_REPACK_NODISK"))
DISK = ("National_CF-3300", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))
ON_DISK = {"dbsaves", "dbsavesbig", "dbsavebig", "dbsavestr"}
CASES = {
    "bsaves": 'BSAVE "CAS:X",&HC000,&HC010,S',
    "bsavesx": 'BSAVE "CAS:X",&HC000,&HC010,SX',
    "dbsaves": 'BSAVE "CAS:X",&HC000,&HC010,S',
    "bsavesbig": 'S=70000:BSAVE "CAS:X",&HC000,&HC010,S',
    "dbsavesbig": 'S=70000:BSAVE "CAS:X",&HC000,&HC010,S',
    "dbsavebig": 'BSAVE "T.BIN",&HC000,&HC00F,70000',
    "dbsavestr": 'BSAVE "T.BIN",&HC000,&HC00F,"A"',
    "savejunk": 'SAVE "CAS:X" Q',
    "csavespd": 'CSAVE "X",3',
    "csavejunk": 'CSAVE "X",1,2',
    "csaveok": 'CSAVE "X",2',
}
# 🔴 THE ERROR ALONE IS A DEFERRED WITNESS on these two: with the exec's type
# check cut, the pending 6 / 13 is still raised later in the statement -- AFTER
# the file is written (K-BO2's and K-BV1's lesson, the same day). They read
# whether T.BIN was CREATED: F = it exists, N = it does not.
FILE_WITNESS = {"dbsavebig", "dbsavestr"}


def reading(machine, stmt, disk=False, witness=False):
    handler = (["90 E=ERR:L=ERL:RESUME 91",
                '91 ON ERROR GOTO 95:OPEN "T.BIN" FOR INPUT AS #1:PRINT"[E";E;L;"F]":END',
                '95 PRINT"[E";E;L;"N]":END'] if witness else ['90 PRINT"[E";ERR;ERL;"]":END'])
    prog = ["NEW", "10 REM", "20 ON ERROR GOTO 90", f"30 {stmt}", '40 PRINT"[OK]":END'] + handler + ["RUN"]
    kw = dict(reset=("CLS",))
    if disk:
        import shutil
        import probe_tmp
        dsk = probe_tmp.tmp(f"tapetail_{machine}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        kw = dict(diska=dsk, boot=14.0, reset=("", "SCREEN 0"))
    raw = omsx_repl.run_cases(machine, [("d", prog)], batch=False, run_gap=15.0, **kw)[0] or ""
    scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
    if "load error" in scr.lower():
        return "load error"
    m = re.findall(r"\[(OK|E[^\]]*)\]", scr)
    if m:
        return " ".join(m[-1].split())
    # a SAVE / CSAVE that completes inside a program returns to the PROMPT on
    # the references (savetail's finding): RUN, then Ok / our ZB
    return "ENDED" if re.search(r"\bRUN (Ok|ZB)\b", scr) else None


def main():
    bad = 0
    only = sys.argv[1:]
    for case, stmt in CASES.items():
        if only and case not in only:
            continue
        disk = case in ON_DISK
        ref, ours = DISK if disk else TAPE
        w = case in FILE_WITNESS
        r, z = reading(ref, stmt, disk, w), reading(ours, stmt, disk, w)
        if r is None:
            print(f"INSTRUMENT FAULT: {ref} gave no reading for {case}")
            return 2
        bad += r != z
        print(f"{'ok  ' if r == z else 'DIFF'} {case:9} {r!r:14} ours {z!r}", flush=True)
    print(f"\n{'PASS' if not bad else 'FAIL'}: the tape save tails as on the VG-8020 ({bad} divergence(s))")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
