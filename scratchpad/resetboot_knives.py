#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-RESETBOOT knife: the cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_resetboot.py (a process per reading, a clean build).

  K-RB1  init's SUBSLOT_OK clear removed -> the four zerobas rows (both builds,
         idle and prog); the VG-8020 rows cannot move (not our ROM)
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/interp.asm"
OLD = "                xor     a\n                ld      (SUBSLOT_OK),a\n"
NEW = "                nop                         ; K-RB1 CUT\n"
WANT = {f"{m}/{x}" for m in ("C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK")
        for x in ("idle", "prog")}
TMP = "/tmp/zerobas"


def rows(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_resetboot.py"],
                        stdout=fh, stderr=subprocess.STDOUT)
    return {f"{m.group(1)}/{m.group(2)}": m.group(3) for m in
            re.finditer(r"^ROW (\S+)\s+(idle|prog): .* (PASS|FAIL)$", open(log).read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    _, before0, rc = knife_guard.build(f"{TMP}/rbknife_base_build.out", knife_guard.hashes(),
                                       clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = rows(f"{TMP}/rbknife_base.out")
    print(f"base: {base}", flush=True)
    if len(base) != 6 or any(v != "PASS" for v in base.values()):
        print("BASELINE BROKEN")
        return 2
    orig = open(SRC).read()
    if orig.count(OLD) != 1:
        print(f"KNIFE BROKEN: anchor count {orig.count(OLD)}")
        return 2
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    try:
        open(SRC, "w").write(orig.replace(OLD, NEW))
        before = knife_guard.hashes()
        moved, after, rc = knife_guard.build(f"{TMP}/K-RB1_build.out", before, clean=True)
        print(knife_guard.report("K-RB1", moved, before, after), flush=True)
        if rc or not moved:
            print("K-RB1: BUILD FAILED or INERT")
            return 2
        cut = rows(f"{TMP}/K-RB1_probe.out")
    finally:
        restore()
        atexit.unregister(restore)
    got = {k for k in base if cut.get(k) != base[k]}
    ok = got == WANT
    print(f"{'PASS' if ok else 'FAIL'}  K-RB1: moved {sorted(got)} (want exactly {sorted(WANT)})")
    _, after, _ = knife_guard.build(f"{TMP}/rbknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH")
        return 2
    print("\nALL KNIVES BITE, EACH ON ITS OWN ROWS" if ok else "\nFAILED: K-RB1")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
