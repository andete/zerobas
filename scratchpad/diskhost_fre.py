#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKROMHOST step 2: the DISK machine's plain-boot memory figures against the CF-3300's -- HIMEM, FRE(0),
FRE(""), and the published layout cells MEMSIZ / STKTOP / FILTAB -- one boot per row, test720.dsk (a data disk) in
the drive. Black box on the reference: typed BASIC and its printed answers.

    python3 -u scratchpad/diskhost_fre.py > scratchpad/AE_diskhost_fre_<when>.out 2>&1
"""
import os, re, sys, shutil
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402

ROWS = [("himem", ['PRINT"[v";PEEK(&HFC4A)+256*PEEK(&HFC4B);"]"']),
        ("fre0", ['X=0:X=FRE(0):PRINT"[v";X;"]"']),
        ("frestr", ['X=0:X=FRE(""):PRINT"[v";X;"]"']),
        ("memsiz", ['PRINT"[v";PEEK(&HF672)+256*PEEK(&HF673);"]"']),
        ("stktop", ['PRINT"[v";PEEK(&HF674)+256*PEEK(&HF675);"]"']),
        ("filtab", ['PRINT"[v";PEEK(&HF860)+256*PEEK(&HF861);"]"'])]


def main():
    got = {}
    for label, m in (("CF-3300", "National_CF-3300"),
                     ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        for n, lines in ROWS:
            dsk = probe_tmp.tmp(f"diskhostfre_{label}_{n}.dsk")
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
