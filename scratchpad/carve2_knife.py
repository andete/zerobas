#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-NGRAM (2026-10-10) knife for the var_alloc_or_find rewrite: cutting
str_set_key's failure branch (`jr nc,ssk_target_oom`) must change the
string-scalar Out-of-memory witness (scratchpad/sskoom_probe.py on zerobas).
array-acceptance was the first choice and moved NOTHING under this cut
(carve2_knife_arrays.out): its OOM rows assign literals, stored by reference.

Compares the whole gate output, row by row, cut vs uncut. 🔴 RESTORE ON EVERY
EXIT: the original held in memory, put back by try/finally AND atexit;
knife_guard proves the cut reached the installed ROM.
"""
import atexit, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/vars.asm"
OLD = "                jr      nc,ssk_target_oom\n"
NEW = "                nop                         ; K-NG1 CUT\n                nop\n"
TMP = "/tmp/zerobas"
PROBE = "python3 -u scratchpad/sskoom_probe.py C-BIOS_MSX1_EU_REPACK_NODISK"


def run(log):
    with open(log, "w") as fh:
        rc = subprocess.call(PROBE, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    return rc, [l.rstrip() for l in open(log)]


def main():
    os.makedirs(TMP, exist_ok=True)
    subprocess.call("make repack-machine > /tmp/zerobas/ng1_base_build.out 2>&1", shell=True)
    brc, base = run(f"{TMP}/ng1_base.out")
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor count {orig.count(OLD)}")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/K-NG1_build.out", before)
        print(knife_guard.report("K-NG1", moved, before, after))
        if rc or not moved:
            print("K-NG1: build failed or INERT -- refusing to score")
            return 2
        crc, cut = run(f"{TMP}/K-NG1_probe.out")
    finally:
        restore()
        atexit.unregister(restore)
    subprocess.call("make repack-machine > /tmp/zerobas/ng1_restore.out 2>&1", shell=True)
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
