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

THE ROADMAP IS ONE FILE PER ITEM (2026-11-23, tools/todo_items.py): todo/open/<id>.md, todo/done/<id>.md, and
TODO.md's stub lines generated from them. So (1) an item file is an input of the two generators that read the
roadmap; (2) when any todo/**.md is staged, the STAGED TODO.md's stub lines are rewritten from the staged item files
(`todo_items.stub_line`) -- index only, the working TODO.md gets the same stub rewrite, its prose is never staged by
this; (3) the commit is REFUSED (exit 1) when `todo_items.check()`, run on the STAGED tree, reports a problem -- a
stub naming a missing file, an item file with no stub, a box that does not match its folder. Unlike a generator's
refusal this one blocks: a commit that loses an item, or carries one nothing indexes, is the defect itself.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
# temp-root-check: every bare tempfile call here lands under the /tmp/zerobas root
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import probe_tmp  # noqa: E402,F401 -- sets tempfile.tempdir


# (name, staged-path pattern that triggers it, the page, how to produce it)
#   produce = ("stdout", argv): the page is the command's stdout;  ("write", argv): the command writes the page itself
ITEM = r"todo/(open|done)/[^/]+\.md"
GENERATORS = [
    ("tier-status", re.compile(r"^(TODO\.md|" + ITEM + r"|basic/kwtable\.inc)$"), "docs/tier-status.md",
     ("stdout", ["tools/tier_table.py", "--keywords", "--markdown"])),
    ("bios-spec-index", re.compile(r"^(TODO\.md|" + ITEM + r"|docs/(bios|bdos|disk)/(?!index\.md$)[^/]+\.md"
                                   r"|tools/entry_table\.py)$"),
     "docs/bios/index.md", ("write", ["tools/bios_spec_index.py", "--write"])),
    ("kw-spec-index", re.compile(r"^(docs/keywords/(?!spec-index\.md$)[^/]+\.md|tools/kw_spec_index\.py)$"),
     "docs/keywords/spec-index.md", ("write", ["tools/kw_spec_index.py", "--write"])),
]


def git(*a, **kw):
    return subprocess.run(["git", *a], capture_output=True, text=True, **kw)


TODO_TRIGGER = re.compile(r"^(TODO\.md|todo/.+\.md)$")


def _todo_items(root):
    sys.path.insert(0, os.path.join(root, "tools"))
    import todo_items
    return todo_items


def todo_index(root):
    """Rewrite the STAGED TODO.md's stub lines from the STAGED item files; the working TODO.md the same way."""
    ti = _todo_items(root)
    r = git("show", ":TODO.md", cwd=root)
    if r.returncode != 0:
        return
    lines = r.stdout.split("\n")
    for i, line in enumerate(lines):
        m = ti.STUB.search(line)
        if not m:
            continue
        rel = f"todo/{m.group(1)}/{m.group(2)}.md"
        t = git("show", f":{rel}", cwd=root)
        if t.returncode == 0:      # a stub with no staged file: todo_check() refuses it below
            lines[i] = ti.stub_line(ti.Item(m.group(1), m.group(2), t.stdout))
    new = "\n".join(lines)
    if new != r.stdout:
        sha = subprocess.run(["git", "hash-object", "-w", "--stdin"], input=new, capture_output=True, text=True,
                             cwd=root).stdout.strip()
        git("update-index", "--cacheinfo", f"100644,{sha},TODO.md", cwd=root)
        print("precommit_generated: TODO.md stub lines regenerated from the staged item files and staged (todo-index)",
              file=sys.stderr)
    try:
        ti.write_index()           # the working copy: stub lines only, never staged from here
    except OSError:
        pass                       # a stub whose file is gone: todo_check() below names it


def todo_check(root):
    """todo_items.check() on the STAGED tree (TODO.md + todo/ checked out of the index into a temp dir)."""
    ti = _todo_items(root)
    tmp = tempfile.mkdtemp(prefix="precommit-todo-")
    try:
        paths = ["TODO.md"] + git("ls-files", "--cached", "--", "todo", cwd=root).stdout.split()
        subprocess.run(["git", "checkout-index", f"--prefix={tmp}/", "--", *paths], cwd=root, capture_output=True)
        saved = ti.ROOT, ti.TODO, ti.DIR
        ti.ROOT, ti.TODO, ti.DIR = tmp, os.path.join(tmp, "TODO.md"), os.path.join(tmp, "todo")
        try:
            return ti.check() if os.path.isfile(ti.TODO) else []
        finally:
            ti.ROOT, ti.TODO, ti.DIR = saved
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    root = git("rev-parse", "--show-toplevel").stdout.strip()
    staged = git("diff", "--cached", "--name-only", cwd=root).stdout.split()
    if any(TODO_TRIGGER.match(p) for p in staged):
        todo_index(root)
        bad = todo_check(root)
        if bad:
            print("🔴 precommit_generated: COMMIT REFUSED -- the staged roadmap's stubs and item files disagree "
                  "(tools/todo_items.py --check):", file=sys.stderr)
            for b in bad:
                print("   " + b, file=sys.stderr)
            print("   stage the missing item file / stub (or `git rm` the stray), then commit again.", file=sys.stderr)
            return 1
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
