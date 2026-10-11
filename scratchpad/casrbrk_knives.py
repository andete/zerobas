#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASRBRK knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_casrbrk.py, judged on the zerobas column, a fresh
process per reading and a clean build per cut (D-CASWBRK's runner, whose first
in-process cut was served from the refcache).

  K-CR1  TAPIN's cas_stop test cut            -> the data rows
  K-CR2  (retired: TAPION's relock test moved nothing and was dropped)
  K-CR3  BLOAD's header-loop CF test cut      -> bb2
  K-CR4  BLOAD's data loop back to bl_load_error -> bb8 bhold
  K-CR5  cas_ascii_drive's past-the-end raise cut -> ab8 ab15 mb8
  K-CR6  cas_in_getbyte's raise cut           -> ib8
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
# 🔴 A FRESH PROCESS PER READING, AND A CLEAN BUILD PER CUT. The first cut of this
# runner imported the probe and called it in-process: the refcache memoises the
# ROM identity per process (omsx_repl's hit path says knife runners must not), so
# K-CW1's eight readings were served from the cache -- `moved []` -- and, being
# instant, let K-CW2's edit land in the same second as the last build, which
# `make` then did not see (knife_guard refused it as INERT).
ALL = {"bnb", "bb2", "bb8", "bhold", "anb", "ab2", "ab8", "ab15", "cnb", "cb8",
       "mb8", "inb", "ib8"}
KNIVES = {
    "K-CR1": ("tape/tape.asm",
              "                call    cas_stop\n                ret     c\n                call    cas_level       ; D = current level\n",
              "                call    cas_level       ; D = current level\n",
              # first run (TAPION's test still in): moved ab2, NOT ab8/mb8 --
              # TAPION caught those -- and K-CR2 moved nothing; the test was dropped
              {"ab2", "bb2", "bb8", "bhold", "ab8", "ab15", "cb8", "mb8", "ib8"}),
    # K-CR2 (TAPION's relock test) RETIRED with the test: it moved nothing
    # (scratchpad/casrbrk_knives_run1.out).
    "K-CR3": ("basic/bload-body.inc",
              "                jp      c,bl_tape_dio       ; Ctrl-STOP / I/O -> 19, raised\n",
              "",
              {"bb2"}),
    "K-CR4": ("basic/bload-body.inc",
              "                jp      c,bl_tape_dio       ; D-CASRBRK: Ctrl-STOP in the data -> 19\n",
              "                jp      c,bl_load_error     ; K-CR4 CUT\n",
              {"bb8", "bhold"}),
    "K-CR5": ("basic/cload.asm",
              "                cp      3                   ; CF <=> not marked\n"
              "                ccf                         ; (the first cut returned THAT carry:\n"
              "                ret     nc                  ; every clean LOAD read `load error`)\n"
              "                jp      dpl_dio\n",
              "                xor     a                   ; K-CR5 CUT\n                ret\n",
              {"ab8", "ab15", "mb8"}),
    "K-CR6": ("basic/cload.asm",
              "                jp      c,dpl_dio\n                cp      $1A\n",
              "                ret     c                   ; K-CR6 CUT\n                cp      $1A\n",
              {"ib8"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_casrbrk.py"],
                        stdout=fh, stderr=subprocess.STDOUT,
                        env=dict(os.environ, CASRBRK_OURS_ONLY="1"))
    got = {m.group(1): m.group(2).strip() for m in
           re.finditer(r"^== (\S+)\s+ours (.*)$", open(log, errors="replace").read(), re.M)}
    return got          # "None" is a reading (nothing matched), a MISSING row is not


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    before0 = knife_guard.hashes()
    _, before0, rc = knife_guard.build(f"{TMP}/crknife_base_build.out", before0, clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/crknife_base.out")
    print(f"base: {base}", flush=True)
    if set(base) != ALL or "None" in base.values():
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
            print(f"{k}: KNIFE RUN INCOMPLETE -- rows {sorted(ALL - set(cut))} never printed; "
                  f"refusing to score them as unmoved ({TMP}/{k}_probe.out)")
            return 2
        got = {r for r in ALL if cut[r] != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly "
              f"{sorted(want)})  {cut}", flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/crknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH: the installed ROM is not the baseline's")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
