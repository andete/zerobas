#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LISTFLT knives: each cut must move EXACTLY its predicted rows of the 24
LIST rows (scratchpad/listflt_probe.py, both rounds; zerobas column; a process
per reading, a clean build per cut).

  K-LF1  the dispatch removed (no float arm)       -> all 24
  K-LF2  the single's `!` suffix removed            -> the five `!` rows
  K-LF3  the x = -1 arm loses its lead digit        -> `.05` only
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC = "basic/detok.inc"
BANG = {"r1:103", "r1:111", "r2:105", "r2:106", "r2:110"}   # 10000000000! 40000! 123456! 0! 100000!
KNIVES = {
    "K-LF1": ("                jp      z,dt_float          ; detok_op below)\n",
              "                nop                         ; K-LF1 CUT\n"
              "                nop\n                nop\n", None),
    "K-LF2": ("                ld      a,'!'\ndtf_sfx:\n",
              "                jr      dtf_end             ; K-LF2 CUT\ndtf_sfx:\n", BANG),
    "K-LF3": ("                dec     hl\n                inc     b\n",
              "                dec     hl\n                nop                         ; K-LF3 CUT\n",
              {"r2:103"}),
}
TMP = "/tmp/zerobas"


def ours(log):
    rows = {}
    for tag, arg in (("r1", []), ("r2", ["2"])):
        with open(f"{log}.{tag}", "w") as fh:
            subprocess.call(["python3", "-u", "scratchpad/listflt_probe.py", *arg],
                            stdout=fh, stderr=subprocess.STDOUT)
        t = open(f"{log}.{tag}").read().split("== ")
        if len(t) < 3:
            continue
        for l in t[2].splitlines()[1:]:
            m = re.match(r"\s*(1\d\d) (.*)$", l)
            if m:
                rows[f"{tag}:{m.group(1)}"] = m.group(2).strip()
    return rows


def main():
    only = sys.argv[1:] or list(KNIVES)
    os.makedirs(TMP, exist_ok=True)
    _, before0, rc = knife_guard.build(f"{TMP}/lfknife_base_build.out", knife_guard.hashes(),
                                       clean=True)
    if rc:
        print("BASELINE BUILD FAILED")
        return 2
    base = ours(f"{TMP}/lfknife_base")
    print(f"base: {len(base)} rows", flush=True)
    if len(base) != 24:
        print(f"BASELINE BROKEN: {base}")
        return 2
    allrows = set(base)
    fails = []
    for k in only:
        old, new, want = KNIVES[k]
        want = allrows if want is None else want
        orig = open(SRC).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)}")
            return 2
        restore = lambda o=orig: open(SRC, "w").write(o)
        atexit.register(restore)
        try:
            open(SRC, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before, clean=True)
            print(knife_guard.report(k, moved, before, after), flush=True)
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            cut = ours(f"{TMP}/{k}_probe")
        finally:
            restore()
            atexit.unregister(restore)
        got = {r for r in allrows if cut.get(r) != base[r]}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {len(got)} {sorted(got)[:8]} "
              f"(want exactly {len(want)})", flush=True)
        if not ok:
            fails.append(k)
    _, after, _ = knife_guard.build(f"{TMP}/lfknife_restore.out", clean=True)
    print(f"restored ROM hashes {after} (baseline {before0})")
    if after != before0:
        print("RESTORE MISMATCH: the installed ROM is not the baseline's")
        return 2
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
