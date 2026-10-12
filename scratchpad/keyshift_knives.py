#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-KEYSHIFT knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_keyshift.py (zerobas column; a process per reading,
a clean build per cut).

  K-KS1  the painter's F6..F10 slot choice removed     -> the five switching rows
  K-KS2  zb_chsns skips straight to CHSNS (no check)   -> the same five
  K-KS3  the KEY OFF guard (CNSDFG) removed            -> keyoff alone
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SWITCH = {"prompt", "inputs", "input", "lineinput", "inkey"}
GUARD = ("                inc     a                   ; $FF (shown) -> 0\n"
         "                jr      nz,zks_go\n")
KNIVES = {
    "K-KS1": ("sub/keystr.asm",
              "                ld      a,(FNKSWI)\n                dec     a                   ; 1 -> 0, 0 -> $FF\n",
              "                xor     a                   ; K-KS1 CUT\n                nop\n                nop\n",
              SWITCH),
    "K-KS2": ("basic/islands.asm", GUARD,
              "                inc     a                   ; $FF (shown) -> 0\n"
              "                jr      zks_go              ; K-KS2 CUT\n", SWITCH),
    "K-KS3": ("basic/islands.asm", GUARD,
              "                inc     a                   ; $FF (shown) -> 0\n"
              "                nop                         ; K-KS3 CUT\n                nop\n",
              {"keyoff"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_keyshift.py"],
                        stdout=fh, stderr=subprocess.STDOUT)
    rows, cur = {}, None
    for line in open(log):
        m = re.match(r"ROW (\S+)", line)
        if m:
            cur = m.group(1)
        m = re.match(r"\s+zerobas \[(.*)\] (SAME|DIVERGES)", line)
        if m and cur:
            rows[cur] = m.group(1)
    return rows


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    _, before0, rc = knife_guard.build(f"{TMP}/ksknife_base_build.out", knife_guard.hashes(),
                                       clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/ksknife_base.out")
    print(f"base: {len(base)} rows", flush=True)
    if len(base) != 7:
        print(f"BASELINE BROKEN: {base}")
        return 2
    fails = []
    for k in only:
        src, old, new, want = KNIVES[k]
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
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            cut = ours(f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        got = {r for r in base if cut.get(r) != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly {sorted(want)})",
              flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/ksknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
