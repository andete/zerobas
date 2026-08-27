#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""check_chokepoints — where a shared helper exists, a hand-rolled copy is a bug.

Three separate items filed "and nothing checks it" and each proposed its own
cheap checker. They are one property, not three subjects:

  🎯 A SHARED HELPER EXISTS **BECAUSE THE OBVIOUS HAND-WRITTEN VERSION WAS
     MEASURED WRONG.** Writing the obvious version again is therefore not a
     style preference -- it is re-introducing a defect that has a number
     attached to it.

Every rule below names the helper, the measurement that created it, and its own
DENOMINATOR. A checker that cannot say what it looked at is the shape this tree
keeps paying for.

RULE 1 -- PUBLISH.  `openmsx_paths.publish()`.  `open(out, "w")` truncates the
  moment it is called, so a shared path holds an EMPTY file until the write
  lands. D-MACHXML measured **412/1200 (34.3 %) of concurrent reads torn**
  against 0/1200 atomic, and `repack-machine` is a prerequisite of 112 targets
  `make gates` runs in parallel.
  DENOMINATOR: `tools/install-*.py` + `tools/openmsx_paths.py` -- the files
  whose job is writing into the shared openMSX tree. Small, complete, and it
  sidesteps the obstacle that filed the item (the destination is built by
  `find_user()` at runtime, so no textual sweep can resolve the path).

RULE 2 -- ROOT.  `dirname(dirname(abspath(__file__)))`.  A tracked script that
  hardcodes an absolute home directory RESOLVES in a fresh clone and then does
  the wrong thing, which is worse than failing. Measured 2026-08-26: 24 files
  did this and **190 already derived it** -- the tree had voted 190 to 25.
  ⚠️ **ELEVEN OF THE 24 WERE KNIFE RUNNERS**, which cut source files.
  DENOMINATOR: every tracked `.py`/`.sh` under `scratchpad/`, `probes/`,
  `tools/`. ⚠️ `.log`/`.out` captures are NOT swept: they hold 343 of the 372
  raw hits, and an absolute path inside a captured log is evidence of what ran.

RULE 3 -- READER.  the ECHO FENCE: `result_span_after_echo` / `screen_tail`.
  The fence exists so *"an aborted case's echoed `[` is not misread as printed
  output"*. A scanner that reads the WHOLE SCREEN returns the echo's bracket
  fragment as its first element, and on an aborted case returns a NON-EMPTY
  result where the fenced reader returns `None` -- so "no output" reads as "a
  value". Separated on 4/4 cases by `scratchpad/spanreader_diff.py`.
  🔴 **THE RULE IS "REACHES A FENCE", NOT "DEFINES A FUNCTION NAMED bracket".**
  The first cut tested the name and reddened **24 gate probes that are
  correct** -- `basic_probe_arylv.bracket()` calls `screen_tail(raw, "RUN")`
  first and then adds `<NO CAPTURE>` / `<NO OUTPUT>` sentinels, which is a
  richer wrapper around the fence, not a copy of it. Wrapping a chokepoint is
  the behaviour this gate wants; only BYPASSING it is the finding.
  DENOMINATOR: every tracked `.py` that imports `omsx_repl` and defines a
  `[...]` reader of its own.

Exceptions are PINNED in `tools/chokepoint-allow.txt` with a reason, and the
pins may SHRINK, never grow -- a stale pin is itself a finding.

Usage:  python3 tools/check_chokepoints.py           (gate; rc 1 = RED)
        python3 tools/check_chokepoints.py --selftest (rc 2 = instrument fault)
"""
from __future__ import annotations

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402

ALLOW = os.path.join(ROOT, "tools", "chokepoint-allow.txt")

R1_FILES = re.compile(r"^tools/(install-.*\.py|openmsx_paths\.py)$")
R2_DIRS = ("scratchpad", "probes", "tools")
R3_NAMES = ("spans", "_spans", "read_rows", "bracket")
# reaching ANY of these means the reader is fenced against the command echo
FENCE = re.compile(r"result_span_after_echo|screen_tail|result_span\\b")

# 🔴 A REGEX CANNOT TELL CODE FROM PROSE **ABOUT** CODE. The first cut matched
# `open(..., "w")` textually and reddened `openmsx_paths.py` twice -- on the
# COMMENT that explains why the raw call is forbidden. Every rule that has an
# AST form uses it; a docstring quoting its own subject is the single most
# likely thing to appear in a file that documents a chokepoint.


def _tree(text):
    try:
        return ast.parse(text)
    except SyntaxError:
        return None


def _raw_open_w(tree):
    """(line, ) for every real `open(..., "w")` CALL outside `def publish`."""
    inside = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "publish":
            inside.update(id(n) for n in ast.walk(node))
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open" and id(node) not in inside):
            mode = node.args[1] if len(node.args) > 1 else None
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
                    and "w" in mode.value:
                out.append(node.lineno)
    return out


def _abs_root_assign(tree):
    """(line, name) for ROOT/REPO = "<absolute home path>", however wrapped."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(n in ("ROOT", "REPO") for n in names):
            continue
        v = node.value
        if isinstance(v, ast.Call) and v.args:      # pathlib.Path("...")
            v = v.args[0]
        if isinstance(v, ast.Constant) and isinstance(v.value, str) \
                and re.match(r"/(?:Users|home)/", v.value):
            out.append((node.lineno, names[0]))
    return out


def _own_reader(tree):
    return [(n.lineno, n.name) for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name in R3_NAMES]


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        print("GATE-SKIPPED: not a git checkout, so there is no file set to sweep")
        sys.exit(0)
    return out.stdout.split()


def load_allow():
    pins = {}
    if os.path.exists(ALLOW):
        for line in open(ALLOW):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, why = line.partition("  ")
            pins[key.strip()] = why.strip() or "(no reason given)"
    return pins


def read(root, rel):
    try:
        return open(os.path.join(root, rel)).read()
    except (OSError, UnicodeDecodeError):
        return None


def scan(files, root=ROOT):
    """-> (findings, denominators). A finding is (rule, rel, line, detail)."""
    f, den = [], {}
    # --- RULE 1
    r1 = [x for x in files if R1_FILES.match(x)]
    den["PUBLISH"] = len(r1)
    for rel in r1:
        t = read(root, rel)
        tree = _tree(t) if t else None
        if tree is None:
            continue
        for line in _raw_open_w(tree):
            f.append(("PUBLISH", rel, line,
                      "raw open(...,'w') into the shared openMSX tree -- "
                      "use openmsx_paths.publish()"))
    # --- RULE 2
    r2 = [x for x in files
          if x.split("/")[0] in R2_DIRS and x.endswith((".py", ".sh"))]
    den["ROOT"] = len(r2)
    for rel in r2:
        t = read(root, rel)
        if t is None:
            continue
        if rel.endswith(".sh"):        # no AST for shell; the textual form is
            for m in re.finditer(r'^\s*(ROOT|REPO)=["\']?/(?:Users|home)/',
                                 t, re.M):          # unambiguous enough here
                f.append(("ROOT", rel, t[:m.start()].count("\n") + 1,
                          "ROOT/REPO hardcodes an absolute home path"))
            continue
        tree = _tree(t)
        if tree is None:
            continue
        for line, name in _abs_root_assign(tree):
            f.append(("ROOT", rel, line,
                      f"{name} hardcodes an absolute home path -- derive it "
                      f"from __file__ as 190 other scripts do"))
    # --- RULE 3
    r3 = []
    for rel in [x for x in files if x.endswith(".py")]:
        t = read(root, rel)
        if not t or "import omsx_repl" not in t:
            continue
        tree = _tree(t)
        if tree is None or not _own_reader(tree):
            continue
        r3.append((rel, t, tree))
    den["READER"] = len(r3)
    for rel, t, tree in r3:
        if FENCE.search(t):        # wraps the fence -> exactly what we want
            continue
        for line, name in _own_reader(tree):
            f.append(("READER", rel, line,
                      f"{name}() scans the screen without reaching the echo "
                      f"fence -- use result_span_after_echo / screen_tail"))
    return f, den


def selftest():
    """🔬 FALSIFY BY PLANTING, ONE ARM PER RULE, BOTH SENSES.

    A copy of the tree must be GREEN, then one planted violation per rule must
    make exactly that rule RED. A rule whose red arm never fires is not a rule,
    and a gate with three rules needs three arms -- proving one does not prove
    the others."""
    tmp = probe_tmp.tmp("chokepoint-selftest")
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    files = tracked()
    need = sorted({x for x in files if R1_FILES.match(x)}
                  | {"scratchpad/spanreader_diff.py", "tools/check_chokepoints.py"})
    for rel in need:
        d = os.path.join(tmp, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, rel))
    base, _ = scan(need, root=tmp)
    base = [x for x in base if key(x) not in load_allow()]
    if base:
        print(f"SELFTEST rc 2: the GREEN control is not green on a copy — "
              f"{base[:2]}. The apparatus is reading something other than its "
              f"subject.")
        return 2

    # 🔴 THE READER PLANT NEEDS ITS OWN FILE. Appending a `spans()` to
    # `spanreader_diff.py` did NOT go red -- correctly, because that file CALLS
    # `result_span_after_echo`, so it reaches the fence and the rule is about
    # bypassing it. A plant that lands in a file already satisfying the rule
    # tests nothing; the arm has to be unfenced by construction.
    NEW = "scratchpad/_chokepoint_plant.py"
    plants = [
        ("PUBLISH", next(x for x in need if x.startswith("tools/install-")),
         '\nopen(_planted, "w").write("x")\n', False),
        ("ROOT", "scratchpad/spanreader_diff.py",
         '\nROOT = "/Users/planted/projects/zerobas"\n', False),
        ("READER", NEW,
         'import omsx_repl\n\n\ndef spans(scr):\n    return []\n', True),
    ]
    for rule, rel, text, is_new in plants:
        p = os.path.join(tmp, rel)
        orig = None if is_new else open(p).read()
        if is_new:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            open(p, "w").write(text)
        else:
            open(p, "a").write(text)
        got, _ = scan(need + ([NEW] if is_new else []), root=tmp)
        if is_new:
            os.remove(p)
        else:
            open(p, "w").write(orig)
        hits = [x for x in got if x[0] == rule]
        if not hits:
            print(f"SELFTEST rc 2: a planted {rule} violation in {rel} did NOT "
                  f"go red. That rule cannot detect the thing it exists for.")
            return 2
    print(f"selftest: green control passes and one planted violation per rule "
          f"({', '.join(r for r, *_ in plants)}) goes RED ✅")
    return 0


def key(finding):
    return f"{finding[0]}:{finding[1]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if selftest():
        return 2
    pins = load_allow()
    files = tracked()
    found, den = scan(files)
    red = [x for x in found if key(x) not in pins]
    pinned = [x for x in found if key(x) in pins]
    print("check_chokepoints — a shared helper exists; a hand-rolled copy is the bug")
    for rule, n in den.items():
        print(f"  {rule:8s} denominator {n:4d} file(s)")
    print(f"  {len(pinned)} pinned exception(s), {len(red)} finding(s)")
    stale = sorted(set(pins) - {key(x) for x in found})
    for k in stale:
        print(f"  🔴 STALE PIN {k}: pinned, but no longer a finding — remove it "
              f"from {os.path.relpath(ALLOW, ROOT)}")
    for rule, rel, line, why in red:
        print(f"  RED  {rule}  {rel}:{line}\n       {why}")
    if red or stale:
        return 1
    print("ALL PASS — every chokepoint is reached, and every pin still bites")
    return 0


if __name__ == "__main__":
    sys.exit(main())
