#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-OPENWILD knife: cut OPEN's wildcard refusal and run kwsweep on
t8openinput56 alone.

  K-OWD  -> the row reads DIVERGENT (53 vs the CF-3300's 56), both sides
            readable, and kwsweep EXITS non-zero naming it (D-KWDIVPIN's rule)

RESTORE ON EVERY EXIT: original held in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/files.asm"
OLD = """                cp      (hl)
                jp      z,pdf_badname       ; 56
"""
NEW = """                cp      (hl)
                nop                         ; K-OWD CUT (restored on exit)
                nop
                nop
"""


def main():
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print("KNIFE BROKEN: anchor")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build("/tmp/zerobas/owd_build.out", before)
        print(knife_guard.report("K-OWD", moved, before, after))
        if rc or not moved:
            print("K-OWD: build failed or inert -- refusing to score")
            return 2
        r = subprocess.run("make kwsweep ONLY=t8openinput56", shell=True, capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if "t8openinput56" in l and l.startswith(("DIVERGENT", "SUPPORTED"))]
        print(lines[0] if lines else "(no verdict line)")
        print("UNPINNED line:", any("UNPINNED SUPPORT DIVERGENCE" in l for l in r.stdout.splitlines()))
        print("make rc:", r.returncode)
        ok = r.returncode != 0 and any("UNPINNED SUPPORT DIVERGENCE" in l for l in r.stdout.splitlines())
        print("PASS  K-OWD" if ok else "FAIL  K-OWD")
    finally:
        restore()
        atexit.unregister(restore)
    subprocess.call("make repack-machine > /tmp/zerobas/owd_restore.out 2>&1", shell=True)
    print("restored:", knife_guard.hashes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
