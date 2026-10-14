#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RG7 knife: does rg7-acceptance SEE cbios-repack/vdp-reg7.patch?

K-RG1  tools/build_repacked_cbios.py: the patch left out of PATCHES and the old
       repacked sha1 pin put back (both anchors in the one file).
       Predicted: s0 s1 s2 s3 s2c s0c DIVERGE; s1tab SAME (the old code filled
       SCREEN 1's colour table with the same FORCLR*16+BAKCLR byte).
Built through knife_guard (ROM must MOVE), restored, rebuilt CLEAN, re-run green.
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "rg7_knife")
CUTS = [
    ("K-RG1", "tools/build_repacked_cbios.py",
     '    os.path.join(REPO, "cbios-repack", "vdp-reg7.patch"),\n',
     '',
     ["s0", "s1", "s2", "s3", "s2c", "s0c"]),
    ("K-RG1", "tools/build_repacked_cbios.py",
     'REPACKED_SHA1 = "373752916ff09f56e319ac63edd93d178fe31566"',
     'REPACKED_SHA1 = "f0e3e80512bc5c70d968ca868241a3f18dd838ce"',
     None),
]


def suite(tag):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "rg7-acceptance"], stdout=fh,
                             stderr=subprocess.STDOUT, timeout=3600)
    red = [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]
    return rc, red


def main():
    os.makedirs(TMP, exist_ok=True)
    for tag, src, old, new, pred in CUTS:
        text = open(src).read()
        if text.count(old) != 1:
            print(f"{tag}: REFUSED, anchor count {text.count(old)} in {src}", flush=True)
            return 2
    tag, src, pred = CUTS[0][0], CUTS[0][1], CUTS[0][4]
    for _ in [0]:
        text = open(src).read()
        cut = text
        for _t, _s, old, new, _p in CUTS:
            cut = cut.replace(old, new)
        before = knife_guard.hashes()
        try:
            open(src, "w").write(cut)
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            if brc or not moved:
                print(f"{tag}: build rc={brc} ROM moved={moved} -- NOT SCORED", flush=True)
                continue
            rc, red = suite(tag)
            score = "HIT" if sorted(red) == sorted(pred) else "MISS"
            print(f"{tag}: rg7 {'RED' if rc else 'green'}, diverging {red}; "
                  f"predicted {pred} -> {score}", flush=True)
        finally:
            open(src, "w").write(text)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    rc, red = suite("restore")
    print(f"restored: build rc={brc}; rg7 {'RED -- RESTORE BROKEN ' + str(red) if rc else 'green'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
