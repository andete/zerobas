#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD

"""check_probe_preflight -- every openMSX launch in this tree goes through the preflight.

`probes/lib/omsx_preflight.py` refuses to measure a machine whose ROMs are missing
or stale. A guard is only worth what it COVERS, and 94 of this tree's 146 probes
build their own openMSX command line, so a preflight wired into `omsx_repl` alone
would have been filtered away from most of its subject by construction
([[echo-guard-never-saw-say-rows]]).

This walks the AST of every `.py` under probes/, tools/ and tests/, finds every
`subprocess.Popen/run/call/check_output/check_call` site, and classifies it:

  EXEMPT   argv is a LIST LITERAL containing no `-machine` string -> it is
           PROVABLY not an openMSX launch. This is the only exemption, and it is
           structural: no name lists, no directory carve-outs, nothing a future
           edit can quietly widen.
  REQUIRED anything else -- a literal carrying `-machine`, a variable whose
           in-function assignments cannot all be proven `-machine`-free, or an
           expression this checker cannot see into. Such a site must spawn
           `omsx_preflight.guarded(...)`.

⚠️ THE EXEMPTION IS DELIBERATELY THE WEAKER-LOOKING SIDE OF THE CUT. A site is
exempt only when the evidence is in the source; everything else must be guarded,
including argv lists that plainly run `pasmo` or `python3`. Guarding those costs a
no-op call (`guard_cmd` returns immediately without `-machine`) and removes the
judgement call that a name-based exemption would reintroduce.

    python3 tools/check_probe_preflight.py            # gate: non-zero if unguarded
    python3 tools/check_probe_preflight.py --list     # print every site + verdict
"""
from __future__ import annotations

import argparse
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SCAN_DIRS = ("probes", "tools", "tests")

SPAWNS = ("Popen", "run", "call", "check_output", "check_call")
GUARDS = ("guarded", "guard_cmd", "preflight")


def _is_spawn(node: ast.AST) -> bool:
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in SPAWNS
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess")


def _is_guard_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    f = node.func
    if isinstance(f, ast.Attribute):
        return f.attr in GUARDS
    return isinstance(f, ast.Name) and f.id in GUARDS


def _literal_has_machine(node: ast.AST) -> bool:
    """True if this expression is a list literal (or a concatenation of them)
    containing the string `-machine`."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and sub.value == "-machine":
            return True
    return False


def _provably_machine_free(node: ast.AST) -> bool:
    """True only when the expression is built ENTIRELY from list literals and
    string/number constants -- i.e. its full contents are visible here -- and none
    of them is `-machine`. Any name, call, attribute, comprehension or f-string
    makes it unprovable, and unprovable means REQUIRED."""
    for sub in ast.walk(node):
        if isinstance(sub, (ast.Name, ast.Call, ast.Attribute, ast.Subscript,
                            ast.JoinedStr, ast.Starred, ast.ListComp,
                            ast.GeneratorExp, ast.IfExp, ast.Await)):
            return False
        if isinstance(sub, ast.Constant) and sub.value == "-machine":
            return False
    return True


def _enclosing_func(tree: ast.AST, node: ast.AST):
    best = None
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.lineno <= node.lineno <= (n.end_lineno or n.lineno):
                if best is None or n.lineno > best.lineno:
                    best = n
    return best or tree


def _name_provably_machine_free(scope: ast.AST, name: str) -> bool:
    """Every contribution to `name` inside `scope` is a visible, `-machine`-free
    literal. `x = [...]`, `x += [...]`, `x = x + [...]`, `x.append/extend(...)`."""
    saw = False
    for n in ast.walk(scope):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    saw = True
                    if not _rhs_ok(n.value, name):
                        return False
        elif isinstance(n, ast.AugAssign):
            if isinstance(n.target, ast.Name) and n.target.id == name:
                saw = True
                if not _rhs_ok(n.value, name):
                    return False
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and isinstance(n.func.value, ast.Name) and n.func.value.id == name
              and n.func.attr in ("append", "extend", "insert", "__iadd__")):
            saw = True
            for a in n.args:
                if not _provably_machine_free(a):
                    return False
    return saw


def _rhs_ok(value: ast.AST, name: str) -> bool:
    """A right-hand side is acceptable if it is a visible `-machine`-free literal,
    optionally concatenated with the variable itself (`cmd = cmd + [...]`)."""
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
        return all(
            (isinstance(side, ast.Name) and side.id == name) or _provably_machine_free(side)
            for side in (value.left, value.right))
    return _provably_machine_free(value)


class Site:
    def __init__(self, path, lineno, argv_src, verdict, guarded):
        self.path, self.lineno = path, lineno
        self.argv_src, self.verdict, self.guarded = argv_src, verdict, guarded


def scan_file(path: str) -> list[Site]:
    src = open(path).read()
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"{os.path.relpath(path, REPO)}: PARSE FAILED: {e}", file=sys.stderr)
        raise SystemExit(3)
    out = []
    for node in ast.walk(tree):
        if not _is_spawn(node):
            continue
        rel = os.path.relpath(path, REPO)
        if not node.args:
            out.append(Site(rel, node.lineno, "<no argv>", "REQUIRED", False))
            continue
        a = node.args[0]
        seg = (ast.get_source_segment(src, a) or "").replace("\n", " ")
        if _is_guard_call(a):
            out.append(Site(rel, node.lineno, seg, "REQUIRED", True))
            continue
        if isinstance(a, ast.List) and not _literal_has_machine(a):
            out.append(Site(rel, node.lineno, seg, "EXEMPT", False))
            continue
        if isinstance(a, ast.Name):
            scope = _enclosing_func(tree, node)
            if _name_provably_machine_free(scope, a.id):
                out.append(Site(rel, node.lineno, seg, "EXEMPT", False))
                continue
        out.append(Site(rel, node.lineno, seg, "REQUIRED", False))
    return out


def collect() -> list[Site]:
    sites = []
    for d in SCAN_DIRS:
        for dirpath, dirnames, names in os.walk(os.path.join(REPO, d)):
            dirnames[:] = [x for x in dirnames if x not in ("__pycache__", ".git")]
            for n in sorted(names):
                if n.endswith(".py"):
                    sites += scan_file(os.path.join(dirpath, n))
    return sorted(sites, key=lambda s: (s.path, s.lineno))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="print every site + verdict")
    args = ap.parse_args()

    sites = collect()
    exempt = [s for s in sites if s.verdict == "EXEMPT"]
    required = [s for s in sites if s.verdict == "REQUIRED"]
    unguarded = [s for s in required if not s.guarded]

    if args.list:
        for s in sites:
            tag = s.verdict if s.verdict == "EXEMPT" else (
                "GUARDED " if s.guarded else "UNGUARDED")
            print(f"  {tag:<10} {s.path}:{s.lineno}  {s.argv_src[:70]}")

    print(f"\nsubprocess spawn sites : {len(sites)}")
    print(f"  exempt by construction (list literal, no -machine) : {len(exempt)}")
    print(f"  require a preflight guard                          : {len(required)}")
    print(f"    guarded                                          : "
          f"{len(required) - len(unguarded)}")
    print(f"    UNGUARDED                                        : {len(unguarded)}")

    if not required:
        print("\nAPPARATUS FAILURE: 0 sites require a guard -- this gate is "
              "measuring nothing. The classifier is broken, not the tree.",
              file=sys.stderr)
        return 3
    if unguarded:
        print("\nUNGUARDED openMSX launch sites -- each can boot a machine whose "
              "ROMs\nare missing or stale and report it as a code result:\n",
              file=sys.stderr)
        for s in unguarded:
            print(f"  {s.path}:{s.lineno}\n      {s.argv_src[:100]}", file=sys.stderr)
        print("\nFIX: wrap the argv -- subprocess.Popen(omsx_preflight.guarded(cmd), ...)"
              "\n     (docs/spec-probe-preflight.md s3.5)", file=sys.stderr)
        return 1
    print("\nALL PASS -- every launch site this checker cannot prove harmless "
          "is guarded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
