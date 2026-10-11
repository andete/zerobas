#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SUBSIG knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_subsig.py (zerobas column; a process per reading, a
clean build per cut -- D-CASWBRK's lessons).

  K-SG1  the boot scan compares 'C' again (the ROM says "ZB") -> no sub ROM:
         every row on both pairs (predicted p1 p0 only: MISSED -- with no sub
         ROM nothing typed runs at all, the tokeniser being a tenant)
  K-SG2  the EXBRSA write restored -> faf8 on both pairs
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {f"{r}:{n}" for r in ("VG-8020", "CF-3300") for n in ("faf8", "p1", "p0")}
KNIVES = {
    "K-SG1": ("basic/subrom-boot.asm",
              "                cp      'Z'\n",
              "                cp      'C'                 ; K-SG1 CUT\n",
              # predicted p1 p0 only -- MISSED (run 1, subsig_knives_run1.out):
              # with no sub ROM NOTHING typed runs (the tokeniser and the line
              # editor are sub-ROM tenants), so faf8 reads nothing too
              set(ALL)),
    "K-SG2": ("basic/subrom-boot.asm",
              "                ld      (SUBSLOT),a\n                ld      a,1\n",
              "                ld      (SUBSLOT),a\n                ld      (EXBRSA),a          ; K-SG2 CUT\n"
              "                ld      a,1\n",
              {"VG-8020:faf8", "CF-3300:faf8"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_subsig.py"],
                        stdout=fh, stderr=subprocess.STDOUT)
    return {f"{m.group(2)}:{m.group(1)}": m.group(3) for m in re.finditer(
        r"^ROW (\S+)\s+(\S+) \[.*?\] zerobas\[(.*?)\]", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    _, before0, rc = knife_guard.build(f"{TMP}/sgknife_base_build.out", None, clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/sgknife_base.out")
    print(f"base: {base}", flush=True)
    if set(base) != ALL:
        print("BASELINE BROKEN")
        return 2
    fails = []
    for k, (src, old, new, want) in KNIVES.items():
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)} in {src}")
            return 2
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            open(src, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before, clean=True)
            print(knife_guard.report(k, moved, before, after), flush=True)
            if rc or not moved:
                print(f"{k}: build failed or INERT -- refusing to score")
                return 2
            cut = ours(f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        if set(cut) != ALL:
            print(f"{k}: KNIFE RUN INCOMPLETE -- {sorted(ALL - set(cut))} missing")
            return 2
        got = {r for r in ALL if cut[r] != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly {sorted(want)})  {cut}",
              flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/sgknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
