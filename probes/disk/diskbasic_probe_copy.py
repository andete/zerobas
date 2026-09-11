#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""copy-acceptance — COPY "src" TO "dst" against the CF-3300 (docs/spec-basic-copy.md).

Every row runs on a PRIVATE copy of disk/test720.dsk (COPY writes), and the
scored value is read from the IMAGE by a host-side FAT12 reader -- the copied
file's bytes, not a LOF on the screen -- so a verb that created the entry and
wrote nothing, or wrote the wrong clusters, cannot pass.
    c.plain   COPY"PROG.BAS"TO"NEW.BAS"       NEW.BAS's bytes == PROG.BAS's (16 B)
    c.big     COPY"TEST.BIN"TO"T2.BIN"        2048 B = four sectors, two clusters
    c.exist   COPY"PROG.BAS"TO"NEW.BAS" then COPY"HI.TXT"TO"NEW.BAS": NEW.BAS == HI.TXT (overwritten)
    c.var     COPY A$ TO B$ (string variables)
    c.missing source absent                  -> ERR 53
    c.self    COPY"PROG.BAS"TO"PROG.BAS"     -> ERR 5, PROG.BAS intact
    c.wild    COPY"*.BAS"TO"Z.BAS"           -> ERR 5
    c.nodest  COPY"PROG.BAS"                 -> ERR 5 (parses, refused -- not ERR 2)
Faces and contents were measured on the CF-3300 first (scratchpad/copyverb_probe.py
and the 2026-09-11 rows in the spec); --survey shows that column.
"""
from __future__ import annotations
import argparse, os, sys, shutil, struct
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")

def fat12_read(img: bytes, name83: str):
    """Bytes of the root-directory file `name83` ('NEW     BAS'), or None if absent."""
    bps, spc, rsv, nf, nroot, _, _, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    fat = img[rsv * bps:(rsv + spf) * bps]
    root = (rsv + nf * spf) * bps
    data0 = root + nroot * 32
    for i in range(nroot):
        e = img[root + 32 * i:root + 32 * i + 32]
        if e[0] in (0, 0xE5) or e[11] & 0x08: continue
        if e[:11].decode("latin1") == name83:
            clus = struct.unpack_from("<H", e, 26)[0]; size = struct.unpack_from("<I", e, 28)[0]
            out = b""
            while 2 <= clus < 0xFF8 and len(out) < size:
                out += img[data0 + (clus - 2) * spc * bps: data0 + (clus - 1) * spc * bps]
                o = clus * 3 // 2; v = struct.unpack_from("<H", fat, o)[0]
                clus = (v >> 4) if clus & 1 else (v & 0xFFF)
            return out[:size]
    return None

CASES = [
    ("c.plain",   ['20 COPY"PROG.BAS"TO"NEW.BAS"', '30 PRINT"[c.plain OK]":END'],                       ("NEW     BAS", "PROG    BAS")),
    ("c.big",     ['20 COPY"TEST.BIN"TO"T2.BIN"', '30 PRINT"[c.big OK]":END'],                          ("T2      BIN", "TEST    BIN")),
    ("c.exist",   ['20 COPY"PROG.BAS"TO"NEW.BAS":COPY"HI.TXT"TO"NEW.BAS"', '30 PRINT"[c.exist OK]":END'], ("NEW     BAS", "HI      TXT")),
    ("c.var",     ['15 A$="PROG.BAS":B$="N3.BAS"', '20 COPY A$ TO B$', '30 PRINT"[c.var OK]":END'],       ("N3      BAS", "PROG    BAS")),
    ("c.missing", ['20 COPY"NOPE.BAS"TO"NEW.BAS"', '30 PRINT"[c.missing OK]":END'],                     None),
    ("c.self",    ['20 COPY"PROG.BAS"TO"PROG.BAS"', '30 PRINT"[c.self OK]":END'],                       ("PROG    BAS", "PROG    BAS")),
    ("c.wild",    ['20 COPY"*.BAS"TO"Z.BAS"', '30 PRINT"[c.wild OK]":END'],                             None),
    ("c.nodest",  ['20 COPY"PROG.BAS"', '30 PRINT"[c.nodest OK]":END'],                                 None),
]
EXPECT = {"c.plain": "OK", "c.big": "OK", "c.exist": "OK", "c.var": "OK",
          "c.missing": "ERR 53", "c.self": "ERR 5", "c.wild": "ERR 5", "c.nodest": "ERR 5"}

def fence(tag, cap):
    """The printed `[tag ...]`, never the typed echo (an echo carries `";`)."""
    c = cap or ""; k = len(c)
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def read(side, cfg):
    faces, files = {}, {}
    fixture = open(FIXTURE, "rb").read()
    for tag, body, chk in CASES:
        dsk = probe_tmp.tmp(f"copy_{tag}_{side}.dsk"); shutil.copyfile(FIXTURE, dsk)
        prog = ['10 ON ERROR GOTO 90'] + body + [f'90 PRINT"[{tag} ERR";ERR;"]":END', 'RUN']
        cap = omsx_repl.run_cases(cfg["machine"], [(tag, prog)], batch=False, boot=cfg["boot"],
                                  reset=cfg["reset"], diska=probe_sides.diska(side, dsk), run_gap=45.0)[0]
        faces[tag] = fence(tag, cap)
        if chk:
            dst, src = chk
            img = open(dsk, "rb").read()
            got, want = fat12_read(img, dst), fat12_read(fixture, src)
            files[tag] = (got == want and got is not None, len(got) if got is not None else None, len(want))
    return faces, files

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--survey", action="store_true"); a = ap.parse_args()
    sides = ("cf3300", "zb") if a.survey else ("zb",)
    cfg = probe_sides.sides(*sides)
    got = {s: read(s, cfg[s]) for s in sides}
    bad = []
    for tag, _, chk in CASES:
        f, w = got["zb"][0][tag], EXPECT[tag]
        ok = f == w
        note = ""
        if chk:
            same, n, m = got["zb"][1][tag]; ok = ok and same
            note = f" bytes={'same' if same else 'DIFFER'}({n}/{m})"
        bad += [] if ok else [tag]
        extra = ""
        if a.survey:
            cf = got["cf3300"]; extra = f"  cf3300={cf[0][tag]!r}" + (f" bytes={'same' if cf[1][tag][0] else 'DIFFER'}({cf[1][tag][1]}/{cf[1][tag][2]})" if chk else "")
        print(f"  {'ok  ' if ok else 'DIFF'} {tag:9} zb={f!r:10}{note:24} want={w!r}{extra}")
    print(f"{len(CASES)} rows, {len(bad)} diverge: {bad or 'none'}")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
