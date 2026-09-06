#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DIRSTAMP — is the per-`PUT` directory stamp what makes the third write slow?

D-PUTIO left one candidate standing: zerobas calls `fat_dir_update` on EVERY
`PUT`, and `frnd_update_size`'s own comment records that the CF-3300 does not --
after `PUT #1,1` the reference moves `LOF`'s field live while *"the on-disk
DIRECTORY entry still holds 0"*. Two extra physical accesses per write, on an
emulated drive that charges for them.

PREDICTIONS, WRITTEN BEFORE THE RUN:

  K-DS1  `jp fat_dir_update` -> `ret` at the tail of fat_rand_put.
         If the stamp is the whole cost, n=3 drops from 3.0 to <=0.5.
         🔴 I DO NOT EXPECT THAT, and the reason is arithmetic: a CONSTANT
         per-write overhead predicts a constant cost, and what D-RUNGAP measured
         is a STEP -- <=0.5 for one and two writes, 3.0 for three. So the
         likely outcome is a figure that MOVES without the shape changing, which
         would make the stamp a contributor and not the cause.

⚠️ THE CUT IS A DIAGNOSTIC, NOT A FIX. Dropping the stamp loses the file size on
disk; nothing here proposes shipping it. The knife is restored byte-identically
and the ROM hash is checked, because a knife that did not reach the ROM reports
"moved nothing", which is what a cut that legitimately found nothing looks like
[[a-knife-can-be-inert-because-the-build-did-not-happen]].
"""
from __future__ import annotations

import atexit
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import knife_guard                                                # noqa: E402
import rungap_probe as R                                          # noqa: E402

SRC = os.path.join(os.path.dirname(HERE), "basic", "randio-body.inc")
CUT = ("                jp      fat_dir_update      ; tail: stamp first cluster "
       "+ size into dir",
       "                ret                         ; K-DS1 CUT (restored on exit)")
ROWS = [(f"n.same{n}", R.samerec(n), "ABCDEFGH"[n - 1] * 3) for n in (3, 4, 6)]

# 🔴 THE FIRST RUN OF THIS KNIFE SAID "CHANGED NOTHING" AND COULD NOT HAVE KNOWN.
# It was driven by rungap_probe BEFORE D-PUTFLOOR fixed two bugs in it: a
# `run_gap` below `step` is a no-op (so every rung under 2.5 was one experiment),
# and the mounted .dsk path was keyed on the LINE COUNT, so different programs
# shared an image the emulator writes to. A verdict of "no change" from an
# instrument that cannot resolve the range it is scanning is not a refutation.
# Re-run against the fixed probe, with the refcache off.


def sweep_all(tag):
    out = {}
    for label, lines, want in ROWS:
        print(f"  {tag} {label} on zb (want {want}):")
        out[label] = R.sweep("zb", lines, want)
        print()
    return out


def main():
    orig = open(SRC, encoding="utf-8").read()
    if orig.count(CUT[0]) != 1:
        print(f"KNIFE BROKEN: the fat_dir_update tail is not unique in {SRC}")
        return 1
    restore = lambda: open(SRC, "w", encoding="utf-8").write(orig)   # noqa: E731
    atexit.register(restore)

    print("\\n=== BASE (unmodified) ===")
    subprocess.call("make repack-machine", shell=True,
                    stdout=open("/tmp/zerobas/dirstamp_base.log", "w"),
                    stderr=subprocess.STDOUT)
    base = sweep_all("base")

    try:
        open(SRC, "w", encoding="utf-8").write(orig.replace(*CUT))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build("/tmp/zerobas/dirstamp_k.log",
                                             before, clean=True)
        print("K-DS1: " + knife_guard.report("K-DS1", moved, before, after))
        if rc or not moved:
            print("K-DS1: \🔴 BUILD FAILED or ROM UNCHANGED — the cut is INERT")
            return 1
        cut = sweep_all("K-DS1")
    finally:
        restore()
        atexit.unregister(restore)
        subprocess.call("make repack-machine", shell=True,
                        stdout=open("/tmp/zerobas/dirstamp_restore.log", "w"),
                        stderr=subprocess.STDOUT)

    print("=" * 66)
    print(f"  {'row':10} {'base':>8} {'K-DS1':>8}   smallest run_gap that completes")
    for label, _, _ in ROWS:
        f = lambda v: f">{R.GAPS[-1]}" if v is None else f"{v}"      # noqa: E731
        print(f"  {label:10} {f(base[label]):>8} {f(cut[label]):>8}")
    b3, c3 = base.get("n.same3"), cut.get("n.same3")
    print()
    if b3 and c3 and c3 <= 0.5 < b3:
        print("\🟢 the directory stamp IS the cost: cutting it makes three writes "
              "as cheap as one.")
    elif b3 and c3 and c3 < b3:
        print("\⚠\️ the stamp CONTRIBUTES but is not the whole cost — the step is "
              "still there. Prediction held.")
    else:
        print("\🔴 cutting the stamp changed nothing measurable: the candidate is "
              "REFUTED and D-PUTIO's last standing explanation is gone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
