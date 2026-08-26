#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 5 — the SPACE and GATE items.

These assert facts about the tree and the battery, not about a running program,
so the instrument is a targeted static check plus today's measured walls and the
39/39 battery. Each check PRINTS ITS EVIDENCE; a check that finds nothing says so
rather than returning a bare boolean, because "0 hits" and "I looked in the wrong
place" read identically otherwise.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(*a):
    return subprocess.run(a, cwd=ROOT, capture_output=True, text=True).stdout


def head(tid, claim):
    print(f"\n=== {tid}\n    CLAIM: {claim}")


def ev(label, text):
    print(f"    {label}: {text}")


# --- T-035C3D: a tracked scratchpad script can hardcode the author's path -----
head("T-035C3D", "a TRACKED scratchpad/probes/tools script can hardcode "
                 "/Users/joost and nothing checks it")
tracked = [f for f in sh("git", "ls-files").split("\n")
           if f.endswith((".py", ".sh")) and
           f.split("/")[0] in ("scratchpad", "probes", "tools", "tests")]
hits = []
for f in tracked:
    try:
        for n, l in enumerate((ROOT / f).read_text(errors="replace").split("\n"), 1):
            if "/Users/joost" in l:
                hits.append((f, n, l.strip()[:80]))
    except OSError:
        pass
ev("denominator", f"{len(tracked)} tracked .py/.sh under scratchpad|probes|tools|tests")
ev("hits", f"{len(hits)} line(s) containing /Users/joost")
for f, n, l in hits[:12]:
    print(f"        {f}:{n}  {l}")
ev("gate", "grep for a checker naming this class: " +
   (", ".join(f for f in tracked if "abspath" in f or "userpath" in f) or "NONE FOUND"))

# --- T-64EB78: "122 hardcoded /tmp literals" ---------------------------------
head("T-64EB78", "122 hardcoded /tmp/... literals are outside the temp root")
out = sh("make", "temp-root-check")
ev("make temp-root-check", " / ".join(l.strip() for l in out.split("\n")
                                      if "pinned" in l or "PASS" in l))
allow = (ROOT / "tools" / "temp-root-allow.txt")
if allow.exists():
    lines = [l for l in allow.read_text().split("\n")
             if l.strip() and not l.startswith("#")]
    ev("tools/temp-root-allow.txt", f"{len(lines)} pinned entries")

# --- T-B5DD7F: latch-check has an EMPTY prerequisite list --------------------
head("T-B5DD7F", "latch-check is the one gate with no prerequisites")
mk = (ROOT / "Makefile").read_text().split("\n")
for i, l in enumerate(mk, 1):
    if re.match(r"^latch-check\s*:", l):
        ev(f"Makefile:{i}", repr(l))
targets = [(i, l) for i, l in enumerate(mk, 1)
           if re.match(r"^[a-z0-9-]+-check\s*:\s*$", l)]
ev("other *-check targets with an EMPTY prereq list",
   ", ".join(f"{l.split(':')[0]}@{i}" for i, l in targets) or "NONE")

# --- T-ABA845: five more non-atomic publishes -------------------------------
head("T-ABA845", "install-openmsx-machine.py still has 5 non-atomic "
                 'open(out,"w").write(...) publishes')
p = ROOT / "tools" / "install-openmsx-machine.py"
src = p.read_text().split("\n")
nonatomic = [(n, l.strip()[:90]) for n, l in enumerate(src, 1)
             if re.search(r'open\([^)]*,\s*["\']w["\']\)\s*\.write', l)]
atomic = [(n, l.strip()[:90]) for n, l in enumerate(src, 1)
          if "atomic" in l.lower() or "os.replace" in l]
ev("non-atomic write sites", f"{len(nonatomic)}: " +
   ", ".join(str(n) for n, _ in nonatomic))
ev("atomic-publish mentions", f"{len(atomic)}: " +
   ", ".join(str(n) for n, _ in atomic))

# --- T-2E1C86: no gate reads the boot banner --------------------------------
head("T-2E1C86", "no gate reads the boot banner; the item counts 34 gates")
g = sh("grep", "-rln", "-e", "zerobas version", "-e", "show_title", "probes", "tools")
ev("probes/tools mentioning the banner", g.replace("\n", " ").strip() or "NONE")
rg = (ROOT / "tools" / "run_gates.py").read_text()
gates = rg.split('GATES = """')[1].split('"""')[0].split()
ev("battery size today", f"{len(gates)} gates (the item says 34)")

# --- T-E27BD0: the tape patch pair is unguarded ------------------------------
head("T-E27BD0", "patch-freshness-check covers only the MAIN pair; the tape "
                 "pair is unguarded and currently FRESH")
chk = (ROOT / "tools" / "check_patch_freshness.py").read_text()
ev("PAIR in the checker", re.search(r"PAIR = \[.*?\]", chk, re.S).group(0))
ev("tape pair tracked?", sh("git", "ls-files", "tape/zerobas-tape-msx1.ips",
                            "tape/zerobas-tape-msx1.bps").replace("\n", " ").strip())
ev("tape pair dirty in the worktree?",
   sh("git", "status", "--porcelain", "--", "tape/").strip() or "clean")
