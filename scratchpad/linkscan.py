#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""linkscan -- count markdown relative links that do not resolve from their own file (2026-11-23 scan).

A target `path:123` / `path:12-34` resolves if `path` does. Fenced code and inline code are skipped.

    python3 scratchpad/linkscan.py [GLOB ...]      # default: every tracked *.md
    python3 scratchpad/linkscan.py --root-fixable  # only links that DO resolve from the repo root
"""
import collections
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK = re.compile(r"\]\(<?([^)>#\s]+)")


def strip(s):
    s = re.sub(r"```.*?```", "", s, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", s)


def target_path(t):
    return re.sub(r":\d+(?:-\d+)?$", "", t)


def broken(f, text=None):
    text = open(os.path.join(ROOT, f), errors="replace").read() if text is None else text
    out = []
    for m in LINK.finditer(strip(text)):
        t = m.group(1)
        if re.match(r"[a-z]+:", t) or t.startswith("/"):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(ROOT, os.path.dirname(f), target_path(t)))):
            out.append(t)
    return out


def main(argv):
    rootfix = "--root-fixable" in argv
    pats = [a for a in argv if not a.startswith("--")]
    os.chdir(ROOT)
    files = (sorted({f for p in pats for f in glob.glob(p, recursive=True)}) if pats else
             subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True).stdout.split())
    by = collections.Counter()
    n = 0
    for f in files:
        for t in broken(f):
            if rootfix and not os.path.exists(target_path(t)):
                continue
            by[os.path.dirname(f) or "."] += 1
            n += 1
    print(f"linkscan: {n} {'root-fixable ' if rootfix else ''}broken link(s) in {len(files)} file(s)")
    for d, k in by.most_common(20):
        print(f"  {k:6d}  {d}")


if __name__ == "__main__":
    main(sys.argv[1:])
