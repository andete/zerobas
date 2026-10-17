#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-HFOXOOM knife: does basicint-acceptance's `rvtarr` row see lh_adopt's reset?

  K-HO1 lh_adopt's test `jr z,lha_kept` -> `jr c,lha_kept`: a VARTAB the ,R code
        moved UP skips the variable-chain reset again (the reset stays reachable,
        so check_dead_code accepts the build)   -> rvtarr DIVERGES, rvt64 SAME
Each cut must prove it BUILT (the ROM moved) and keep the pins (`make pin-check`).
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "hfoxoom_knife")
KNIVES = [
    ("K-HO1", {"basic/missing.asm": [("                jr      z,lha_kept          ; the code left VARTAB where it was\n",
                                      "                jr      c,lha_kept          ; KNIFE K-HO1\n")]},
     {"rvtarr"}),
]
ROWSRUN = ["rvtarr", "rvt64"]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def red_rows(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_basicint.py"] + ROWSRUN,
                        stdout=fh, stderr=subprocess.STDOUT, timeout=3600)
    return {ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln}


def main():
    os.makedirs(TMP, exist_ok=True)
    files = sorted({f for _t, fe, _p in KNIVES for f in fe})
    saved = {f: open(f).read() for f in files}
    for _t, fe, _p in KNIVES:
        for f, edits in fe.items():
            cut(saved[f], edits)
    for tag, fe, pred in KNIVES:
        before = knife_guard.hashes()
        try:
            for f, edits in fe.items():
                open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            red = red_rows(tag)
            print(f"{tag}: diverging {sorted(red)}; predicted {sorted(pred)} -> "
                  f"{'HIT' if red == pred else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = red_rows("restore")
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(sorted(red)) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
