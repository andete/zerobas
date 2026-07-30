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

⚠️ THE FOUR APPARATUS FIXES BELOW ARE THE TOOL'S ACTUAL CONTENT. The fixed-point
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

SEEDS -- the choice matters more than the algorithm.

  main: `init` (the cartridge header's entry point) plus every label named anywhere
  in sub/ or tools/. ⚠️ NOT tests/ or probes/: a test naming a routine is not a
  reason to keep ROM bytes, and seeding on them hides the whole vars.asm block
  because the ported tests still name it. That one choice is the difference between
  16 dead spans and 4.

  sub: the page-0 and page-1 ENTRY-TABLE tenants, plus all prologues. This seed set
  is closed and provably complete -- the main ROM can reach sub code only through
  SUBROM_ENTRY_BASE_P0/_P1 + 3*index, so the two tables ARE the whole external
  surface.

Every seed is asserted to resolve to a real label, so a rename fails loudly instead
of silently shrinking the seed set.
"""
from __future__ import annotations
import collections
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "ctc", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "check_tenant_closure.py"))
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)

ALLOWFILE = os.path.join("tools", "deadcode-allow.txt")
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


def external_names(roots):
    """Every identifier appearing anywhere under `roots`. Deliberately coarse:
    over-seeding keeps a live routine alive, which is the safe direction."""
    out = set()
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if not fn.endswith(('.asm', '.inc', '.py')):
                    continue
                try:
                    txt = open(os.path.join(dirpath, fn), errors='ignore').read()
                except OSError:
                    continue
                out.update(m.group(0) for m in IDENT.finditer(txt))
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
    m_seeds = {'init'} | (set(m.nodes) & external_names(['sub', 'tools']))
    m_seeds |= {n for n in m.nodes if n.startswith(PROLOGUE)}
    if 'init' not in m.nodes:
        sys.exit("FAIL: seed `init` is not a label in the main build -- renamed?")
    builds['main'] = (m, m_seeds, main_sym)

    s = Spans('sub/sub.asm', 'sub')
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
