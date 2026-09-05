#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-FI1 — does `f.filesinp` actually pin `do_files`' op-selector guard?

TODO (filed 2026-08-21 by D-FNEXPR2 §3.5, AGAINST ITS OWN FIX): `do_files` parks
its dirverb op selector on the stack across the filespec parse, because the parse
now begins with `str_eval` and `INPUT$(n,#ch)` reaches the drive through
`fatprim_bounce`, whose first instruction is `ld (DISKOP_OP),a`. The BALANCE of
that push/pop is pinned by every FILES row. The CLOBBER protection was pinned by
NOTHING — **no row in any battery executed `FILES INPUT$(n,#ch)`**.

`f.filesinp` is that row. This knife is the only thing that can say whether
adding it was coverage or decoration.

🎯 THE CUT KEEPS THE STACK BALANCED ON PURPOSE. Removing the `push`/`pop` pair
would derail every FILES row and prove nothing about the CLOBBER — the two
properties would be cut at once. So the `pop af` stays and only the VALUE
changes: the selector is re-read from `DISKOP_OP`, i.e. from whatever the
filespec's own evaluation left there. That is exactly the pre-fix behaviour, and
it isolates the clobber from the balance.

    predicted: f.filesinp MOVES (its INPUT$ runs fatprim_bounce, so DISKOP_OP
               holds a FAT-primitive selector by the time the dirverb sees it)
    predicted: every other FILES row HOLDS (no INPUT$, nothing writes DISKOP_OP
               between the head and the call, so the re-read finds the same value)

⚠️ The green half is the load-bearing half here. If the plain FILES rows moved
too, the cut would be breaking the verb rather than the guard, and f.filesinp's
red would mean nothing [[a-case-that-agrees-can-agree-for-the-wrong-reason]].

    python3 scratchpad/filesinp_knife.py
"""
from __future__ import annotations

import atexit
import hashlib
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
os.chdir(ROOT)
sys.path.insert(0, HERE)
import knife_guard                                                # noqa: E402

TMP = "scratchpad/filesinp_knife"
SRC = "basic/files.asm"
GATE = "probes/basic/basic_probe_namspc.py"
ROWS = "f.filesinp,f.fileslit,f.filesvar,f.filesbare,f.fileslitl,f.filesvarl"

# 🔴 THE FIRST CUT WAS WRONG AND THE GREEN CONTROL SAID SO. It changed only the
# READ, leaving DISKOP_OP never written at the head -- so every row, `f.filesbare`
# included, saw a stale cell, and `f.filesbare` moved. That is not the pre-fix
# behaviour, it is a third thing. The pre-fix shape WROTE the selector at the head
# and read it back at the call, so BOTH halves have to be restored: with the head
# write back, a plain FILES finds its own value intact (nothing writes DISKOP_OP
# in between) and only a filespec that reaches the drive clobbers it.
HEAD_A = """                push    af                  ; the DISKOP_SEL_* op, across the parse"""
HEAD_B = """                ld      (DISKOP_OP),a       ; K-FI1: parked at the HEAD again
                push    af                  ; (balance untouched)"""
ANCHOR = """                pop     af                  ; the op selector, parked at the head
                ld      (DISKOP_OP),a       ; asserted AFTER the evaluator, not"""
CUT = """                pop     af                  ; K-FI1: balance kept...
                ld      a,(DISKOP_OP)       ; ...but the value taken from the CELL,
                ld      (DISKOP_OP),a       ; which the evaluator may have clobbered"""

ROW = re.compile(r"^\s*(?:ok|DIFF|FAIL|PASS)\s+(\S+)\s+(.*)$", re.M)


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATE, "--gate", "--only", ROWS],
                             stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    return rc, dict(ROW.findall(txt)), log


def main():
    os.makedirs(TMP, exist_ok=True)
    src = open(SRC).read()
    for name, a in (("pop-site", ANCHOR), ("head", HEAD_A)):
        if src.count(a) != 1:
            print(f"INSTRUMENT FAULT: the {name} anchor occurs {src.count(a)} "
                  f"time(s), not once.")
            return 2
    digest = hashlib.sha256(src.encode()).hexdigest()

    def restore():
        open(SRC, "w").write(src)
        assert hashlib.sha256(open(SRC).read().encode()).hexdigest() == digest
        print(f"  restored {SRC} byte-identically")
    atexit.register(restore)

    print("=== baseline")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: clean tree does not build ({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc0, before, log0 = run_gate("base")
    print(f"  namspc rc={rc0}, {len(before)} row(s)   {log0}")
    if rc0 or not before:
        print("INSTRUMENT FAULT: the gate is red or silent BEFORE the cut.")
        return 2

    print("\n=== K-FI1: the selector re-read from DISKOP_OP (balance untouched)")
    open(SRC, "w").write(src.replace(HEAD_A, HEAD_B, 1).replace(ANCHOR, CUT, 1))
    h0 = knife_guard.hashes()
    moved, h1, brc = knife_guard.build(f"{TMP}/cut_build.log", h0)
    if brc:
        print(f"INSTRUMENT FAULT: knifed tree does not build ({TMP}/cut_build.log)")
        return 2
    print(knife_guard.report("K-FI1", moved, h0, h1))
    if not moved:
        print("INSTRUMENT FAULT: the ROM did not change.")
        return 2
    rc1, after, log1 = run_gate("cut")
    print(f"  namspc rc={rc1}   {log1}")

    print("\n=== rows")
    ok = True
    for k in sorted(before):
        b, a = before[k], after.get(k, "<absent>")
        want_move = (k == "f.filesinp")
        if a == "<absent>":
            verdict, ok = "🔴 UNREADABLE (an absence is not a reading)", False
        elif (b != a) == want_move:
            verdict = "MOVED (predicted)" if want_move else "held (predicted)"
        else:
            verdict, ok = ("🔴 HELD — the row cannot see the clobber"
                           if want_move else
                           "🔴 MOVED — the cut is breaking the verb, not the guard"), False
        print(f"  {k:14} {verdict}")
        if b != a:
            print(f"     before: {b}")
            print(f"     after:  {a}")
    print("\nK-FI1: PASS — f.filesinp pins the clobber, the plain rows are untouched"
          if ok else "\n🔴 K-FI1 RED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
