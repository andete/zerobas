#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14g-b knife: the widen body takes the operand TYPE in a register
(WSRC_TYP is gone). Do `s14gb` / `ovwsrc` see a wrong type or a wrong pad?

K-WS80 widen_lhsframe_to loads FACTYP instead of LHS_FACTYP: a mixed-precision
       operation unpacks its LEFT operand with the RIGHT one's mantissa length
       -> `ovwsrc` and `s14gb` (the same widened values) DIVERGE
K-WS81 the two pad counts swapped (ld b,9 <-> ld b,1): every widened single is
       zero-padded short and every double long -> both rows DIVERGE
Both cuts are size-neutral, so no pin moves; each must still prove it BUILT.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14gb_knife")
SRC = "basic/float-arith.asm"
ROWS = ["ctl", "s14gb", "ovwsrc"]
KNIVES = [
    ("K-WS80", [("widen_lhsframe_to:\n                ld      a,(LHS_FACTYP)",
                 "widen_lhsframe_to:\n                ld      a,(FACTYP)")], ["ovwsrc", "s14gb"]),
    ("K-WS81", [("                ld      b,9\n                jr      nz,wsrc_padcount\n"
                 "                ld      b,1\n",
                 "                ld      b,1\n                jr      nz,wsrc_padcount\n"
                 "                ld      b,9\n")], ["ovwsrc", "s14gb"]),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor: {text.count(old)} x {old[:50]!r}")
        text = text.replace(old, new)
    return text


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    for _t, edits, _p in KNIVES:
        cut(text, edits)                            # refuses before anything is touched
    only = sys.argv[1:]
    for tag, edits, pred in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            open(SRC, "w").write(cut(text, edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, ROWS)
            print(f"{tag}: rows {ROWS} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ROWS)
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
