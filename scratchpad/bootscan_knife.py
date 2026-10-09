#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-BOOTSCAN knife: cutting the `ld (SCNCNT),a` store must fail EXACTLY the two
zerobas rows of probes/basic/basic_probe_bootkey.py (nodisk, disk) and leave the
VG-8020 control passing. Every row must be PRINTED (D-KNIFEROWS: a run with rows
missing refuses rather than scoring them as unmoved).

🔴 RESTORE ON EVERY EXIT: the original held in memory, put back by try/finally
AND atexit; knife_guard proves the cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/interp.asm"
OLD = "                ld      (SCNCNT),a\n"
NEW = "                nop                         ; K-BS1 CUT\n                nop\n                nop\n"
WANT = {"nodisk", "disk"}
ALL = {"vg8020", "nodisk", "disk"}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_bootkey.py"


def rows(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW (\w+) gap=\S+ (\w+)", open(log).read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor count {orig.count(OLD)}")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/K-BS1_build.out", before)
        print(knife_guard.report("K-BS1", moved, before, after))
        if rc or not moved:
            print("K-BS1: build failed or INERT -- refusing to score")
            return 2
        with open(f"{TMP}/K-BS1_probe.out", "w") as fh:
            subprocess.call(PROBE, shell=True, stdout=fh, stderr=subprocess.STDOUT)
    finally:
        restore()
        atexit.unregister(restore)
    got = rows(f"{TMP}/K-BS1_probe.out")
    print(open(f"{TMP}/K-BS1_probe.out").read().strip())
    if set(got) != ALL:
        print(f"K-BS1: KNIFE RUN INCOMPLETE -- rows {sorted(ALL - set(got))} never printed")
        return 2
    failed = {r for r, v in got.items() if v != "PASS"}
    subprocess.call("make repack-machine > /tmp/zerobas/bsknife_restore.out 2>&1", shell=True)
    ok = failed == WANT
    print(f"\n{'PASS' if ok else 'FAIL'}  K-BS1: failed {sorted(failed)} (want exactly {sorted(WANT)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
