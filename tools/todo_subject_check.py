#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""todo_subject_check.py — does each TODO item's SUBJECT still exist?

A bulk SCREEN for a TODO sweep, not a verdict. For every checkbox block it pulls
the things the item names in backticks — file paths, and assembler/Python
identifiers — and asks whether they are still in the tree.

🔴 WHAT THIS PROVES AND WHAT IT DOES NOT.
  * A named file or symbol that is GONE is strong evidence the item is stale:
    its subject left the tree and nobody re-read the item.
  * A named symbol that is PRESENT proves only that the subject exists. It says
    nothing about whether the claimed BEHAVIOUR still holds — that needs the
    machine. "Subject present" is a necessary condition, never a verdict.
This distinction is the whole point: the screen is allowed to retire items, and
is NOT allowed to confirm them.

⚠️ FOUR FALSE-POSITIVE CLASSES, ALL FOUND BY RUNNING IT, and the first three are
fixed in the code below:
  1. A BARE BASENAME IS NOT A PATH. The first run declared `run_gates.py` and
     `omsx_repl.py` GONE because they are not at the repo root. That is the
     basename-vs-path error `check_citation_paths.py` was written to prevent,
     made here in the inverse direction.
  2. A 7-HEX TOKEN IS A GIT REVISION, not an identifier.
  3. A `.rom`/`.dsk` IS A GITIGNORED BUILD ARTIFACT -- absent from `ls-files` and
     present in `build/`.
  These three inflated "candidates for stale" from 13 to 54.
  4. 🔴 AND THE ONE THAT CANNOT BE FIXED HERE: AN ITEM MAY NAME A SYMBOL BECAUSE
     IT IS PROPOSING IT. `sg_walk_fnframe` is absent from the tree because the
     item says *"the fix is either a `sg_walk_fnframe` or a snapshot at bind
     time"*. A screen cannot tell a named subject from a named REMEDY, so a GONE
     symbol is a REASON TO READ THE ITEM and never a verdict.

Usage: python3 tools/todo_subject_check.py [--json OUT]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

TICK = re.compile(r"`([^`\n]{2,80})`")
# `.rom`/`.dsk` are gitignored build artifacts: absent from ls-files, present in
# build/. Checking them manufactures staleness, so they are not path claims here.
PATHY = re.compile(r"^[A-Za-z0-9_.\-/]+\.(asm|inc|py|md|txt|ips|bps|sh|json)$")
SYMBOL = re.compile(r"^[a-z][a-z0-9_]{3,}$")          # asm labels / py identifiers
# 🔴 A 7-HEX-CHAR TOKEN IS A GIT REVISION, NOT A SYMBOL. The first run of this
# screen reported `a897bcd`, `b8a8137` and `c04606b` as "gone symbols" -- they are
# commits this repo contains. A screen that cannot tell a revision from an
# identifier manufactures staleness.
GITISH = re.compile(r"^[0-9a-f]{7,40}$")
UPPER = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")           # equates / switches


def tree_text():
    allf = [f for f in subprocess.run(["git", "-C", str(ROOT), "ls-files"],
                                      capture_output=True, text=True).stdout.split("\n") if f]
    files = [f for f in allf
             if f.endswith((".asm", ".inc", ".py", ".mk")) or f == "Makefile"]
    buf = []
    for f in files:
        try:
            buf.append((ROOT / f).read_text(errors="replace"))
        except OSError:
            pass
    return "\n".join(buf), set(allf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()

    import importlib.util
    spec = importlib.util.spec_from_file_location("inv", ROOT / "tools" / "todo_inventory.py")
    inv = importlib.util.module_from_spec(spec); spec.loader.exec_module(inv)
    blocks = inv.blocks()
    lines = (ROOT / "TODO.md").read_text().split("\n")
    text, tracked = tree_text()
    basenames = {f.rsplit('/', 1)[-1] for f in tracked}

    out = []
    for b in blocks:
        if b["depth"] or not (b["state"] == "open" or b["residual_marker"]):
            continue
        body = "\n".join(lines[b["start"] - 1:b["end"]])
        names = set(TICK.findall(body))
        paths = {n for n in names if PATHY.match(n)}
        syms = {n for n in names if SYMBOL.match(n) or UPPER.match(n)}
        # 🔴 AND MATCH A BARE BASENAME AGAINST BASENAMES, NOT AGAINST PATHS.
        # The first run declared `run_gates.py` and `omsx_repl.py` GONE because
        # they are not at the repo root -- they are tools/run_gates.py and
        # probes/lib/omsx_repl.py. That is the basename-vs-path error the
        # citation gate written earlier TODAY exists to prevent, made by me in
        # the inverse direction: prose legitimately names a file, and only a name
        # containing a slash is a path claim.
        gone_p = sorted(p for p in paths
                        if ("/" in p and p not in tracked and not (ROOT / p).exists())
                        or ("/" not in p and p not in basenames))
        gone_s = sorted(s for s in syms
                        if not GITISH.match(s) and s not in text)
        out.append(dict(id=b["id"], start=b["start"], state=b["state"],
                        headline=b["headline"][:80],
                        paths=len(paths), syms=len(syms),
                        gone_paths=gone_p, gone_syms=gone_s))

    dead = [r for r in out if r["gone_paths"] or r["gone_syms"]]
    named = [r for r in out if r["paths"] or r["syms"]]
    print(f"screened {len(out)} subject blocks")
    print(f"  name at least one path/symbol : {len(named)}")
    print(f"  name NOTHING checkable        : {len(out) - len(named)}  "
          f"(the screen is silent on these -- not evidence of anything)")
    print(f"  name something that is GONE   : {len(dead)}  <- candidates for STALE")
    for r in dead:
        print(f"\n  {r['id']} L{r['start']} [{r['state']}] {r['headline']}")
        if r["gone_paths"]:
            print(f"      GONE paths  : {', '.join(r['gone_paths'])}")
        if r["gone_syms"]:
            print(f"      GONE symbols: {', '.join(r['gone_syms'][:8])}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
