#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S14g-d knife: POINT's target in E / D, the line-editor op in C.
Do the rows see a wrong register on the way in?

K-WS85 main's pair `ld d,e / ld e,c` -> `ld d,c / nop`: D = x and E stays y,
       the coordinates swapped on the way in -> `ovpt` (two pixels, x / y
       swapped, different colours) and `s14gd` (one pixel) DIVERGE
K-WS86 the tenant's `ld a,c` -> `ld a,b`: the op is read from the wrong
       register. Every typed program line is an LE store, so this is broad by
       construction -> `ctl` and `s14ga` DIVERGE (less certain: if B happened to
       hold the op, a row would agree for the wrong reason)
Both cuts are size-neutral, so no pin moves; each must still prove it BUILT.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s14gd_knife")
KNIVES = [
    ("K-WS85", "basic/graphics.asm",
     [("                ld      d,e                 ; D = y, 0..191 (gfx_in_range passed)\n"
       "                ld      e,c                 ; E = x, 0..255\n",
       "                ld      d,c                 ; KNIFE: D = x\n"
       "                nop                         ; KNIFE: E stays y\n")],
     ["ctl", "s14gd", "ovpt"], ["ovpt", "s14gd"]),
    ("K-WS86", "sub/lineedit.asm",
     [("le_dispatch:\n                ld      a,c ", "le_dispatch:\n                ld      a,b ")],
     ["ctl", "s14ga"], ["ctl", "s14ga"]),
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
    saved = {f: open(f).read() for _t, f, _e, _r, _p in KNIVES}
    for _t, f, edits, _r, _p in KNIVES:
        cut(saved[f], edits)                        # refuses before anything is touched
    only = sys.argv[1:]
    for tag, f, edits, rows, pred in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, rows)
            print(f"{tag}: rows {rows} diverging {red}; predicted {pred} -> "
                  f"{'HIT' if sorted(red) == sorted(pred) else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ["ctl", "s14ga", "s14gd", "ovpt"])
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
