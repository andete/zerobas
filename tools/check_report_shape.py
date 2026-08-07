#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""check_report_shape -- one report-row GRAMMAR on every exit path of a probe.

docs/spec-probe-rowshape.md. A knife runner parses a probe's report to decide
whether a cut reddened anything. Twice in one session (D-CASOPEN, 2026-08-07) a
runner was defeated by the report's SHAPE: an `^`-anchored row regex matched
every green run and no knifed one (the exit-2 rows are indented two spaces), and
a runner diffing report LINES scored every row as moved (the same reading prints
as `ok  label  'value'` when the sides agree and `....  label  a='..'  b='..'`
when nothing is scored).

⚠️ THIS GATE IS STATIC ON PURPOSE. The branch that carries the fault only ever
executes under a knife -- no green run and no acceptance gate has ever printed
the `....` shape -- so a behavioural gate would have to FAIL A CONTROL to see its
own subject. Four probes carried the fault for months underneath a fully green
corpus.

WHAT IS A REPORT ROW (spec §3). All three, or it is prose:

  1. a WIDTH-PADDED LABEL field -- `{lab:<22}`, `{key:14}`. A *string* pad;
     `{addr:04X}` pads a number and is prose.
  2. at least one value in the tail rendered with `repr()`. This is the
     load-bearing one: repr is what DELIMITS a value that may contain spaces or
     `=` or nothing at all, and without it no runner can parse the line whatever
     its layout. A probe whose rows fail this is out of contract and said so
     out loud (`basic_probe_kwsweep.py`, spec §2.4) -- never silently skipped.
  3. printed by `print()` with the label field in the first argument.

THE CONTRACT (spec §4). A probe is IN CONTRACT when it prints report rows on an
exit-2 path AND on another path -- that is the only shape in which a runner
meets two renderings of the SAME reading. Then:

  I1  every row's label starts at the SAME COLUMN. A constant-width tag is fine
      however it is written: `{'PASS' if ok else 'FAIL'}` is 4 either way.
      `{'ok ' if ok else 'DIFF'}` is 3-or-4 and is exactly the fault.
  I2  ONE value encoding: `side=repr` pairs on every row, or a bare repr on
      every row. Never both.
  I3  every block that prints rows and exits prints a `footer()` terminator, so
      a runner reads a COUNT instead of guessing a layout.

    python3 tools/check_report_shape.py           # gate
    python3 tools/check_report_shape.py --list    # every site + verdict
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PROBES = os.path.join(REPO, "probes")

sys.path.insert(0, os.path.join(PROBES, "lib"))
import probe_report                                              # noqa: E402

# Module-level `NAME = <int>` of the file being walked, so a label pad written as
# a named constant (`LABEL_W`) reads as a number in --list rather than as None.
_CONSTS: dict[str, int] = {}

# A LABEL column is a STRING pad: ':<22', ':22', ':^12', ':.<22s'. NOT '04X'.
WIDTH_SPEC = re.compile(r"^(.?[<>^])?(\d+)s?$")

# ⚠️ 0 probes in contract is not a clean tree, it is a broken classifier. The
# floor is not a count of files but of SUBJECTS: this gate exists to watch a
# five-probe class, and a walk that finds none has gone blind.
MIN_CONTRACT = 1
MIN_FILES = 100


# --------------------------------------------------------------- f-string bits
def spec_text(node: ast.FormattedValue) -> str | None:
    """A FormattedValue's literal format_spec, or None if absent/computed."""
    if node.format_spec is None:
        return None
    out = []
    for v in node.format_spec.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            out.append(v.value)
        else:
            return None
    return "".join(out)


def parts_of(node: ast.AST) -> list:
    """Flatten a print() argument that may be `f".." + expr + f".."`."""
    if isinstance(node, ast.JoinedStr):
        out = []
        for v in node.values:
            if isinstance(v, ast.Constant) and isinstance(v.value, str):
                out.append(("t", v.value))
            elif isinstance(v, ast.FormattedValue):
                out.append(("f", v))
        return out
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return parts_of(node.left) + parts_of(node.right)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [("t", node.value)]
    return [("x", node)]


def const_width(fv: ast.FormattedValue) -> int | None:
    """Rendered width of an unpadded field when it is provably CONSTANT.

    🔴 THIS IS THE FUNCTION THE WHOLE GATE TURNS ON. A tag written as an
    IfExp of two string literals is fine when both literals are the same
    length -- `{'PASS' if ok else 'FAIL'}` never moves the column -- and is the
    D-CASOPEN fault when they are not: `{'ok ' if ok else 'DIFF'}` is 3 on an
    agreeing row and 4 on a diverging one, so the label column moves between two
    rows of the SAME run, before any exit path is involved."""
    if spec_text(fv) is not None:
        return None                     # padded: handled by the caller
    v = fv.value
    if isinstance(v, ast.Constant) and isinstance(v.value, str):
        return len(v.value)
    if isinstance(v, ast.IfExp):
        a, b = v.body, v.orelse
        if (isinstance(a, ast.Constant) and isinstance(a.value, str)
                and isinstance(b, ast.Constant) and isinstance(b.value, str)
                and len(a.value) == len(b.value)):
            return len(a.value)
    return None                          # not provably constant -> variable


def has_repr(tail: list) -> bool:
    for k, v in tail:
        if k == "f" and v.conversion == ord("r"):
            return True
        src = ""
        if k == "f":
            src = ast.unparse(v.value)
        elif k == "x":
            src = ast.unparse(v)
        if "!r" in src or "repr(" in src:
            return True
    return False


def encoding(tail: list) -> str:
    """'pairs' if the tail renders `side=value`, else 'bare'."""
    for k, v in tail:
        if k == "t" and "=" in v:
            return "pairs"
        src = ""
        if k == "f":
            src = ast.unparse(v.value)
        elif k == "x":
            src = ast.unparse(v)
        if re.search(r"=\{|\}=|=.\{|f['\"][^'\"]*=", src) or \
                ("join" in src and "=" in src):
            return "pairs"
    return "bare"


class Site:
    __slots__ = ("lineno", "column", "enc", "padded")

    def __init__(self, lineno, column, enc, padded):
        self.lineno, self.column, self.enc, self.padded = lineno, column, enc, padded

    @property
    def col_str(self):
        return "VARIABLE" if self.column is None else str(self.column)


# `probe_report.row(tag, label, width, vals, note)` renders `{tag:<TAG_W} ` then
# the padded label, and always names every side -- so its column and encoding are
# fixed by the module, not by this call site.
SHARED_COL = probe_report.TAG_W + 1


def _shared_row_call(node: ast.AST) -> ast.Call | None:
    """A call to probe_report.row(...), however it was imported."""
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Attribute) and f.attr == "row" \
            and isinstance(f.value, ast.Name) and f.value.id == "probe_report":
        return node
    if isinstance(f, ast.Name) and f.id == "row":
        return node
    return None


def site_of(call: ast.Call) -> Site | None:
    """The report-row Site this print() is, or None."""
    if not (isinstance(call.func, ast.Name) and call.func.id == "print"
            and call.args):
        return None

    # 🔴 THE SHARED FORMATTER IS A ROW SITE, AND FORGETTING THAT MADE THIS GATE
    # BLIND TO ITS OWN SUBJECT. Measured while writing this slice: the first cut
    # of this checker only recognised inline f-strings, so the instant
    # `basic_probe_castail.py` was migrated to probe_report.row() the probe
    # DROPPED OUT OF THE CONTRACT -- contract 5 -> 4 -- and the gate would have
    # gone green by ceasing to look ([[readout-blind-to-its-own-subject]]). A
    # fully-migrated tree would have scored `0 in contract` and tripped the
    # APPARATUS floor; a half-migrated one scores a quiet, wrong PASS.
    shared = _shared_row_call(call.args[0])
    if shared is not None:
        w = None
        if len(shared.args) >= 3:
            a = shared.args[2]
            if isinstance(a, ast.Constant):
                w = a.value
            elif isinstance(a, ast.Name):
                w = _CONSTS.get(a.id)
        return Site(call.lineno, SHARED_COL, "pairs", w)

    parts = parts_of(call.args[0])
    for i, (k, v) in enumerate(parts):
        if k != "f":
            continue
        spec = spec_text(v)
        if spec is None or not WIDTH_SPEC.match(spec):
            continue
        head, tail = parts[:i], parts[i + 1:]
        if not has_repr(tail):
            return None                  # prose, not a machine-parseable row
        col, ok = 0, True
        for k2, v2 in head:
            if k2 == "t":
                if "\n" in v2:
                    return None          # a banner
                col += len(v2)
            elif k2 == "f":
                w = const_width(v2)
                if w is None:
                    ok = False
                else:
                    col += w
            else:
                ok = False
        return Site(call.lineno, col if ok else None, encoding(tail),
                    int(WIDTH_SPEC.match(spec).group(2)))
    return None


# ------------------------------------------------------------- block analysis
def rows_in(stmts: list) -> list[Site]:
    out = []
    for s in stmts:
        for n in ast.walk(s):
            if isinstance(n, ast.Call):
                st = site_of(n)
                if st:
                    out.append(st)
    return out


def exits(stmts: list):
    """The status this statement list terminates with, or None if it does not.

    🔴 ANY `return` COUNTS, NOT ONLY A CONSTANT ONE. The first cut of this
    checker matched `return 2` and `return 0` but not `return 0 if ok else 1` --
    so `disk_probe_fat_error_disposition.py`, whose main() ends exactly that way,
    was never asked for a terminator on its SUCCESS path. Restricting the rule to
    constant returns would have scoped I3 by how someone happened to spell a
    return statement, which is a distinction without a principle."""
    for s in stmts:
        if isinstance(s, ast.Return):
            if isinstance(s.value, ast.Constant) and isinstance(s.value.value, int):
                return s.value.value
            return "?"
        if isinstance(s, ast.Expr) and isinstance(s.value, ast.Call):
            f = s.value.func
            if isinstance(f, ast.Attribute) and f.attr == "exit" and s.value.args:
                a = s.value.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, int):
                    return a.value
    return None


def calls_footer(stmts: list) -> bool:
    for s in stmts:
        for n in ast.walk(s):
            if isinstance(n, ast.Call):
                f = n.func
                name = f.attr if isinstance(f, ast.Attribute) else (
                    f.id if isinstance(f, ast.Name) else "")
                if name == "footer":
                    return True
    return False


def blocks(tree: ast.AST):
    """Every statement LIST in the module."""
    for n in ast.walk(tree):
        for field in ("body", "orelse", "finalbody"):
            blk = getattr(n, field, None)
            if isinstance(blk, list) and blk:
                yield n, blk


class Probe:
    def __init__(self, rel, tree):
        global _CONSTS
        _CONSTS = {t.id: s.value.value
                   for s in tree.body if isinstance(s, ast.Assign)
                   and isinstance(s.value, ast.Constant)
                   and isinstance(s.value.value, int)
                   for t in s.targets if isinstance(t, ast.Name)}
        self.rel = rel
        self.sites = rows_in(tree.body)
        self.exit2_lines, self.rowblocks = set(), []
        for owner, blk in blocks(tree):
            r = rows_in(blk)
            if not r:
                continue
            self.rowblocks.append((owner, blk, r))
            if exits(blk) == 2:
                self.exit2_lines |= {s.lineno for s in r}
        self.other_lines = {s.lineno for s in self.sites} - self.exit2_lines

    @property
    def in_contract(self):
        return bool(self.exit2_lines) and bool(self.other_lines)

    def violations(self):
        """(rule, message) for each invariant this probe breaks."""
        bad = []
        cols = {s.col_str for s in self.sites}
        if len(cols) > 1 or cols == {"VARIABLE"}:
            where = ", ".join(f"{s.lineno}:col={s.col_str}" for s in self.sites)
            bad.append(("I1", f"the label column is not constant ({where})"))
        encs = {s.enc for s in self.sites}
        if len(encs) > 1:
            where = ", ".join(f"{s.lineno}:{s.enc}" for s in self.sites)
            bad.append(("I2", f"two value encodings in one probe ({where})"))
        for owner, blk, r in self.rowblocks:
            if exits(blk) is None or calls_footer(blk):
                continue
            bad.append(("I3", f"the block printing row(s) at "
                              f"{sorted({s.lineno for s in r})} exits "
                              f"{exits(blk)} with no footer() terminator"))
        return bad


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    files, unparseable, probes = [], [], []
    padded_only = 0
    for root, dirs, names in os.walk(PROBES):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for n in sorted(names):
            if not n.endswith(".py"):
                continue
            path = os.path.join(root, n)
            rel = os.path.relpath(path, REPO)
            files.append(rel)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError as e:
                unparseable.append((rel, e))
                continue
            # the wider "tabular prose" population, for the denominator only
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                        and node.func.id == "print" and node.args:
                    for k, v in parts_of(node.args[0]):
                        if k == "f" and WIDTH_SPEC.match(spec_text(v) or ""):
                            padded_only += 1
                            break
                    else:
                        continue
                    break
            p = Probe(rel, tree)
            if p.sites:
                probes.append(p)

    contract = [p for p in probes if p.in_contract]
    offenders = [(p, p.violations()) for p in contract]
    offenders = [(p, v) for p, v in offenders if v]

    if args.list:
        for p in probes:
            tag = "CONTRACT" if p.in_contract else "        "
            print(f"  {tag} {p.rel}")
            for s in sorted(p.sites, key=lambda s: s.lineno):
                kind = "exit2" if s.lineno in p.exit2_lines else "     "
                print(f"           :{s.lineno:<5} {kind}  col={s.col_str:<8} "
                      f"enc={s.enc:<5} labelw={s.padded}")

    print(f"\nprobe .py files walked             : {len(files)}")
    print(f"  unparseable                      : {len(unparseable)}")
    print(f"  print a width-padded label line  : {padded_only}")
    print(f"  print a REPORT ROW (spec s3)     : {len(probes)}")
    print(f"  IN CONTRACT (rows on exit 2 AND  : {len(contract)}")
    print(f"              another path)")
    print(f"    conform                        : {len(contract) - len(offenders)}")
    print(f"    VIOLATIONS                     : {len(offenders)}")
    for p in contract:
        v = dict(offenders).get(p)
        print(f"      {'RED ' if v else 'ok  '} {p.rel}")

    if unparseable:
        for rel, e in unparseable:
            print(f"\nUNPARSEABLE {rel}: {e}", file=sys.stderr)
        return 2
    if len(files) < MIN_FILES or len(contract) < MIN_CONTRACT:
        print(f"\nAPPARATUS FAILURE: {len(files)} file(s) walked, "
              f"{len(contract)} in contract (floors {MIN_FILES}/{MIN_CONTRACT}). "
              "A gate that finds no subject is not reporting a clean tree, it is "
              "reporting a broken classifier -- and a gate whose answer is an "
              "error must never pass a dead subject.", file=sys.stderr)
        return 3
    if offenders:
        print("\nREPORT-SHAPE VIOLATIONS -- a knife runner holding a baseline "
              "taken\non one exit path cannot read this probe's other path:\n",
              file=sys.stderr)
        for p, v in offenders:
            for rule, msg in v:
                print(f"  {rule}  {p.rel}\n        {msg}", file=sys.stderr)
        print("\nFIX: route every report row through probes/lib/probe_report.py "
              "row()\n     and print footer() on every exit path "
              "(docs/spec-probe-rowshape.md s5).", file=sys.stderr)
        return 1
    print(f"\nALL PASS -- {len(contract)} probe(s) print two exit paths' worth of "
          "report rows,\nand every one of them prints ONE grammar on both.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
