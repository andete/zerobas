#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""OPEN twice, the exact rule (gate: namecase-acceptance; Joost 2026-10-27: "come up
with an exact match without costing more RAM then reference"). A disk name keeps the
TYPED case in the channel's FCB; the open check -- OPEN, KILL, NAME, COPY -- compares
it case-sensitively, and what reaches the disk is upper case. Measured on the CF-3300
(scratchpad/fcbcase_run.out, fcbcase2_run.out, fcbcase2_bdos.out):

  s.case        `TS.DAT` open, OPEN "ts.dat" on a second channel   -> opens
  kill_open     `TS.DAT` open, KILL "ts.dat"                        -> deleted
  name_open     `TS.DAT` open, NAME "ts.dat" AS "UU.DAT"            -> renamed
  copy_open     `TS.DAT` open, COPY "ts.dat" TO "VV.DAT"            -> copied
  kill_open_uc  `TS.DAT` open, KILL "TS.DAT"                        -> File still open
  save_lc       SAVE "ts.dat"                                       -> TS.DAT on the disk
  bdos_fmake    BDOS _FMAKE from a lower-case FCB (a USR routine)   -> LC.TXT on the disk

Each row boots a fresh copy of disk/test720.dsk on both machines; typed BASIC in, the
screen out. Prints `ROW <name> CF=[...] ZB=[...] <SAME|DIVERGES>`; exit 0 all agree, 1
a divergence, 2 the CF-3300 gave no reading.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

FMAKE = "17,0,209,14,22,205,125,243,17,0,209,14,16,205,125,243,201"
ROWS = {
    "s.case":       ("direct", ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'OPEN"ts.dat"FOR OUTPUT AS 2',
                                'PRINT "[OK]":CLOSE']),
    "kill_open":    ("direct", ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'KILL"ts.dat"', 'CLOSE:FILES"*.DAT"']),
    "name_open":    ("direct", ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'NAME"ts.dat"AS"UU.DAT"', 'CLOSE:FILES"*.DAT"']),
    "copy_open":    ("direct", ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'COPY"ts.dat"TO"VV.DAT"', 'CLOSE:FILES"*.DAT"']),
    "kill_open_uc": ("direct", ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'KILL"TS.DAT"', 'CLOSE']),
    "save_lc":      ("direct", ["NEW", "10 REM", 'SAVE"ts.dat"', 'FILES"*.DAT"']),
    "bdos_fmake":   ("stored", ['FOR I=0 TO 36:POKE &HD100+I,0:NEXT:N$="lc      txt":FOR I=1 TO 11:POKE &HD100+I,ASC(MID$(N$,I,1)):NEXT',
                                'RESTORE:FOR I=0 TO 16:READ B:POKE &HD000+I,B:NEXT:DEFUSR=&HD000:A=USR(0):FILES"*.TXT"',
                                "DATA " + FMAKE]),
}
SIDES = (("CF", "National_CF-3300"), ("ZB", "C-BIOS_MSX1_EU_REPACK_DISK"))


def reading(scr, lines):
    """The screen rows after the last typed line, minus prompts and the key bar."""
    rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
    keep = [r.strip() for r in rows if r.strip() and r.strip() not in ("Ok", "ZB")
            and "color" not in r
            and not (len(r.strip()) > 4 and any(r.strip() in ln for ln in lines))]
    return " | ".join(keep)


def main():
    only = sys.argv[1:] or list(ROWS)
    bad, blind = [], []
    for name in only:
        kind, lines = ROWS[name]
        got = {}
        for side, m in SIDES:
            dsk = probe_tmp.tmp(f"namecase_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            scr = omsx_repl.run_cases(m, [(kind, lines)], batch=False, diska=dsk, boot=14.0,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=4.0, run_gap=10.0)[0]
            got[side] = reading(scr, lines) if scr else None
        if not got["CF"]:
            verdict = "NO-REFERENCE"
            blind.append(name)
        elif got["CF"] == got["ZB"]:
            verdict = "SAME"
        else:
            verdict = "DIVERGES"
            bad.append(name)
        print(f"ROW {name} CF=[{got['CF']}] ZB=[{got['ZB']}] {verdict}", flush=True)
    if blind:
        print(f"\nINSTRUMENT FAULT: the CF-3300 gave no reading on {', '.join(blind)}")
        return 2
    print(f"\n{'PASS' if not bad else 'FAIL'}: disk names, case ({len(only) - len(bad)}/{len(only)})")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
