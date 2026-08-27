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

GATING: this used to report a repack/lean/both column per group, because the lean
16 KB cart was byte-frozen and a group present in BOTH builds could only be
collapsed behind an `IF ROM_BASE < $4000`.  That build and its 284 gates are gone
(docs/spec-lean-retire-s3-gates.md), so every group is unconditionally resident and
free to collapse; the column would report `both` for everything and has been
dropped.  What still constrains a candidate is its REGION (page 1 vs the low
region) and whether it is shared with the sub-ROM side."""
import os
import sys, glob, re, collections, argparse
sys.path.insert(0, "tools")
from check_tenant_closure import load_syms, _is_terminator

_ap = argparse.ArgumentParser()
_ap.add_argument("--min", type=int, default=25, help="minimum est. saving (B)")
_ap.add_argument("--members", type=int, default=3, help="minimum clones per group")
_ap.add_argument("--extend", action="store_true",
                 help="after grouping, EXTEND each group across label "
                      "boundaries while every member's next block still "
                      "matches. A routine split by an interior loop label is "
                      "otherwise priced at a FRACTION of its collapse.")
_args = _ap.parse_args()

syms = load_syms("build/basic-reloc.sym")
ordered = sorted((v, k) for k, v in syms.items())
span = {n: (ordered[i+1][0] - a if i+1 < len(ordered) else 0)
        for i, (a, n) in enumerate(ordered)}

LBL = re.compile(r'^([A-Za-z_]\w*):')
DIRECTIVE = re.compile(r'^\s*(IF|ELSE|ENDIF|include|ENDM|MACRO|org|end)\b', re.I)
EQU = re.compile(r'^\s*\S+\s+equ\s', re.I)


def blocks_of(path):
    """Yield (label, [(mnemonic, operand)]) per label-delimited block."""
    cur_lbl, cur_body = None, []
    out = []

    def flush():
        if cur_lbl and cur_body:
            out.append((cur_lbl, list(cur_body)))

    for raw in open(path):
        line = raw.split(';', 1)[0].rstrip()
        if not line.strip():
            continue
        m = DIRECTIVE.match(line)
        if m:
            flush(); cur_lbl, cur_body = None, []
            continue
        if EQU.match(line):
            continue
        lm = LBL.match(line)
        if lm:
            flush()
            cur_lbl, cur_body = lm.group(1), []
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



# 🔴 A LABEL-BLOCK IS NOT A ROUTINE, AND PRICING ONE AS THE OTHER UNDERSTATES
# THE CARVE. `arga_pack_fac`/`arga_pack_single` ranked at 14 B and MEASURED at
# 27: the two 13-byte loops that follow their 22-byte headers live under their
# own labels (`apf_lp`/`aps_lp`), so this scanner compared the headers and never
# saw the loops (D-DEFFNLAND §4.3). `--extend` grows a MATCHED group forward
# across label boundaries while every member's next block still agrees, which
# prices the collapse whole.
#
# ⚠️ EXTENDING IS NOT MERGING. A first attempt merged blocks into
# terminator-delimited runs BEFORE matching, and that is the wrong shape: it
# made spans longer and therefore LESS likely to be identical, so it found
# FEWER groups (10 vs 27) and LOWER savings (55 B vs 180 B). Two routines that
# share a prefix and diverge after it are a real clone at block granularity and
# vanish at run granularity. Grow the match; do not pre-merge the input.
allblocks = []
order, pos = {}, {}
for f in sorted(glob.glob("basic/*.asm") + glob.glob("basic/*.inc")):
    bs = blocks_of(f)
    order[f] = [(lbl, tuple(body)) for lbl, body in bs]
    for i, (lbl, body) in enumerate(bs):
        pos[(lbl, f)] = i
        if len(body) < 4:                      # too small to be worth collapsing
            continue
        allblocks.append((lbl, tuple(body), f))
print(f"{len(allblocks)} span(s)"
      + ("  [--extend: groups grow across label boundaries]" if _args.extend else ""))

# signature = the block with UP TO TWO operands masked.  ONE is not enough and
# the scanner proved it: at 099c809 (pre-carve) a 1-position mask found NOTHING
# in basic/fat.asm, because those thirteen shims differ in TWO places -- the
# DISKOP_SEL_* immediate AND the `jr nz,<own err label>` target.  A scanner that
# cannot rediscover the carve already made is not measuring its subject.
sig = collections.defaultdict(list)
for lbl, body, f in allblocks:
    n = len(body)
    for i in range(n):
        masked1 = tuple((mn, '<*>' if j == i else op)
                        for j, (mn, op) in enumerate(body))
        sig[masked1].append((lbl, f))
        for k in range(i + 1, n):
            masked2 = tuple((mn, '<*>' if j in (i, k) else op)
                            for j, (mn, op) in enumerate(body))
            sig[masked2].append((lbl, f))

def _norm(lbl, body):
    """A block body with its OWN label replaced by <self>, so two copies of the
    same loop compare equal despite their different self-jump targets."""
    return tuple((mn, op.replace(lbl, "<self>")) for mn, op in body)


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
    chosen = p1 or low
    grown = 0
    if _args.extend:
        # Walk forward one block at a time. Every member must HAVE a next block
        # and all of them must be byte-for-byte equal to each other -- no extra
        # operand masking, because the group's mask budget was already spent on
        # the head. The first disagreement stops the whole group.
        k = 1
        while True:
            nxt = []
            for lbl, f in chosen:
                i = pos.get((lbl, f))
                if i is None or i + k >= len(order[f]):
                    nxt = None; break
                nxt.append(order[f][i + k])
            # 🎯 ALPHA-NORMALISE EACH BLOCK'S OWN LABEL BEFORE COMPARING. Two
            # copies of one loop end `djnz apf_lp` and `djnz aps_lp` -- the same
            # instruction targeting the equivalent place, which is a RENAMING
            # and not a difference. Comparing raw bodies calls them distinct and
            # refuses to extend, which is exactly what the strict first cut did
            # to this item's own 27 B example.
            if not nxt or len({_norm(l, b) for l, b in nxt}) != 1:
                break
            grown += max(span.get(l, 0) for l, _ in nxt)
            k += 1
            # 🔴 AND STOP AT A REAL TERMINATOR. Unbounded, this walk runs past
            # every `ret` and keeps matching: `gosub_stk_over` grew +1307 B,
            # `tokenise` +1107 B -- the rest of the file, not a clone. The item
            # is about a routine split by an INTERIOR label, so the extension
            # must end where the routine does. `_is_terminator` is the same test
            # check_dead_code uses; `ret nz` and `jp nc,X` are NOT terminators.
            last = " ".join(x for x in nxt[0][1][-1] if x) if nxt[0][1] else ""
            if _is_terminator(last):
                break
    sizes = [span.get(m[0], 0) for m in chosen]
    body_b = (max(sizes) if sizes else 0) + grown
    n = len(p1 or low)
    save = (n - 1) * body_b - 4 * n          # shared body kept, 4 B stub each
    if save < _args.min:
        continue
    rows.append((save, n, body_b, names, 'page1' if p1 else 'low',
                 members[0][1]))

rows.sort(reverse=True)
print(f"{'est.save':>8} {'n':>3} {'each':>5}  region  file / members")
print("=" * 100)
for save, n, body_b, names, region, f in rows[:20]:
    print(f"{save:8} {n:3} {body_b:5}  {region:6}  {f}")
    print(f"{'':8}   {', '.join(names[:8])}" + (f" (+{len(names)-8})" if len(names) > 8 else ""))
print(f"\n{len(rows)} candidate groups; total est. savings "
      f"{sum(r[0] for r in rows)} B (overlapping groups NOT deduped)")
