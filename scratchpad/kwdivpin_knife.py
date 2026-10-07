#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KWDIVPIN / D-OPENEND knife: cut OPEN's end-of-statement check (the
D-OPENEND fix) and run kwsweep on t8openappend2 alone.

  K-KDP  -> the row reads DIVERGENT with BOTH sides readable, and kwsweep
            EXITS 6 naming it (before D-KWDIVPIN it exited 0 on exactly this)

RESTORE ON EVERY EXIT: original held in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/files.asm"
OLD = """                cp      ':'
                jp      nz,oo_fail_syn      ; junk after the clause: 2, nothing opened
"""
NEW = """                cp      ':'
                jr      oo_endok            ; K-KDP CUT (restored on exit)
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
        moved, after, rc = knife_guard.build("/tmp/zerobas/kdp_build.out", before)
        print(knife_guard.report("K-KDP", moved, before, after))
        if rc or not moved:
            print("K-KDP: build failed or inert -- refusing to score")
            return 2
        r = subprocess.run("make kwsweep ONLY=t8openappend2", shell=True, capture_output=True, text=True)
        lines = [l for l in r.stdout.splitlines() if "t8openappend2" in l and l.startswith(("DIVERGENT", "SUPPORTED"))]
        print(lines[0] if lines else "(no verdict line)")
        print("UNPINNED line:", any("UNPINNED SUPPORT DIVERGENCE" in l for l in r.stdout.splitlines()))
        print("make rc:", r.returncode)
        ok = r.returncode != 0 and any("UNPINNED SUPPORT DIVERGENCE" in l for l in r.stdout.splitlines())
        print("PASS  K-KDP" if ok else "FAIL  K-KDP")
    finally:
        restore()
        atexit.unregister(restore)
    subprocess.call("make repack-machine > /tmp/zerobas/kdp_restore.out 2>&1", shell=True)
    print("restored:", knife_guard.hashes())
    return 0


if __name__ == "__main__":
    sys.exit(main())
