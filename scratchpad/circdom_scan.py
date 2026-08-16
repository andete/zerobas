#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""circdom_scan.py -- the CIRCLE-radius / aspect DENOMINATOR, machine-produced.

D-CIRCDOM. The `gfx_circ_scale` header claims a bounded domain "|v|*ASPS <= 65535
(true for |v|<=255, ASPS<=256)". Four `$8000` verdicts in
docs/fixpoint8000-msx1-sweep.md §4.2 rest on it. Before asking whether the bound
is ENFORCED, ask what has ever been MEASURED: walk every Python file in the tree
(probes + tests + scratchpad) and extract every literal CIRCLE statement, with its
radius and aspect. Nothing is hand-listed.

Also reports the host-unit-test layer separately: rows that call gfx_circ_scale /
gfx_circ_bvec_mag / gfx_circ_init directly are emulator-free and are a different
denominator from the pixel differential.

    python3 scratchpad/circdom_scan.py
"""
from __future__ import annotations

import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# CIRCLE [STEP] (x,y) , r [, c [, start [, end [, aspect ]]]]
CIRC = re.compile(
    r"CIRCLE\s*(STEP)?\s*\(([^)]*)\)\s*,([^,\"']*)((?:,[^,\"']*)*)",
    re.IGNORECASE,
)


def numeric(tok: str):
    """Return a float if the token is a bare numeric literal, else None."""
    t = tok.strip()
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def main() -> int:
    files_total = files_hit = 0
    rows = []          # (relpath, lineno, radius_tok, aspect_tok, raw)
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in (".git", "build", "__pycache__")]
        for fn in sorted(filenames):
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, REPO)
            files_total += 1
            try:
                text = open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            hit = False
            for lineno, line in enumerate(text.splitlines(), 1):
                for m in CIRC.finditer(line):
                    hit = True
                    rtok = m.group(3)
                    # positional: the optional fields after r are c,start,end,aspect.
                    # EMPTY fields are significant (CIRCLE(80,80),20,15,,,.25 omits
                    # start and end) -- do NOT filter them out or aspect shifts left.
                    tail = m.group(4).split(",")[1:] if m.group(4) else []
                    atok = tail[3] if len(tail) >= 4 else ""
                    rows.append((rel, lineno, rtok.strip(), atok.strip(), m.group(0)[:70]))
            if hit:
                files_hit += 1

    print("=" * 74)
    print("CIRCLE literal denominator, machine-produced")
    print("=" * 74)
    print(f"  python files walked                {files_total:5d}")
    print(f"    with >= 1 CIRCLE literal         {files_hit:5d}")
    print(f"    with ZERO (scanned, no match)    {files_total - files_hit:5d}")
    print(f"  CIRCLE statements extracted        {len(rows):5d}")
    print()

    radii = {}
    aspects = {}
    for rel, lineno, rtok, atok, raw in rows:
        radii.setdefault(rtok, []).append((rel, lineno))
        if atok:
            aspects.setdefault(atok, []).append((rel, lineno))

    print("--- radius literals, by value ---")
    num, sym = [], []
    for tok, sites in radii.items():
        v = numeric(tok)
        (num if v is not None else sym).append((v, tok, sites))
    num.sort(key=lambda t: t[0])
    for v, tok, sites in num:
        print(f"  r = {tok:<10} {len(sites):3d} site(s)   e.g. {sites[0][0]}:{sites[0][1]}")
    for _, tok, sites in sorted(sym, key=lambda t: t[1]):
        print(f"  r = {tok:<10} {len(sites):3d} site(s)  [non-literal]   e.g. {sites[0][0]}:{sites[0][1]}")

    # A scratchpad characterization is not a gate. Split the denominator by
    # whether a regression run would ever execute the row again.
    def is_gate(rel: str) -> bool:
        return rel.startswith("probes/") or rel.startswith("tests/")

    gate_r = [numeric(rtok) for rel, _, rtok, _, _ in rows
              if is_gate(rel) and numeric(rtok) is not None]
    gate_drawn = [v for v in gate_r if 0 <= v <= 32767]
    print()
    print(f"  rows in a GATE (probes/ or tests/)     {sum(1 for r in rows if is_gate(r[0]))}")
    print(f"  rows in scratchpad/ only               {sum(1 for r in rows if not is_gate(r[0]))}")
    print(f"  >>> LARGEST RADIUS DRAWN BY A GATE:    {max(gate_drawn) if gate_drawn else None}")

    drawn = [v for v, tok, sites in num]
    refused = [v for v in drawn if v is not None and (v < 0 or v > 32767)]
    ok = [v for v in drawn if v is not None and 0 <= v <= 32767]
    print()
    print(f"  distinct numeric radii             {len(num)}")
    print(f"    refused before any draw (<0 / >32767)  {len(refused)}  {sorted(set(refused))}")
    print(f"    reach the geometry                     {len(ok)}  max = {max(ok) if ok else None}")
    print(f"  >>> LARGEST RADIUS EVER DRAWN ANYWHERE IN THE TREE: {max(ok) if ok else None}")
    print()

    print("--- aspect literals, by value ---")
    anum = []
    for tok, sites in aspects.items():
        anum.append((numeric(tok), tok, sites))
    anum.sort(key=lambda t: (t[0] is None, t[0] if t[0] is not None else 0))
    for v, tok, sites in anum:
        print(f"  aspect = {tok:<10} {len(sites):3d} site(s)   e.g. {sites[0][0]}:{sites[0][1]}")
    avals = [v for v, _, _ in anum if v is not None]
    print(f"  distinct aspect literals           {len(anum)}  max = {max(avals) if avals else None}")

    # --- the host-unit-test layer: direct calls to the bounded-domain routines ---
    print()
    print("--- host unit-test layer: direct calls to the circle math ---")
    names = ["gfx_circ_scale", "gfx_circ_bvec_mag", "gfx_circ_bvec_nudge",
             "gfx_circ_init", "gfx_circ_next", "gfx_neg16_bc", "gfx_neg16_de",
             "gcbv_y", "gfx_mul16u"]
    for name in names:
        hits = []
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, "tests")):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                for lineno, line in enumerate(open(p, encoding="utf-8",
                                                   errors="replace").read().splitlines(), 1):
                    if name in line:
                        hits.append((os.path.relpath(p, REPO), lineno))
        mark = "  <-- NO HOST ROW" if not hits else ""
        print(f"  {name:<20} {len(hits):3d} mention(s) in tests/{mark}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
