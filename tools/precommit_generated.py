#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""precommit_generated -- keep the GENERATED docs pages in step with their inputs AT COMMIT TIME
(tools/git-hooks/pre-commit).

The recurring red: an input changes, the generator is forgotten (or run but its output left unstaged), and the
gate's `*-check` fails minutes later in the worktree (Joost 2026-11-23: "we keep running into that every time, how
about fixing that?" -- tiers-md-check, then bios-spec-index-check the same evening). For each generator below:
when the commit stages one of its inputs, regenerate the page and, if it differs from the staged copy, WRITE and
STAGE it -- the page is generated, never hand-edited, so there is nothing to lose. If a generator refuses (e.g.
tier_table.py on a stale knife pin after a ROM change) the commit goes ahead with a warning: the gate's check stays
the check of record, and blocking here would hide the real cause. Generators read the WORKING tree; the gate, which
builds from the commit, is what proves the pair.

ROM sources (basic/kwidx.inc) are deliberately NOT here: a ROM byte is rebuilt on purpose, not by a hook.
"""
import os
import re
import subprocess
import sys

# (name, staged-path pattern that triggers it, the page, how to produce it)
#   produce = ("stdout", argv): the page is the command's stdout;  ("write", argv): the command writes the page itself
GENERATORS = [
    ("tier-status", re.compile(r"^(TODO\.md|basic/kwtable\.inc)$"), "docs/tier-status.md",
     ("stdout", ["tools/tier_table.py", "--keywords", "--markdown"])),
    ("bios-spec-index", re.compile(r"^(TODO\.md|docs/(bios|bdos|disk)/(?!index\.md$)[^/]+\.md|tools/entry_table\.py)$"),
     "docs/bios/index.md", ("write", ["tools/bios_spec_index.py", "--write"])),
]


def git(*a, **kw):
    return subprocess.run(["git", *a], capture_output=True, text=True, **kw)


def main():
    root = git("rev-parse", "--show-toplevel").stdout.strip()
    staged = git("diff", "--cached", "--name-only", cwd=root).stdout.split()
    for name, trig, page, (how, argv) in GENERATORS:
        if not any(trig.match(p) for p in staged):
            continue
        r = subprocess.run([sys.executable, os.path.join(root, argv[0]), *argv[1:]], cwd=root,
                           capture_output=True, text=True)
        if r.returncode != 0 or (how == "stdout" and not r.stdout.strip()):
            print(f"⚠️ precommit_generated: {name} refused (rc={r.returncode}); {page} NOT refreshed -- the gate's "
                  f"check will say why:\n{(r.stderr or r.stdout)[-600:]}", file=sys.stderr)
            continue
        if how == "stdout":
            with open(os.path.join(root, page), "w", encoding="utf-8") as fh:
                fh.write(r.stdout)
        if git("show", f":{page}", cwd=root).stdout == open(os.path.join(root, page), encoding="utf-8").read():
            continue
        git("add", page, cwd=root)
        print(f"precommit_generated: {page} regenerated and staged ({name}: an input was staged)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
