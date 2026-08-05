#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Standing closure gates for sub-ROM tenants — BOTH page directions.

CALSLT switches only the CALLED page, so the two tenant flavours have OPPOSITE
visibility (docs/decision-phase3-space-strategy.md §8d, subrom-tenant-playbook §2):

  * PAGE-1 tenant (e.g. fp_sqrt) runs with main-ROM PAGE 1 switched OUT, so every
    MAIN routine it (transitively) calls MUST live in the page-0 low region
    (< $4000). A callee at >= $4000 (main page 1) is switched out -> rst $38 /
    wild jump / hang. (This bit us twice: cmp16_bits @ $4A02, div10 @ $5233.)

  * PAGE-0 tenant (e.g. dtk_tenant, ary_engine, pu_tofield_tenant) runs with
    slot-0 PAGE 0 (BIOS + the low region $2812-$3FFF + the $0038 ISR) switched
    OUT, while main PAGE 1 stays mapped. So every callee must be SUB-LOCAL (the
    sub-ROM's own page-0 code / RAM) or a MAIN PAGE-1 routine ($4000-$7FFF); a
    call into the main low region ($2812-$3FFF) or the BIOS (< $2812) hits code
    that is paged out -> crash. It must ALSO not reach the sub-ROM's OWN page 1
    (>= $4000 sub-local), which is unmapped during a page-0 call.

Three modes:

  page-1 ABI-import (default) — seed = the symbols imported in
  sub/basic-resident-abi.inc; walk the MAIN call graph (basic/*.asm); fail on
  any callee >= $4000. This audits the resident routines a page-1 tenant CALLS
  BACK INTO (fp_sqrt/fp_atan/.../fp_rnd's shared FAC ops) — it does NOT walk a
  tenant's own sub-side call graph, so a tenant that imports NOTHING from
  sub/basic-resident-abi.inc (a pure RAM+BIOS leaf, e.g. format_tenant) passes
  this trivially without being walked at all. Use --page1 below for that.

    python3 tools/check_tenant_closure.py build/basic-reloc.sym sub/basic-resident-abi.inc

  page-0 (--page0) — seed = the page-0 entry-table tenants (sub/sub.asm
  sub_p0_table); walk the SUB call graph (sub/*.asm + its includes); fail on any
  callee that is a MAIN routine < $4000 (low region / BIOS) or a SUB-LOCAL label
  >= $4000 (the sub's own page 1). Sub-local page-0 code + main page-1 + RAM are
  fine. Distinguishing a sub-local $2900 (ok) from a main low-region $2900
  (escape) is by NAME (sub-defined label vs external equ import), not address.

    python3 tools/check_tenant_closure.py --page0 build/sub.sym sub/sub.asm

  page-1 tenant walk (--page1) — the MIRROR of --page0, added for the CALL
  FORMAT eviction (docs/spec-evict-call-format.md §6): seed = the page-1
  entry-table tenants (sub/sub.asm sub_p1_table); walk the SUB call graph; fail
  on any callee that is a MAIN routine >= $4000 (main-BASIC page 1, switched
  OUT while a page-1 tenant runs) or a SUB-LOCAL label < $4000 (the sub's own
  page-0 island, also unmapped). Sub-local page-1 code + ANY main routine
  < $4000 (BIOS + the reclaimed low region, both stay visible — the same fact
  sub/basic-resident-abi.inc's ceiling check already relies on) + RAM are fine.

    python3 tools/check_tenant_closure.py --page1 build/sub.sym sub/sub.asm
"""
from __future__ import annotations
import os
import re
import sys
import glob

PAGE1 = 0x4000
LOWREGION = 0x2812   # main page-0 low region starts here; below it is BIOS

_SYM = re.compile(r'^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H', re.IGNORECASE)
_LBL = re.compile(r'^([A-Za-z_]\w*):')
# call/jp/jr/djnz <optional cc,> <label>   (label = symbolic target, not a number)
_XFER = re.compile(
    r'\b(?:call|jp|jr|djnz)\s+(?:(?:nz|z|nc|c|p|m|pe|po)\s*,\s*)?([A-Za-z_]\w*)')
_INC_SYM = re.compile(r'^\s*([A-Za-z_]\w*)\s+equ\b', re.IGNORECASE)
_IDENT = re.compile(r'[A-Za-z_]\w*')


def load_syms(path):
    syms = {}
    for line in open(path):
        m = _SYM.match(line)
        if m:
            syms[m.group(1)] = int(m.group(2), 16)
    return syms


# An unconditional control-flow terminator ends a routine's linear span (code
# past it is NOT reached by fallthrough). ret/reti/retn WITHOUT a condition,
# jp/jr with an unconditional target, and jp (hl/ix/iy).
_COND = ('nz', 'z', 'nc', 'c', 'p', 'm', 'pe', 'po')


def _is_terminator(code: str) -> bool:
    s = code.strip().lower()
    if not s:
        return False
    parts = s.split(None, 1)
    op = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""
    if op in ('reti', 'retn'):
        return True
    if op == 'ret':
        return rest == ""                     # `ret` uncond; `ret nz` falls through
    if op in ('jp', 'jr'):
        if rest.startswith('(') or op == 'jp' and rest in ('(hl)', '(ix)', '(iy)'):
            return True
        first = rest.split(',', 1)[0].strip()
        return first not in _COND             # `jp X` uncond; `jp nz,X` falls through
    return False


def build_callgraph(files):
    """label -> set(transfer targets) using each routine's LINEAR SPAN: from its
    label through any fallthrough into later labels, up to and including the first
    unconditional terminator. This captures call/jp targets that sit past a
    fallthrough into an internal label (how div10 was missed by naive
    nearest-label attribution). Over-attribution across fallthrough is safe (a
    closure gate must never MISS an edge). Fallthrough is tracked WITHIN a file
    only (each `include` is scanned separately), matching how the original
    basic/*.asm glob worked; edges between routines are still connected by name
    across the whole file set."""
    graph = {}
    for f in files:
        if not os.path.exists(f):
            continue
        lines = [ln.split(';', 1)[0] for ln in open(f)]
        labels = []  # (line_index, name)
        for i, code in enumerate(lines):
            m = _LBL.match(code)
            if m:
                labels.append((i, m.group(1)))
                graph.setdefault(m.group(1), set())
        for i, name in labels:
            j = i
            while j < len(lines):
                code = lines[j]
                for x in _XFER.finditer(code):
                    graph[name].add(x.group(1))
                if j > i and _is_terminator(code):
                    break
                j += 1
    return graph


def build_datagraph(files):
    """label -> set(identifiers its LINEAR SPAN mentions that are NOT transfer
    targets). Same spans as build_callgraph; the complement of its edge set.

    These are DATA references -- `ld de,tkf_ref32768`, `dw handler`, `ld hl,tbl`.
    A tenant that reaches such a span READS THE BYTES at that address with a page
    switched out, so a data target is subject to exactly the same region contract
    as a callee. Walking only call/jp/jr/djnz cannot see them, which is the error
    the ROM REGION STRUCTURE REVIEW hit with `ld hl,zkey_hook` (§0.1 error 3) and
    fixed only in check_dead_code.py -- so this gate, the review's own named
    feasibility oracle, stayed blind to the whole class. D-PINDATA,
    docs/spec-rom-region-promote-input.md §2.3.

    TWO rules, and both are load-bearing (spec §2.5 measured what breaks without
    each):

      * AN `equ` IS A VALUE, ONLY A `label:` IS A LOCATION. Callers filter this
        set against a label universe. Treating every symbol as an address reports
        63 spurious page-0 escapes on a clean tree -- token numbers, PSG ports,
        buffer capacities.
      * A DATA EDGE DOES NOT PROPAGATE CONTROL FLOW. Callers must not walk
        THROUGH a data target. Reading the 5 bytes of `tkf_ref32768` does not
        enter the routine that happens to follow it; propagating falls out of that
        `db` table into `flt_out` and pins 482 B of formatter nothing executes.

    ⚠️ A data reference to CODE (a hook whose address is installed, then called by
    the BIOS) IS executed, and this pass under-pins it: it marks the hook span and
    stops. Hooks stay explicitly seeded -- see DEFAULT_ISR_SEEDS in
    promote_scout.py, and `zkey_hook`."""
    data = {}
    for f in files:
        if not os.path.exists(f):
            continue
        lines = [ln.split(';', 1)[0] for ln in open(f)]
        labels = [(i, m.group(1)) for i, c in enumerate(lines)
                  if (m := _LBL.match(c))]
        for _, n in labels:
            data.setdefault(n, set())
        for i, name in labels:
            j = i
            while j < len(lines):
                code = lines[j]
                xfer = {m.group(1) for m in _XFER.finditer(code)}
                for t in _IDENT.finditer(code):
                    g = t.group(0)
                    if g not in xfer and g != name:
                        data[name].add(g)
                if j > i and _is_terminator(code):
                    break
                j += 1
    return data


def data_targets(seen, data, universe):
    """The labels reached by a DATA reference from the control closure `seen` and
    not already in it. `universe` is the set of `label:` definitions that count as
    locations (see build_datagraph's first rule)."""
    out = set()
    for n in seen:
        out |= {g for g in data.get(n, ()) if g in universe}
    return out - set(seen)


_ABI_INC = os.path.join("sub", "basic-resident-abi.inc")


def _abi_data_hole(seen, data):
    """The one hole build_datagraph's label-only rule leaves, made CHECKABLE.

    Main-ROM routines enter the sub build as `equ` addresses via
    sub/basic-resident-abi.inc, so they are VALUES to the label-only rule and a
    DATA reference to one would be silently unclassified. That is stated as a
    coverage limit in docs/spec-rom-region-promote-input.md §3.3 -- and stated
    with a measurement, "empty today", which is only worth something if the tree
    keeps re-measuring it. This returns the ABI names a walked span mentions
    non-transfer; a non-empty result means the exemption stopped being true and
    the case needs classifying by hand, not that the gate should widen."""
    if not os.path.exists(_ABI_INC):
        return set()
    abi = {m.group(1) for line in open(_ABI_INC)
           if (m := _INC_SYM.match(line))}
    hit = set()
    for n in seen:
        hit |= (data.get(n, set()) & abi)
    return hit


def seeds_from_inc(inc_path):
    return [m.group(1) for line in open(inc_path)
            if (m := _INC_SYM.match(line))]


_INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)


def _resolve_include(arg):
    """Mirror the sub build's `-I sub` search: a bare name resolves under sub/;
    an explicit path (basic/...) is repo-root relative."""
    return arg if '/' in arg else os.path.join('sub', arg)


def collect_sources(top, seen=None):
    """Ordered, de-duplicated list of every source file the assembly at `top`
    pulls in via `include` (recursively). Used to build the whole sub call graph
    (its own .asm + basic/pu-render.inc, basic/detok.inc, ...)."""
    if seen is None:
        seen = []
    if top in seen or not os.path.exists(top):
        return seen
    seen.append(top)
    for line in open(top):
        m = _INCLUDE.match(line.split(';', 1)[0])
        if m:
            collect_sources(_resolve_include(m.group(1)), seen)
    return seen


def _table_seeds(sub_asm, table_label):
    """The entry-table tenants: the `jp <tenant>` run right after `table_label:`
    (comment-only continuation lines are skipped; the run ends at the first
    non-jp code line). Shared by the page-0 (sub_p0_table) and page-1
    (sub_p1_table) entry tables."""
    seeds, in_table = [], False
    pat = re.compile(r'^\s*' + re.escape(table_label) + r':')
    for line in open(sub_asm):
        code = line.split(';', 1)[0]
        if not in_table:
            if pat.match(code):
                in_table = True
            continue
        s = code.strip()
        if not s:
            continue                              # comment-only / blank -> skip
        m = re.match(r'jp\s+([A-Za-z_]\w*)$', s)
        if m:
            seeds.append(m.group(1))
        else:
            break                                 # first non-jp -> table ended
    return seeds


def page0_seeds(sub_asm):
    return _table_seeds(sub_asm, 'sub_p0_table')


def page1_seeds(sub_asm):
    return _table_seeds(sub_asm, 'sub_p1_table')


def check_page1(argv) -> int:
    syms = load_syms(argv[0])
    files = sorted(glob.glob("basic/*.asm"))
    graph = build_callgraph(files)
    seeds = seeds_from_inc(argv[1])
    if not seeds:
        print(f"FAIL: no seed symbols in {argv[1]}", file=sys.stderr)
        return 1

    seen = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(c for c in graph.get(n, ()) if c not in seen)

    # DATA references out of that closure: bytes the tenant READS with main
    # page 1 switched out, so the same >= $4000 test applies (spec §2.4 —
    # basic/float.asm's tkf_ref* bound tables are reached this way and no gate
    # could see them before).
    dref = data_targets(seen, build_datagraph(files), set(graph))

    escapes = sorted((n, syms[n], "called") for n in seen
                     if n in syms and syms[n] >= PAGE1)
    escapes += sorted((n, syms[n], "DATA-referenced") for n in dref
                      if n in syms and syms[n] >= PAGE1)
    if escapes:
        print("FAIL: page-1 escapes in the tenant's resident closure — these "
              "routines/bytes are switched OUT while the page-1 tenant runs, so "
              "calling or reading them hangs/crashes. Relocate each to the "
              "page-0 low region (see cmp16_bits/div10 in basic/float-arith.asm):",
              file=sys.stderr)
        for n, a, how in escapes:
            print(f"  {n} = {a:04X}  <- {how}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} routines in the resident closure of {len(seeds)} "
          f"ABI seeds, + {len(dref)} data-referenced label(s), all page-0 "
          f"(< ${PAGE1:04X}). No page-1 escapes.")
    return 0


def check_page0(argv) -> int:
    sub_sym, sub_asm = argv[0], argv[1]
    syms = load_syms(sub_sym)
    sources = collect_sources(sub_asm)
    graph = build_callgraph(sources)
    sub_local = set(graph)                        # every label DEFINED in the sub image
    seeds = page0_seeds(sub_asm)
    if not seeds:
        print(f"FAIL: no page-0 seeds found (sub_p0_table) in {sub_asm}",
              file=sys.stderr)
        return 1

    seen = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(c for c in graph.get(n, ()) if c not in seen)

    # Classify every callee reached from the page-0 tenants. Sub-local page-0
    # code + main page-1 + RAM are fine; escapes are (a) an external/main import
    # < $4000 (main low region / BIOS, paged out), or (b) a sub-local label
    # >= $4000 (the sub's OWN page 1, not mapped during a page-0 call).
    dref = data_targets(seen, build_datagraph(sources), sub_local)
    bad = _abi_data_hole(seen, build_datagraph(sources))
    if bad:
        print(f"FAIL: a page-0 tenant DATA-references resident-ABI symbol(s) "
              f"{sorted(bad)}. Those arrive as `equ` addresses, so the "
              f"label-only rule in build_datagraph cannot classify them "
              f"(docs/spec-rom-region-promote-input.md §3.3 records this hole as "
              f"CHECKED EMPTY). It is no longer empty — classify by hand.",
              file=sys.stderr)
        return 1

    escapes = []
    for n in sorted(seen) + sorted(dref):
        addr = syms.get(n)
        if addr is None:
            continue                              # constant / not a placed label
        how = "called" if n in seen else "DATA-referenced"
        if n in sub_local:
            if addr >= PAGE1:
                escapes.append((n, addr, f"sub page-1 (own $4000+ island, unmapped "
                                         f"during a page-0 call), {how}"))
        elif addr < PAGE1:
            where = ("main low region $2812-$3FFF" if addr >= LOWREGION
                     else "main BIOS < $2812")
            escapes.append((n, addr,
                            f"{where} (switched out under a page-0 call), {how}"))

    if escapes:
        print("FAIL: page-0 escapes — a page-0 tenant runs with slot-0 page 0 "
              "(BIOS + low region + ISR) switched out, so these callees crash "
              "when reached. Keep them sub-local (page 0) or call only main "
              "page-1 ($4000-$7FFF):", file=sys.stderr)
        for n, a, why in escapes:
            print(f"  {n} = {a:04X}  <- {why}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} routines in the closure of {len(seeds)} page-0 "
          f"tenants ({', '.join(seeds)}), + {len(dref)} data-referenced label(s); "
          f"every callee and data target is sub-local page-0, main page-1, or "
          f"RAM. No low-region/BIOS escape.")
    return 0


def check_page1_tenant(argv) -> int:
    """The MIRROR of check_page0: walk the SUB call graph from the page-1
    entry-table tenants and fail on any callee that would be switched out while
    a page-1 tenant runs (docs/spec-evict-call-format.md §6 — added because the
    default check_page1 above only audits the resident-ABI IMPORT LIST, so a
    tenant that imports nothing there, like format_tenant, was never actually
    walked). Every main-BASIC page-1 tenant so far (fp_sqrt..fp_rnd) also passes
    this: their resident-ABI callees are all < $4000 (checked separately by
    check_resident_abi.py / the default mode above), and they call no main
    page-1 routine, so this is a strictly ADDITIONAL, not conflicting, gate."""
    sub_sym, sub_asm = argv[0], argv[1]
    syms = load_syms(sub_sym)
    sources = collect_sources(sub_asm)
    graph = build_callgraph(sources)
    sub_local = set(graph)                        # every label DEFINED in the sub image
    seeds = page1_seeds(sub_asm)
    if not seeds:
        print(f"FAIL: no page-1 seeds found (sub_p1_table) in {sub_asm}",
              file=sys.stderr)
        return 1

    seen = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(c for c in graph.get(n, ()) if c not in seen)

    # Classify every callee reached from the page-1 tenants. Sub-local page-1
    # code + ANY main routine < $4000 (BIOS + the reclaimed low region, both
    # stay mapped while a page-1 tenant runs) + RAM are fine; escapes are
    # (a) a sub-local label < $4000 (the sub's OWN page-0 island, not mapped
    # during a page-1 call), or (b) an external/main import >= $4000
    # (main-BASIC page 1, switched out under a page-1 call).
    dref = data_targets(seen, build_datagraph(sources), sub_local)
    bad = _abi_data_hole(seen, build_datagraph(sources))
    if bad:
        print(f"FAIL: a page-1 tenant DATA-references resident-ABI symbol(s) "
              f"{sorted(bad)}, which arrive as `equ` addresses and cannot be "
              f"classified by the label-only rule "
              f"(docs/spec-rom-region-promote-input.md §3.3, CHECKED EMPTY — no "
              f"longer). Classify by hand.", file=sys.stderr)
        return 1

    escapes = []
    for n in sorted(seen) + sorted(dref):
        addr = syms.get(n)
        if addr is None:
            continue                              # constant / not a placed label
        how = "called" if n in seen else "DATA-referenced"
        if n in sub_local:
            if addr < PAGE1:
                escapes.append((n, addr, f"sub page-0 (own island, unmapped "
                                         f"during a page-1 call), {how}"))
        elif addr >= PAGE1:
            escapes.append((n, addr, f"main-BASIC page-1 (switched out under "
                                     f"a page-1 call), {how}"))

    if escapes:
        print("FAIL: page-1 escapes — a page-1 tenant runs with slot-0 page 1 "
              "(main BASIC) switched out, so these callees crash when reached. "
              "Keep them sub-local (page 1) or call only main routines below "
              "$4000 (BIOS / the reclaimed low region):", file=sys.stderr)
        for n, a, why in escapes:
            print(f"  {n} = {a:04X}  <- {why}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} routines in the closure of {len(seeds)} page-1 "
          f"tenants ({', '.join(seeds)}), + {len(dref)} data-referenced label(s); "
          f"every callee and data target is sub-local page-1, main "
          f"low-region/BIOS (< ${PAGE1:04X}), or RAM. No main-page-1 escape.")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--page0":
        if len(args) != 3:
            sys.exit(__doc__)
        return check_page0(args[1:])
    if args and args[0] == "--page1":
        if len(args) != 3:
            sys.exit(__doc__)
        return check_page1_tenant(args[1:])
    if len(args) != 2:
        sys.exit(__doc__)
    return check_page1(args)


if __name__ == "__main__":
    raise SystemExit(main())
