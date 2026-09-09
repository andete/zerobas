#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FG2 — the faithful pre-guard cut for `do_files`, at NEGATIVE byte cost.

K-FG1 imported K-FI1's cut and could not run: that cut ADDS 6 bytes (a
`ld (DISKOP_OP),a` at the head *in addition to* the `push af`, and a
`ld a,(DISKOP_OP)` at the pop site), and page 1 had 2 B free on 2026-09-07. The
runner correctly said KNIFE INERT and the real cause -- the build never
happened -- lived only in the build log.

\U0001f3af TWO BLOCKERS, AND BOTH ARE GONE.

1. THE BUDGET. TODO.md itself named the byte-neutral shape and then did not take
   it: *"the head write can REPLACE the `push af` rather than precede it, and the
   pop site can drop its two instructions"*. Done properly that is
   `push af`(1) -> `ld (DISKOP_OP),a`(3) = **+2**, minus the DISKSLOT abort's
   balancing `pop af`(1) = **-1**, minus the pop site's `pop af`(1) +
   `ld (DISKOP_OP),a`(3) = **-4**. Net **-3 B**: the cut is SMALLER than the
   guard, so no wall can refuse it. It never needed a budget at all.

2. "WHICH PRE-FIX MACHINE?" The item worried that inverting only the DISKOP_OP
   half of commit 227a1d37 -- which changed the guard AND the filespec parser in
   one -- builds "a verb that never existed": today's expression parser with
   yesterday's parked selector.
   \U0001f534 THAT IS TRUE AND IT IS THE WRONG TEST TO APPLY. A knife is not a time
   machine; it is a falsification instrument. The question is not "what did the
   August build do" but "does this guard do anything on the build we ship". The
   right cut is therefore TODAY'S machine with the guard REMOVED -- which is
   exactly the machine whose guard is under test, and the historical hybrid is
   irrelevant to it. Stated here so the next reader inherits the distinction
   rather than the worry.

THE CUT: the selector is written at the head and NEVER re-asserted, so a
filespec expression that reaches the drive clobbers `DISKOP_OP` and the clobbered
value is what the dirverb tenant sees.

    predicted  lfl-inp   printer listing -> <nothing>            MOVES
    predicted  lfl-inpb  screen <nothing> -> the packed listing  MOVES
    predicted  lfl-wild / lfl-all / lfl-sink / lfl-ctlp / lfl-ctlf  HOLD

⚠️ THE GREEN HALF IS LOAD-BEARING, and it is what refuted K-FG1: under that cut
`lfl-wild`, `lfl-all` and `lfl-sink` moved too, to `????????.BAS` -- which is not
corruption but the 8.3 PATTERN printed where matches belong (`bn_star_fill`). A
cut that moves the controls is breaking the VERB, and its red proves nothing.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)                          # knife_guard.hashes() reads build/ relatively
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import knife_guard                                                # noqa: E402

SRC = os.path.join(ROOT, "basic", "files.asm")
GATE = os.path.join(ROOT, "probes", "basic", "basic_probe_lptverb.py")
TMP = tempfile.mkdtemp(prefix="fg2-")
WATCH = ("lfl-inp", "lfl-inpb", "lfl-wild", "lfl-all", "lfl-sink",
         "lfl-ctlp", "lfl-ctlf")
MOVERS = {"lfl-inp", "lfl-inpb"}

HEAD_A = """                push    af                  ; the DISKOP_SEL_* op, across the parse"""
HEAD_B = """                ld      (DISKOP_OP),a       ; K-FG2: parked at the HEAD and never
                                            ; re-asserted -- the pre-guard shape"""
ABORT_A = """                pop     af                  ; balance before the returning abort
                jp      load_error"""
ABORT_B = """                jp      load_error          ; K-FG2: nothing was pushed"""
POP_A = """                pop     af                  ; the op selector, parked at the head
                ld      (DISKOP_OP),a       ; asserted AFTER the evaluator, not
                                            ; before it -- see the block at do_files"""
POP_B = """                                            ; K-FG2: the re-assertion is GONE, so a
                                            ; clobber by the filespec expression
                                            ; survives to the tenant"""

ROW = re.compile(r"^\s*(?:ok|DIFF|FAIL|PASS)\s+(\S+)\s+(.*)$", re.M)


def build():
    log = os.path.join(TMP, "build.out")
    with open(log, "w") as fh:
        rc = subprocess.call(["make", "repack-machine"], cwd=ROOT,
                             stdout=fh, stderr=subprocess.STDOUT)
    return rc, log


# \U0001f534 ROW ISOLATION, ADDED 2026-09-09. K-FG1 and K-FG2 both scored "the
# controls moved", and the obvious next suspicion -- one row contaminating the
# next -- is refuted by the probe itself: `prn_battery` is BOOT-PER-CASE. Running
# a single row anyway is what turns that from an argument into a reading.
ONLY = sys.argv[1] if len(sys.argv) > 1 else ""


def run_gate(tag):
    log = os.path.join(TMP, f"{tag}.out")
    cmd = [sys.executable, GATE, "--gate"] + (["--only", ONLY] if ONLY else [])
    with open(log, "w") as fh:
        subprocess.call(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    return {k: v for k, v in ROW.findall(txt) if k in WATCH}, log


def main() -> int:
    orig = open(SRC, encoding="utf-8").read()
    for name, a in (("HEAD", HEAD_A), ("ABORT", ABORT_A), ("POP", POP_A)):
        if orig.count(a) != 1:
            print(f"\U0001f534 ANCHOR {name} matched {orig.count(a)}x -- the source moved; "
                  f"nothing planted, nothing scored.")
            return 2
    try:
        rc, log = build()
        if rc:
            print(f"\U0001f534 the CLEAN build failed (rc={rc}) -- apparatus, not a finding")
            return 3
        base_h = knife_guard.hashes()
        before, blog = run_gate("before")
        print(f"  baseline rows: {before}\n", flush=True)

        cut = (orig.replace(HEAD_A, HEAD_B, 1)
                   .replace(ABORT_A, ABORT_B, 1)
                   .replace(POP_A, POP_B, 1))
        open(SRC, "w").write(cut)
        rc, log = build()
        after_h = knife_guard.hashes()
        if rc:
            print(f"\U0001f534 THE BUILD FAILED (rc={rc}) -- read {log}; the UNCUT rom is "
                  f"still on disk, so any score below would be the clean build's")
            for ln in open(log, encoding="utf-8", errors="replace"):
                if ln.startswith("ERROR"):
                    print("   ", ln.rstrip())
            return 3
        if base_h == after_h:
            print("\U0001f534 KNIFE INERT: the ROM did not move, so the cut never reached "
                  "the image. Score discarded.")
            return 3
        after, alog = run_gate("after")
        print(f"  knifed rows:   {after}\n", flush=True)

        moved = {k for k in WATCH if before.get(k) != after.get(k)}
        print(f"  MOVED: {sorted(moved) or 'none'}")
        print(f"  want:  {sorted(MOVERS)}")
        ctl_moved = moved - MOVERS
        if ctl_moved:
            print(f"\n  \U0001f534 CONTROLS MOVED ({sorted(ctl_moved)}) -- the cut is breaking "
                  f"the VERB, not the guard, and the red proves nothing. This is "
                  f"exactly how K-FG1 failed.")
            return 1
        if moved == MOVERS:
            print("\n  \U0001f7e2 EXACT: only the two INPUT$ rows moved, and every plain "
                  "LFILES control held. The op-selector guard is PINNED -- removing "
                  "it is visible, and visible ONLY where the filespec expression "
                  "reaches the drive.")
            return 0
        print(f"\n  ⚠️ MISS: expected {sorted(MOVERS)}, got {sorted(moved)}. A miss is "
              f"a finding about the row set as often as about the code.")
        return 1
    finally:
        open(SRC, "w").write(orig)
        build()
        assert open(SRC, encoding="utf-8").read() == orig, "source not restored!"
        print(f"\n  restored; roms={knife_guard.hashes()}")


if __name__ == "__main__":
    raise SystemExit(main())
