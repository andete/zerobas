#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CASBAUD: the cassette baud set -- what SCREEN ,,,n and CSAVE ,n make active, the
VG-8020 against zerobas.

Both references hold CS120 ($F3FC: LOW, HIGH, HEADER = 53 5C 26 2D 0F) and CS240 ($F401:
25 2D 0E 16 1F) from power-on and copy the WHOLE selected 5-byte set into the active slots
at $F406: `SCREEN ,,,2` copies CS240, `,,,1` CS120 (scratchpad/cstables.out). zerobas's
SCREEN ignored its fourth argument and CSAVE ,n set the LOW word alone. One program reads
the active five bytes after boot, after SCREEN ,,,2 / ,,,1 and after CSAVE "X",2 (written
to the empty cassette slot -- only the cells matter here). Black box: work-area RAM only.

    python3 -u probes/basic/basic_probe_casbaud.py      (`make casbaud-acceptance`)
Exit 0 SAME; 1 a divergence; 2 the VG-8020 gave no reading.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

MACHINES = (("VG", "Philips_VG_8020"), ("ZB", "C-BIOS_MSX1_EU_REPACK_NODISK"))
ACT = "FOR I=&HF406 TO &HF40A:PRINT RIGHT$(\"0\"+HEX$(PEEK(I)),2);:NEXT"
PROG = ["NEW",
        f'10 PRINT "[B";:{ACT}:PRINT "]"',
        f'20 SCREEN ,,,2:PRINT "[2";:{ACT}:PRINT "]"',
        f'30 SCREEN ,,,1:PRINT "[1";:{ACT}:PRINT "]"',
        '40 CSAVE "X",2',                 # (alone: zerobas skipped the rest of a CSAVE line --
        f'50 PRINT "[C";:{ACT}:PRINT "]"',  #  D-CSAVEREST, filed separately)
        "RUN"]
ROWS = (("B", "boot"), ("2", "SCREEN ,,,2"), ("1", "SCREEN ,,,1"), ("C", "CSAVE ,2"))


# D-CSAVEREST (2026-11-14): a tape save mid-line. CSAVE and BSAVE "CAS:" go on with the
# rest of their line on the VG-8020; zerobas ended the line (its continuation was a handler
# `ret`). SAVE "CAS:" ENDS the run on both -- the row that keeps a fix from overreaching.
REST = {
    "CSAVE mid-line": '20 CSAVE "X":PRINT "[C]"',
    'BSAVE "CAS:" mid-line': '20 BSAVE "CAS:Z",&HC000,&HC00F:PRINT "[C]"',
    'SAVE "CAS:" mid-line': '20 SAVE "CAS:Y":PRINT "[C]"',
}


def rest_rows(m):
    out = {}
    for what, line in REST.items():
        prog = ["NEW", '10 PRINT "[A]"', line, '30 PRINT "[D]"', "RUN"]
        raw = omsx_repl.run_cases(m, [("direct", prog)], batch=False, reset=("",),
                                  step=3.0, run_gap=40.0)[0] or ""
        flat = re.sub(r"\s+", "", raw)
        tail = flat[flat.rfind("RUN"):] if "RUN" in flat else ""
        out[what] = "".join(re.findall(r"\[[ACD]\]", tail)) or None
    return out


def main():
    got = {}
    for side, m in MACHINES:
        raw = omsx_repl.run_cases(m, [("direct", PROG)], batch=False, reset=("",),
                                  step=3.0, run_gap=40.0)[0] or ""
        flat = re.sub(r"\s+", "", raw)
        got[side] = {k: (re.findall(rf"\[{k}([0-9A-F]{{10}})\]", flat) or [None])[-1] for k, _ in ROWS}
        print(f"{side} " + "  ".join(f"{what}={got[side][k]}" for k, what in ROWS), flush=True)
    rest = {side: rest_rows(m) for side, m in MACHINES}
    for side in ("VG", "ZB"):
        print(f"{side} " + "  ".join(f"{w}={v}" for w, v in rest[side].items()), flush=True)
    if any(v is None for v in got["VG"].values()) or any(v is None for v in rest["VG"].values()):
        print("NO READING on the VG-8020")
        return 2
    bad = [what for k, what in ROWS if got["VG"][k] != got["ZB"][k]]
    bad += [w for w in REST if rest["VG"][w] != rest["ZB"][w]]
    print(f"\n{'PASS' if not bad else 'FAIL'}: the active cassette set "
          f"({len(ROWS) + len(REST) - len(bad)}/{len(ROWS) + len(REST)} as the VG-8020){'; differs: ' + ', '.join(bad) if bad else ''}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
