#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASDIRECT knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_casdirect.py (zerobas column; a process per reading,
a clean build per cut).

  K-DS1  the tape LOAD arm back to dpl_err          -> dload pload
  K-DS2  the disk LOAD arm back to dpl_err          -> kload kpload kbinload
  K-DS3  MERGE's shared tail back to stmt_error     -> every MERGE row, tape AND disk
  K-DS4 / K-DS5  (retired: the DIRECTF store and the forced abort they cut moved
                 nothing, run 1, and were removed)
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
ALL = {"dload", "dmerge", "pload", "pmerge", "kload", "kmerge", "kpload", "kpmerge", "kbinload"}
KNIVES = {
    "K-DS1": ("basic/cload.asm",
              "                jr      c,dpl_direct        ; non-numbered line -> 57 (D-CASDIRECT)\n",
              "                jr      c,dpl_err           ; K-DS1 CUT\n",
              {"dload", "pload"}),
    "K-DS2": ("basic/cload.asm",
              "                jr      c,dpl_direct        ; non-numbered line / not an ASCII program\n",
              "                jr      c,dpl_err           ; K-DS2 CUT\n",
              {"kload", "kpload", "kbinload"}),
    "K-DS3": ("basic/files.asm",
              "                jp      c,dpl_direct        ; non-numbered line -> 57 \"Direct statement in\n",
              "                jp      c,stmt_error        ; K-DS3 CUT\n",
              {"dmerge", "pmerge", "kmerge", "kpmerge"}),
    # K-DS4 (no DIRECTF) and K-DS5 (raise_error, not forced) moved NOTHING in
    # run 1 (casdirect_knives_run1.out): both steps were dead and are gone.
}
TMP = "/tmp/zerobas"


def ours(log):
    with open(log, "w") as fh:
        subprocess.call(["python3", "-u", "probes/basic/basic_probe_casdirect.py"],
                        stdout=fh, stderr=subprocess.STDOUT,
                        env=dict(os.environ, CASDIRECT_OURS_ONLY="1"))
    got = {m.group(1): m.group(2).strip() for m in
           re.finditer(r"^== (\S+)\s+ours (.*)$", open(log, errors="replace").read(), re.M)}
    return got          # "None" is a reading (nothing matched), a MISSING row is not


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    before0 = knife_guard.hashes()
    _, before0, rc = knife_guard.build(f"{TMP}/cdknife_base_build.out", before0, clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/cdknife_base.out")
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
    _, after, _ = knife_guard.build(f"{TMP}/cdknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH: the installed ROM is not the baseline's")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
