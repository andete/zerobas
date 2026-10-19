#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FATSCRATCH measure-first (2026-10-19): on the DISK machine, does zerobas give the user
the CF-3300's free memory? Main's old FAT scratch span ($EE06.., FCH_STATE0) is named by
no code since the disk engine left for disk.rom; whether it costs RAM depends on where
HIMEM and the channel blocks sit. Boot per row, variables existing first:
  boot     FRE(0) right after boot (MAXFILES=1)
  mf2      after MAXFILES=2
  mf0      after MAXFILES=0
  himem    PEEK HIMEM ($FC4A)
  clear    after CLEAR 200 (the string space set explicitly)
"""
import os, re, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

ROWS = [("boot", ['X=0:X=FRE(0):PRINT"[v";X;"]"']),
        ("mf2", ['X=0:MAXFILES=2:X=FRE(0):PRINT"[v";X;"]"']),
        ("mf0", ['X=0:MAXFILES=0:X=FRE(0):PRINT"[v";X;"]"']),
        ("himem", ['PRINT"[v";PEEK(&HFC4A)+256*PEEK(&HFC4B);"]"']),
        ("clear", ['X=0:CLEAR 200:X=0:X=FRE(0):PRINT"[v";X;"]"'])]


def main():
    got = {}
    for label, m in (("CF-3300", "National_CF-3300"),
                     ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        for n, lines in ROWS:
            dsk = probe_tmp.tmp(f"diskfre_{label}_{n}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            r = omsx_repl.run_cases(m, [("direct", lines)], batch=False,
                                    reset=("", "SCREEN 0:WIDTH 40"), boot=14.0, step=1.5,
                                    run_gap=20.0, diska=dsk)[0] or ""
            v = [x for x in re.findall(r"\[v([^\]\[]*)\]", r.replace("\n", "")) if '"' not in x]
            got[(label, n)] = v[-1].strip() if v else "NO READING"
    print(f"{'row':6} {'CF-3300':>10} {'OURS':>10}  OURS-CF")
    for n, _l in ROWS:
        a, b = got[("CF-3300", n)], got[("OURS", n)]
        try:
            d = int(float(b)) - int(float(a))
        except ValueError:
            d = "-"
        print(f"{n:6} {a:>10} {b:>10}  {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
