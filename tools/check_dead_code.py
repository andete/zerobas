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

⚠️ THE SEVEN APPARATUS FIXES BELOW ARE THE TOOL'S ACTUAL CONTENT. The fixed-point
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

  (7) AN EMPTY PROLOGUE CANNOT FALL THROUGH, SO EVERY FILE'S FIRST LABEL WAS
      UNCONDITIONALLY LIVE. Fix (2) gives each file an always-live prologue span
      so references made above its first label stay visible. That span also
      carried a FALLTHROUGH edge into the first label -- and 42 of 49 main
      prologues (53 of 66 sub) are comments only, emitting no bytes. A comment
      block cannot fall into anything, so 42 main first labels were live by
      CONSTRUCTION: no seed set could ever report them. D-SEEDHOLE2's read_sector
      hid there, through that very slice's seed rebuild.
      🔴 THE OBVIOUS GENERALISATION IS CATASTROPHIC AND WAS MEASURED, NOT
      ARGUED. "Empty span cannot fall through" is FALSE: a bare label directly
      above another label is an ALTERNATE ENTRY POINT and its fallthrough IS the
      routine. Cutting those too reports 1227 spans / 27727 B dead -- in a
      22510 B ROM, which is what says the measurement is wrong rather than the
      tree. Only PROLOGUE spans are skipped.
      ⚠️ A prologue that genuinely emits still falls through, untouched:
      basic/sprtrap-body.inc opens with `jr z,sp_done` above its first label.

  (12) A CALLEE WHOSE ONLY CALLER IS IN ANOTHER ROM. The disk ROM calls back
      into main BASIC across slots, so a main routine can be live with zero
      main-side callers. Until 2026-09-15 nothing modelled that: the first such
      routine was held up only by the `tools/` intersection arm, which is what
      the standing control below caught. The arm is NOT the model -- the model is
      disk_abi_seeds(), which reads the GENERATED disk import and checks it
      against tools/gen_resident_abi.py's declared profile, so the generator, the
      file and the label set must all agree or the gate fails. ⚠️ The three
      symbols already in that import were masked from this because they have
      main-side callers too; a callee that exists PURELY for the disk ROM does
      not, and that is the case this fix exists for
      (disk/docs/spec-diskbasic-hook-rearchitecture.md §4 phase 0a).

SEEDS -- the choice matters more than the algorithm.

  main: `init` (the cartridge header's entry point), the resident-ABI import
  (fix 6), and every label named in the CODE COLUMN of tools/ -- a tool naming a
  symbol it looks up in the .sym file IS an external reference to it, and prose
  does not seed (fix 5). ⚠️ NOT sub/ (fix 6), and NOT tests/
  or probes/: a test naming a routine is not a
  reason to keep ROM bytes, and seeding on them hides the whole vars.asm block
  because the ported tests still name it. That one choice is the difference between
  16 dead spans and 4.

  ⚠️ AND the DISK ROM's resident-ABI import (fix 12). `disk.rom` is a
  page-1 ROM in another slot; a main routine that exists ONLY to be called back
  into from there has no main-side caller at all and reads as DEAD. Seeded from
  the same GENERATED import the assembler consumes, with the name list taken
  from tools/gen_resident_abi.py's own profile -- so a rename fails LOUDLY in
  three places instead of dropping out of an intersection.

  sub: the page-0 and page-1 ENTRY-TABLE tenants, plus all prologues. This seed set
  is closed and provably complete -- the main ROM can reach sub code only through
  SUBROM_ENTRY_BASE_P0/_P1 + 3*index, so the two tables ARE the whole external
  surface.

`init`, the sub entry-table tenants and BOTH resident-ABI imports are each
asserted to resolve to a real label, so a rename fails loudly instead of silently shrinking
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
DISK_ABI = os.path.join("disk", "basic-resident-abi.inc")
DISK_ABI_FLOOR = 2       # REQUIRED_DISK_CODE is 3; a floor an edit cannot cross
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

    # (8) AN `include` IS NOT AN INSTRUCTION, AND NEITHER IS ANY DIRECTIVE.
    # This walk returned the last SOURCE line, so a span ending on `include "f"`
    # was handed that directive and asked whether it terminates. `_is_terminator`
    # correctly says no -- it is not an instruction at all -- and the result was a
    # FALLTHROUGH EDGE THAT DOES NOT EXIST, which makes the next label reachable
    # and HIDES dead code. A gate going quiet, not one crying wolf.
    # 🔴 IT WAS HIDING 16 B (D-ENDIFWALK, docs/spec-endifwalk.md): `skip_to_eol`/
    # `ste_done` (11 B) behind `include "basic/tokskip-body.inc"`, whose real last
    # instruction is the unconditional `jr tsk_data`, and `fat_delete` (5 B).
    # ⚠️ ONLY `include` IS RESOLVED HERE, and that is a scope decision, not an
    # oversight. Over both builds 68 span pairs end on a directive -- endif 32,
    # if 22, include 13, else 1 -- but deciding an `IF/ELSE/ENDIF` needs every ARM
    # to terminate, and 20 of those conditionals OPEN IN A PREVIOUS SPAN where a
    # per-span walk cannot see them. Resolving includes is unambiguous; the rest
    # needs file-level context and stays open in TODO.md.
    _INC = re.compile(r'^include\s+"([^"]+)"', re.I)

    @staticmethod
    def _last_code(lines, _depth=0):
        for c in reversed(lines):
            t = c.strip()
            if not t or re.match(r'^\w+:$', t):
                continue
            m = Spans._INC.match(t)
            if m and _depth < 6:
                for cand in (m.group(1), os.path.join('basic', m.group(1)),
                             os.path.join('sub', m.group(1))):
                    if os.path.exists(cand):
                        inner = [ln.split(';', 1)[0] for ln in open(cand)]
                        got = Spans._last_code(inner, _depth + 1)
                        if got:
                            return got
                return t                  # unresolvable -> unchanged, edge kept
            return t
        return ""

    # (9) A PADDING SPAN EMITS NO INSTRUCTIONS, SO IT CANNOT BE UNREACHABLE CODE.
    # The region markers (`__MEAS_SUB_P1_END:` then `ds $8000 - $, $FF`) exist to
    # be READ FROM THE SYM FILE by check_sub_walls.py; nothing jumps to them, by
    # design. They were only ever kept out of the dead set by an incoming
    # fallthrough edge, so fix (8) above made them reportable -- as findings that
    # are true and useless. Deliberately NARROW: the span's only code line must be
    # a `ds`. A `db` table is data a reference can genuinely go missing from and
    # stays reportable.
    _DATA = re.compile(r'^(db|dw|ds|defb|defw|defs|equ|org|if|ifdef|ifndef|else|'
                       r'endif|macro|endm|end)\b', re.I)
    _LBLEQU = re.compile(r'^[A-Za-z_]\w*\s+equ\b', re.I)

    @staticmethod
    def _data_only(lines):
        """Only data/directives, no executable instruction. EMPTY is NOT data-only."""
        seen = False
        for c in lines:
            t = c.strip()
            if not t or re.match(r'^[A-Za-z_]\w*:$', t):
                continue
            t2 = re.sub(r'^[A-Za-z_]\w*:\s*', '', t)
            if not t2:
                continue
            seen = True
            if not (Spans._DATA.match(t2) or Spans._LBLEQU.match(t2)
                    or Spans._DATA.match(t)):
                return False
        return seen

    @staticmethod
    def _names(lines, label):
        pat = re.compile(r'\b%s\b' % re.escape(label))
        return any(pat.search(l) for l in lines)

    @staticmethod
    def _padding_only(lines):
        code = [c.strip() for c in lines
                if c.strip() and not re.match(r'^\w+:$', c.strip())]
        return bool(code) and all(re.match(r'^ds\b', c, re.I) for c in code)

    def _edges(self):
        edges = collections.defaultdict(set)
        # fallthrough, within a file, gated on (1) the condition-aware terminator
        for order in self.seq.values():
            for a, b in zip(order, order[1:]):
                last = self._last_code(self.nodes.get(a, []))
                # (7) A PROLOGUE THAT EMITS NOTHING CANNOT FALL THROUGH. Fix (2)
                # makes every prologue span always-live so references made above
                # a file's first label stay visible -- but the SAME span also
                # carried a fallthrough edge into that first label, and 42 of 49
                # main prologues (53 of 66 sub) are comments only. A comment
                # block emits no bytes and cannot fall into anything, so those
                # first labels were live NO MATTER WHAT, unreportable by
                # construction. ⚠️ Only a PROLOGUE is skipped, never any other
                # empty span: a bare label with no body directly above another
                # label is an ALTERNATE ENTRY POINT, and its "fallthrough" IS the
                # routine -- cutting those too reported 1227 spans / 27727 B dead
                # in a 22510 B ROM while measuring this.
                if a.startswith(PROLOGUE) and not last:
                    continue
                # (11) A SPAN THAT EMITS ONLY DATA CANNOT FALL THROUGH. Nothing
                # runs off the end of a string table; `err_io: db "load",…` was
                # conferring liveness on `do_cload` purely by source adjacency
                # (D-PROLOGUE §12.5). Measured: main 26 edges cut -> 0 findings,
                # sub 37 -> 3, all three of them the address-arithmetic class
                # (fix 10 seeds two; the third pair was genuinely dead and is gone).
                # 🔴 AN EMPTY SPAN IS NOT DATA-ONLY, and that distinction is §12.1:
                # cutting those too reported 1195 spans / 28820 B dead in a 22510 B
                # ROM. An empty span is an ALTERNATE ENTRY POINT and its
                # "fallthrough" IS the routine.
                # 🔴 AND A TARGET THE SPAN NAMES KEEPS ITS EDGE. A fallthrough edge
                # and a REFERENCE edge to the same label are one entry in this dict,
                # so discarding one discards both: `stmt_table` holds `dw ex_sep`
                # AND is followed by `ex_sep`, which is how main's only "finding"
                # (4 B) was an artifact of the rule rather than dead code.
                # `em_ill_direct`/`em_table` is the same shape.
                if (self._data_only(self.nodes.get(a, []))
                        and not self._names(self.nodes.get(a, []), b)):
                    continue
                if not ctc._is_terminator(last):
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


def disk_abi_seeds(spans):
    """The main labels `disk.rom` may legitimately call back into -- fix (12).

    THIS IS THE PER-TOOL LOOKUP MODEL the tools/ arm could not substitute for.
    Three things must agree and any disagreement is fatal:

      1. tools/gen_resident_abi.py's DECLARED profile for this file (the CODE
         half -- the RAM half is work-area cells, not labels, and is checked to
         be exactly that);
      2. the GENERATED disk/basic-resident-abi.inc the assembler consumes;
      3. the main build's label set.

    A rename that reaches only one of the three fails here. That is the whole
    point: the tools/ arm seeded these names by INTERSECTION, so a rename made
    them silently stop being seeds instead of making anything go red.
    """
    sys.path.insert(0, "tools")
    try:
        import gen_resident_abi as gra
    except ImportError as e:                                # pragma: no cover
        sys.exit(f"FAIL: cannot import tools/gen_resident_abi.py ({e}) -- it "
                 f"DECLARES the disk ROM's call-back surface and this seed arm "
                 f"is only as loud as that declaration")
    prof = gra.PROFILES.get(DISK_ABI)
    if prof is None:
        sys.exit(f"FAIL: tools/gen_resident_abi.py has no profile for "
                 f"{DISK_ABI} -- the disk ROM's call-back surface is undeclared, "
                 f"so a main routine callable only from disk.rom would read DEAD")
    # 🔴 THE SAME ALIAS SPLIT THE GENERATOR DOES, AND FOR THE SAME REASON. An
    # import written "local=symbol" is EMITTED under `local` (disk.rom has its
    # own fat_mount/fat_find, so main's are imported as main_fat_*), but it is
    # the SYMBOL half that must resolve to a main label. Comparing the two
    # halves against the wrong side is what this arm caught on itself the first
    # time an alias existed: drift on four names that were really two.
    def _sym(entry):
        return entry.rpartition("=")[2]

    def _local(entry):
        head, _, tail = entry.rpartition("=")
        return head or tail

    code, ram = {_sym(n) for n in prof.code}, {_sym(n) for n in prof.ram}
    callback = {_sym(n) for n in prof.callback}
    # what the GENERATED file is expected to spell, which is the local half
    spelled = {_local(n) for n in prof.code + prof.ram + prof.callback}
    if len(code) < DISK_ABI_FLOOR:
        sys.exit(f"FAIL: the disk ABI declares {len(code)} code import(s), floor "
                 f"is {DISK_ABI_FLOOR} -- an emptied list would stop seeding the "
                 f"cross-ROM callees and report live code as dead")
    if not os.path.exists(DISK_ABI):
        sys.exit(f"FAIL: {DISK_ABI} is missing -- it is GENERATED into the build "
                 f"and is what disk.rom actually calls")
    infile = {m.group(1) for m in
              (ABI_EQU.match(ln.split(';', 1)[0]) for ln in open(DISK_ABI))
              if m}
    drift = sorted(spelled ^ infile)
    if drift:
        sys.exit(f"FAIL: {DISK_ABI} and tools/gen_resident_abi.py's profile "
                 f"disagree on {drift} -- the generated file is STALE (rebuild) "
                 f"or the profile changed without it. This seed arm reads the "
                 f"declaration, so a drift here is a hole in the seed set")
    missing = sorted(n for n in (code | callback) if n not in spans.nodes)
    if missing:
        sys.exit(f"FAIL: disk-ABI code import(s) {missing} do not resolve to a "
                 f"main label -- renamed? A cross-ROM callee that stops matching "
                 f"drops out of the seed set and its span reads as dead")
    mislabelled = sorted(n for n in ram if n in spans.nodes)
    if mislabelled:
        sys.exit(f"FAIL: disk-ABI RAM import(s) {mislabelled} ARE main labels -- "
                 f"the profile files them as work-area cells (ceiling-exempt, not "
                 f"seeds). One of the two classifications is wrong")
    return code | callback, len(callback)


def _assert_disk_resolves_locally(m, abi):
    """THE STANDING CONTROL on fix (12), symmetric to the sub one below.

    A main label named in disk/ CODE that is not in the disk ABI must resolve
    DISK-LOCALLY, or disk.rom reaches main by a route this sweep does not model.
    The assembler enforces it -- and "the assembler owns it" is exactly the
    reasoning that rots when nobody re-runs it.
    """
    d = Spans('disk/disk.asm', 'disk')
    local = set(d.nodes)
    for f in d.files:
        for ln in open(f, errors='ignore'):
            e = ABI_EQU.match(ln.split(';', 1)[0])
            if e:
                local.add(e.group(1))
    named = set(m.nodes) & external_names(['disk'])
    escapes = sorted(n for n in named if n not in abi and n not in local)
    if escapes:
        sys.exit(f"FAIL: {escapes} name main label(s) in disk/ CODE and resolve "
                 f"to neither the disk ABI ({DISK_ABI}) nor a disk-local "
                 f"definition. Either disk.rom reaches main by a route this sweep "
                 f"does not model -- add it to tools/gen_resident_abi.py's "
                 f"REQUIRED_DISK_CODE and regenerate -- or the name is a leftover")
    return len(named)


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
    # fix (12): the disk ROM's call-back surface. UNLIKE the tools/ arm this is a
    # declaration checked three ways, so it may carry weight -- that is what it is
    # for. It goes into BOTH seed sets below, which is what lets the tools/ arm's
    # standing control keep measuring only the tools/ arm.
    dabi, _n_callback = disk_abi_seeds(m)
    _n_disk = _assert_disk_resolves_locally(m, dabi)
    # 🔴 THE `tools/` ARM IS AN INTERSECTION, NOT AN ASSERTION (D-SEEDHOLE2
    # §11.5, filed 2026-08-22). `init`, the sub entry-table tenants and the
    # resident-ABI import all fail LOUDLY if they stop resolving; this arm is
    # `set(m.nodes) & external_names(['tools'])`, so a main routine renamed out
    # from under a `tools/` by-name `.sym` lookup silently drops out of the seed
    # set. Nothing could see that happen.
    #
    # 🎯 THE STANDING CONTROL BELOW IS WHAT MAKES THE SILENCE OBSERVABLE, and it
    # works because of a MEASURED fact: as of 2026-09-05 this arm contributes 37
    # seeds, 23 of them seeded no other way, and **removing it entirely changes
    # no finding** -- dead-with = dead-without = 0. Every name it seeds is
    # already reachable from `init` + the resident ABI + the prologue seeds, so
    # the arm is REDUNDANT and both of its failure directions (a missed finding
    # from over-seeding, a dropped seed from a rename) are empty today.
    #
    # So the assertion is not "every tools/ name resolves" -- that is the
    # per-tool lookup model this cannot substitute for -- it is "this arm still
    # carries no weight". The moment it does, its silence starts to matter, and
    # THAT is the moment to build the real model for the specific names named
    # below. Until then the arm is belt-and-braces and its hole cannot bite.
    tools_arm = set(m.nodes) & external_names(['tools'])
    m_seeds = {'init'} | abi | dabi | tools_arm
    m_seeds |= {n for n in m.nodes if n.startswith(PROLOGUE)}
    _without = ({'init'} | abi | dabi
                | {n for n in m.nodes if n.startswith(PROLOGUE)})
    _d_with, _ = m.dead(m_seeds)
    _d_without, _ = m.dead(_without)
    _carried = sorted(set(_d_without) - set(_d_with))
    if _carried:
        sys.exit(
            "FAIL: the `tools/` seed arm has started CARRYING WEIGHT -- "
            f"{len(_carried)} routine(s) are live ONLY because a tools/ file "
            f"mentions them by name: {_carried[:12]}"
            + (" ..." if len(_carried) > 12 else "")
            + "\n  That arm is an INTERSECTION, so a rename drops it SILENTLY "
              "(D-SEEDHOLE2 §11.5) -- and it was measured contributing NOTHING "
              "on 2026-09-05, which is what made it safe to leave coarse.\n"
              "  Give these names a per-tool lookup model that fails loudly, or "
              "seed them from something that does -- disk_abi_seeds() above is "
              "the worked example (fix 12).")
    print(f"  main: disk import surface {len(dabi)} seed(s) "
          f"({_n_callback} of them page-1 call-backs), {_n_disk} main label(s) "
          f"named in disk/ code, 0 escapes")
    builds['main'] = (m, m_seeds, main_sym)

    tenants = ctc.page0_seeds('sub/sub.asm') + ctc.page1_seeds('sub/sub.asm')
    missing = [t for t in tenants if t not in s.nodes]
    if missing:
        sys.exit(f"FAIL: sub entry-table seeds do not resolve to labels: {missing}")
    if len(tenants) < 20:
        sys.exit(f"FAIL: only {len(tenants)} sub tenants parsed from the entry "
                 f"tables -- the table scrape broke, seeds would be vacuous")
    # (10) THE ENTRY TABLES THEMSELVES ARE REACHED BY ADDRESS ARITHMETIC.
    # `page0_seeds`/`page1_seeds` parse these tables to seed their TENANTS, but the
    # tables are dispatched into by the main ROM as
    # `SUBROM_ENTRY_BASE_P1 + 3*index` -- arithmetic no name-following model can
    # see. Fix (11) below made `sub_p1_table` (72 B) reportable, and it is
    # unmistakably live. Seeded rather than allowlisted: an allowlist entry claims
    # "dead and kept on purpose", which would be false.
    s_seeds = (set(tenants) | {n for n in s.nodes if n.startswith(PROLOGUE)}
               | {n for n in ('sub_p0_table', 'sub_p1_table') if n in s.nodes})
    builds['sub'] = (s, s_seeds, sub_sym)

    allow = load_allow()
    findings, canary_alive = [], []
    for name, (spans, seeds, syms) in builds.items():
        if blind:
            seeds = set(spans.nodes)
        dead, live = spans.dead(seeds)
        pad = [d for d in dead if Spans._padding_only(spans.nodes.get(d, []))]
        if pad:
            # never silent: a skipped finding that nobody can see is the shape
            # this whole gate exists to remove.
            print(f"  {name:4s}: {len(pad)} padding-only span(s) not reportable "
                  f"(fix 9): {', '.join(sorted(pad))}")
            dead = [d for d in dead if d not in set(pad)]
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
