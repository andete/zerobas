#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-CIRCOVF -- are the two arc DIFFs MINE, or were they already shipping?

scratchpad/circovf_arc.py found 2 divergences after the fix:

    arc_r700_a137  CIRCLE(128,96),700,15,0,1.57,.137   ref 127 px / zb 126 px
    arc_big_r400   CIRCLE(128,96),400,15,-1.57,0       ref 97 px  / zb 97 px, 1 col off

"After the fix" is not "because of the fix". This reverts the slice's source
edits, rebuilds the PRE-SLICE ROM, and re-asks the same rows -- so the answer is
measured on both builds instead of argued from one.

⚠️ It also re-asks the four rows that came back BOTH-BLANK. Both-blank is not
agreement, it is a vacuous row (D-CIRCDOM §4.2: `r200`/`r255` agreed for exactly
that wrong reason), and a row set whose middle is vacuous cannot carry a verdict
about the arc mask at all.

Discipline per docs/dev-workflow.md §Knives: snapshot to a temp dir, restore in
a `finally`, build BEFORE each measurement, and gate on the ROM hash so a stale
build cannot be scored as a result.

    python3 -u scratchpad/circovf_prefix.py
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, HERE)

import omsx_repl                                    # noqa: E402
from circovf_calib import reduce_plane              # noqa: E402

REF = os.environ.get("ZEROBAS_REF_MACHINE", "Philips_VG_8020")
ZB = os.environ.get("ZEROBAS_SUBROM_INTTEST_MACHINE",
                    "C-BIOS_MSX1_EU_REPACK_DISK")
LINIT = "COLOR15,4,7:SCREEN2"
PLANE = [(0, 6144)]

EDITED = ["sub/graphics.asm", "basic/sysvars.inc"]
PRE_SHA = "8161c1a2"        # sub.rom at b602eac, before this slice
POST_SHA = "bc7573df"       # sub.rom with the slice applied

ROWS = [
    # round 2: the arc2 rows. arcctl_r200 was written as a GREEN CONTROL and
    # came back RED -- at r=200 every cross product is 40000, inside 16 bits on
    # BOTH arithmetics, and ASPS=256 makes the scale the identity on both, so
    # NOTHING this slice touches can move it. If it is red on the pre-slice
    # build too, the arc mask has a second, pre-existing defect at these angles
    # and the arc rows cannot speak to the widened product at all.
    ("arcctl_r200", "CIRCLE(128,352),200,15,1.1,2.04"),
    ("arcovf_span", "CIRCLE(128,445),284,15,1.1,2.04"),
    ("arcovf_right", "CIRCLE(128,445),284,15,1.1,1.5708"),
    ("arcctl_r15", "CIRCLE(60,60),15,15,0,1.57"),
    ("arc_r120_a", "CIRCLE(128,96),120,15,1.1,2.04"),
]


def prog(stmts):
    return stmts + [f"GOTO {10 * (len(stmts) + 1)}"]


def red(hexs):
    if not hexs:
        return None
    b = bytes.fromhex(hexs)
    return ("SHORT", len(b), None) if len(b) != 6144 else reduce_plane(b)


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True,
                          text=True)


def sub_sha():
    p = os.path.join(REPO, "build", "sub.rom")
    if not os.path.exists(p):
        return "MISSING"
    return hashlib.sha256(open(p, "rb").read()).hexdigest()[:8]


def build():
    r = sh("rm -rf build && make repack-machine")
    return r.returncode == 0, sub_sha()


def measure():
    out = {}
    for lbl, ops in ROWS:
        specs = [("stored", prog([LINIT, ops]))]
        out[lbl] = (
            red(omsx_repl.run_cases(REF, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0]),
            red(omsx_repl.run_cases(ZB, specs, batch=False,
                                    capture=("vram_segs", PLANE), step=25.0)[0]),
        )
    return out


def main():
    snap = tempfile.mkdtemp(prefix="circovf-prefix-")
    for rel in EDITED:
        shutil.copy2(os.path.join(REPO, rel),
                     os.path.join(snap, os.path.basename(rel)))
    print(f"snapshot: {snap}")
    try:
        print("=== POST-slice build ===")
        ok, sha = build()
        if not ok or sha != POST_SHA:
            print(f"ABORT: post-slice build ok={ok} sub.rom={sha} "
                  f"(expected {POST_SHA})")
            return 2
        print(f"  sub.rom {sha}")
        post = measure()

        print("\n=== reverting the slice's source edits ===")
        r = sh("git checkout -- " + " ".join(EDITED))
        if r.returncode != 0:
            print(f"ABORT: revert failed: {r.stderr}")
            return 2
        ok, sha = build()
        if not ok or sha != PRE_SHA:
            print(f"ABORT: pre-slice build ok={ok} sub.rom={sha} "
                  f"(expected {PRE_SHA}) -- a full revert MUST rebuild the "
                  f"pre-slice image byte for byte")
            return 2
        print(f"  sub.rom {sha}  <- rebuilt the pre-slice image EXACTLY")
        pre = measure()

        print("\n" + "=" * 72)
        print("PRE vs POST -- is each divergence MINE or already shipping?")
        print("=" * 72)
        for lbl, ops in ROWS:
            pr, pz = pre[lbl]
            qr, qz = post[lbl]
            pre_d = "DIFF" if pr != pz else "agree"
            post_d = "DIFF" if qr != qz else "agree"
            vac = " ⚠️ VACUOUS (both blank)" if (pr and pr[0] == 0 and
                                                 pz and pz[0] == 0) else ""
            if pre_d == "DIFF" and post_d == "DIFF":
                verdict = "PRE-EXISTING -- not introduced by this slice"
            elif pre_d == "agree" and post_d == "DIFF":
                verdict = "🔴 INTRODUCED BY THIS SLICE"
            elif pre_d == "DIFF" and post_d == "agree":
                verdict = "FIXED by this slice"
            else:
                verdict = "unchanged, agreeing"
            print(f"\n  {lbl:14} {ops}{vac}")
            print(f"     pre  ({PRE_SHA}) {pre_d:5} ref={pr} zb={pz}")
            print(f"     post ({POST_SHA}) {post_d:5} ref={qr} zb={qz}")
            print(f"     -> {verdict}")
        return 0
    finally:
        for rel in EDITED:
            shutil.copy2(os.path.join(snap, os.path.basename(rel)),
                         os.path.join(REPO, rel))
        print(f"\nrestored {EDITED} from {snap}")
        ok, sha = build()
        print(f"rebuilt after restore: sub.rom {sha} "
              f"({'OK' if sha == POST_SHA else 'MISMATCH -- TREE IS DIRTY'})")


if __name__ == "__main__":
    sys.exit(main())
