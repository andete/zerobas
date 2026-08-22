#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""Standing gate: TRANSITIVE dead-code sweep, BOTH builds.

docs/spec-deadcode-gate.md. Built by the ROM REGION STRUCTURE REVIEW
(docs/rom-region-structure-review.md), which used a throwaway version of this to
find 122 B where pasmo's warnings showed 80.

WHY A TOOL. pasmo's `Var x is never used` is PER-SYMBOL, so it cannot see a
routine that IS referenced but only from code that is itself dead -- which is how
`var_find` (reached only from the callerless `var_get_key`/`var_set_key`) and
`div_zero` (reached only from the callerless `div_de_bc`/`mod_de_bc`) hid. And the
part pasmo COULD see had been printing on every build for months inside ~230 lines
of warning noise nobody read. That is the failure this gate exists to prevent.

THE MODEL. Every label owns a LINEAR SPAN: its line through the line before the
next label in the same file. A span is LIVE if it is a seed, is mentioned by a live
span, or is entered by FALLTHROUGH from a live span whose last code line is not an
unconditional terminator. Iterate to a fixed point; whatever is still dead is
unreachable ROM.

    python3 tools/check_dead_code.py build/basic-reloc.sym build/sub.sym
    python3 tools/check_dead_code.py --report build/basic-reloc.sym build/sub.sym

⚠️ THE SIX APPARATUS FIXES BELOW ARE THE TOOL'S ACTUAL CONTENT. The fixed-point
loop is the easy part. Each fix corresponds to a confident WRONG row this sweep
produced during the review, three of which were caught only by a control and one
only by the assembler:

  (1) TERMINATOR TEST. Uses check_tenant_closure.py's `_is_terminator`, which
      honours the condition field. A naive `^(ret|jp|jr)` matches `jp nc,x` and
      `ret nz` and so falsely kills fallthrough-entered routines -- it reported
      `ei_set` and `spr_set` as dead when both are live.

  (2) PROLOGUE SPANS. Lines BEFORE a file's first label belong to no span, so
      references made there are invisible. `basic/sprtrap-body.inc` opens with a
      `jr z,sp_done` above its first label, and `sp_done` read as dead. Each file
      gets a synthetic always-live prologue span, and an `include` edge points at
      the included file's prologue.

  (3) DATA REFERENCES. The closure follows EVERY identifier a span mentions, not
      just call/jp/jr/djnz targets. `zkey_hook` -- the C-BIOS function-key hook,
      the one thing basic/keytrap.asm says cannot leave the low region -- is
      installed by `ld hl,zkey_hook`. A call-graph-only walk never reached it, and
      the review nearly nominated the $0038 keyboard hook for promotion into a page
      a sub-ROM tenant swaps out.

  (4) "DEAD" IS PER-BUILD. Each build is walked separately with its own include
      closure and its own seeds. `disk_putword` is defined in the SHARED
      basic/sv-diskwr.inc and called only from basic/sv-bsvdisk.inc, which ONLY
      sub/save.asm includes -- outside basic/main.asm's closure entirely. It is dead
      in main and live in sub; deleting it broke the build. The fix for that shape is
      `IF SUB_BUILD`, not deletion.

  (5) A COMMENT IS NOT A REFERENCE, SO IT MAY NOT BE A SEED. The main seed set is
      scraped out of sub/ and tools/, and until D-SEEDPROSE (2026-08-21) that scrape
      read whole FILES -- prose included. A main-build span was therefore invisible
      to this gate for as long as its label's name appeared in a comment over there,
      and the sweep reported a clean tree while structurally unable to see it.
      🔴 The prose that hid the first one was the comment D-FNEXPR2 wrote to explain
      that `parse_close_run`'s head had been removed from the SUB copy: documenting a
      removal is what stopped this gate asking for the same removal in the main build.
      The class measured 24 B the day it was found (`str_heap_alloc` 21 B + `sha_oom`
      2 B + `ex_mid_stmt` 1 B, all page-0 LOW, carved by that slice).
      `_code_column()` below is the fix: `;` tails go for .asm/.inc, `#` comments AND
      docstrings go for .py, and STRING LITERALS STAY -- a tool naming a symbol it
      looks up in the .sym file does so in a string, and that IS a reference.
      _selftest_code_column() runs on every invocation because a stripper that
      silently stops stripping restores the old blindness exactly.

  (6) A NAME IS NOT A ROUTE: sub/ CODE MAY NOT SEED THE MAIN BUILD. Fix (5) made
      the scrape read the code column; it did not make the scrape correct. Until
      D-SEEDHOLE2 (2026-08-22) a name referenced in sub/ CODE seeded the MAIN
      label of that name EVEN WHEN THE SUB REFERENCE RESOLVED SUB-LOCALLY -- and
      that is the normal case, not an odd one: sub/fatprim.asm's
      `call fat_read_fat_sector` reaches basic/fat-prim-body.inc's own copy, and
      sub/format.asm DEFINES its own write_sector.
      🔴 The shape that creates these is an EVICTION. Moving a caller into the
      sub-ROM leaves its main-side shim standing, and the moved body's own `call`
      is then read as the reason to keep it -- so the commit that orphans the
      span is the commit that hides it. d3885b3 and 0cbf495 did exactly that to
      five 4 B DISKOP_SEL_* bounces in basic/fat.asm, 20 B of main PAGE 1 (where
      the wall read 11 B), invisible to this gate for weeks.
      THE FIX IS NOT A NARROWER SCRAPE, IT IS THE REAL SURFACE:
      sub/basic-resident-abi.inc, GENERATED from build/basic-reloc.sym, is the
      ONLY file in the tree that imports a main address. Anything else a sub file
      names resolves sub-locally or the sub build does not assemble -- so that
      import list IS the sub->main surface, not a proxy for it.
      _assert_sub_resolves_locally() is the standing control on precisely that
      claim, because "the assembler enforces it" is the kind of reasoning that
      rots when nothing re-runs it. Measured the day it shipped: 60 main labels
      named in sub/ code, 60 resolvable, 0 escapes.
      ⚠️ Fix (5) still matters -- for tools/, which still seeds.

SEEDS -- the choice matters more than the algorithm.

  main: `init` (the cartridge header's entry point), the resident-ABI import
  (fix 6), and every label named in the CODE COLUMN of tools/ -- a tool naming a
  symbol it looks up in the .sym file IS an external reference to it, and prose
  does not seed (fix 5). ⚠️ NOT sub/ (fix 6), and NOT tests/
  or probes/: a test naming a routine is not a
  reason to keep ROM bytes, and seeding on them hides the whole vars.asm block
  because the ported tests still name it. That one choice is the difference between
  16 dead spans and 4.

  sub: the page-0 and page-1 ENTRY-TABLE tenants, plus all prologues. This seed set
  is closed and provably complete -- the main ROM can reach sub code only through
  SUBROM_ENTRY_BASE_P0/_P1 + 3*index, so the two tables ARE the whole external
  surface.

`init`, the sub entry-table tenants and the resident-ABI import are each asserted
to resolve to a real label, so a rename fails loudly instead of silently shrinking
the seed set. ⚠️ The tools/ arm is NOT -- it is an INTERSECTION with the label set,
so a main routine renamed out from under a tools/ lookup drops out of the seeds
quietly. That arm is over-seeding by construction, so the failure direction is a
missed finding rather than a false one; it is written down here rather than fixed
because the fix is a per-tool lookup model, not a stricter regex.
"""
from __future__ import annotations
import ast
import collections
import io
import os
import re
import sys
import tokenize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "ctc", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "check_tenant_closure.py"))
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)

ALLOWFILE = os.path.join("tools", "deadcode-allow.txt")
# fix (6): the GENERATED resident-ABI import is the main build's external surface.
RESIDENT_ABI = os.path.join("sub", "basic-resident-abi.inc")
ABI_EQU = re.compile(r'^\s*([A-Za-z_]\w*)\s+equ\b', re.IGNORECASE)
ABI_FLOOR = 8            # REQUIRED is 12; a floor an edit cannot quietly cross
IDENT = re.compile(r'[A-Za-z_]\w*')
INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"', re.IGNORECASE)
PROLOGUE = "@prologue:"
PAGE1 = 0x4000


def _resolve(arg, build):
    """Mirror each build's include search: the sub build assembles with `-I sub`,
    so a bare name resolves under sub/; an explicit path is repo-root relative."""
    if '/' in arg:
        return arg
    return os.path.join('sub', arg) if build == 'sub' else arg


class Spans:
    """The span model for one build."""

    def __init__(self, top, build):
        self.build = build
        self.nodes = {}          # name -> code lines
        self.owner = {}          # name -> defining file
        self.seq = {}            # file -> ordered span names (prologue first)
        self.first_label = {}    # file -> its first label
        files = [f for f in ctc.collect_sources(top) if os.path.exists(f)]
        if not files:
            sys.exit(f"FAIL: {top} pulled in no readable sources")
        self.files = files
        for f in files:
            code = [ln.split(';', 1)[0] for ln in open(f)]
            idx = [i for i, c in enumerate(code) if ctc._LBL.match(c)]
            # (2) prologue span -- lines before the first label belong to no
            # routine, but references made there are real.
            pro = PROLOGUE + f
            self.nodes[pro] = code[:idx[0]] if idx else code
            order = [pro]
            if idx:
                self.first_label[f] = ctc._LBL.match(code[idx[0]]).group(1)
            for k, i in enumerate(idx):
                end = idx[k + 1] if k + 1 < len(idx) else len(code)
                name = ctc._LBL.match(code[i]).group(1)
                if name not in self.nodes:       # first definition wins
                    self.nodes[name] = code[i:end]
                    self.owner[name] = f
                order.append(name)
            self.seq[f] = order
        self.edges = self._edges()

    @staticmethod
    def _last_code(lines):
        for c in reversed(lines):
            t = c.strip()
            if t and not re.match(r'^\w+:$', t):
                return t
        return ""

    def _edges(self):
        edges = collections.defaultdict(set)
        # fallthrough, within a file, gated on (1) the condition-aware terminator
        for order in self.seq.values():
            for a, b in zip(order, order[1:]):
                if not ctc._is_terminator(self._last_code(self.nodes.get(a, []))):
                    edges[a].add(b)
        for name, lines in self.nodes.items():
            for line in lines:
                m = INCLUDE.match(line)
                if m:
                    tgt = _resolve(m.group(1), self.build)
                    if PROLOGUE + tgt in self.nodes:
                        edges[name].add(PROLOGUE + tgt)
                    elif tgt in self.first_label:
                        edges[name].add(self.first_label[tgt])
                # (3) EVERY identifier, not just transfer targets -- catches
                # `ld hl,label`, `dw label`, `equ label`, table bodies.
                for t in IDENT.finditer(line):
                    if t.group(0) in self.nodes:
                        edges[name].add(t.group(0))
        return edges

    def dead(self, seeds):
        live, stack = set(), list(seeds)
        while stack:
            n = stack.pop()
            if n in live or n not in self.nodes:
                continue
            live.add(n)
            stack.extend(self.edges.get(n, ()))
        return [n for n in self.nodes
                if n not in live and not n.startswith(PROLOGUE)], live

    def size(self, name, syms):
        """Bytes from this span's label to the next label in the same file."""
        f = self.owner.get(name)
        if f is None or name not in syms:
            return None
        order = self.seq[f]
        i = order.index(name)
        if i + 1 >= len(order):
            return None
        nxt = syms.get(order[i + 1])
        a = syms[name]
        return nxt - a if (nxt is not None and nxt > a) else None


def _py_code_column(txt, path):
    """A .py file with `#` comments and DOCSTRINGS removed, everything else kept.

    Tokenised rather than regexed, because a `#` inside a string literal is not a
    comment and a `'label'` argument to a symbol lookup IS a reference. Docstrings
    go too: a triple-quoted module header is prose by any other name, and this
    tool's own docstring names a dozen labels in both builds.

    A .py under tools/ that does not parse fails LOUDLY. Falling back to the raw
    text would restore fix (5)'s blindness for that file and say nothing.
    """
    try:
        tree = ast.parse(txt)
    except SyntaxError as e:
        sys.exit(f"FAIL: {path} does not parse ({e}) -- the seed scrape cannot "
                 f"read its code column, and falling back to the raw text would "
                 f"silently restore the comment-seeding blindness of fix (5)")
    docs = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, 'body', None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docs.add((body[0].lineno, body[0].col_offset))
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(txt).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING and tok.start in docs:
                continue
            out.append(tok.string)
    except tokenize.TokenError as e:
        sys.exit(f"FAIL: {path} does not tokenise ({e}) -- see above")
    return "\n".join(out)


def _code_column(path, txt):
    """The CODE COLUMN of one source file -- prose out, string literals in.
    Fix (5). .asm/.inc use the same `;` split the span model itself uses."""
    if path.endswith('.py'):
        return _py_code_column(txt, path)
    return "\n".join(ln.split(';', 1)[0] for ln in txt.splitlines())


# Vectors for _selftest_code_column(). Each is (path, source, must_contain,
# must_not_contain). ⚠️ BOTH SENSES ARE MANDATORY and the table is FLOORED: a
# self-test table emptied to [] prints 0/0 and exits 0, which is how four tables
# in audit_citations.py were vacuous for the tool's whole life.
_CC_VECTORS = [
    ("x.asm", "                call    live_one    ; dead_one is gone\n",
     ["live_one"], ["dead_one"]),
    ("x.inc", "; dead_one: the head this slice removed\nlive_one:  ld a,1\n",
     ["live_one"], ["dead_one"]),
    ("x.asm", "                cp      ';'         ; dead_one\n",
     ["cp"], ["dead_one"]),
    ("x.py", "# dead_one is dead\nx = sym['live_one']\n",
     ["live_one"], ["dead_one"]),
    ("x.py", '"""Module prose naming dead_one."""\ny = "live_one"\n',
     ["live_one"], ["dead_one"]),
    ("x.py", 'def f():\n    """Doc naming dead_one."""\n    return "live_one"\n',
     ["live_one"], ["dead_one"]),
    ("x.py", 'z = "a # dead_one is not a comment here"\n',
     ["dead_one"], []),          # a `#` INSIDE a string is not a comment
]


def _selftest_code_column():
    """Calibrate the stripper against known positives AND known negatives before
    trusting a clean sweep. A stripper that stops stripping reads as `0 dead`."""
    if len(_CC_VECTORS) < 6:
        sys.exit(f"FAIL: _CC_VECTORS has {len(_CC_VECTORS)} rows -- the code-column "
                 f"self-test has been gutted; an empty table proves nothing")
    if not any(v[2] for v in _CC_VECTORS) or not any(v[3] for v in _CC_VECTORS):
        sys.exit("FAIL: _CC_VECTORS needs vectors of BOTH senses -- something the "
                 "stripper must KEEP and something it must REMOVE. A table of one "
                 "sense passes a stripper that strips everything, or nothing.")
    for path, src, keep, drop in _CC_VECTORS:
        names = {m.group(0) for m in IDENT.finditer(_code_column(path, src))}
        for k in keep:
            if k not in names:
                sys.exit(f"FAIL: code-column self-test: {path} {src!r} dropped "
                         f"{k!r}, which is a REFERENCE -- the seed set would shrink "
                         f"and live code would be reported dead")
        for d in drop:
            if d in names:
                sys.exit(f"FAIL: code-column self-test: {path} {src!r} kept {d!r}, "
                         f"which is PROSE -- fix (5) has regressed and this sweep "
                         f"is blind to every span a comment names")


def resident_abi_seeds(spans):
    """The main labels the SUB build may legitimately reach -- fix (6).

    sub/basic-resident-abi.inc is GENERATED (tools/gen_resident_abi.py) from
    build/basic-reloc.sym and is the ONLY file in the tree that imports a main
    address. Everything else a sub file names resolves SUB-LOCALLY or the sub
    build does not assemble, which is what makes this list the whole surface
    rather than a proxy for it -- see _assert_sub_resolves_locally() below, the
    standing control on exactly that claim.

    FLOORED, because an import list silently emptied would shrink the seed set
    to `init` and report live code as dead -- loud, but for the wrong reason --
    and an import list silently IGNORED would restore the over-seeding this fix
    removes. Every name is asserted to be a real main label: a renamed resident
    routine fails here rather than quietly dropping out of the seed set.
    """
    if not os.path.exists(RESIDENT_ABI):
        sys.exit(f"FAIL: {RESIDENT_ABI} is missing -- it is GENERATED into the "
                 f"build (tools/gen_resident_abi.py) and is the main build's "
                 f"external seed surface; without it this sweep cannot say what "
                 f"the sub-ROM may reach")
    names = []
    for ln in open(RESIDENT_ABI):
        m = ABI_EQU.match(ln.split(';', 1)[0])
        if m:
            names.append(m.group(1))
    if len(names) < ABI_FLOOR:
        sys.exit(f"FAIL: {RESIDENT_ABI} yielded {len(names)} import(s), floor is "
                 f"{ABI_FLOOR} -- the resident-ABI surface is the main build's "
                 f"whole external seed set and it cannot be this small. An empty "
                 f"one would seed only `init` and report live code as dead")
    missing = [n for n in names if n not in spans.nodes]
    if missing:
        sys.exit(f"FAIL: resident-ABI import(s) {missing} do not resolve to a "
                 f"main label -- renamed? A seed that silently stops matching "
                 f"shrinks this sweep's seed set instead of failing")
    return set(names)


def _assert_sub_resolves_locally(m, s, abi):
    """THE STANDING CONTROL on fix (6), and the reason dropping sub/ is safe.

    Fix (6) rests on one claim: a main label named in sub/ CODE that is not in
    the resident ABI resolves to something SUB-LOCAL, so it is not a reason to
    keep main bytes. The claim is enforced by the assembler (an unresolved
    symbol does not build) -- but "the assembler owns it" is exactly the kind of
    reasoning that rots when nobody re-runs it, and this sweep would go quiet
    rather than loud if it stopped holding. Measured 2026-08-22: 60 main labels
    named in sub/ code, 60 resolvable, 0 escapes.
    """
    named = set(m.nodes) & external_names(['sub'])
    local = set(s.nodes)
    for f in s.files:
        for ln in open(f, errors='ignore'):
            e = ABI_EQU.match(ln.split(';', 1)[0])
            if e:
                local.add(e.group(1))
    escapes = sorted(n for n in named if n not in abi and n not in local)
    if escapes:
        sys.exit(f"FAIL: {escapes} name main label(s) in sub/ CODE and resolve "
                 f"to neither the resident ABI ({RESIDENT_ABI}) nor a sub-local "
                 f"definition. Either the sub build reaches main by a route this "
                 f"sweep does not model -- add it to the ABI import and to "
                 f"tools/gen_resident_abi.py's REQUIRED -- or the name is a "
                 f"leftover. Fix (6) assumes this list is EMPTY; it is the one "
                 f"assumption that lets sub/ stop seeding the main build")


def external_names(roots):
    """Every identifier appearing in the CODE COLUMN of the files under `roots`.

    ⚠️ THIS USED TO READ WHOLE FILES, and its own justification was "deliberately
    coarse: over-seeding keeps a live routine alive, which is the safe direction."
    That reasoning is sound for a genuine reference made in an odd place; it is
    FALSE for prose, because a comment cannot execute. Over-seeding on prose is not
    the safe direction, it is the SILENT one -- the gate reports a clean tree and
    cannot see the span at all. See fix (5) in this file's header.
    """
    _selftest_code_column()
    out = set()
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(('.asm', '.inc', '.py')):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    txt = open(path, errors='ignore').read()
                except OSError:
                    continue
                out.update(m.group(0)
                           for m in IDENT.finditer(_code_column(path, txt)))
    return out


def load_allow():
    """`<build> <label> <reason>` per line. A MISSING REASON IS A PARSE ERROR --
    an allowlist entry without a justification is how a gate rots."""
    allow = {}
    if not os.path.exists(ALLOWFILE):
        return allow
    for lineno, raw in enumerate(open(ALLOWFILE), 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[2].strip():
            sys.exit(f"FAIL: {ALLOWFILE}:{lineno}: need `<build> <label> <reason>`, "
                     f"got {raw.strip()!r} -- a reason is MANDATORY")
        build, label, reason = parts[0], parts[1], parts[2].strip()
        if build not in ('main', 'sub'):
            sys.exit(f"FAIL: {ALLOWFILE}:{lineno}: build must be main|sub, "
                     f"got {build!r}")
        allow[(build, label)] = reason
    return allow


def main(argv):
    report_only = '--report' in argv
    args = [a for a in argv if not a.startswith('--')]
    # --blind is an internal FALSIFICATION switch (spec §6.1 row B): it seeds the
    # closure with every label, which makes the sweep find nothing. The allowlist
    # canary below MUST then fail -- that is what proves this gate cannot go
    # quietly blind and report a clean sweep forever.
    blind = '--blind' in argv
    if len(args) != 3:
        sys.exit(__doc__.strip().splitlines()[0] +
                 "\nusage: check_dead_code.py [--report] "
                 "build/basic-reloc.sym build/sub.sym")
    main_sym, sub_sym = ctc.load_syms(args[1]), ctc.load_syms(args[2])

    builds = {}
    m = Spans('basic/main.asm', 'main')
    s = Spans('sub/sub.asm', 'sub')
    if 'init' not in m.nodes:
        sys.exit("FAIL: seed `init` is not a label in the main build -- renamed?")
    # fix (6): the main build's external surface is the GENERATED resident-ABI
    # import plus whatever tools/ looks up BY NAME -- not every identifier that
    # happens to appear under sub/. The sub build is walked first because the
    # standing control below needs it.
    abi = resident_abi_seeds(m)
    _assert_sub_resolves_locally(m, s, abi)
    m_seeds = {'init'} | abi | (set(m.nodes) & external_names(['tools']))
    m_seeds |= {n for n in m.nodes if n.startswith(PROLOGUE)}
    builds['main'] = (m, m_seeds, main_sym)

    tenants = ctc.page0_seeds('sub/sub.asm') + ctc.page1_seeds('sub/sub.asm')
    missing = [t for t in tenants if t not in s.nodes]
    if missing:
        sys.exit(f"FAIL: sub entry-table seeds do not resolve to labels: {missing}")
    if len(tenants) < 20:
        sys.exit(f"FAIL: only {len(tenants)} sub tenants parsed from the entry "
                 f"tables -- the table scrape broke, seeds would be vacuous")
    s_seeds = set(tenants) | {n for n in s.nodes if n.startswith(PROLOGUE)}
    builds['sub'] = (s, s_seeds, sub_sym)

    allow = load_allow()
    findings, canary_alive = [], []
    for name, (spans, seeds, syms) in builds.items():
        if blind:
            seeds = set(spans.nodes)
        dead, live = spans.dead(seeds)
        deadset = set(dead)
        for lbl in dead:
            reason = allow.get((name, lbl))
            sz = spans.size(lbl, syms)
            addr = syms.get(lbl)
            row = (name, lbl, spans.owner.get(lbl, '?'), addr, sz, reason)
            if reason is None:
                findings.append(row)
            elif report_only:
                print(f"  allowed  [{name}] {lbl:24s} "
                      f"{spans.owner.get(lbl,'?'):26s} "
                      f"{'' if addr is None else format(addr,'#06x')} "
                      f"{sz if sz else '?'} B  -- {reason}")
        # the allowlist doubles as the VACUITY CANARY: an entry that is no longer
        # detected means either it gained a caller (drop the entry) or the sweep
        # went blind (fix the sweep). Either way this must not pass silently.
        for (b, lbl), reason in allow.items():
            if b == name and lbl not in deadset:
                canary_alive.append((b, lbl, lbl in spans.nodes, reason))
        n_dead = len([d for d in dead if (name, d) not in allow])
        print(f"  {name:4s}: {len(spans.nodes)} spans, {len(seeds)} seeds -> "
              f"{n_dead} dead (+{len(dead)-n_dead} allowlisted)")

    ok = True
    # In --report mode nothing fails, so the findings must NOT be headed "FAIL":
    # a red-looking readout on a zero exit is exactly the misleading signal this
    # tool exists to remove. `make deadcode` says REPORT; the gate says FAIL.
    tag = "REPORT" if report_only else "FAIL"
    if canary_alive:
        ok = False
        print(f"\n{tag}: allowlisted span(s) are no longer detected as dead. Either "
              "they gained a caller (remove the entry) or THIS SWEEP HAS GONE "
              "BLIND (fix it) -- an allowlist that stops matching is the only "
              "warning you get that the gate is measuring nothing:")
        for b, lbl, exists, reason in canary_alive:
            print(f"  [{b}] {lbl}  (label {'exists' if exists else 'IS GONE'})"
                  f"  -- {reason}")
    if findings:
        ok = False
        print(f"\n{tag}: {len(findings)} unreachable span(s) -- delete them, or if a "
              f"SHARED body .inc makes one live in the OTHER build, gate it with "
              f"`IF SUB_BUILD` (see this file's header, fix 4):")
        tot = collections.Counter()
        for b, lbl, f, addr, sz, _ in sorted(findings,
                                             key=lambda r: (r[0], r[3] or 0)):
            reg = '?' if addr is None else ('LOW/P0' if addr < PAGE1 else 'PAGE1')
            if sz:
                tot[(b, reg)] += sz
            print(f"  [{b}] {lbl:24s} {f:28s} "
                  f"{'' if addr is None else format(addr,'#06x')} {reg:6s} "
                  f"~{sz if sz else '?'} B")
        for (b, reg), n in sorted(tot.items()):
            print(f"    {b} {reg}: {n} B")
    if ok:
        print("OK: no unreachable spans in either build; every allowlist entry "
              "still verified dead (the sweep is not blind).")
    if report_only:
        if not ok:
            print("  (advisory: `make deadcode` always exits 0. The same sweep runs "
                  "as a HARD gate in `make basic-reloc`, and there it fails.)")
        return 0
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
