#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-LAYOUTPRIZE — what can a layout pass actually WIN? Measure before moving.

A layout pass is being considered. Before any code moves, two things have to be
established, because if either comes out small the pass is risk without a number.

## 1. Moving between the low region and page 1 is ZERO-SUM

Both are one contiguous main image ($2812-$7FFF); page-1 code already calls into
the low region and vice versa. So a routine moved from one to the other frees
bytes in one wall and spends the same bytes in the other. It creates NOTHING.
The only hard constraint separating them is the RESIDENT CLOSURE: 155 routines
reachable from the 13 ABI seeds must stay below $4000, because the sub-ROM calls
them while page 1 is banked out.

## 2. So the real prize is LOCALITY: `jp` -> `jr`

`jp` is 3 bytes and `jr` is 2. A branch can be `jr` only if its target is within
-128..+127 of the instruction after it. Clustering callers near callees converts
`jp` to `jr`, and each conversion is 1 byte -- that IS the layout win, and it is
the one thing "chosen with the whole call graph in view" buys that incremental
eviction cannot.

This walks every instruction in the main image, computes each `jp`'s distance to
its target, and reports the distribution. Branches ALREADY in range are what
scratchpad/jr_mapper.py finds; the interesting number is how many sit just
outside it, because those are what clustering could capture.

⚠️ `jp cc,X` converts only for cc in {nz,z,nc,c} -- there is no `jr po/pe/p/m`.
Counted separately, since a pass cannot win those at any distance.
"""
from __future__ import annotations

import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scratchpad"))
import ngram_sweep                                                # noqa: E402

SYM = os.path.join(ROOT, "build", "basic-reloc.sym")
JRCC = {"nz", "z", "nc", "c"}


def symbols() -> dict:
    out = {}
    for ln in open(SYM):
        m = re.match(r"(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", ln.strip())
        if m:
            out[m.group(1).lower()] = int(m.group(2), 16)
    return out


def walk():
    """-> (rows, validated, total). A routine is VALIDATED when walking its
    instruction sizes from its own label lands exactly on the NEXT label's
    linker address. Only branches inside validated routines are returned.

    🔴 THIS FILTER IS THE WHOLE INSTRUMENT. The first cut walked every routine
    and reported a confident 704-byte ceiling; checked against the linker,
    **405 of 1592 label-to-label walks DISAGREED** -- `db`/`dw` data is not an
    instruction, so any routine carrying a table under-counts and every address
    after it drifts. The distances were plausible and wrong
    [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
    """
    sym = symbols()
    recs = list(ngram_sweep.parse())
    # pass 1: which routines walk true?
    good, cur, addr, pend = set(), None, None, []
    for rec in recs:
        if rec[0] == "LABEL":
            lab = rec[3].lower()
            if cur is not None and addr is not None and lab in sym:
                if addr == sym[lab]:
                    good.add(cur)
            addr = sym[lab] if lab in sym else None
            cur = rec[3]
        elif rec[0] == "I" and addr is not None:
            addr += rec[4] or 0
    # pass 2: collect branches, but only from routines that walked true
    rows, cur, addr, total = [], None, None, 0
    for rec in recs:
        if rec[0] == "LABEL":
            lab = rec[3].lower()
            addr = sym[lab] if lab in sym else None
            cur = rec[3]
            continue
        if rec[0] != "I":
            continue
        key, size, rel = rec[3], rec[4], rec[1]
        m = re.match(r"^jp\s+(?:(nz|z|nc|c|po|pe|p|m),)?([a-z_][a-z0-9_]*)$", key)
        if m and rel.startswith("basic/"):
            total += 1
            if addr is not None and cur in good and m.group(2) in sym:
                rows.append((m.group(1), sym[m.group(2)] - (addr + 2), rel, cur))
        if addr is not None:
            addr += size or 0
    return rows, len(good), total


def main() -> int:
    rows, nvalid, total = walk()
    conv = [r for r in rows if r[0] is None or r[0] in JRCC]
    nonc = [r for r in rows if r[0] is not None and r[0] not in JRCC]
    inrange = [r for r in conv if -128 <= r[1] <= 127]
    b = collections.Counter()
    for _cc, d, _f, _s in conv:
        a = abs(d)
        for lim in (128, 256, 512, 1024, 2048, 4096, 1 << 30):
            if a <= lim:
                b[lim] += 1
                break

    print(f"main-image `jp` with a symbolic target        : {total}")
    print(f"  measurable (inside a LINKER-VALIDATED routine): {len(rows)}"
          f"   [{100*len(rows)//max(total,1)}% coverage, {nvalid} routines walk true]")
    print(f"  convertible condition (uncond / nz z nc c)   : {len(conv)}")
    print(f"  never convertible (po pe p m)                : {len(nonc)}")
    print(f"\nalready in jr range                            : {len(inrange)}")
    print("\ndistance of the rest — each conversion is worth 1 byte:")
    run = 0
    for lim in (128, 256, 512, 1024, 2048, 4096, 1 << 30):
        n = b[lim]
        if lim > 128:
            run += n
        nm = "<= 127 (in range)" if lim == 128 else (
            f"<= {lim}" if lim < (1 << 30) else "> 4096")
        print(f"  {nm:22s} {n:5d}" + (f"   cumulative: {run}" if lim > 128 else ""))
    near = b[256]
    print(f"\n🎯 THE ONLY HONEST NUMBER HERE IS THE NEAR ONE: {near} branches sit "
          f"within 256 B of their target and are the ones a LOCAL reordering "
          f"could plausibly capture, at 1 byte each. The far tail is arithmetic, "
          f"not a plan: bringing one pair together pushes another apart, and "
          f"nothing here models that.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
