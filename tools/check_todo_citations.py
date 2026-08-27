#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Gate: every `TODO.md:NNN (T-xxxxxx)` citation still points at that block.

A line number into a file that gets edited is a rotting citation, and this repo
had 42 of them. The 2026-08-26 archive split repointed all 42 and gave each one
the block's CONTENT-DERIVED id as well -- the id from `tools/todo_inventory.py`,
a digest of the headline, which survives reflow, renumbering and moving the
block to another file. That is exactly what makes this checkable:

    the LINE is for a human's click; the ID is what the check trusts.

RED when a cited line no longer sits inside the block whose id the citation
names. `--fix` rewrites the line number from the id, so the repair is mechanical
rather than a hunt.

⚠️ AN ID-LESS CITATION IS ONLY WEAKLY CHECKED -- the line must exist, and that is
all a bare line number can support. Those are counted and named in the summary
rather than passed over silently, because a check that reports 100 % while a
third of its subject is uncheckable is the 0/0-ALL-CONVERGED shape.

Usage:  python3 tools/check_todo_citations.py            (gate; rc 1 = RED)
        python3 tools/check_todo_citations.py --fix
        python3 tools/check_todo_citations.py --selftest  (rc 2 = instrument fault)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import todo_inventory                                            # noqa: E402
import probe_tmp                                                 # noqa: E402

# Matches `../TODO.md:<n> (T-4AC4B2)` and the `TODO-done.md:<n>` spelling; the
# id group is optional. (The forms are described rather than written out: a
# literal example in this file is a citation this check would then try to
# resolve, and it would be right to fail it.)
CITE = re.compile(r"(?<![-\w])((?:\.\./)?TODO(?:-done)?\.md):(\d+)"
                  r"(?:\s*\((T-[0-9A-F]{6}(?:\.\d+)?)\))?")
SCAN_EXT = (".md", ".py", ".asm", ".inc")


def tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                         text=True)
    if out.returncode != 0:
        sys.exit(2)
    return [f for f in out.stdout.split()
            if f.endswith(SCAN_EXT) or os.path.basename(f) == "Makefile"]


def resolve(citing_rel: str, spelled: str, root=ROOT) -> str | None:
    """Repo-relative path of the file a citation in `citing_rel` names.

    ⚠️ RELATIVE FIRST, THEN REPO ROOT. A `../TODO.md` in `docs/` is relative;
    a bare `TODO.md` in a `scratchpad/` docstring means the repo's TODO.md, not
    a sibling that has never existed. The first cut resolved relative ONLY and
    reddened five citations that were perfectly correct -- the check was wrong
    about the convention, not the repo."""
    for cand in (os.path.normpath(os.path.join(os.path.dirname(citing_rel), spelled)),
                 os.path.normpath(spelled.replace("../", ""))):
        if os.path.exists(os.path.join(root, cand)):
            return cand
    return None


_CACHE: dict[str, list] = {}


def blocks_of(rel: str):
    if rel not in _CACHE:
        _CACHE[rel] = todo_inventory.blocks(os.path.join(ROOT, rel))
    return _CACHE[rel]


def block_at(rel, line):
    """The DEEPEST block covering `line`. A nested `- [x]` has an id too, and
    restricting this to depth 0 left 12 citations permanently uncheckable --
    they point INTO nested items, which is exactly where the detail lives."""
    hit = [b for b in blocks_of(rel) if b["start"] <= line <= b["end"]]
    return max(hit, key=lambda b: b["depth"]) if hit else None


def block_by_id(rel, bid):
    for b in blocks_of(rel):
        if b["id"] == bid:
            return b
    return None


def scan(files, root=ROOT):
    """-> list of findings (rel, lineno, spelled, line, bid, verdict, detail)."""
    out = []
    for rel in files:
        path = os.path.join(root, rel)
        try:
            text = open(path).read()
        except (OSError, UnicodeDecodeError):
            continue
        if "TODO" not in text:
            continue
        for n, src in enumerate(text.splitlines(), 1):
            for m in CITE.finditer(src):
                spelled, line, bid = m.group(1), int(m.group(2)), m.group(3)
                tgt = resolve(rel, spelled)
                if tgt is None:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"names {spelled}, which does not exist"))
                    continue
                nlines = len(open(os.path.join(root, tgt)).read().splitlines())
                href = src[:m.start()].endswith("](")
                if line < 1 or line > nlines:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{tgt} has {nlines} lines; :{line} is past the end"))
                    continue
                if href:
                    # 🔴 THE TWO HALVES OF A MARKDOWN LINK MUST AGREE. The
                    # 2026-08-26 repoint rewrote labels and skipped hrefs on
                    # its first pass, leaving a link whose label named one line
                    # and whose target named another -- it reads right and goes
                    # somewhere else. (Spelled in prose: a literal example would
                    # be read by this very check as a live citation.) The id
                    # belongs on the LABEL (a `](path (T-x))` is not a URL), so
                    # an href is checked against the label beside it instead.
                    lab = list(CITE.finditer(src[:m.start()]))
                    if not lab:
                        out.append((rel, n, spelled, line, bid, "RED",
                                    "link target with no label citation to agree with"))
                    elif (lab[-1].group(1), lab[-1].group(2)) != (spelled, str(line)):
                        out.append((rel, n, spelled, line, bid, "RED",
                                    f"the link's two halves disagree: label says "
                                    f"{lab[-1].group(1)}:{lab[-1].group(2)}, "
                                    f"target says {spelled}:{line}"))
                    else:
                        out.append((rel, n, spelled, line, bid, "PAIR", ""))
                    continue
                if bid is None:
                    here = block_at(tgt, line)
                    out.append((rel, n, spelled, line, bid, "WEAK",
                                f"no block id -- annotatable as "
                                f"({here['id']})" if here else
                                "no block id, and the line is in no block at all"))
                    continue
                here = block_at(tgt, line)
                if here is not None and here["id"] == bid:
                    out.append((rel, n, spelled, line, bid, "OK", ""))
                    continue
                want = block_by_id(tgt, bid)
                if want is None:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{bid} is in no block of {tgt} "
                                f"(headline edited, or moved to the other file?)"))
                else:
                    out.append((rel, n, spelled, line, bid, "RED",
                                f"{bid} is at {tgt}:{want['start']}, not :{line}"))
    return out


def apply_fix(findings, root=ROOT):
    """Rewrite drifted line numbers from the id. Only touches repairable REDs."""
    by_file: dict[str, list] = {}
    for f in findings:
        if f[5] == "RED" and f[4]:
            tgt = resolve(f[0], f[2])
            if tgt and block_by_id(tgt, f[4]):
                by_file.setdefault(f[0], []).append(f)
    n = 0
    for rel, fs in by_file.items():
        path = os.path.join(root, rel)
        lines = open(path).read().splitlines(keepends=True)
        for rel_, lineno, spelled, line, bid, _, _ in fs:
            tgt = resolve(rel_, spelled)
            new = block_by_id(tgt, bid)["start"]
            lines[lineno - 1] = lines[lineno - 1].replace(
                f"{spelled}:{line}", f"{spelled}:{new}")
            n += 1
        open(path, "w").writelines(lines)
    return n


def annotate(weak, root=ROOT):
    """Attach `(T-xxxxxx)` to an id-less citation from the block at that line."""
    by_file: dict[str, list] = {}
    for w in weak:
        by_file.setdefault(w[0], []).append(w)
    n = 0
    for rel, ws in by_file.items():
        path = os.path.join(root, rel)
        lines = open(path).read().splitlines(keepends=True)
        for rel_, lineno, spelled, line, _, _, _ in ws:
            tgt = resolve(rel_, spelled)
            b = block_at(tgt, line) if tgt else None
            if not b:
                continue
            lines[lineno - 1] = lines[lineno - 1].replace(
                f"{spelled}:{line}", f"{spelled}:{line} ({b['id']})", 1)
            n += 1
        open(path, "w").writelines(lines)
    return n


def selftest():
    """🔬 FALSIFY BY PLANTING. Both senses required: a drifted citation must go
    RED, and the SAME apparatus must be GREEN on the same citation undrifted.
    A red arm that passes because it never fired is not an arm."""
    import shutil
    real = scan(tracked())
    ok = [f for f in real if f[5] == "OK"]
    if not ok:
        print("SELFTEST rc 2: no OK citation to plant against -- the apparatus "
              "has nothing to prove it can pass.")
        return 2
    # the selftest copies the tree; probe_tmp owns the directory and gives it
    # back at exit (`make temp-root-check`), so a failed run leaves nothing.
    tmp = probe_tmp.tmp("todocite-selftest")
    os.makedirs(tmp, exist_ok=True)
    for rel in {"TODO.md", "docs/TODO-done.md", ok[0][0]}:
        d = os.path.join(tmp, os.path.dirname(rel))
        os.makedirs(d, exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, rel), os.path.join(tmp, rel))
    rel, lineno, spelled, line, bid, _, _ = ok[0]
    _CACHE.clear()
    green = scan([rel], root=tmp)
    g = [f for f in green if f[1] == lineno and f[4] == bid]
    if not (g and g[0][5] == "OK"):
        print(f"SELFTEST rc 2: the GREEN control did not pass on the copy "
              f"({g[0][5] if g else 'citation not found'}). The apparatus is "
              f"reading something other than its subject.")
        return 2
    # plant the drift: same id, a line number one block away
    p = os.path.join(tmp, rel)
    txt = open(p).read().splitlines(keepends=True)
    txt[lineno - 1] = txt[lineno - 1].replace(f"{spelled}:{line}",
                                              f"{spelled}:{line + 400}")
    open(p, "w").writelines(txt)
    _CACHE.clear()
    red = scan([rel], root=tmp)
    r = [f for f in red if f[1] == lineno and f[4] == bid]
    _CACHE.clear()
    if not (r and r[0][5] == "RED"):
        print(f"SELFTEST rc 2: the planted drift did NOT go red "
              f"({r[0][5] if r else 'citation not found'}). The check cannot "
              f"detect the thing it exists to detect.")
        return 2
    print(f"selftest: GREEN control passes and a planted drift goes RED "
          f"on {rel}:{lineno} ({bid}) ✅")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--annotate", action="store_true",
                    help="attach the block id to id-less citations, from the "
                         "block that is at that line NOW (idempotent)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rc = selftest()
    if rc:
        return 2
    _CACHE.clear()
    f = scan(tracked())
    red = [x for x in f if x[5] == "RED"]
    weak = [x for x in f if x[5] == "WEAK"]
    ok = [x for x in f if x[5] == "OK"]
    pair = [x for x in f if x[5] == "PAIR"]
    if a.annotate and weak:
        n = annotate(weak)
        print(f"--annotate: attached {n} block id(s); re-run to confirm")
        return 0
    if a.fix and red:
        n = apply_fix(f)
        print(f"--fix: rewrote {n} line number(s) from the block id; re-run to confirm")
        return 0
    print(f"todo-citations: {len(f)} citation(s) into TODO.md / docs/TODO-done.md "
          f"across {len({x[0] for x in f})} file(s)")
    print(f"  {len(ok):3d} verified against the block id")
    print(f"  {len(pair):3d} link targets agreeing with their label")
    print(f"  {len(weak):3d} id-less (line existence only -- NOT verified):")
    for x in weak:
        print(f"        {x[0]}:{x[1]} -> {x[2]}:{x[3]}")
    if red:
        print(f"  {len(red):3d} RED:")
        for x in red:
            print(f"        {x[0]}:{x[1]} -> {x[2]}:{x[3]} "
                  f"{'(' + x[4] + ') ' if x[4] else ''}{x[6]}")
        print("\n  fix mechanically with: python3 tools/check_todo_citations.py --fix")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
