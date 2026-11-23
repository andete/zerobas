#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""precommit_tiers -- keep docs/tier-status.md in step with TODO.md AT COMMIT TIME (tools/git-hooks/pre-commit).

The recurring red: TODO.md changes, `make tiers-md` is forgotten (or run but its output left unstaged), and the
gate's tiers-md-check fails minutes later in the worktree (Joost 2026-11-23: "we keep running into that every
time, how about fixing that?"). When a commit stages one of the generator's inputs (TODO.md, basic/kwtable.inc),
this regenerates the page and, if the staged copy differs, WRITES and STAGES it -- the generated file is never
hand-edited, so there is nothing to lose. If the generator refuses (e.g. a stale knife pin after a ROM change) the
commit goes ahead with a warning: the gate still has tiers-md-check, and blocking here would hide the real cause.
The generator reads the WORKING tree; a TODO.md with unstaged edits gets a page that matches those -- the gate,
which builds from the commit, is the check of record.
"""
import os
import subprocess
import sys

INPUTS = {"TODO.md", "basic/kwtable.inc"}
PAGE = "docs/tier-status.md"


def git(*a, **kw):
    return subprocess.run(["git", *a], capture_output=True, text=True, **kw)


def main():
    root = git("rev-parse", "--show-toplevel").stdout.strip()
    staged = set(git("diff", "--cached", "--name-only", cwd=root).stdout.split())
    if not staged & INPUTS:
        return 0
    r = subprocess.run([sys.executable, os.path.join(root, "tools", "tier_table.py"), "--keywords", "--markdown"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        print(f"⚠️ precommit_tiers: tier_table.py refused (rc={r.returncode}); {PAGE} NOT refreshed -- "
              "the gate's tiers-md-check will say why:\n" + r.stderr[-600:], file=sys.stderr)
        return 0
    indexed = git("show", f":{PAGE}", cwd=root).stdout
    if indexed == r.stdout:
        return 0
    with open(os.path.join(root, PAGE), "w", encoding="utf-8") as fh:
        fh.write(r.stdout)
    git("add", PAGE, cwd=root)
    print(f"precommit_tiers: {PAGE} regenerated and staged (a generator input was staged)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
