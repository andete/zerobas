#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""K-CL1..3 — the CTLLIM gate, falsified by planting.

`CTLLIM` is the control pool's collision floor, and it is a STORED derivation
(docs/spec-basic-trapsvc.md §17) refreshed at exactly three places: the two
allocator success paths in `sub/arrays.asm` and `sh_ctl_reset`. The whole risk is
that one of those refreshes goes missing and the cache silently drifts
**stale-LOW**, letting control frames land inside live variables. So the knives
are precisely "remove one refresh" — the real failure, not a proxy for it.

    knife                     rows the gate must name corrupted
    K-CL1  scalar hook gone    l.ctl, l.scal          (l.ary GREEN: its DIM refreshes)
    K-CL2  ARRAY hook gone     l.ary                  (the others GREEN: no array)
    K-CL3  BOTH hooks gone     l.ctl, l.ary, l.scal

🎯 K-CL1 AND K-CL2 ARE ORTHOGONAL, AND THAT IS THE WHOLE VALUE. Each cut reddens
exactly the rows whose last growth went through the hook it removed, and leaves
the others green. A knife that reddened everything would prove only that the
machine broke.

🔴 THIS MATRIX IS THE SECOND ATTEMPT AND THE FIRST ONE SCORED 0/3. The hooks
COVER FOR EACH OTHER: `CTLLIM` is recomputed from scratch by whichever allocator
ran last, so a scalar created after a `DIM` refreshes the floor and hides a
missing array hook completely. `l.ary` now creates every scalar it will ever use
BEFORE the `DIM`, which is what makes K-CL2 able to fire at all. (And K-CL3's
first cut removed the RESET hook, which is likewise invisible: the first variable
allocation refreshes it.)

🔴 THE ROM HASH ROUND EVERY PLANT (D-KNIFEROM2), and the tree is restored
byte-identically; the mtime is deliberately left bumped so `make` rebuilds.

    python3 scratchpad/ctllim_knives.py [--only K-CL2]
"""
from __future__ import annotations

import argparse
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

TMP = "scratchpad/ctllim_knives"
ARR = "sub/arrays.asm"
SUBSH = "sub/strheap.asm"
GATE = "probes/basic/basic_probe_ctllim.py"

_SCAL = """                ; D-CTLPOOL: the region's end just moved -- refresh the control
                ; pool's collision floor. HL is the caller's result, so it rides
                ; the stack across the walk.
                push    hl
                call    strheap_ctllim
                pop     hl
"""
_ARY = """                ; D-CTLPOOL: same refresh as scv_ceil_fits' -- a new array moved
                ; the region's end, so the pool's floor moved with it.
                push    hl
                call    strheap_ctllim
                pop     hl
"""

# tag -> (file, anchor, replacement, rows the gate must name, why)
KNIVES = [
    ("K-CL1", ARR, _SCAL, "                ; K-CL1 CUT: no scalar refresh\n",
     {"l.ctl", "l.scal"},
     "scv_alloc stops refreshing -- l.ary is GREEN, its own DIM refreshes last"),
    ("K-CL2", ARR, _ARY, "                ; K-CL2 CUT: no array refresh\n",
     {"l.ary"},
     "ary_alloc stops refreshing the floor -- ONLY the DIM row may move"),
    # 🔴 K-CL3 CUTS **BOTH** ALLOCATOR HOOKS, and its first cut (the reset hook)
    # was the wrong knife: with either allocator hook still standing, CTLLIM is
    # recomputed at the first variable and the missing reset never shows. The
    # cache can only go stale when NOTHING refreshes after a growth.
    ("K-CL3", ARR, _SCAL + "%%ARY%%", "                ; K-CL3 CUT: neither hook\n",
     {"l.ctl", "l.ary", "l.scal"},
     "BOTH allocator hooks removed -- the floor never moves off its reset value"),
]

ROW = re.compile(r"🔴 \S+ (l\.\w+): \d+ CELL\(S\) CORRUPTED")
BAD = re.compile(r"🔴 \S+ (l\.\w+):")


def run_gate(tag):
    log = f"{TMP}/{tag}.out"
    with open(log, "w") as fh:
        rc = subprocess.call([sys.executable, GATE, "--gate"],
                             stdout=fh, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    return rc, set(BAD.findall(txt)), log, txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    args = ap.parse_args()
    os.makedirs(TMP, exist_ok=True)

    sel = [k for k in KNIVES if not args.only or k[0] == args.only]
    if not sel:
        print(f"no knife matches {args.only!r}")
        return 2

    originals = {}
    for tag, path, anchor, _r, _e, _w in sel:
        originals.setdefault(path, open(path).read())
        need = ([_SCAL, _ARY] if "%%ARY%%" in anchor else [anchor])
        if any(originals[path].count(a) != 1 for a in need):
            print(f"INSTRUMENT FAULT: {tag}'s anchor occurs "
                  f"{originals[path].count(anchor)} time(s) in {path}, not once. "
                  f"The knife would cut nothing and its red arm would pass by "
                  f"never firing.")
            return 2
    digests = {p: hashlib.sha256(s.encode()).hexdigest()
               for p, s in originals.items()}

    def restore():
        for p, s in originals.items():
            open(p, "w").write(s)
            assert hashlib.sha256(open(p).read().encode()).hexdigest() == digests[p]
        print(f"  restored {', '.join(originals)} byte-identically")
    atexit.register(restore)

    # 🔴 REBUILD BEFORE THE BASELINE. The restore at the end of a previous run
    # puts the SOURCE back but leaves build/ holding the last knifed image, so a
    # baseline taken without this measures the PREVIOUS KNIFE and refuses. That
    # is what happened on the first run of this matrix; the ROM hash printed
    # below is what made it obvious rather than mysterious.
    print("=== baseline: the gate must be GREEN before a cut means anything")
    _m, _a, brc = knife_guard.build(f"{TMP}/base_build.log", None)
    if brc:
        print(f"INSTRUMENT FAULT: the clean tree does not build "
              f"({TMP}/base_build.log)")
        return 2
    print(f"  ROM {knife_guard.hashes()}")
    rc, rows, log, _ = run_gate("base")
    print(f"  ctllim rc={rc} rows={sorted(rows) or 'none'}   {log}")
    if rc:
        print("INSTRUMENT FAULT: the gate is red BEFORE any cut.")
        return 2

    results, faults = [], []
    for tag, path, anchor, repl, want, why in sel:
        print(f"\n=== {tag}: {why}")
        for p, s in originals.items():
            open(p, "w").write(s)
        if "%%ARY%%" in anchor:               # K-CL3: two cuts, one knife
            body = originals[path].replace(_SCAL, repl, 1).replace(_ARY, repl, 1)
        else:
            body = originals[path].replace(anchor, repl, 1)
        open(path, "w").write(body)
        before = knife_guard.hashes()
        moved, after, brc = knife_guard.build(f"{TMP}/{tag}_build.log", before)
        if brc:
            print(f"INSTRUMENT FAULT: the KNIFED tree does not build "
                  f"({TMP}/{tag}_build.log)")
            faults.append(tag)
            continue
        print(knife_guard.report(tag, moved, before, after))
        if not moved:
            faults.append(tag)
            continue
        rc, rows, log, _ = run_gate(tag)
        ok = rc != 0 and rows == want
        results.append((tag, want, rows, rc, ok))
        print(f"  gate rc={rc}  rows named {sorted(rows) or 'none'}  "
              f"want {sorted(want)}  {'ok' if ok else '🔴 WRONG'}   {log}")

    print("\n=== verdict")
    for tag, want, rows, rc, ok in results:
        print(f"  {tag}  want {sorted(want)}  got {sorted(rows)}  rc={rc}  "
              f"{'ok' if ok else '🔴'}")
    bad = [r for r in results if not r[4]]
    if faults:
        print(f"🔴 INSTRUMENT FAULT on {faults} -- those knives measured nothing.")
    if bad:
        print("🔴 A prediction missed. A red arm that stayed green means the gate "
              "cannot see a missing refresh; a green control that reddened means "
              "the row is not isolating the hook it names.")
    print("KNIVES: PASS" if not bad and not faults
          else f"KNIVES: RED ({len(bad)} wrong, {len(faults)} fault(s))")
    return 1 if (bad or faults) else 0


if __name__ == "__main__":
    sys.exit(main())
