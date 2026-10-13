#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""RAM-usage audit, step 1 (Joost, 2026-10-13: "for every ram buffer or memory
location we invented ourselves, we need to verify how reference does it and if
we should not be using an existing "official" ram location instead").

An INVENTORY, by job: every cell zerobas declares in its own workspace
($E26A..$F37F, both components), grouped by what it is for, with each group's
byte footprint (aliased cells counted once -- the union of their bytes). It
reads the source map only (tools/ram_map.py); it measures nothing. The groups
are the unit the next step measures on the VG-8020 (which official work-area
cells it writes for that job).

Grouping is by the cell's NAME PREFIX (this tree names cells by subsystem) and,
failing that, by keywords in its declaration comment; anything unmatched is
listed under "unclassified" for a human to place -- never guessed.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
import ram_map                                     # noqa: E402

LO, HI = 0xE26A, 0xF380
GROUPS = [   # (group, name regex, comment regex)
    ("graphics (PAINT / DRAW / CIRCLE / sprites / SCREEN)", r"^GFX_|^GRP_|^CIRC|^PNT_", r"PAINT|DRAW|CIRCLE|SPRITE|SCREEN 2"),
    ("PRINT USING / number formatting", r"^PU_|^FMT_|^FOUT|^CVT|^NUMBUF|^TKDIG|^TKPOS|^FOSIG", r"PRINT USING|formatter"),
    ("DEF FN", r"^FN_|^FNSP", r"DEF FN"),
    ("traps (ON ... GOSUB, STOP, INTERVAL, KEY)", r"^Z|^TRAP|^SAVSTK|^ERRRESUME|^SAVTXT|^ONE|^STOP", r"trap"),
    ("control pool (FOR / GOSUB / stack)", r"^CSP|^CTL|^GSP|^FSP|^TSP|^FOR_|^GOTO|^RESUME|^CURLINE|^ENDFLAG|^SL_CEIL|^DIRECTF", r"FOR frame|GOSUB|control"),
    ("string engine / heap", r"^STR|^SH_|^RVDESC|^ISRCH|^MIDS|^FRETOP|^TEMP|^LHS_", r"string|heap"),
    ("arrays / variables", r"^ARY_|^VAR|^DIM|^DEF|^VALTYP", r"array|variable"),
    ("tokeniser / line entry / editor", r"^TK|^RL_|^CSR_|^LINE|^MRG|^PLN_|^AU_|^RN_|^LST_|^SL_|^LE_|^INP_", r"tokeni|line editor|RENUM|AUTO|MERGE"),
    ("files / channels / disk", r"^FCH_|^FLD_|^GP_|^FAT_|^DISK|^DSK|^FILE[S]|^COPY|^LRSET|^FS|^FW|^OO_|^BN_|^FREAD|^FWR_|^BDOS|^WRBLK|^RRND|^DBUF|^MBUF|^SECTOR|^WBUF|^FDC_|^DRV|^RDBLK|^DOS|^RES_|^W50|^BASENT|^DATE|^RAMAD|^CURDRV|^INT_|^CON|^WA_|^PG_|^F365|^P1_|^SEQ_|^LOC_|^EOF", r"disk|channel|FIELD|FAT|sector"),
    ("cassette", r"^CAL_|^CAS_|^CLPTR|^CLINK|^CURPTR|^ENDPTR|^EXECPTR", r"cassette|tape"),
    ("math pack scratch", r"^MATH_|^SQRT_|^RND_|^HORNER|^FP_|^MUL|^DIV|^MC_", r"math|RND|SQR"),
    ("PLAY / sound", r"^PLY|^PLAY|^SND|^BEEP", r"PLAY|PSG"),
    ("sub-ROM bridge / slot scan / boot", r"^SUB|^SCAN_|^INT_MAIN|^BROM|^KEYARG|^DB_|^DT_|^TXTCEIL|^ERRMARK|^PRMWANT|^SW_|^SVT|^BL_", r"sub-ROM|tenant|slot scan|boot"),
]


def group_of(name, comment):
    for g, nre, cre in GROUPS:
        if re.search(nre, name):
            return g
    for g, nre, cre in GROUPS:
        if comment and re.search(cre, comment, re.IGNORECASE):
            return g
    return "unclassified"


def main():
    rows = {}
    for c in ("basic", "disk"):
        m = ram_map.Map(c, LO, HI)
        for a in m.addrs:
            names = m.byaddr[a]
            if c == "disk" and all(m.raw.get(n, ("", ""))[1].endswith("basic-resident-abi.inc")
                                   for n in names):
                continue                                  # a mirror of a basic cell
            w = m.width.get(a) or 1
            com = m.raw.get(names[0], ("", "", 0, ""))[3] or ""
            g = group_of(names[0], com)
            rows.setdefault(g, []).append((a, w, c, "/".join(names), com.strip()[:70]))
    total = set()
    print(f"zerobas workspace ${LO:04X}..${HI - 1:04X} by job (declared cells; widths from the map,"
          f" width-less counted as 1 B)\n")
    summary = []
    for g, cells in rows.items():
        foot = set()
        for a, w, *_ in cells:
            foot |= set(range(a, a + w))
        total |= foot
        summary.append((len(foot), g, len(cells)))
    for n, g, k in sorted(summary, reverse=True):
        print(f"{n:5d} B  {k:3d} cells  {g}")
    print(f"{len(total):5d} B  in all (union)\n")
    for n, g, k in sorted(summary, reverse=True):
        print(f"=== {g}  ({n} B)")
        for a, w, c, names, com in sorted(rows[g]):
            print(f"   ${a:04X} {w:4d} B {c[0]} {names[:40]:40s} {com}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
