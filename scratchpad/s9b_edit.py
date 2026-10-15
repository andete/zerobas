#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S9b: DISK-ONLY / BOOT-ONLY tags on the cells S9 made disk-only in
fact, the alias splits that would launder a diskless user through A17's alias
rule, and `tools/ram_map.py --floor-top HEX` (S15's census). 0 ROM bytes.
Anchored on each equate's NAME; refuses on a missing or non-unique anchor."""
import re, sys

def edit(path, old, new):
    s = open(path).read()
    if s.count(old) != 1:
        sys.exit(f"{path}: anchor count {s.count(old)} for {old[:60]!r}")
    open(path, "w").write(s.replace(old, new))

P = "basic/sysvars.inc"
L = open(P).read().split("\n")
def line_of(name):
    hits = [i for i, l in enumerate(L) if re.match(rf"{name}\s+equ\s+", l)]
    if len(hits) != 1:
        sys.exit(f"{name}: {len(hits)} equ lines")
    return hits[0]

def tag(name, word):
    i = line_of(name)
    l = L[i]
    if word in l:
        return
    if ";" in l:
        a, b = l.split(";", 1)
        L[i] = a + "; " + word + ":" + (" " if not b.startswith(" ") else "") + b.lstrip(" ").join(["", ""]) if False else a + "; " + word + ": " + b.lstrip(" ")
    else:
        L[i] = l + "   ; " + word

# E16: alias splits -- same VALUES, so every ROM stays byte-identical
for name, old, new in (("FMT_GEOMSEL", "TSV_CNT", "$EF61"), ("FMT_RESULT", "TSV_NAME", "$EF62"),
                       ("PLY_NUMOVF", "DISKOP_A", "$EE3A")):
    i = line_of(name)
    m = re.match(rf"({name}\s+equ\s+)(\S+)(.*)$", L[i])
    if m.group(2) != old:
        sys.exit(f"{name}: {m.group(2)} != {old}")
    L[i] = m.group(1) + new + m.group(3) + f"  [D-WSZERO S9b: was `equ {old}` -- an alias of a DISK-ONLY name would hide a diskless user]"
DISK = ("FLD_CUROFF FLD_CHAN LRSET_JUST LRSET_W LRSET_DEST DISK_FCB DISK_FCB_NAME DSV_PTR DSV_END "
        "FMT_GEOMSEL FMT_RESULT FMT_SEC FMT_DESC FILES_ENTIDX FILES_HASPAT DSKBUF_PTR DISKOP_A "
        "DISKOP_HL DISKOP_ERR FCH_RECLENS FCH_RECNOS FLD_TAB GP_RECNO GP_SEC GP_WITHIN GP_CLUS "
        "GP_CLIDX GP_SECINCL GP_PHYS GP_FLAGS GP_RECLEN GP_SRC GP_LEFT COPY_SRC COPY_CLUS COPY_LEFT "
        "FAT_SECPERCLUS FAT_FATSTART FAT_FIRSTROOT FAT_TOTCLUS FAT_FIRSTDATA FAT_CURCLUS FAT_CLUSSEC "
        "FAT_FIRSTCLUS FAT_FILESIZE FAT_NUMFATS FAT_SECPERFAT FAT_PARITY FAT_BYTEIDX FAT_FATSEC "
        "FAT_B0 FAT_B1 FAT_NAMEPTR FAT_DIRSEC FAT_DIRREM FAT_WRTMP FAT_WRTMP2 FREAD_OFF FREAD_LEFT "
        "FWR_CLUS FWR_FIRST FWR_SECIDX FWR_BUFLEN FWR_BYTES FWR_DIRSEC FWR_DIROFF").split()
for n in DISK:
    tag(n, "DISK-ONLY")
for n in ("SCAN_PRIM", "SCAN_SLOT", "SCAN_INIT", "SCAN_IY"):
    tag(n, "BOOT-ONLY")
for n in ("FLD_TABEND", "FN_STK_FLOOR"):
    tag(n, "NOT-A-CELL")
open(P, "w").write("\n".join(L))

# E18: the floor rule accepts BOOT-ONLY, and --floor-top HEX lists the projected floor
R = "tools/ram_map.py"
edit(R, '''def disk_floor(m) -> tuple:
    """(offenders, tagged) for the DISKLESS FLOOR: [TXTMAX, TXTMAX_NODISK).
''', '''def disk_floor(m, top=None) -> tuple:
    """(offenders, tagged) for the DISKLESS FLOOR: [TXTMAX, TXTMAX_NODISK).

    `top` replaces TXTMAX_NODISK: D-WSZERO S9b's `--floor-top F380` asks what
    would stand in the way if the diskless ceiling rose to $F380 (S15's census).
    A `BOOT-ONLY` tag counts too: a cell used only by the boot scan, before any
    program exists (SCAN_*).
''')
edit(R, '''    tx, tn = m.vals.get("TXTMAX"), m.vals.get("TXTMAX_NODISK")
    if tx is None or tn is None:''', '''    tx, tn = m.vals.get("TXTMAX"), m.vals.get("TXTMAX_NODISK")
    if top is not None:
        tn = top
    if tx is None or tn is None:''')
edit(R, '''        return bool(rec and rec[3] and "DISK-ONLY" in rec[3].split(";")[0][:120])

    offenders, tagged = [], []''', '''        head = rec[3].split(";")[0][:120] if rec and rec[3] else ""
        return "DISK-ONLY" in head or "BOOT-ONLY" in head

    offenders, tagged = [], []''')
edit(R, '''    ok["A17 a bare alias of a tagged name is accepted (FAT_DBUF's shape)"] = \\
        "ZZ_FLOOR_ALIAS" in _tag3 and all(n != "ZZ_FLOOR_ALIAS" for n, _a in _off3)
''', '''    ok["A17 a bare alias of a tagged name is accepted (FAT_DBUF's shape)"] = \\
        "ZZ_FLOOR_ALIAS" in _tag3 and all(n != "ZZ_FLOOR_ALIAS" for n, _a in _off3)
    for _w, _want in (("BOOT-ONLY: the boot scan's (1)", True), ("BOOT ONLY: no hyphen (1)", False)):
        _raw4 = dict(_fm.raw)
        _raw4["ZZ_FLOOR_BOOT"] = (f"${_tx + 1:04X}", "plant", 0, _w)
        _off4, _ = disk_floor(Map("basic", 0, 0x10000, raw=_raw4, use_sym=False))
        ok["A17 a BOOT-ONLY tag is accepted" if _want else
           "A17 NEGATIVE: `BOOT ONLY` (no hyphen) is RED"] = \\
            (all(n != "ZZ_FLOOR_BOOT" for n, _a in _off4) == _want)
    _offt, _ = disk_floor(_fm, top=0xF380)
    ok["A17 --floor-top widens the floor (F380 lists more than TXTMAX_NODISK)"] = \\
        len(_offt) > len(_off)
''')
edit(R, '''    if "--check" in sys.argv:
        maps = {c: Map(c, lo, hi) for c in ("basic", "disk")}''', '''    if "--floor-top" in sys.argv:
        # D-WSZERO S9b: ADVISORY, never a gate -- what still stands below a
        # projected diskless ceiling, untagged. S15 raises TXTMAX_NODISK only
        # when this list is empty.
        top = int(sys.argv[sys.argv.index("--floor-top") + 1], 16)
        offenders, tagged = disk_floor(Map("basic", 0, 0x10000), top=top)
        print(f"floor-top ${top:04X}: {len(offenders)} untagged basic name(s) in "
              f"[TXTMAX, ${top:04X}) -- diskless state that must move before the "
              f"ceiling can rise there; {len(tagged)} DISK-/BOOT-ONLY name(s) may stay")
        for n, a in offenders:
            print(f"    {a}  {n}")
        return 0
    if "--check" in sys.argv:
        maps = {c: Map(c, lo, hi) for c in ("basic", "disk")}''')
print("ok", len(DISK), "disk-only tags")
