#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""needle-case-check — a capitalised needle in a CASE-FOLDED table can never match.

🔴 WHY THIS EXISTS (filed 2026-08-02 by D-MSGEXACT §6b). That slice silently
broke **30 comparisons across 9 files**, and every one failed BY AGREEING: a
needle matched against an already-`.lower()`-ed screen string cannot match if it
is capitalised, so the row reclassifies from `error:<phrase>` to `value` instead
of going red. `diskbasic_probe_badfnum.py` was invisible to TWO rounds of
auditing -- it has no `.lower()` of its own at all; it `setdefault`s its needles
into `ERR_CLASSES`, a dict **imported from `diskbasic_probe_lof`**. The gate
caught it (12 oracle drifts), not the audit.

🎯 SO THE TABLE IS DISCOVERED, NOT LISTED. A hand-kept list of "tables that must
stay lowercase" is the thing that already failed: nobody adds the entry for the
module they are about to break. Pass 1 finds every table CONSUMED case-folded --
a `for … in TABLE` whose loop variable is then tested `in <something>.lower()`
-- and pass 2 flags any capitalised string written into one of those names
ANYWHERE in the tree, which is what crosses the module boundary.

Exit: 0 clean, 1 a capitalised needle, 2 the instrument could not measure.

    python3 tools/check_needle_case.py [--selftest] [--list]
"""
from __future__ import annotations

import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ("probes/basic", "probes/disk", "probes/lib", "tools", "scratchpad")
MIN_TABLES = 2      # fewer than this means the discovery pass broke


def sources():
    for d in DIRS:
        for p in sorted(glob.glob(os.path.join(ROOT, d, "*.py"))):
            yield os.path.relpath(p, ROOT)


def _parse(rel):
    try:
        return ast.parse(open(os.path.join(ROOT, rel), errors="replace").read())
    except (SyntaxError, ValueError):
        return None


def folded_tables(tree):
    """Names iterated over whose element is then tested `in <x>.lower()`."""
    found = set()
    scopes = [n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module))]
    for fn in scopes:
        folded = {a.targets[0].id for a in ast.walk(fn)
                  if isinstance(a, ast.Assign) and len(a.targets) == 1
                  and isinstance(a.targets[0], ast.Name)
                  and isinstance(a.value, ast.Call)
                  and isinstance(a.value.func, ast.Attribute)
                  and a.value.func.attr in ("lower", "casefold")}
        if not folded:
            continue
        srcof = {}
        for lp in [n for n in ast.walk(fn) if isinstance(n, ast.For)]:
            it, base = lp.iter, None
            if isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) \
                    and isinstance(it.func.value, ast.Name):
                base = it.func.value.id
            elif isinstance(it, ast.Name):
                base = it.id
            for tgt in ast.walk(lp.target):
                if isinstance(tgt, ast.Name):
                    srcof[tgt.id] = base or srcof.get(tgt.id)
        for cmp in [n for n in ast.walk(fn) if isinstance(n, ast.Compare)]:
            if not any(isinstance(o, ast.In) for o in cmp.ops):
                continue
            if not (isinstance(cmp.left, ast.Name)
                    and isinstance(cmp.comparators[0], ast.Name)
                    and cmp.comparators[0].id in folded):
                continue
            nm, seen = cmp.left.id, set()
            while nm in srcof and srcof[nm] and nm not in seen:
                seen.add(nm)
                nm = srcof[nm]
            if nm and nm.isupper():
                found.add(nm)
    return found


def _strings(node):
    """Every string literal in `node` -- but for a dict, only the VALUES.

    🔴 THE FIRST CUT WALKED THE WHOLE DICT AND REPORTED 19 FINDINGS, ALL FALSE:
    they were the KEYS (`'SYNTAX'`, `'IFC'`, `'FNF'` ...), which are class labels
    and are never matched against anything. Worse, this function carried a
    comment claiming keys were already excluded "by only walking the VALUE side"
    -- an asserted property the code did not have
    [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]. A needle
    table's keys are UPPERCASE BY CONVENTION, so the bug produced a full, tidy,
    entirely wrong report."""
    if isinstance(node, ast.Dict):
        for v in node.values:
            yield from _strings(v)
        return
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for e in node.elts:
            yield from _strings(e)
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node
        return
    for n in ast.iter_child_nodes(node):
        yield from _strings(n)


def writes_to(tree, tables):
    """(table, lineno, literal) for every string written into one of `tables`."""
    out = []
    for n in ast.walk(tree):
        # NAME = {...} / NAME = (...)
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id in tables:
                    out += [(t.id, s.lineno, s.value) for s in _strings(n.value)]
                # NAME[k] = (...)
                if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) \
                        and t.value.id in tables:
                    out += [(t.value.id, s.lineno, s.value) for s in _strings(n.value)]
        # NAME.setdefault(k, v) / NAME.update({...})
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and isinstance(n.func.value, ast.Name) \
                and n.func.value.id in tables \
                and n.func.attr in ("setdefault", "update"):
            for a in n.args[1:] if n.func.attr == "setdefault" else n.args:
                out += [(n.func.value.id, s.lineno, s.value) for s in _strings(a)]
    return out


# --- PASS 3: the ONE-OFF shape, which pass 1/2 cannot see (D-ONEOFFCASE) -----
# 🔴 THE FILED SCOPE NOTE SAID "0 of those today, measured separately" AND
# NOTHING KEPT IT AT 0. A comparison between a literal and a `.lower()`-ed
# expression, with no table between them, is the same defect in one line:
#
#     if "Type mismatch" in txt.lower():        # can NEVER be true
#
# It fails by AGREEING, exactly like the 30 comparisons D-MSGEXACT broke -- the
# branch simply never runs, so the row reclassifies rather than going red. The
# mirror (`"abc" == x.upper()`) is checked too, because a table-free comparison
# has no convention to lean on in either direction.
# ⚠️ AN EMPTY RESULT IS THE EXPECTED ONE HERE, which is why the selftest carries
# a planted instance: "0 findings" from a pass that cannot find anything looks
# identical to "0 findings" from a clean tree
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
def _folded_call(n, meth):
    return (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == meth and not n.args)


def oneoffs(tree):
    """(line, literal, method, op) for a literal that can never match."""
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare) or len(n.ops) != 1:
            continue
        op = type(n.ops[0]).__name__
        if op not in ("In", "NotIn", "Eq", "NotEq"):
            continue
        for lit, other in ((n.left, n.comparators[0]),
                           (n.comparators[0], n.left)):
            if not (isinstance(lit, ast.Constant)
                    and isinstance(lit.value, str) and lit.value.strip()):
                continue
            v = lit.value
            if _folded_call(other, "lower") and v != v.lower():
                out.append((n.lineno, v, "lower", op))
            elif _folded_call(other, "upper") and v != v.upper():
                out.append((n.lineno, v, "upper", op))
    return out


def scan():
    trees = {rel: _parse(rel) for rel in sources()}
    trees = {k: v for k, v in trees.items() if v is not None}
    tables = set()
    consumers = {}
    for rel, t in trees.items():
        for name in folded_tables(t):
            tables.add(name)
            consumers.setdefault(name, []).append(rel)
    bad, total = [], 0
    for rel, t in trees.items():
        for tbl, line, lit in writes_to(t, tables):
            total += 1
            if any(c.isupper() for c in lit):
                bad.append((rel, line, tbl, lit))
    solo = [(rel, line, lit, meth, op)
            for rel, t in trees.items() for line, lit, meth, op in oneoffs(t)]
    return tables, consumers, bad, total, solo


def selftest() -> int:
    fails = 0
    good = ("def f(t):\n    low = t.lower()\n"
            "    for cls, needles in TAB.items():\n"
            "        for n in needles:\n"
            "            if n in low:\n                return cls\n")
    tree = ast.parse(good + "TAB = {'A': ('syntax error',)}\n")
    if folded_tables(tree) != {"TAB"}:
        print(f"  selftest: discovery found {folded_tables(tree)}, want {{'TAB'}}")
        fails += 1
    # a capitalised needle must be caught...
    t2 = ast.parse(good + "TAB = {'A': ('Syntax error',)}\n")
    w = writes_to(t2, {"TAB"})
    if not any(any(c.isupper() for c in lit) for _t, _l, lit in w):
        print("  selftest: a capitalised needle in a dict literal was not seen")
        fails += 1
    # ...including one inserted across a module boundary by setdefault
    t3 = ast.parse("TAB.setdefault('OVF', ('Overflow',))\n")
    w3 = writes_to(t3, {"TAB"})
    if not any(lit == "Overflow" for _t, _l, lit in w3):
        print("  selftest: a setdefault'ed needle -- the badfnum shape -- was "
              "not seen")
        fails += 1
    # 🔴 THE ARM THAT WOULD HAVE CAUGHT THE KEY BUG, and did not exist when the
    # bug shipped: a table whose KEYS are uppercase (which is the convention --
    # 'SYNTAX', 'IFC', 'FNF') and whose NEEDLES are lowercase must produce ZERO
    # findings. The original selftest only asserted "some uppercase literal was
    # seen", which the buggy walker satisfied by finding the KEY -- it agreed for
    # the wrong reason [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
    tk = ast.parse(good + "TAB = {'SYNTAX': ('syntax error',), 'IFC': ('x',)}\n")
    keyhits = [lit for _t, _l, lit in writes_to(tk, {"TAB"})
               if any(c.isupper() for c in lit)]
    if keyhits:
        print(f"  selftest: uppercase dict KEYS reported as needles: {keyhits}")
        fails += 1
    # ...and a lowercase one must NOT be flagged
    t4 = ast.parse("TAB.setdefault('OVF', ('overflow',))\n")
    if any(any(c.isupper() for c in lit) for _t, _l, lit in writes_to(t4, {"TAB"})):
        print("  selftest: a lowercase needle was flagged")
        fails += 1
    # a table nobody folds must not be discovered
    if folded_tables(ast.parse("for k in TAB:\n    print(k)\n")):
        print("  selftest: a table with no case-folded comparison was discovered")
        fails += 1

    # --- PASS 3 ARMS. \U0001f534 THE LIVE RUN OF PASS 3 FINDS NOTHING, WHICH IS THE
    # EXPECTED ANSWER -- so nothing about a clean tree distinguishes a working
    # pass from a pass that cannot see. Every arm below plants the shape.
    P3 = [
        ('if "Type mismatch" in t.lower(): pass\n', 1, "the plain shape"),
        ('if "Type mismatch" not in t.lower(): pass\n', 1, "negated"),
        ('if t.lower() == "Ok": pass\n', 1, "equality, literal on the RIGHT"),
        ('if "abc" == t.upper(): pass\n', 1, "the .upper() mirror"),
        ('if "type mismatch" in t.lower(): pass\n', 0,
         "a lowercase literal against .lower() is CORRECT and must not fire"),
        ('if "ABC" in t.upper(): pass\n', 0,
         "an uppercase literal against .upper() is CORRECT"),
        ('if "Type mismatch" in t: pass\n', 0, "no folding at all -- not in scope"),
        ('if "Type mismatch" in t.lower(x): pass\n', 0,
         "a .lower() that takes an argument is somebody else's method"),
    ]
    for src, want, why in P3:
        got = len(oneoffs(ast.parse(src)))
        if got != want:
            print(f"  selftest: pass 3 -- {why}: want {want} finding(s), got {got}")
            fails += 1
    print("  selftest: PASS" if not fails else f"  selftest: {fails} FAILURE(S)")
    return fails


def main(argv):
    if "--selftest" in argv:
        return 2 if selftest() else 0
    tables, consumers, bad, total, solo = scan()
    if len(tables) < MIN_TABLES:
        print(f"INSTRUMENT FAULT: discovered {len(tables)} case-folded needle "
              f"table(s); the floor is {MIN_TABLES}. The discovery pass broke -- "
              f"a clean run here would mean nothing.")
        return 2
    print(f"needle-case-check: {len(tables)} case-folded needle table(s), "
          f"{total} needle(s) written into them")
    for name in sorted(tables):
        print(f"  {name:14} consumed case-folded in "
              f"{', '.join(sorted(consumers[name]))}")
    if "--list" in argv:
        for rel, line, tbl, lit in sorted(bad):
            print(f"    {rel}:{line}  {tbl}  {lit!r}")
    print()
    for rel, line, tbl, lit in bad:
        print(f"🔴 {rel}:{line} writes {lit!r} into {tbl}, which is matched "
              f"against a `.lower()`-ed string -- it can NEVER match, and the "
              f"row reclassifies instead of going red.")
    for rel, line, lit, meth, op in solo:
        print(f"🔴 {rel}:{line} compares {lit!r} ({op}) against an expression "
              f"already `.{meth}()`-ed -- it can NEVER match, and the branch "
              f"simply never runs.")
    if bad or solo:
        print(f"\n{len(bad)} capitalised needle(s), "
              f"{len(solo)} one-off comparison(s) that can never match")
        return 1
    print(f"clean -- every needle in a case-folded table is lowercase, and "
          f"0 one-off comparison(s) can never match.")
    print("⚠️ SCOPE: needles in tables DISCOVERED as case-folded (passes 1-2) "
          "plus table-free literal-vs-`.lower()`/`.upper()` comparisons "
          "(pass 3, added 2026-09-05 -- the filed \"0 today, measured "
          "separately\" is now KEPT at 0 rather than re-measured by hand).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
