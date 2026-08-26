#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""TODO sweep 2026-08-26, tranche 6 — more gate/space items, checked statically.

Same rule as tranche 5: every check PRINTS ITS EVIDENCE, so "0 hits" cannot be
confused with "I looked in the wrong place".
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


def ev(k, t):
    print(f"    {k}: {t}")


# --- T-027472: the 4 B dup-span D-ONLIST created -----------------------------
head("T-027472", "esn_notlineno's discriminator is byte-identical to esn_p1's "
                 "countdown test four instructions above it (4 B)")
src = sh("grep", "-rn", "-A6", "esn_notlineno:", "basic/")
ev("esn_notlineno site", (src.strip().split("\n")[0] if src.strip() else "NOT FOUND"))
for lab in ("esn_notlineno", "esn_p1"):
    body = sh("grep", "-rn", "-A5", f"{lab}:", "basic/")
    ins = [l.split(":", 2)[-1].strip() for l in body.split("\n")
           if re.search(r"\b(dec de|ld a,d|or e|jr )", l)]
    ev(f"{lab} discriminator", " / ".join(ins[:4]) or "NOT FOUND")

# --- T-F184BB: CLEARPOOL=0 cannot be added to switch-build-check -------------
head("T-F184BB", "CLEARPOOL=0 is untested and cannot be added to switch-build-check")
sw = (ROOT / "tools" / "check_switch_builds.py").read_text()
names = sorted(set(re.findall(r"[\"']([A-Z][A-Z0-9_]{3,})[\"']", sw)))
ev("switches the gate flips", ", ".join(names) or "NONE")
ev("CLEARPOOL among them", "YES" if "CLEARPOOL" in names else "NO -- still untested")
sv = (ROOT / "basic" / "sysvars.inc").read_text()
m = [l.strip() for l in sv.split("\n") if "FPERR_MISSOP" in l]
ev("FPERR_MISSOP lines in basic/sysvars.inc", " | ".join(m[:4]) or "NOT FOUND")

# --- T-FE0E95: a wall figure hardcoded inside a gate --------------------------
head("T-FE0E95", "gen_resident_abi.py's LOW_CEILING was a hardcoded wall; the "
                 "CLASS (a wall figure inside a gate) is open")
hard = []
for f in sorted(ROOT.glob("tools/*.py")):
    for n, l in enumerate(f.read_text(errors="replace").split("\n"), 1):
        if re.search(r"(CEILING|WALL|_END|LIMIT)\s*=\s*0x[0-9A-Fa-f]{4}", l):
            hard.append(f"{f.name}:{n} {l.strip()[:70]}")
ev("hardcoded 16-bit ceiling/wall constants in tools/", f"{len(hard)}")
for h in hard[:8]:
    print(f"        {h}")

# --- T-466ECC: D-DUPSPAN2's 28 aliases have no per-site row set ---------------
head("T-466ECC", "D-DUPSPAN2 shipped 28 aliases with NO per-site row set")
al = sh("grep", "-rn", "equ ", "--include=*.asm", "--include=*.inc", "basic/", "sub/")
aliases = [l for l in al.split("\n") if re.search(r"^\S+:\d+:\s*\w+\s+equ\s+\w+\s*($|;)", l)]
ev("label-to-label `equ` aliases in basic/ + sub/", f"{len(aliases)}")
ev("a per-site row set for them",
   sh("grep", "-rln", "dupspan", "probes/").replace("\n", " ").strip() or "NONE in probes/")

# --- T-B34E15: a DEF FN string formal's shadow slot is not a GC root ---------
head("T-B34E15", "a DEF FN STRING formal's shadow slot is not a GC root")
gc = sh("grep", "-rn", "strheap_gc", "--include=*.asm", "--include=*.inc", "basic/", "sub/")
ev("strheap_gc sites", f"{len([l for l in gc.split(chr(10)) if l.strip()])}")
roots = sh("grep", "-rn", "-i", "-e", "gc root", "-e", "shadow", "basic/", "sub/")
hits = [l for l in roots.split("\n") if "deffn" in l.lower() or "shadow" in l.lower()]
ev("deffn/shadow mentions near the GC", f"{len(hits)}")
for h in hits[:5]:
    print(f"        {h.strip()[:100]}")
ev("a probe row naming the class",
   sh("grep", "-rln", "-i", "fnstr", "probes/").replace("\n", " ").strip() or "NONE")
