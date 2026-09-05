#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-PE1 re-run — the four "unexplained" rows, explained and then re-armed.

TODO (filed 2026-08-09 by D-PENDERR §9.1): with `penderr_set` cut so NO deferred
code can be recorded, four rows kept answering ERR 5 — `o.nn.5dz`, `o.nn.5ov`,
`o.sub.5ex`, `u.nn.5dz`, all with `0*SQR(-1)` first — while `n.5.w` correctly
lost its error. The filing read that as *"the SQR-domain error can reach ERR 5 by
a route that does not pass through the pending-error cell"*.

🎯 IT IS NOT A SECOND ROUTE. IT IS A SECOND ERROR. Every `FP*` constant in the
probe is `0*(<faulting expr>)`, so when the fault does not fire the term is 0 and
a row written `WIDTH {FP5}+{FP}` has the argument **0** — and `WIDTH 0` is itself
Illegal function call. Measured on the VG-8020 and zerobas: `WIDTH 0` → ERR 5,
`WIDTH 1` → ok, `WIDTH 40` → ok, `WIDTH 41` → ERR 5. The verb's own domain check
raises the very code the pending cell would have delivered. `n.5.w` is
`WIDTH {FP5}+1`, argument 1, legal — which is exactly why it was the one row that
behaved.

⚠️ AND IT WAS NOT ONLY A PROPERTY OF THE CUT TREE, which is what the filing
assumed. On the LIVE machine those rows are green for two reasons, and one of
them is not the subject: had the pending mechanism silently stopped working, the
argument would collapse to `WIDTH 0` and they would still read ERR 5.

THE REPAIR is one character of arithmetic: every WIDTH row now reads
`WIDTH 1+…`, so an error-free argument is 1 and the statement SUCCEEDS. An ERR 5
can then only have come from the pending cell.

THIS RUN IS THE PROOF. With `penderr_set` neutered the four rows must now LOSE
their error, where before the repair they kept it. A knife whose predicted
rows move is the difference between a story and a measurement.

    python3 scratchpad/pe1_knife.py
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

TMP = "scratchpad/pe1_knife"
SRC = "basic/str-engine.asm"
GATE = "probes/basic/basic_probe_penderr.py"

# Neuter first-error recording: the store never happens, so no deferred code can
# ever be armed. (A RETARGET is preferable to a NOP in general, but here the
# subject IS "nothing gets recorded", so removing the store is the real cut.)
ANCHOR = """                pop     af                  ; A = the code again, F = the caller's
                ld      (FPERR),a
                ret"""
CUT = """                pop     af                  ; K-PE1 CUT: the store never happens
                ret"""

WANT = {"o.nn.5dz", "o.nn.5ov", "o.sub.5ex", "u.nn.5dz", "n.5.w"}


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        # 🔴 NOT `--gate`. In gate mode the cut makes the probe's POSITIVE
        # CONTROLS fail (correctly — with nothing recorded, `n.dz.w` reads 0
        # instead of 11), so it REFUSES and prints no rows at all. The first
        # version of this knife read that as all 61 rows "moving" to <absent>
        # and called it success: an absence scored as an outcome
        # [[an-unnamed-outcome-reads-as-no-outcome]]. Characterize mode prints
        # the readings without the refusal, which is what a per-row question
        # needs.
        rc = subprocess.call([sys.executable, GATE],
                             stdout=fh, stderr=subprocess.STDOUT)
    return rc, open(log, encoding="utf-8", errors="replace").read(), log


def rows_of(txt):
    out = {}
    for ln in txt.splitlines():
        m = re.match(r"\s*(?:ok|PASS|DIFF|FAIL)\s+(\S+)\s+(.*)", ln)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def main():
    os.makedirs(TMP, exist_ok=True)
    src = open(SRC).read()
    if src.count(ANCHOR) != 1:
        print(f"INSTRUMENT FAULT: the anchor occurs {src.count(ANCHOR)} time(s) "
              f"in {SRC}, not once.")
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
    rc0, txt0, log0 = run_gate("base")
    before = rows_of(txt0)
    print(f"  penderr rc={rc0}, {len(before)} row(s)   {log0}")
    if rc0:
        print("INSTRUMENT FAULT: the gate is red BEFORE the cut.")
        return 2

    print("\n=== K-PE1: penderr_set's `ld (FPERR),a` removed")
    open(SRC, "w").write(src.replace(ANCHOR, CUT, 1))
    h0 = knife_guard.hashes()
    moved, h1, brc = knife_guard.build(f"{TMP}/cut_build.log", h0)
    if brc:
        print(f"INSTRUMENT FAULT: knifed tree does not build ({TMP}/cut_build.log)")
        return 2
    print(knife_guard.report("K-PE1", moved, h0, h1))
    if not moved:
        print("INSTRUMENT FAULT: the ROM did not change.")
        return 2
    rc1, txt1, log1 = run_gate("cut")
    after = rows_of(txt1)
    print(f"  penderr rc={rc1}   {log1}")

    print("\n=== the five rows the filing named")
    ok = True
    for k in sorted(WANT):
        b, a = before.get(k, "<absent>"), after.get(k, "<absent>")
        if a == "<absent>" or b == "<absent>":
            mv = "🔴 UNREADABLE — an absence is not a reading"
            ok = False
        elif b != a:
            mv = "MOVED"
        else:
            mv = "🔴 HELD"
            ok = False
        print(f"  {k:12} {mv}")
        print(f"     before: {b}")
        print(f"     after:  {a}")
    total = [k for k in before if before[k] != after.get(k, "<absent>")]
    print(f"\n{len(total)} row(s) moved of {len(before)}")
    print("K-PE1: the four are ARMED at last" if ok
          else "🔴 at least one still cannot see the cut")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
