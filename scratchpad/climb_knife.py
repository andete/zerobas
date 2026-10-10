#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DIMRESERVE S1 (2026-10-10) knife for the logical-layer climber: cutting
the "rhs takes only TIGHTER operators" step (the three `inc hl` before the rhs
`call evc_min`) makes a same-level chain RIGHT-associative. AND/OR/XOR/EQV
chains agree either way; IMP does not, so ONLY logicops-acceptance's IMP
associativity row(s) may move.

Compares the whole gate output, row by row, cut vs uncut. 🔴 RESTORE ON EVERY
EXIT: the original held in memory, put back by try/finally AND atexit;
knife_guard proves the cut reached the installed ROM.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/expr.asm"
OLD = "                inc     hl\n                inc     hl\n                inc     hl                  ; the rhs takes only TIGHTER operators\n"
NEW = "                nop                         ; K-CL1 CUT\n                nop\n                nop\n"
TMP = "/tmp/zerobas"
PROBE = "make logicops-acceptance"


def run(log):
    with open(log, "w") as fh:
        rc = subprocess.call(PROBE, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    return rc, [l.rstrip() for l in open(log)]


def main():
    os.makedirs(TMP, exist_ok=True)
    subprocess.call("make repack-machine > /tmp/zerobas/cl1_base_build.out 2>&1", shell=True)
    brc, base = run(f"{TMP}/cl1_base.out")
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor count {orig.count(OLD)}")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/K-CL1_build.out", before)
        print(knife_guard.report("K-CL1", moved, before, after))
        if rc or not moved:
            print("K-CL1: build failed or INERT -- refusing to score")
            return 2
        crc, cut = run(f"{TMP}/K-CL1_probe.out")
    finally:
        restore()
        atexit.unregister(restore)
    subprocess.call("make repack-machine > /tmp/zerobas/cl1_restore.out 2>&1", shell=True)
    print(f"uncut rc={brc} lines={len(base)}   cut rc={crc} lines={len(cut)}")
    import difflib
    diff = [l for l in difflib.unified_diff(base, cut, "uncut", "cut", n=0, lineterm="")
            if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    print(f"{len(diff)} differing line(s):")
    for l in diff[:40]:
        print("  " + l[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
