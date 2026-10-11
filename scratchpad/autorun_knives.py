#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-AUTORUN knives: each cut must move EXACTLY its predicted rows of
scratchpad/autorun_e2e_probe.py (zerobas diskless column: ascii, binary,
tokenised; a process per reading, a clean build per cut).

  K-AR1  the H_READ call removed  -> all three (openMSX's breakpoint never fires)
  K-AR2  the H_MAIN call removed  -> all three. PREDICTED "tokenised only" and
         MISSED (autorun_knives_run1.out): the installed openMSX's H.READ
         callback is `auto_run_cb {{}} ...` -- it types NOTHING and only arms a
         breakpoint on H.MAIN; the load command is typed when H.MAIN fires (and
         CLOAD's RUN on the NEXT H.MAIN). So every tape type needs both hooks.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ROWS = ["ascii", "binary", "tokenised"]
ALL = set(ROWS)
KNIVES = {
    "K-AR1": ("basic/repl.asm",
              "                call    H_READ              ; D-AUTORUN: the prompt is up (the\n",
              "                nop                         ; K-AR1 CUT\n",
              {"ascii", "binary", "tokenised"}),
    "K-AR2": ("basic/repl.asm",
              "                call    H_MAIN              ; D-AUTORUN: a line is about to be\n",
              "                nop                         ; K-AR2 CUT\n",
              {"ascii", "binary", "tokenised"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "scratchpad/autorun_e2e_probe.py"],
                        stdout=fh, stderr=subprocess.STDOUT,
                        env=dict(os.environ, AUTORUN_MACHINES="C-BIOS_MSX1_EU_REPACK_NODISK"))
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^\S+\s+(ascii|binary|tokenised)\s+(\S+)", open(log).read(), re.M)}


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    _, before0, rc = knife_guard.build(f"{TMP}/arknife_base_build.out", knife_guard.hashes(),
                                       clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/arknife_base.out")
    print(f"base: {base}", flush=True)
    if set(base) != ALL or any(v != "RAN" for v in base.values()):
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
        if set(cut) != ALL:
            print(f"{k}: KNIFE RUN INCOMPLETE -- {cut}")
            return 2
        got = {r for r in ALL if cut[r] != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly "
              f"{sorted(want)})  {cut}", flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/arknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH: the installed ROM is not the baseline's")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
