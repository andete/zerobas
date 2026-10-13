#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ARYCUR knife: do the new graphics-acceptance rows SEE the alias?

K-AC1  basic/sysvars.inc: ARY_CUR back at $EB2F, where its high byte is GFX_OP.
       Predicted: phase B's draw_arr_sub, draw_xarr_sub and vdp_arr_idx FAIL
       (the two DRAW rows by hanging -- no reading), the other five PASS.
Built through knife_guard; restored on a CLEAN build and phase B re-run green.
(The clean build drops build/'s sweep pins: re-run the sweeps before tiers-md.)
"""
import io, os, sys, contextlib, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "scratchpad"), os.path.join(REPO, "probes", "basic"),
                os.path.join(REPO, "probes", "lib")]
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "arycur_knife")
SRC = "basic/sysvars.inc"
OLD = "ARY_CUR         equ     $EB46   ;"
NEW = "ARY_CUR         equ     $EB2F   ;"


def phase_b():
    import importlib
    import basic_probe_graphics as g
    importlib.reload(g)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fails = g.phase_b()
    rows = [ln.split()[:2] for ln in buf.getvalue().splitlines()
            if ln.strip().startswith(("PASS", "FAIL"))]
    return fails, [n for v, n in rows if v == "FAIL"], len(rows)


def main():
    os.makedirs(TMP, exist_ok=True)
    text = open(SRC).read()
    if text.count(OLD) != 1:
        print(f"K-AC1: REFUSED, anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-AC1.log", before)
        if brc or not moved:
            print(f"K-AC1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            os.system("make repack-machine > /dev/null 2>&1")
            fails, red, n = phase_b()
            print(f"K-AC1: phase B {fails} of {n} FAIL: {red}", flush=True)
            print("K-AC1: predicted FAIL = draw_arr_sub, draw_xarr_sub, vdp_arr_idx")
    finally:
        open(SRC, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    os.system("make repack-machine > /dev/null 2>&1")
    fails, red, n = phase_b()
    print(f"restored: build rc={brc}; phase B {fails} of {n} FAIL"
          + (f" -- RESTORE BROKEN {red}" if fails else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
