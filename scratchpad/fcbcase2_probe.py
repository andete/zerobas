#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""OPEN twice, the exact rule (Joost 2026-10-27), the second pair of questions (2026-10-28): KILL / NAME / COPY
of a case-changed name while the file is open, and BDOS _FMAKE's case. Derived from fcbcase_probe.py.
The first set: before keeping the TYPED case in a
channel's FCB, measure what case reaches the DISK on the CF-3300 and whether a
lower-case name finds an upper-case file. Each case runs on a fresh copy of
disk/test720.dsk; typed BASIC in, the screen out.
    python3 -u scratchpad/fcbcase_probe.py [MACHINE ...]
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

CASES = {
    # (1) a case-changed name while the file is OPEN -- KILL / NAME / COPY
    "kill_open": ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1:ON ERROR GOTO 0', 'KILL"ts.dat"', 'CLOSE:FILES"TS.*"'],
    "name_open": ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'NAME"ts.dat"AS"UU.DAT"', 'CLOSE:FILES"*.DAT"'],
    "copy_open": ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'COPY"ts.dat"TO"VV.DAT"', 'CLOSE:FILES"*.DAT"'],
    "kill_open_uc": ['MAXFILES=2:OPEN"TS.DAT"FOR OUTPUT AS 1', 'KILL"TS.DAT"', 'CLOSE'],
    # (2) BDOS _FMAKE ($16) then _FCLOSE ($10) from a USR routine, with a LOWER-CASE FCB
    "bdos_fmake": ['FOR I=0 TO 36:POKE &HD100+I,0:NEXT:N$="lc      txt":FOR I=1 TO 11:POKE &HD100+I,ASC(MID$(N$,I,1)):NEXT',
                   'RESTORE:FOR I=0 TO 16:READ B:POKE &HD000+I,B:NEXT:DEFUSR=&HD000:A=USR(0):FILES"*.TXT"',
                   'DATA 17,0,209,14,22,205,125,243,17,0,209,14,16,205,125,243,201'],
}
MACHINES = ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]


def main():
    for m in [a for a in sys.argv[1:] if a.startswith(("National", "C-BIOS", "Philips"))] or MACHINES:
        for name, lines in CASES.items():
            dsk = probe_tmp.tmp(f"fcbcase_{name}_{m}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            kind = "stored" if name.startswith("bdos") else "direct"   # DATA must be READ from a program
            if "--only" in sys.argv and name not in sys.argv:
                continue
            scr = omsx_repl.run_cases(m, [(kind, lines)], batch=False, diska=dsk, boot=14.0,
                                      reset=("", "SCREEN 0:WIDTH 40"), step=4.0, run_gap=10.0)[0]
            rows = [scr[i:i + 40].rstrip() for i in range(0, len(scr or ""), 40)]
            out = " | ".join(r for r in rows if r.strip() and r.strip() not in ("Ok",))[-260:]
            print(f"{m:28s} {name:14s} [{out}]", flush=True)


if __name__ == "__main__":
    main()
