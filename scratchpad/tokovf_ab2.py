#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-TOKOVF A/B, round 2: WHICH half of the change loses typed keys?

tokovf_ab.out: geteject `put` red with the bound live AND with it cut, and its
screen shows TYPING damage, not disk timing -- `NNEW` (a key doubled) and
`0 PUT 1,20` (line 60's `6` lost). Both arms share the BEEP move (main low
region +3 B from sound.asm's stub onward; sub page 0 -74 B from beep.asm's
include onward) and the bound's 9 B in sub page 0.

  V2  the bound REMOVED entirely (tokenise.inc as at HEAD), BEEP still moved.
Runs geteject (all rows) and fdcdi. Restores on a CLEAN build after.

Prediction: V2 still red on geteject -- the damage follows an address shift,
not the tokeniser's work.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "tokovf_ab2")
PATH = "basic/tokenise.inc"
START = "                ; 🔴 D-TOKOVF (2026-10-12): THE BOUND AT EVERY STEP."
END = "                jp      c,tk_end\n                ld      a,(TKNAME)\n"
PROBES = ("probes/disk/disk_probe_geteject.py", "probes/disk/disk_probe_fdcdi.py")


def probes(tag):
    for p in PROBES:
        log = f"{TMP}/{tag}_{os.path.basename(p)}.log"
        with open(log, "w") as fh:
            rc = subprocess.call(["python3", "-u", p], cwd=REPO, stdout=fh,
                                 stderr=subprocess.STDOUT, timeout=1800)
        print(f"{tag} {os.path.basename(p)} rc={rc}")
        for r in [l.strip() for l in open(log) if l.startswith(("ROW", "FAIL"))]:
            print("   " + r, flush=True)


def main():
    os.makedirs(TMP, exist_ok=True)
    src = os.path.join(REPO, PATH)
    text = open(src).read()
    if text.count(START) != 1 or text.count(END) != 1:
        print(f"REFUSED: anchors {text.count(START)} {text.count(END)}")
        return 2
    a = text.index(START)
    b = text.index(END)
    v2 = text[:a] + "                ld      a,(TKNAME)\n" + text[b + len(END):]
    if "--v4" in sys.argv:
        # V4: no bound, but 9 B of never-executed padding after tke_fits's ret,
        # so everything from tk_op_eq onward sits where it does in the live build
        pad = "tke_fits:\n                ret\n"
        if v2.count(pad) != 1:
            print(f"REFUSED: V4 anchor count {v2.count(pad)}")
            return 2
        v2 = v2.replace(pad, pad + "                ds      9,0         ; A/B V4 PAD\n")
    tag = "V4" if "--v4" in sys.argv else "V2"
    before = knife_guard.hashes()
    try:
        open(src, "w").write(v2)
        ok, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
        if brc or not ok:
            print(f"{tag}: build rc={brc} reached-ROM={ok} -- NOT SCORED")
        else:
            probes(tag)
    finally:
        open(src, "w").write(text)
    ok, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    print(f"restored: clean build rc={brc} reached-ROM={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
