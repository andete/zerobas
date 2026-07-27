#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""clone_scout.py -- find carves of the fat.asm shape: groups of label-blocks
that are IDENTICAL except for one or two operands, i.e. N copies of one body
saying one thing N times.  Estimates the main-ROM saving from collapsing each
group onto a shared body (`ld <x>` + jump).

  python3 tools/clone_scout.py [--min BYTES] [--members N]

This is the VALUE question; tools/p1scout.py and tools/carve_scout.py answer the
LEGALITY question (can this move to a tenant).  They are complementary, and the
FAT carve needed both readings: p1scout called basic/fat.asm "811 B, zero
frontier", which looked like a large eviction candidate but was the opposite --
the eviction had already happened and what remained was glue.  clone_scout is
what actually named the win.

CALIBRATION -- and the reason this file has a docstring this long.  The first
version masked ONE operand position and found NOTHING in basic/fat.asm at
099c809, the commit immediately before those thirteen shims were collapsed.  It
could not rediscover a carve that was sitting right there, because the shims
differ in TWO places: the DISKOP_SEL_* immediate AND the `jr nz,<own err label>`
target.  Masking up to two positions finds the group (13 members, est. 260 B,
plus the error-tail groups at 44/48 B -- against 367 B actually measured, so the
estimate reads LOW, which is the safe direction).

Re-run that check against 099c809 if you change the matcher:
    git worktree add /tmp/cc 099c809 && cd /tmp/cc && make basic-reloc
    python3 tools/clone_scout.py        # basic/fat.asm must be the top row
Build the worktree FIRST -- symbol spans come from build/basic-reloc.sym, and
scanning old sources against a current .sym silently reports post-carve sizes
(read_sector measures 2 B), which suppresses the very group you are looking for.

BLIND SPOTS, so nobody reads a small total as "no redundancy left": this finds
only structurally identical label-blocks differing in <=2 operands.  It does not
see near-duplicates with different instruction counts, the same logic expressed
differently, or duplicated DATA.  A small total is a floor on THIS SHAPE, not a
verdict on redundancy.

FALSE POSITIVES, the other way round: a group here is not automatically a carve.
An ALREADY-COLLAPSED family still reports as clones -- after 4bfafa2 the eight
math stubs reduced to `call evmc_prologue / ret nz / ld hl,<entry> / jp
evmc_dispatch`, and those five 10 B remnants are STILL structurally identical.
They are irreducible: each exists precisely to supply one distinct constant, and
squeezing them further would mean an index-to-entry mapping that costs more than
it saves.  Read `each` -- once a group's per-member size approaches the cost of a
stub (~5-10 B) there is nothing left to take.

GATING: the lean cart is BYTE-FROZEN, so a group reported `both` assembles into
both builds and can only be collapsed behind an `IF ROM_BASE < $4000` (which
basic/fat.asm demonstrates).  A group reported `repack` is free to collapse
outright."""
import sys, glob, re, collections, argparse
sys.path.insert(0, "tools")
from check_tenant_closure import load_syms

_ap = argparse.ArgumentParser()
_ap.add_argument("--min", type=int, default=25, help="minimum est. saving (B)")
_ap.add_argument("--members", type=int, default=3, help="minimum clones per group")
_args = _ap.parse_args()

syms = load_syms("build/basic-reloc.sym")
ordered = sorted((v, k) for k, v in syms.items())
span = {n: (ordered[i+1][0] - a if i+1 < len(ordered) else 0)
        for i, (a, n) in enumerate(ordered)}

LBL = re.compile(r'^([A-Za-z_]\w*):')
DIRECTIVE = re.compile(r'^\s*(IF|ELSE|ENDIF|include|ENDM|MACRO|org|end)\b', re.I)
EQU = re.compile(r'^\s*\S+\s+equ\s', re.I)


def blocks_of(path):
    """Yield (label, [(mnemonic, operand)], gate) per label-delimited block."""
    gate = []            # stack of 'repack' | 'lean' | 'other'
    cur_lbl, cur_body, cur_gate = None, [], None
    out = []

    def flush():
        if cur_lbl and cur_body:
            out.append((cur_lbl, list(cur_body), cur_gate))

    for raw in open(path):
        line = raw.split(';', 1)[0].rstrip()
        if not line.strip():
            continue
        m = DIRECTIVE.match(line)
        if m:
            kw = m.group(1).upper()
            if kw == 'IF':
                s = line.strip()
                gate.append('repack' if 'ROM_BASE < $4000' in s
                            else 'lean' if 'ROM_BASE >= $4000' in s else 'other')
            elif kw == 'ELSE' and gate:
                gate[-1] = {'repack': 'lean', 'lean': 'repack'}.get(gate[-1], 'other')
            elif kw == 'ENDIF' and gate:
                gate.pop()
            flush(); cur_lbl, cur_body = None, []
            continue
        if EQU.match(line):
            continue
        lm = LBL.match(line)
        if lm:
            flush()
            cur_lbl, cur_body = lm.group(1), []
            cur_gate = ('repack' if 'repack' in gate else
                        'lean' if 'lean' in gate else 'both')
            rest = line[lm.end():].strip()
            if not rest:
                continue
            line = '        ' + rest
        if cur_lbl is None:
            continue
        parts = line.strip().split(None, 1)
        cur_body.append((parts[0].lower(), parts[1].strip() if len(parts) > 1 else ''))
    flush()
    return out


allblocks = []
for f in sorted(glob.glob("basic/*.asm") + glob.glob("basic/*.inc")):
    for lbl, body, gate in blocks_of(f):
        if len(body) < 4:                      # too small to be worth collapsing
            continue
        allblocks.append((lbl, tuple(body), gate, f))

# signature = the block with UP TO TWO operands masked.  ONE is not enough and
# the scanner proved it: at 099c809 (pre-carve) a 1-position mask found NOTHING
# in basic/fat.asm, because those thirteen shims differ in TWO places -- the
# DISKOP_SEL_* immediate AND the `jr nz,<own err label>` target.  A scanner that
# cannot rediscover the carve already made is not measuring its subject.
sig = collections.defaultdict(list)
for lbl, body, gate, f in allblocks:
    n = len(body)
    for i in range(n):
        masked1 = tuple((mn, '<*>' if j == i else op)
                        for j, (mn, op) in enumerate(body))
        sig[masked1].append((lbl, gate, f))
        for k in range(i + 1, n):
            masked2 = tuple((mn, '<*>' if j in (i, k) else op)
                            for j, (mn, op) in enumerate(body))
            sig[masked2].append((lbl, gate, f))

seen_group = set()
rows = []
for masked, members in sig.items():
    names = tuple(sorted(m[0] for m in members))
    if len(members) < _args.members or names in seen_group:
        continue
    seen_group.add(names)
    members = list({m[0]: m for m in members}.values())
    p1 = [m for m in members if m[0] in syms and 0x4000 <= syms[m[0]] < 0x8000]
    low = [m for m in members if m[0] in syms and syms[m[0]] < 0x4000]
    if not (p1 or low):
        continue
    sizes = [span.get(m[0], 0) for m in (p1 or low)]
    body_b = max(sizes) if sizes else 0
    n = len(p1 or low)
    save = (n - 1) * body_b - 4 * n          # shared body kept, 4 B stub each
    if save < _args.min:
        continue
    gates = collections.Counter(m[1] for m in members)
    rows.append((save, n, body_b, names, gates, 'page1' if p1 else 'low',
                 members[0][2]))

rows.sort(reverse=True)
print(f"{'est.save':>8} {'n':>3} {'each':>5}  region  gating            file / members")
print("=" * 100)
for save, n, body_b, names, gates, region, f in rows[:20]:
    g = ','.join(f"{k}={v}" for k, v in gates.most_common())
    print(f"{save:8} {n:3} {body_b:5}  {region:6}  {g:16}  {f}")
    print(f"{'':8}   {', '.join(names[:8])}" + (f" (+{len(names)-8})" if len(names) > 8 else ""))
print(f"\n{len(rows)} candidate groups; total est. savings "
      f"{sum(r[0] for r in rows)} B (overlapping groups NOT deduped)")
