#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Repoint markdown links whose target is a source file that no longer exists.

Three remedies, chosen per target:
  MOVED    the code moved into disk.rom (D-ROMSIZE step 1): the old name stays as
           plain text with the deleting commit, and a link to the new home.
  DELETED  no new home: the old name as plain text with the deleting commit.
  RELPATH  the file exists; the link's relative path was wrong: fix the path.
Refuses if any planned replacement does not match exactly once on its line.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

MOVED = {   # dead target (repo-relative) -> (deleting commit, new home file, symbol)
    "basic/randio-body.inc": ("c577b59c", "disk/kernel.asm", "hk_dget"),
    "sub/randio.asm": ("c577b59c", "disk/kernel.asm", "hk_dget"),
    "sub/dirverb.asm": ("347452e0", "disk/kernel.asm", "hk_dsk"),
    "sub/fiawalk.asm": ("21f76704", "disk/kernel.asm", "hk_dpbsave"),
    "basic/fiawalked-body.inc": ("21f76704", "disk/kernel.asm", "hk_dpbsave"),
}
DELETED = {  # dead target -> deleting commit
    "basic/lineedit-body.inc": "b58f34b7",
    "basic/main-reloc.asm": "19e8bfde",
    "probes/basic/basic_probe_cont.py": "5c300c74",
    "probes/lib/savestate_check.py": "e50c2331",
}
RELPATH = {  # resolved dead path -> the file it meant (repo-relative)
    "disk/docs/kernel.asm": "disk/kernel.asm",
    "docs/tokenise.inc": "basic/tokenise.inc",
}
UPSTREAM = {  # resolved dead path -> plain-text wording (never in this tree)
    "disk/reference/cbios/disk/disk.asm": "upstream C-BIOS `disk/disk.asm`, not in this tree",
}

LINK = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)\)")


def rel(frm_doc, target):
    return os.path.relpath(target, os.path.dirname(frm_doc) or ".")


def code(label):
    return label if label.startswith("`") else f"`{label}`"


def candidates(target):
    """The repo-relative readings of a link target: as written, and from the root."""
    path = re.sub(r":\d+(-\d+)?$", "", target.split("#")[0])
    return path


files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True).stdout.split()
plan = []  # (file, line_no, old, new)
for f in files:
    lines = open(f, encoding="utf-8").read().split("\n")
    for n, line in enumerate(lines, 1):
        for m in LINK.finditer(line):
            label, target = m.group(1), m.group(2)
            if re.match(r"^(https?:|mailto:|#)", target):
                continue
            path = candidates(target)
            resolved = os.path.normpath(os.path.join(os.path.dirname(f), path))
            rootread = os.path.normpath(path.replace("../", ""))
            if os.path.exists(resolved):
                continue
            key = next((k for k in (resolved, rootread)
                        if k in MOVED or k in DELETED or k in RELPATH or k in UPSTREAM), None)
            if key is None:
                continue
            old = m.group(0)
            if key in MOVED:
                sha, home, sym = MOVED[key]
                if label.startswith(":"):          # a bare line number after a named link
                    new = f"`{label}`"
                else:
                    new = f"{code(label)} (deleted by {sha}; now [`{sym}`]({rel(f, home)}))"
            elif key in DELETED:
                new = f"{code(label)} (deleted by {DELETED[key]})"
            elif key in RELPATH:
                suffix = target[len(target.split("#")[0].split(":")[0]):] if ":" in target else ""
                new = f"[{label}]({rel(f, RELPATH[key])}{suffix})"
            else:
                new = f"{code(label)} ({UPSTREAM[key]})"
            plan.append((f, n, old, new))

for f, n, old, new in plan:
    print(f"{f}:{n}\n    - {old}\n    + {new}")
if "--apply" not in sys.argv:
    print(f"\n{len(plan)} link(s); dry run, pass --apply")
    sys.exit(0)
by_file = {}
for f, n, old, new in plan:
    by_file.setdefault(f, []).append((n, old, new))
for f, edits in by_file.items():
    lines = open(f, encoding="utf-8").read().split("\n")
    for n, old, new in edits:
        if lines[n - 1].count(old) != 1:
            sys.exit(f"REFUSED {f}:{n}: {old!r} occurs {lines[n - 1].count(old)}x on its line")
        lines[n - 1] = lines[n - 1].replace(old, new)
    open(f, "w", encoding="utf-8").write("\n".join(lines))
print(f"\napplied {len(plan)} link(s) in {len(by_file)} file(s)")
