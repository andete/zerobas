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
    slot-0 PAGE 0 (BIOS + the low region $2781-$3FFF + the $0038 ISR) switched
    OUT, while main PAGE 1 stays mapped. So every callee must be SUB-LOCAL (the
    sub-ROM's own page-0 code / RAM) or a MAIN PAGE-1 routine ($4000-$7FFF); a
    call into the main low region ($2781-$3FFF) or the BIOS (< $2781) hits code
    that is paged out -> crash. It must ALSO not reach the sub-ROM's OWN page 1
    (>= $4000 sub-local), which is unmapped during a page-0 call.
    🔁 SINCE MAKING ROOM lever A (2026-09-25) a MAIN PAGE-1 callee is refused as
    well: main code uses `rst $10` (CHRGTR), and under a page-0 tenant page 0 is
    the SUB ROM, so its $0010 is not CHRGTR. Measured empty when it was added.
    And any `rst` in the sub build's own sources is refused (rst_sites).

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
  >= $4000 (the sub's own page 1). Sub-local page-0 code + RAM are fine, and main
  page-1 as a DATA target; a main page-1 CALLEE is refused since lever A (see
  above). Distinguishing a sub-local $2900 (ok) from a main low-region $2900
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

  🔴 D-P1CLOSURE (2026-11-04): both tenant walks used to seed from the table
  rows up to the FIRST retired `ret / nop / nop` -- page 1 stopped at index 13,
  page 0 at index 11, and every tenant after was never walked. The scrape now
  reads each table to its end (table_rows; a malformed row is a failure, and
  the row count is checked against the assembled symbols), and the rule set
  carries the NAMED allowances those tenants need, each with a negative
  selftest arm: (a) BIOS_RAM_ROUTINES (CLPRIM) and, page 1 only, PAGE1_HOOKS
  (H_ERRP); (b) p0cb / p1cb IX targets, `ld de,p0_X / ret` continuations and
  call-back arguments, judged per SITE (classify_abi_site); (c) page 0: a
  direct main page-1 call the build ASSERTS (`IF p0_X < $4000` + `db`) and
  whose main body is walked for rst / low-region callees; (d) page 1: a direct
  call to a p0cb-section main routine whose main body closes below $4000.
"""
from __future__ import annotations
import os
import re
import sys
import glob

PAGE1 = 0x4000
LOWREGION = 0x2781   # main page-0 low region starts here; below it is BIOS

_SYM = re.compile(r'^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H', re.IGNORECASE)
_LBL = re.compile(r'^([A-Za-z_]\w*):')
# `name equ other` with a BARE identifier on the right -- an ALIAS, not a
# constant. See sub_local_aliases() for why the distinction is load-bearing.
_ALIAS = re.compile(r'^([A-Za-z_]\w*)\s+equ\s+([A-Za-z_]\w*)\s*$', re.I)
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


def sub_local_aliases(files, sub_local):
    """`name equ other` where `other` is a sub-local LABEL -> {name}.

    🔴 WHY THIS EXISTS. `sub_local` is built from `label:` definitions only, for
    a documented reason (build_datagraph: "an `equ` is a VALUE, only a `label:`
    is a LOCATION" -- without it, token numbers and PSG ports read as addresses
    and 63 spurious escapes appear). But D-DUPSPAN2's whole method is ALIASING a
    routine with `name equ other`, and such an alias is not a label -- so a
    SUB-LOCAL alias of a SUB-LOCAL routine fell through to the external branch
    and was reported as a main-ROM escape at its own correct address.

    Measured 2026-08-30 (D-NGRAM14): `fexp_underflow equ fexp_overflow` in
    sub/fp_exp.asm, both names resolving to $4F5C in build/sub.sym, reported as
    `fexp_underflow = 4F5C <- main-BASIC page-1`. The alias was ABANDONED rather
    than the checker fixed, which is the wrong way round.

    ⚠️ DELIBERATELY NARROW. Only an `equ` whose right-hand side is a BARE
    IDENTIFIER that is already known sub-local counts. `X equ 12`, `X equ Y+3`
    and `X equ SOME_MAIN_LABEL` are all untouched, so the rule this repairs can
    only ever ADD a symbol the tree already proves is sub-local. Resolved to a
    fixed point, so an alias of an alias is also sub-local."""
    out = set()
    pairs = []
    for f in files:
        if not os.path.exists(f):
            continue
        for line in open(f, errors="replace"):
            m = _ALIAS.match(line.split(";", 1)[0].rstrip())
            if m:
                pairs.append((m.group(1), m.group(2)))
    known = set(sub_local)
    changed = True
    while changed:                               # an alias OF an alias
        changed = False
        for name, target in pairs:
            if name not in known and target in known:
                known.add(name)
                out.add(name)
                changed = True
    return out


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
                r = _RST.match(code)
                if r:
                    graph[name].add(rst_target(r.group(1)))
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

# ---------------------------------------------------------------------------
# D-P1CLOSURE (2026-11-04): the NAMED allowances the whole-table walk needs.
# Each is narrow and each has a negative selftest arm. None is a blanket: an
# ABI / RAM / main-page-1 name that matches none of them stays an escape.
# ---------------------------------------------------------------------------

RAMBASE = 0xC000

# (a) BIOS RAM routines a tenant may transfer to. The MSX work area is page 3,
# mapped under every tenant of either page. Keyed by NAME with its documented
# address, so an `equ` that drifts (or a different name at $F38C) is not
# covered. CLPRIM: the BIOS's RAM inter-slot call primitive, the tail of p0cb /
# p1cb (sub/sub.asm) -- `jp CLPRIM` with A = the new primary slot register.
BIOS_RAM_ROUTINES = {"CLPRIM": 0xF38C}

# (a') MSX hooks a PAGE-1 tenant may call, by name and documented address. A
# hook is 5 bytes of page-3 RAM, a bare `ret` or a CALLF (`rst $30`) into the
# slot that claimed it -- which needs BIOS page 0, mapped under a page-1
# tenant and NOT under a page-0 one (there `rst $30` lands in the sub ROM), so
# this list is page 1 only. H_ERRP: sub/errmsg.asm (errmsg_tenant, index 22)
# offers a code it does not host to the disk ROM (D-DISKERR).
PAGE1_HOOKS = {"H_ERRP": 0xFEFD}

# (b) the call-back routines. `ld ix,p0_X` hands one of these a MAIN address,
# which it reaches with main mapped (CLPRIM), so p0_X is an IX TARGET, not a
# callee and not a byte this tenant reads.
CALLBACKS = ("p0cb", "p1cb")
_CB_XFER = re.compile(r'^(?:call|jp)\s+(?:(?:nz|z|nc|c|p|m|pe|po)\s*,\s*)?'
                      r'(p0cb|p1cb)$', re.I)
_LD_IX = re.compile(r'^ld\s+ix\s*,\s*([A-Za-z_]\w*)$', re.I)
_LD_DH = re.compile(r'^ld\s+(de|hl)\s*,\s*([A-Za-z_]\w*)$', re.I)
_DIRECT = re.compile(r'^(?:call|jp)\s+(?:(?:nz|z|nc|c|p|m|pe|po)\s*,\s*)?'
                     r'([A-Za-z_]\w*)$', re.I)
# (c) `IF <name> < $4000` + `db <error>`: the build refuses to assemble if a
# main routine a page-0 tenant calls DIRECTLY leaves main page 1.
_ASSERT_P1 = re.compile(r'^\s*IF\s+([A-Za-z_]\w*)\s*<\s*(?:\$4000|4000[hH]|0x4000)\s*$',
                        re.I)


def abi_names(path=_ABI_INC):
    """{name: is_callback_target} for every `equ` in a resident-ABI include --
    True for the p0cb section (the `p0_*` names), False for the code seeds."""
    out, cb = {}, False
    if not os.path.exists(path):
        return out
    for line in open(path):
        if line.startswith("; --- page-0 call-back (p0cb) targets"):
            cb = True
        if (m := _INC_SYM.match(line)):
            out[m.group(1)] = cb
    return out


def asserted_page1(files):
    """Names the build ASSERTS stay at or above $4000: an `IF name < $4000`
    whose next code line is a `db` (the deliberate assemble error). An IF with
    any other body is not an assert and does not count."""
    out = {}
    for f in files:
        if not os.path.exists(f):
            continue
        lines = [ln.split(';', 1)[0] for ln in open(f, errors="replace")]
        for i, code in enumerate(lines):
            m = _ASSERT_P1.match(code)
            if not m:
                continue
            nxt = next((c.strip() for c in lines[i + 1:] if c.strip()), "")
            if re.match(r'db\b', nxt, re.I):
                out[m.group(1)] = f"{f}:{i + 1}"
    return out


def _code_lines(f):
    return [ln.split(';', 1)[0].strip() for ln in open(f, errors="replace")]


def _forward(lines, i, labels, hops=4, limit=40):
    """Instructions on the forward path from line i+1: label-only lines are
    stepped over (fallthrough), an unconditional `jr/jp L` to a label in the
    same file is followed (at most `hops` times). Ends at any other terminator
    (it is yielded first). Yields (line_index, code)."""
    j, n = i + 1, 0
    while j < len(lines) and n < limit:
        code = lines[j]
        m = _LBL.match(code)
        if m:
            code = code[m.end():].strip()
        if not code:
            j += 1
            continue
        n += 1
        yield j, code
        if _is_terminator(code):
            t = re.match(r'^(?:jp|jr)\s+([A-Za-z_]\w*)$', code, re.I)
            if t and t.group(1) in labels and hops > 0:
                hops -= 1
                j = labels[t.group(1)] + 1
                lb = _LBL.match(lines[labels[t.group(1)]])
                rest = lines[labels[t.group(1)]][lb.end():].strip()
                if rest:                           # `label: insn` on one line
                    n += 1
                    yield j - 1, rest
                    if _is_terminator(rest):
                        return
                continue
            return
        j += 1


def _ix_reaches_callback(lines, i, labels):
    """(b) the IX loaded at line i is the one a p0cb / p1cb transfer consumes:
    one is reached on the forward path before IX is overwritten. `push ix` /
    `pop ix` nest (sub2/filestmt.asm's focas_buf calls p0cb once in between
    with a different IX, then once with this one)."""
    depth = 0
    for _, code in _forward(lines, i, labels):
        low = code.lower()
        if re.match(r'^push\s+ix$', low):
            depth += 1
        elif re.match(r'^pop\s+ix$', low):
            depth -= 1
            if depth < 0:
                return False
        elif depth == 0 and _CB_XFER.match(code):
            return True
        elif depth == 0 and re.match(r'^(ld\s+ix\s*,|ex\s+\(sp\)\s*,\s*ix|inc\s+ix|dec\s+ix|add\s+ix)', low):
            return False
        if _is_terminator(code) and not re.match(r'^(?:jp|jr)\s+[A-Za-z_]\w*$', code, re.I):
            return False
    return False


def classify_abi_site(lines, i, name, labels, abi, asserted):
    """Why the ABI name `name`, mentioned NOT as a transfer target on line i,
    is allowed -- or None (an escape the gate reports). Three shapes:

      IX   `ld ix,p0_X` whose IX a p0cb / p1cb transfer consumes (b).
      CONT `ld de,p0_X` + an unconditional `ret`: a CONTINUATION -- the
           tenant returns it to main's stub, which jumps there with main mapped.
      ARG  `ld de|hl,p0_X` + the main callee that reads it, next: either an IX
           shape above (the call-back runs main with main mapped) or a direct
           `call` the build asserts is main page 1 (c). The bytes are read by
           MAIN code, never by this tenant.
    Only p0cb-section names qualify; a code-seed ABI name never does."""
    if not abi.get(name):
        return None
    code = lines[i]
    m = _LBL.match(code)
    if m:
        code = code[m.end():].strip()
    if (mi := _LD_IX.match(code)) and mi.group(1) == name:
        return "IX target of p0cb/p1cb" if _ix_reaches_callback(lines, i, labels) else None
    md = _LD_DH.match(code)
    if not md or md.group(2) != name:
        return None
    j, nxt = next(_forward(lines, i, labels, hops=0, limit=1), (None, ""))
    if md.group(1).lower() == "de" and nxt.lower() == "ret":
        return "continuation (ld de / ret)"
    if (mi := _LD_IX.match(nxt)) and abi.get(mi.group(1)) \
            and _ix_reaches_callback(lines, j, labels):
        return f"argument of call-back {mi.group(1)}"
    if (mc := _DIRECT.match(nxt)) and mc.group(1) in asserted:
        return f"argument of asserted direct call {mc.group(1)}"
    return None


def abi_data_escapes(seen, files, abi, asserted):
    """Every non-transfer mention of a resident-ABI name in a walked span that
    classify_abi_site does not allow, as (name, file, line). Line-level, so an
    allowed `ld ix,p0_X` elsewhere cannot excuse a bare `ld hl,p0_X` here."""
    out, allowed = [], 0
    for f in files:
        if not os.path.exists(f):
            continue
        lines = _code_lines(f)
        labels = {}
        for k, c in enumerate(lines):
            if (m := _LBL.match(c)):
                labels.setdefault(m.group(1), k)
        for k, c in enumerate(lines):
            if (m := _LBL.match(c)) and m.group(1) in seen:
                j = k
                while j < len(lines):
                    code = lines[j]
                    xfer = {x.group(1) for x in _XFER.finditer(code)}
                    for t in _IDENT.finditer(code):
                        g = t.group(0)
                        if g in abi and g not in xfer:
                            if classify_abi_site(lines, j, g, labels, abi, asserted):
                                allowed += 1
                            else:
                                out.append((g, f, j + 1))
                    if j > k and _is_terminator(code):
                        break
                    j += 1
    return sorted(set(out)), allowed


def main_closure(name, graph):
    seen, stack = set(), [name]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.get(n, ()))
    return seen


def direct_main_call_ok(n, page, main_syms, main_graph, abi, asserted):
    """(c) / (d): may a tenant of `page` CALL the main routine `n` (a p0cb-
    section ABI name, main's routine without the p0_ prefix) DIRECTLY?

      page 0: only if the build asserts `n` stays >= $4000, and main's closure
              of it (basic/*.asm, rst edges included) stays in main page 1 on
              this build with every exported member asserted too -- the lever-A
              question ("walk its body for rst before allowing it"), asked.
      page 1: main's closure of it stays < $4000 (or RAM): page 1 is switched
              out under a page-1 tenant.
    Returns (ok, why)."""
    if not abi.get(n) or not n.startswith("p0_"):
        return False, "not a p0cb-section main routine"
    if main_syms is None:
        return False, "no main symbol file to walk the main body against"
    body = n[3:]
    if body not in main_graph:
        return False, f"main routine {body} not found in basic/*.asm"
    clo = main_closure(body, main_graph)
    if page == 0:
        if n not in asserted:
            return False, f"no `IF {n} < $4000` assert in the build"
        for m in sorted(clo):
            a = main_syms.get(m)
            if a is None or not (PAGE1 <= a < 0x8000):
                return False, (f"main closure member {m} "
                               f"{'unplaced' if a is None else f'= {a:04X}'} "
                               f"is not main page 1 (rst / low region / BIOS)")
            if "p0_" + m in abi and "p0_" + m not in asserted:
                return False, f"closure member {m} is exported but not asserted"
        return True, f"asserted at {asserted[n]}; closure {len(clo)} labels, all main page 1"
    for m in sorted(clo):
        a = main_syms.get(m)
        if a is None or (PAGE1 <= a < RAMBASE):
            return False, (f"main closure member {m} "
                           f"{'unplaced' if a is None else f'= {a:04X}'} "
                           f"is main page 1 (switched out)")
    return True, f"closure {len(clo)} labels, all < $4000 or RAM"




def seeds_from_inc(inc_path):
    """The CODE seeds of a generated import. 🔴 It stops at the p0cb section
    (D-P0CB, 2026-10-21): those targets are reached through CLPRIM with main's
    page 0 mapped, so their closures may legitimately leave the low region --
    walking them as page-1-tenant imports would report every one as an escape."""
    out = []
    for line in open(inc_path):
        if line.startswith("; --- page-0 call-back (p0cb) targets"):
            break
        if (m := _INC_SYM.match(line)):
            out.append(m.group(1))
    return out


_INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)


def _resolve_include(arg, incdir):
    """Mirror the assembler's `-I <incdir>` search: a bare name resolves under
    `incdir`; an explicit path (basic/...) is repo-root relative.

    🔴 `incdir` USED TO BE HARDCODED TO `sub`, and that was invisible because it
    is the RIGHT answer for the only caller there was. The disk ROM is built
    with `-I disk` (Makefile) and has its OWN equates.inc, so walking
    disk/disk.asm under the old rule quietly returned SUB's equates.inc and
    dropped every disk part whose name sub/ does not also carry -- a closure of
    3 files for an 8-file ROM, with no error anywhere. An instrument that
    misreads its input and hands back a plausible table is the shape this
    project keeps meeting; the fix is to take the search path from the caller
    rather than from the one build that existed first.
    """
    return arg if '/' in arg else os.path.join(incdir, arg)


def collect_sources(top, seen=None, incdir=None):
    """Ordered, de-duplicated list of every source file the assembly at `top`
    pulls in via `include` (recursively). Used to build the whole sub call graph
    (its own .asm + basic/pu-render.inc, basic/detok.inc, ...).

    `incdir` is the assembler's `-I` directory; it defaults to the TOP file's
    own directory, which is what every build in this tree actually passes
    (`-I sub` for sub/sub.asm, `-I disk` for disk/disk.asm) and is a no-op for
    basic/main.asm, whose includes are all repo-root paths.
    """
    if seen is None:
        seen = []
    if incdir is None:
        incdir = os.path.dirname(top) or '.'
    if top in seen or not os.path.exists(top):
        return seen
    seen.append(top)
    for line in open(top):
        m = _INCLUDE.match(line.split(';', 1)[0])
        if m:
            collect_sources(_resolve_include(m.group(1), incdir), seen, incdir)
    return seen


class TableError(Exception):
    """An entry-table row that is neither a live `jp <tenant>` nor the retired
    `ret / nop / nop` shape. A malformed row is a FAILURE, never a skip."""


_RETIRED = ("ret", "nop", "nop")


def table_rows(sub_asm, table_label):
    """Every row of the entry table at `table_label`, to its DECLARED END.

    🔴 D-P1CLOSURE (2026-11-04): this used to stop at the first code line that
    was not a `jp`, and both tables carry RETIRED rows (`ret / nop / nop`, kept
    so later indexes stay put). Page 1 stopped at index 13 and page 0 at index
    11, so every tenant appended after a retirement -- 21 page-1 rows and 7
    page-0 rows -- was never closure-checked, and both gates printed OK.

    The table's end is the NEXT `label:` in the file (sub_p0_ping /
    sub_p1_ping today): the table is a run of 3-byte rows with no label of its
    own inside it, and check_page0 / check_page1_tenant cross-check the row
    count against the assembled symbols (end label - table label == 3 * rows),
    so a row this scrape mis-counts is a failure too.

    Returns [(index, tenant_or_None, line_no)] -- None for a retired row.
    Raises TableError on any other shape, on a row whose comment names a
    different `index N` than its position, and on a table with no end label."""
    pat = re.compile(r'^\s*' + re.escape(table_label) + r':')
    rows, in_table, retired, end = [], False, [], None
    for ln, line in enumerate(open(sub_asm), 1):
        code, _, comment = line.partition(';')
        if not in_table:
            if pat.match(code):
                in_table = True
            continue
        if _LBL.match(code):
            end = _LBL.match(code).group(1)
            break
        s = code.strip()
        if not s:
            continue                              # comment-only / blank -> skip
        idx = len(rows)
        named = re.search(r'\bindex\s+(\d+)\b', comment)
        if retired:
            want = _RETIRED[len(retired)]
            if s.lower() != want:
                raise TableError(f"{sub_asm}:{ln}: {table_label} row {idx} "
                                 f"starts the retired shape `ret / nop / nop` "
                                 f"but has `{s}` where `{want}` belongs")
            retired.append(ln)
            if len(retired) == 3:
                rows.append((idx, None, retired[0]))
                retired = []
            continue
        if named and int(named.group(1)) != idx:
            raise TableError(f"{sub_asm}:{ln}: {table_label} row {idx} is "
                             f"commented `index {named.group(1)}` -- the scrape "
                             f"and the table disagree on where it is")
        m = re.match(r'jp\s+([A-Za-z_]\w*)$', s)
        if m:
            rows.append((idx, m.group(1), ln))
        elif s.lower() == "ret":
            retired = [ln]
        else:
            raise TableError(f"{sub_asm}:{ln}: {table_label} row {idx} is "
                             f"`{s}` -- neither `jp <tenant>` nor a retired "
                             f"`ret / nop / nop`")
    if retired:
        raise TableError(f"{sub_asm}:{retired[0]}: {table_label} ends inside a "
                         f"retired row ({len(retired)} of 3 lines)")
    if not in_table or end is None:
        raise TableError(f"{sub_asm}: {table_label} not found, or no label "
                         f"after it to end the table")
    return rows, end


def check_table_extent(syms, table_label, end_label, rows):
    """The assembled cross-check: 3 bytes per row, end label right after."""
    a, b = syms.get(table_label), syms.get(end_label)
    if a is None or b is None:
        return (f"{table_label} / {end_label} missing from the symbol file -- "
                f"cannot confirm the scraped row count")
    if b - a != 3 * len(rows):
        return (f"{table_label} ${a:04X} .. {end_label} ${b:04X} is "
                f"{b - a} B, but the scrape found {len(rows)} rows "
                f"({3 * len(rows)} B)")
    return None


def _table_seeds(sub_asm, table_label):
    """The LIVE tenants of an entry table, every row to its end (retired rows
    skipped -- see table_rows)."""
    rows, _ = table_rows(sub_asm, table_label)
    return [t for _, t, _ in rows if t]


def page0_seeds(sub_asm):
    return _table_seeds(sub_asm, 'sub_p0_table')


def page1_seeds(sub_asm):
    return _table_seeds(sub_asm, 'sub_p1_table')


def disk_code_seeds():
    """--disk (D-DISKREST slice 0, 2026-10-20): disk.rom is a PAGE-1 ROM, so while
    it runs main page 1 is switched OUT exactly as under a sub-ROM page-1 tenant.
    The main routines it calls by ABSOLUTE address -- `tools/gen_resident_abi.py`'s
    REQUIRED_DISK_CODE -- must therefore close entirely below $4000. The default
    mode cannot be pointed at disk/basic-resident-abi.inc: that file also carries
    the RAM cells and the `calbak` targets, which are page 1 ON PURPOSE (reached
    by an inter-slot call, not a `call`). Seeding from the code list alone is the
    question. 🔴 Nothing asked it before: `widen_rhs_operand` sat in the list,
    unused, while its callee `factyp_is2` was page 1 -- a crash waiting for a
    caller (found by reading, 2026-10-20)."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gen_resident_abi                        # noqa: E402
    return list(gen_resident_abi.REQUIRED_DISK_CODE)


def check_page1(argv, seeds=None) -> int:
    syms = load_syms(argv[0])
    files = sorted(glob.glob("basic/*.asm"))
    graph = build_callgraph(files)
    if seeds is None:
        seeds = seeds_from_inc(argv[1])
    if not seeds:
        print(f"FAIL: no seed symbols in {argv[1:] or 'the disk code list'}",
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


_RST = re.compile(r'^\s*(?:[A-Za-z_]\w*:)?\s*rst\b\s*([^;]*)', re.I)


# 🔁 MAKING ROOM lever A (2026-09-25): main's RST vectors are ITS OWN routines
# (basic/islands.asm, repointed by tools/build_mainrom.py PATCH_RANGES), so an
# `rst` in main is a CALL and the walk must follow it. `rst $18` is the one that
# matters: outdo jumps to `pchar` in MAIN PAGE 1, so a low-region routine a
# page-1 tenant calls back into must not use it -- and without this edge the
# default walk would never see it.
RST_TARGETS = {0x10: "chrgtr", 0x18: "outdo"}


def rst_target(arg: str) -> str:
    """The routine an `rst <arg>` enters: a named main vector, else a
    placeholder no symbol table holds (so the walk records it and moves on)."""
    t = arg.strip().lower()
    try:
        if t.startswith("$"):
            v = int(t[1:], 16)
        elif t.startswith("0x"):
            v = int(t[2:], 16)
        elif t.endswith("h"):
            v = int(t[:-1], 16)
        else:
            v = int(t)
    except ValueError:
        return "__rst_" + t
    return RST_TARGETS.get(v, "__rst_%02x" % v)


def rst_sites(files):
    """Every `rst` instruction in the sub build's sources, as (file, line, arg).

    🔁 MAKING ROOM lever A (2026-09-25): main's `rst $10` is CHRGTR, and it
    lands in basic/islands.asm through the $0010 vector of SLOT-0 PAGE 0. The
    call-graph walk above never sees an `rst` (its target is a number, not a
    label), so a tenant that used one would pass it silently -- and a PAGE-0
    tenant's `rst $10` reaches the SUB-ROM's own $0010, not CHRGTR. A shared
    `*-body.inc` converted by the next carve sweep is exactly how one would
    arrive. Measured EMPTY on the day the vector was taken; this keeps it so."""
    out = []
    for f in files:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                m = _RST.match(line.split(";", 1)[0])
                if m:
                    out.append((f, i, m.group(1).strip()))
    return out


def tenant_closure(page, sub_sym, sub_asm, abi_path=_ABI_INC,
                   main_sym=None, main_files=None):
    """The shared walk behind --page0 and --page1. Returns
    (seeds, rows, seen, dref, escapes, allowed); raises TableError on a
    malformed entry table.

    page 0 -- a page-0 tenant runs with slot-0 page 0 (BIOS + low region +
    ISR) switched out and main page 1 mapped. Fine: sub-local page-0 code,
    RAM, main page 1 as DATA. Escapes: a main routine < $4000, a sub-local
    label >= $4000, and -- since MAKING ROOM lever A (2026-09-25), because main
    code may `rst $10` and an rst under a page-0 tenant lands in the SUB ROM's
    $0010 -- any main page-1 CALLEE, except (c) below.

    page 1 -- the mirror: main page 1 is switched out, main page 0 (BIOS + low
    region) and RAM stay mapped. Escapes: a sub-local label < $4000, a main
    routine >= $4000.

    D-P1CLOSURE's named allowances (see their definitions above): (a)
    BIOS_RAM_ROUTINES as callees; (b) p0cb / p1cb IX targets, continuations and
    call-back arguments, per SITE (classify_abi_site); (c) page 0: a direct
    main page-1 call the build asserts and whose main body is walked; (d) page
    1: a direct call to a p0cb-section main routine whose main body closes
    below $4000 -- a BIOS / low-region callee was always fine here."""
    syms = load_syms(sub_sym)
    if main_sym is None:
        cand = os.path.join(os.path.dirname(sub_sym), "basic-reloc.sym")
        main_sym = cand if os.path.exists(cand) else None
    main_syms = load_syms(main_sym) if main_sym else None
    main_graph = build_callgraph(main_files if main_files is not None
                                 else sorted(glob.glob("basic/*.asm")))
    sources = collect_sources(sub_asm)
    graph = build_callgraph(sources)
    sub_local = set(graph)                        # every label DEFINED in the sub image
    sub_local |= sub_local_aliases(sources, sub_local)   # ...and aliases OF those
    table = 'sub_p0_table' if page == 0 else 'sub_p1_table'
    rows, end = table_rows(sub_asm, table)
    escapes = []
    ext = check_table_extent(syms, table, end, rows)
    if ext:
        escapes.append((table, syms.get(table, 0), "TABLE: " + ext))
    seeds = [t for _, t, _ in rows if t]

    seen = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(c for c in graph.get(n, ()) if c not in seen)

    abi = abi_names(abi_path)
    asserted = asserted_page1(sources)
    dref = data_targets(seen, build_datagraph(sources), sub_local)
    bad, allowed = abi_data_escapes(seen, sources, abi, asserted)
    for n, f, ln in bad:
        escapes.append((n, syms.get(n, abi_sym_value(n, abi_path)),
                        f"resident-ABI name DATA-referenced at {f}:{ln} in no "
                        f"allowed shape (IX target / continuation / call-back "
                        f"argument) -- classify by hand"))

    for n in sorted(seen) + sorted(dref):
        addr = syms.get(n)
        if addr is None:
            continue                              # constant / not a placed label
        how = "called" if n in seen else "DATA-referenced"
        if n in sub_local:
            if page == 0 and addr >= PAGE1:
                escapes.append((n, addr, f"sub page-1 (own $4000+ island, unmapped "
                                         f"during a page-0 call), {how}"))
            if page == 1 and addr < PAGE1:
                escapes.append((n, addr, f"sub page-0 (own island, unmapped "
                                         f"during a page-1 call), {how}"))
            continue
        if how == "called" and n in BIOS_RAM_ROUTINES:
            if addr == BIOS_RAM_ROUTINES[n]:
                allowed += 1
                continue                          # (a)
            escapes.append((n, addr, f"named BIOS RAM routine at the wrong "
                                     f"address (documented "
                                     f"{BIOS_RAM_ROUTINES[n]:04X}), called"))
            continue
        if page == 1 and how == "called" and n in PAGE1_HOOKS:
            if addr == PAGE1_HOOKS[n]:
                allowed += 1
                continue                          # (a')
            escapes.append((n, addr, f"named hook at the wrong address "
                                     f"(documented {PAGE1_HOOKS[n]:04X}), called"))
            continue
        if page == 0:
            if addr < PAGE1:
                where = ("main low region $2781-$3FFF" if addr >= LOWREGION
                         else "main BIOS < $2781")
                escapes.append((n, addr,
                                f"{where} (switched out under a page-0 call), {how}"))
            elif how == "called":
                ok, why = direct_main_call_ok(n, 0, main_syms, main_graph,
                                              abi, asserted)
                if ok:
                    allowed += 1
                else:
                    escapes.append((n, addr, "main page-1 routine CALLED from a "
                                             "page-0 tenant -- main code may "
                                             "`rst $10`, which would land in the "
                                             "sub ROM's own $0010 (" + why + ")"))
        else:
            if addr >= PAGE1:
                escapes.append((n, addr, f"main-BASIC page-1 (switched out under "
                                         f"a page-1 call), {how}"))
            elif how == "called" and abi.get(n):
                ok, why = direct_main_call_ok(n, 1, main_syms, main_graph,
                                              abi, asserted)
                if ok:
                    allowed += 1
                else:
                    escapes.append((n, addr, "main routine CALLED DIRECTLY from a "
                                             "page-1 tenant whose main body leaves "
                                             "page 0 (" + why + ")"))
    return seeds, rows, seen, dref, escapes, allowed


def abi_sym_value(name, abi_path=_ABI_INC):
    if os.path.exists(abi_path):
        for line in open(abi_path):
            m = re.match(r'^\s*' + re.escape(name) + r'\s+equ\s+([0-9A-Fa-f]+)H', line, re.I)
            if m:
                return int(m.group(1), 16)
    return 0


def _row_summary(rows):
    return ", ".join(f"{i}:{t}" if t else f"{i}:retired" for i, t, _ in rows)


def _run_page(argv, page) -> int:
    sub_sym, sub_asm = argv[0], argv[1]
    rst = rst_sites(collect_sources(sub_asm)) if page == 0 else []
    if rst:
        print("FAIL: `rst` in the sub build -- a page-0 tenant's rst lands in the "
              "SUB-ROM's own vector, not main's (main `rst $10` is CHRGTR, "
              "basic/islands.asm). Use a `call`:", file=sys.stderr)
        for f, i, arg in rst:
            print(f"  {f}:{i}  rst {arg}", file=sys.stderr)
        return 1
    try:
        seeds, rows, seen, dref, escapes, allowed = tenant_closure(page, sub_sym, sub_asm)
    except TableError as e:
        print(f"FAIL: malformed entry table -- {e}", file=sys.stderr)
        return 1
    if not seeds:
        print(f"FAIL: no page-{page} seeds found in {sub_asm}", file=sys.stderr)
        return 1
    if escapes:
        if page == 0:
            print("FAIL: page-0 escapes — a page-0 tenant runs with slot-0 page 0 "
                  "(BIOS + low region + ISR) switched out, so these callees crash "
                  "when reached. Keep them sub-local (page 0), or reach main "
                  "through p0cb:", file=sys.stderr)
        else:
            print("FAIL: page-1 escapes — a page-1 tenant runs with slot-0 page 1 "
                  "(main BASIC) switched out, so these callees crash when reached. "
                  "Keep them sub-local (page 1), call only main routines below "
                  "$4000 (BIOS / the reclaimed low region), or reach main "
                  "through p1cb:", file=sys.stderr)
        for n, a, why in escapes:
            print(f"  {n} = {a:04X}  <- {why}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} routines in the closure of {len(seeds)} page-{page} "
          f"tenants, every table row walked ({_row_summary(rows)}), + {len(dref)} "
          f"data-referenced label(s), {allowed} site(s) passed by a named "
          f"allowance (CLPRIM / H_ERRP / p0cb-p1cb IX / continuation / call-back arg / "
          f"asserted direct call). No escape.")
    return 0


def check_page0(argv) -> int:
    return _run_page(argv, 0)


def check_page1_tenant(argv) -> int:
    """The MIRROR of check_page0 (docs/spec-evict-call-format.md §6 -- added
    because the default check_page1 only audits the resident-ABI IMPORT LIST,
    so a tenant that imports nothing there, like format_tenant, was never
    walked)."""
    return _run_page(argv, 1)


def selftest() -> int:
    """Arms for sub_local_aliases -- the rule D-NGRAM14 needed and did not have.

    🔴 THE CONTROL IS THE POINT. The label-only rule exists because treating
    every `equ` as an address reports 63 spurious escapes; a fix that widened it
    to ALL equs would trade one blind spot for a much louder one. So C1/C2 assert
    that a constant and an expression are still NOT sub-local, and they would
    both pass trivially if the alias rule had simply been made permissive."""
    ok = True

    def arm(name, cond):
        nonlocal ok
        print(f"{'PASS' if cond else 'FAIL'}  {name}")
        ok = ok and bool(cond)

    # probe_tmp owns the scratch root and clears it at exit -- `temp-root-check`
    # refuses a hardcoded one, and it caught this line.
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "probes", "lib"))
    import probe_tmp                                              # noqa: E402
    tmp = probe_tmp.tmp("closure_selftest.asm")
    with open(tmp, "w") as fh:
        fh.write(
            "real_body:\n"
            "                ret\n"
            "the_alias       equ     real_body\n"
            "alias_of_alias  equ     the_alias\n"
            "a_constant      equ     12\n"
            "an_expression   equ     real_body+3\n"
            "main_import     equ     $4F5C\n"
            "with_comment    equ     real_body    ; an alias, and a comment\n")
    got = sub_local_aliases([tmp], {"real_body"})

    arm("A1 `the_alias equ real_body` is sub-local "
        "(the exact shape subrom-closure-check refused in D-NGRAM14)",
        "the_alias" in got)
    arm("A2 an alias OF an alias resolves too (fixed point)",
        "alias_of_alias" in got)
    arm("A3 a trailing comment does not hide the alias",
        "with_comment" in got)
    # 🔴 the three that must NOT be reclassified
    arm("C1 CONTROL: `a_constant equ 12` is NOT sub-local",
        "a_constant" not in got)
    arm("C2 CONTROL: `an_expression equ real_body+3` is NOT sub-local "
        "(it is a VALUE derived from a label, not that label)",
        "an_expression" not in got)
    arm("C3 CONTROL: an equ of an address literal is NOT sub-local",
        "main_import" not in got)
    arm("C4 CONTROL: an alias of an UNKNOWN name is NOT sub-local",
        sub_local_aliases([tmp], set()) == set())
    # rst guard (lever A): a planted rst is found, a comment and a label are not
    with open(tmp, "w") as fh:
        fh.write("x:              rst     $10\n"
                 "                ld      a,1     ; rst $10 in a comment\n"
                 "first_rst:\n"
                 "                call    y\n")
    found_rst = rst_sites([tmp])
    arm("R1 a planted `rst $10` (behind a label) is found, once",
        len(found_rst) == 1 and found_rst[0][1] == 1 and found_rst[0][2] == "$10")
    arm("R2 CONTROL: `rst` in a comment or inside a label name is NOT a site",
        all(i == 1 for _, i, _ in found_rst))
    g = build_callgraph([tmp])
    arm("R3 `rst $10` is an EDGE to chrgtr in the call graph (lever A)",
        "chrgtr" in g.get("x", ()))
    arm("R4 `rst 18h` / `rst $18` / `rst 24` all name outdo; `rst $38` names none",
        rst_target("18h") == rst_target("$18") == rst_target("24") == "outdo"
        and rst_target("$38") == "__rst_38")
    # the live tree: the rule must not be vacuous OR sweeping
    live = collect_sources("sub/sub.asm") if os.path.exists("sub/sub.asm") else []
    if live:
        base = set(build_callgraph(live))
        found = sub_local_aliases(live, base)
        arm(f"L1 on the live sub tree it adds a BOUNDED set "
            f"({len(found)} alias(es): {sorted(found) or 'none'}) — "
            f"fewer than the {len(base)} labels it starts from",
            len(found) < len(base))
    os.remove(tmp)
    _selftest_tables(arm, probe_tmp)
    print("selftest:", "GREEN" if ok else "🔴 RED")
    return 0 if ok else 1


def _selftest_tables(arm, probe_tmp):
    """D-P1CLOSURE arms: the whole-table walk and each named allowance, every
    one with its NEGATIVE. A planted mini sub ROM (table + tenants + ABI include
    + symbols) and a planted mini main (basic/*.asm stand-in + its symbols)."""
    d = probe_tmp.tmp("closure_tables")
    os.makedirs(d, exist_ok=True)
    abi = os.path.join(d, "abi.inc")
    with open(abi, "w") as fh:
        fh.write("code_seed equ 01000H\n"
                 "; --- page-0 call-back (p0cb) targets: planted ---\n"
                 "p0_lowfn equ 02800H\n"
                 "p0_hifn equ 05000H\n"
                 "p0_hirst equ 05100H\n"
                 "p0_hicalls_low equ 05200H\n"
                 "p0_lowfn_calls_hi equ 02900H\n"
                 "p0_hidata equ 05300H\n")
    main_asm = os.path.join(d, "main.asm")
    with open(main_asm, "w") as fh:
        fh.write("lowfn:\n ret\n"
                 "hifn:\n ret\n"
                 "hirst:\n rst $10\n ret\n"
                 "hicalls_low:\n call lowfn\n ret\n"
                 "lowfn_calls_hi:\n call hifn\n ret\n")
    main_sym = os.path.join(d, "main.sym")
    with open(main_sym, "w") as fh:
        for n, a in (("lowfn", 0x2800), ("hifn", 0x5000), ("hirst", 0x5100),
                     ("hicalls_low", 0x5200), ("lowfn_calls_hi", 0x2900),
                     ("chrgtr", 0x0160)):
            fh.write(f"{n}\tEQU 0{a:04X}H\n")

    def scenario(page, rows, body, syms, asserts=""):
        """rows: table lines; body: tenant code. Returns the escapes, or the
        TableError text."""
        tab = "sub_p0_table" if page == 0 else "sub_p1_table"
        asm = os.path.join(d, "sub.asm")
        with open(asm, "w") as fh:
            fh.write(asserts + tab + ":\n" + rows + "tab_end:\n" + body)
        sym = os.path.join(d, "sub.sym")
        base = 0x0040 if page == 0 else 0x4010
        nrows = sum(1 for ln in rows.splitlines()
                    if ln.split(";")[0].strip()
                    and ln.split(";")[0].strip().lower() not in ("nop",))
        allsyms = {tab: base, "tab_end": base + 3 * nrows}
        allsyms.update(syms)
        with open(sym, "w") as fh:
            for n, a in allsyms.items():
                fh.write(f"{n}\tEQU 0{a:04X}H\n")
        try:
            out = tenant_closure(page, sym, asm, abi_path=abi,
                                 main_sym=main_sym, main_files=[main_asm])
        except TableError as e:
            return "TableError: " + str(e)
        return out

    def names(r):
        return set() if isinstance(r, str) else {n for n, _, _ in r[4]}

    def seeds(r):
        return [] if isinstance(r, str) else r[0]

    P1 = 0x5000          # a sub-local page-1 address
    P0 = 0x1000          # a sub-local page-0 address
    retired_rows = (" jp ta ; index 0\n ret ; index 1: RETIRED\n nop\n nop\n"
                    " jp tb ; index 2\n")

    # --- the scrape --------------------------------------------------------
    r = scenario(1, retired_rows, "ta:\n ret\ntb:\n ret\n", {"ta": P1, "tb": P1 + 1})
    arm("W1 a tenant row AFTER a retired row is walked (the old blind spot: "
        "the scrape stopped at the first non-jp)", seeds(r) == ["ta", "tb"])
    arm("W2 ...and the same table, clean, has no escape", names(r) == set())
    r = scenario(1, retired_rows, "ta:\n ret\ntb:\n call lowlocal\n ret\n"
                 "lowlocal:\n ret\n", {"ta": P1, "tb": P1 + 1, "lowlocal": P0})
    arm("W3 a forbidden call in the tenant after the retired row is RED "
        "(page 1 -> the sub's own page 0)", "lowlocal" in names(r))
    r = scenario(1, " jp ta\n ret\n nop\n ld a,1\n jp tb\n",
                 "ta:\n ret\ntb:\n ret\n", {"ta": P1, "tb": P1 + 1})
    arm("W4 a malformed retired row (`ret / nop / ld a,1`) is a FAILURE, not "
        "a skip", isinstance(r, str) and "retired shape" in r)
    r = scenario(1, " jp ta\n ld a,1\n", "ta:\n ret\n", {"ta": P1})
    arm("W5 a row that is neither `jp` nor `ret` is a FAILURE",
        isinstance(r, str) and "neither" in r)
    r = scenario(1, " jp ta ; index 0\n jp tb ; index 2\n",
                 "ta:\n ret\ntb:\n ret\n", {"ta": P1, "tb": P1 + 1})
    arm("W6 a row whose comment names another index is a FAILURE",
        isinstance(r, str) and "index 2" in r)
    r = scenario(1, " jp ta\n jp tb\n", "ta:\n ret\ntb:\n ret\n",
                 {"ta": P1, "tb": P1 + 1, "tab_end": 0x4010 + 9})
    arm("W7 a table whose assembled size disagrees with the scrape is RED",
        "sub_p1_table" in names(r))

    # --- (a) CLPRIM ---------------------------------------------------------
    r = scenario(1, " jp ta\n", "ta:\n jp CLPRIM\n", {"ta": P1, "CLPRIM": 0xF38C})
    arm("A1 `jp CLPRIM` at $F38C is allowed", names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n jp CLPRIM\n", {"ta": P1, "CLPRIM": 0xF38D})
    arm("A2 NEG: CLPRIM equ'd to a different address is RED", "CLPRIM" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n call OTHERRAM\n ret\n",
                 {"ta": P1, "OTHERRAM": 0xF400})
    arm("A3 NEG: any other RAM callee is still RED (no blanket RAM rule)",
        "OTHERRAM" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n call H_ERRP\n ret\n",
                 {"ta": P1, "H_ERRP": 0xFEFD})
    arm("A4 page 1 may call H_ERRP ($FEFD)", names(r) == set())
    r = scenario(0, " jp ta\n", "ta:\n call H_ERRP\n ret\n",
                 {"ta": P0, "H_ERRP": 0xFEFD})
    arm("A5 NEG: page 0 may NOT (its CALLF `rst $30` lands in the sub ROM)",
        "H_ERRP" in names(r))

    # --- (b) p0cb / p1cb IX targets, continuations, arguments ---------------
    cb = "p1cb:\n jp CLPRIM\n"
    cbs = {"p1cb": P1 + 0x100, "CLPRIM": 0xF38C}
    r = scenario(1, " jp ta\n", "ta:\n ld ix,p0_hifn\n call p1cb\n ret\n" + cb,
                 {"ta": P1, **cbs})
    arm("B1 `ld ix,p0_X / call p1cb` is an IX target, allowed", names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n ld ix,p0_hifn\n jr tb\ntb:\n push ix\n"
                 " ld ix,p0_lowfn\n call p1cb\n pop ix\n jp p1cb\n" + cb,
                 {"ta": P1, "tb": P1 + 1, **cbs})
    arm("B2 ...through a `jr` and a nested push/pop ix (focas_buf's shape)",
        names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n ld ix,p0_hifn\n ret\n", {"ta": P1})
    arm("B3 NEG: `ld ix,p0_X` that no call-back consumes is RED",
        "p0_hifn" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n ld ix,p0_hifn\n ld ix,p0_lowfn\n"
                 " call p1cb\n ret\n" + cb, {"ta": P1, **cbs})
    arm("B4 NEG: an IX overwritten before the call-back is RED",
        "p0_hifn" in names(r) and "p0_lowfn" not in names(r))
    r = scenario(1, " jp ta\n", "ta:\n ld hl,p0_hidata\n ld a,(hl)\n ret\n",
                 {"ta": P1})
    arm("B5 NEG: a tenant READING a p0_ address itself is RED",
        "p0_hidata" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n ld de,p0_hifn\n ret\n", {"ta": P1})
    arm("B6 `ld de,p0_X / ret` is a continuation, allowed", names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n ld de,p0_hifn\n nop\n ret\n", {"ta": P1})
    arm("B7 NEG: `ld de,p0_X / nop / ret` is not that shape, RED",
        "p0_hifn" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n ld de,p0_hidata\n ld ix,p0_hifn\n"
                 " call p1cb\n ret\n" + cb, {"ta": P1, **cbs})
    arm("B8 `ld de,p0_D / ld ix,p0_F / call p1cb` (main reads D), allowed",
        names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n ld de,code_seed\n ret\n", {"ta": P1})
    arm("B9 NEG: a CODE-SEED ABI name in a continuation shape is still RED "
        "(only the p0cb section qualifies)", "code_seed" in names(r))

    # --- (c) page 0: direct main page-1 calls need the build's assert -------
    ok_assert = "    IF p0_hifn < $4000\n db HIFN_LEFT_PAGE_1\n    ENDIF\n"
    r = scenario(0, " jp ta\n", "ta:\n call p0_hifn\n ret\n",
                 {"ta": P0, "p0_hifn": 0x5000}, asserts=ok_assert)
    arm("C1 page 0: a direct call the build asserts >= $4000 is allowed",
        names(r) == set())
    r = scenario(0, " jp ta\n", "ta:\n call p0_hifn\n ret\n",
                 {"ta": P0, "p0_hifn": 0x5000})
    arm("C2 NEG: the same call WITHOUT the assert is RED", "p0_hifn" in names(r))
    r = scenario(0, " jp ta\n", "ta:\n call p0_hifn\n ret\n",
                 {"ta": P0, "p0_hifn": 0x5000},
                 asserts="    IF p0_hifn < $4000\n nop\n    ENDIF\n")
    arm("C3 NEG: an IF whose body is not a `db` error is not an assert, RED",
        "p0_hifn" in names(r))
    r = scenario(0, " jp ta\n", "ta:\n call p0_hirst\n ret\n",
                 {"ta": P0, "p0_hirst": 0x5100},
                 asserts="    IF p0_hirst < $4000\n db X\n    ENDIF\n")
    arm("C4 NEG: asserted, but main's body does `rst $10` (lever A), RED",
        "p0_hirst" in names(r))
    r = scenario(0, " jp ta\n", "ta:\n call p0_hicalls_low\n ret\n",
                 {"ta": P0, "p0_hicalls_low": 0x5200},
                 asserts="    IF p0_hicalls_low < $4000\n db X\n    ENDIF\n")
    arm("C5 NEG: asserted, but main's body calls the low region, RED",
        "p0_hicalls_low" in names(r))
    r = scenario(0, " jp ta\n", "ta:\n call p0_lowfn\n ret\n",
                 {"ta": P0, "p0_lowfn": 0x2800})
    arm("C6 NEG: page 0 calling the main LOW region directly (no p0cb) is RED",
        "p0_lowfn" in names(r))

    # --- (d) page 1: BIOS / low-region calls ---------------------------------
    r = scenario(1, " jp ta\n", "ta:\n call CHPUT\n ret\n",
                 {"ta": P1, "CHPUT": 0x00A2})
    arm("D1 page 1: a direct BIOS call is allowed (page 0 is main/BIOS)",
        names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n call p0_lowfn\n ret\n",
                 {"ta": P1, "p0_lowfn": 0x2800})
    arm("D2 page 1: a direct low-region p0_ call whose main body stays low",
        names(r) == set())
    r = scenario(1, " jp ta\n", "ta:\n call p0_lowfn_calls_hi\n ret\n",
                 {"ta": P1, "p0_lowfn_calls_hi": 0x2900})
    arm("D3 NEG: ...but one whose main body calls main page 1 is RED",
        "p0_lowfn_calls_hi" in names(r))
    r = scenario(1, " jp ta\n", "ta:\n call p0_hifn\n ret\n",
                 {"ta": P1, "p0_hifn": 0x5000})
    arm("D4 NEG: page 1 calling main page 1 directly is RED", "p0_hifn" in names(r))

    # --- the live tree: the scrape reaches each table's end -----------------
    if os.path.exists("sub/sub.asm") and os.path.exists("build/sub.sym"):
        ls = load_syms("build/sub.sym")
        for tab in ("sub_p0_table", "sub_p1_table"):
            rows, end = table_rows("sub/sub.asm", tab)
            ret = sum(1 for _, t, _ in rows if t is None)
            arm(f"L2 live {tab}: {len(rows)} rows ({ret} retired) to {end}, "
                f"and the assembled size agrees",
                ret >= 1 and check_table_extent(ls, tab, end, rows) is None)


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--selftest":
        return selftest()
    if args and args[0] == "--page0":
        if len(args) != 3:
            sys.exit(__doc__)
        return check_page0(args[1:])
    if args and args[0] == "--disk":
        return check_page1(args[1:], seeds=disk_code_seeds())
    if args and args[0] == "--page1":
        if len(args) != 3:
            sys.exit(__doc__)
        return check_page1_tenant(args[1:])
    if len(args) != 2:
        sys.exit(__doc__)
    return check_page1(args)


if __name__ == "__main__":
    raise SystemExit(main())
