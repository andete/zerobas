#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DRAWSUBVAR knife: do the new graphics-acceptance rows SEE the check?

K-DS1  sub/graphics.asm: the first-character test in gdrw_sub_scan removed.
       Predicted: phase B's draw_sub_const, draw_sub_xlit, draw_sub_empty and
       draw_sub_neg FAIL, the other eight PASS.
(Runs 1-2: the restore read red from a stale in-process refcache identity --
NOT SCORED; knife_guard.build now clears it.)
Built through knife_guard; restored on a CLEAN build and phase B re-run green.
(The clean build drops build/'s sweep pins: re-run the sweeps before tiers-md.)
"""
import io, os, sys, contextlib, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [os.path.join(REPO, "scratchpad"), os.path.join(REPO, "probes", "basic"),
                os.path.join(REPO, "probes", "lib")]
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "drawsubvar_knife")
SRC = "sub/graphics.asm"
OLD = "                ld      a,(GFX_DEXP)\n                cp      'A'\n                jp      c,gdrw_err5\n"
NEW = "                ; KNIFE K-DS1: the first-character test removed\n"


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
        print(f"K-DS1: REFUSED, anchor count {text.count(OLD)}")
        return 2
    before = knife_guard.hashes()
    try:
        open(SRC, "w").write(text.replace(OLD, NEW))
        moved, _, brc = knife_guard.build(f"{TMP}/mk_K-DS1.log", before)
        if brc or not moved:
            print(f"K-DS1: build rc={brc} ROM moved={moved} -- NOT SCORED")
        else:
            os.system("make repack-machine > /dev/null 2>&1")
            fails, red, n = phase_b()
            print(f"K-DS1: phase B {fails} of {n} FAIL: {red}", flush=True)
            print("K-DS1: predicted FAIL = draw_sub_const, draw_sub_xlit, draw_sub_empty, draw_sub_neg")
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
