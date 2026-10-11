#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-LISTFLT's other half: ASCII SAVE writes through the same detok as LIST,
so before the fix `SAVE "X",A` of a program with a float literal wrote
garbage. A round trip on disk -- type, SAVE ,A, NEW, LOAD, LIST, RUN -- on
the CF-3300 and the zerobas disk build. Clean room: typed BASIC, the screen.

Prediction: everything from LOAD on reads the same on both machines.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "tools"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402
from make_test_dsk import Fat12Image               # noqa: E402

CF, ZBD = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"
LINES = ["NEW", "10 A=0.123456789:B=1.5E-10",
         "20 C=40000:D=1.5D20:E=0.05", "30 PRINT A;B;C;D;E",
         'SAVE"T.BAS",A', "NEW", 'LOAD"T.BAS"', "LIST", "RUN"]


def main():
    out = {}
    for m in (CF, ZBD):
        p = probe_tmp.tmp("listflt_rt.dsk")
        open(p, "wb").write(Fat12Image().finish())
        raw = omsx_repl.run_cases(m, [("direct", LINES)], batch=False,
                                  reset=("", "SCREEN 0"), diska=p)[0] or ""
        flat = re.sub(r"\s+", " ", raw)
        i = flat.rfind('LOAD"T.BAS"')
        out[m] = flat[i:] if i >= 0 else None
        print(f"== {m}\n   {out[m]}")
    same = out[CF] is not None and out[CF].replace("Ok", "ZB") == out[ZBD]
    print(f"\n{'SAME' if same else 'DIVERGES'} (the prompt word aside)")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
