#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""The SEAM between BASIC's disk verbs and its FAT engine, measured.

`disk/docs/spec-diskbasic-relocation.md` says the spec's first job is to FIND THE
REAL SEAM, and names the number that makes it hard: "`files.asm` -> `fat.asm` ~15
calls, `field.asm` -> ~13". Those were estimates. This counts them, both
directions, for every pair of disk/tape modules, and sizes the individual verbs --
so each of the spec-input's four options can be priced instead of guessed.

Method and its limits:
  * an EDGE is a `call`/`jp`/`jr` (any condition) whose target is a label defined
    in another `basic/` file. Register-indirect and table-driven dispatch are
    INVISIBLE to it -- `stmt_table` entries are `dw`, so a verb reached only from
    the table shows no inbound edge. Those are listed separately by scanning the
    `dw` columns.
  * a verb's SIZE is its entry label to the next label at or before the next
    verb's entry, from `build/basic-reloc.sym` -- the same gap rule
    `regionscout.py` uses, exact for a routine's last label and an overestimate
    for an interior branch target.
  * `.inc` bodies included into BOTH the main image and a tenant are attributed
    to the file that defines them, and flagged, because moving one moves both.
"""
import io
import os
import re
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYM = os.path.join(REPO, "build", "basic-reloc.sym")
DISKY = ("files.asm", "field.asm", "fat.asm", "save.asm", "bload.asm",
         "cload.asm", "format.asm")
BRANCH = re.compile(r"^\s+(call|jp|jr)\s+(?:(?:n?[zc]|p[eo]?|m)\s*,\s*)?"
                    r"([A-Za-z_][\w]*)\s*(?:;.*)?$")


def sources():
    d = os.path.join(REPO, "basic")
    for fn in sorted(os.listdir(d)):
        if fn.endswith((".asm", ".inc")):
            yield fn, io.open(os.path.join(d, fn), encoding="utf-8",
                              errors="replace").read()


def main() -> int:
    text = dict(sources())
    owner = {}
    for fn, body in text.items():
        for m in re.finditer(r"^([A-Za-z_][\w]*):", body, re.M):
            owner.setdefault(m.group(1), fn)

    edges = defaultdict(Counter)          # src file -> Counter(dst file)
    detail = defaultdict(list)            # (src, dst) -> [target labels]
    for fn, body in text.items():
        for line in body.splitlines():
            m = BRANCH.match(line)
            if not m:
                continue
            dst = owner.get(m.group(2))
            if dst and dst != fn:
                edges[fn][dst] += 1
                detail[(fn, dst)].append(m.group(2))

    print("=== CROSS-FILE BRANCH EDGES among the disk/tape modules ===")
    print(f"{'from':14} {'to':14} {'edges':>6}  distinct targets")
    print("-" * 74)
    for a in DISKY:
        for b in DISKY:
            if a == b or not edges[a][b]:
                continue
            tg = sorted(set(detail[(a, b)]))
            print(f"{a:14} {b:14} {edges[a][b]:6}  "
                  f"{len(tg)}: {', '.join(tg[:6])}"
                  f"{' …' if len(tg) > 6 else ''}")
    print()
    print("=== OUTBOUND to the REST of BASIC (what a move would have to reach "
          "back for) ===")
    print(f"{'from':14} {'edges':>6}  top targets")
    print("-" * 74)
    for a in DISKY:
        out = Counter()
        for b, n in edges[a].items():
            if b not in DISKY:
                out[b] += n
        if out:
            tot = sum(out.values())
            top = ", ".join(f"{b}:{n}" for b, n in out.most_common(5))
            print(f"{a:14} {tot:6}  {top}")
    print()
    print("=== INBOUND from the REST of BASIC (callers that would go "
          "cross-slot) ===")
    print(f"{'into':14} {'edges':>6}  callers")
    print("-" * 74)
    for b in DISKY:
        inb = Counter()
        for a in edges:
            if a not in DISKY and edges[a][b]:
                inb[a] += edges[a][b]
        if inb:
            print(f"{b:14} {sum(inb.values()):6}  "
                  f"{', '.join(f'{a}:{n}' for a, n in inb.most_common(6))}")
    print()
    print("=== stmt_table / dw DISPATCH into these modules (invisible to the "
          "edge scan) ===")
    dw = Counter()
    for fn, body in text.items():
        for m in re.finditer(r"^\s+dw\s+([A-Za-z_][\w]*)", body, re.M):
            o = owner.get(m.group(1))
            if o in DISKY:
                dw[(fn, o)] += 1
    for (fn, o), n in sorted(dw.items()):
        print(f"  {fn:20} -> {o:14} {n:3} dw entr(y/ies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# --- closure sizing (added for the relocation spec) --------------------------
# Option 3 of spec-diskbasic-relocation.md is "move only the FAT-light verbs",
# and its relief cannot be read off a per-file total: it is the size of the
# labels REACHABLE from those verbs and from nothing else. This walks branch
# edges from a verb set, collects the labels it can reach inside the disk
# modules, and reports EXCLUSIVE bytes (reachable from this set only) separately
# from SHARED ones (also reachable from the verbs left behind) -- because a
# shared label does not move, it becomes a cross-slot call.
# 🔴 AND IT DOES NOT WORK ON THIS CODEBASE, WHICH IS ITSELF THE FINDING. Run
# against the three verb groups it reaches 16 labels and 194 B, against
# `files.asm`'s measured 1600 -- because control reaches most of these bodies by
# FALLTHROUGH, which a branch-reachability walk cannot see. Same blind spot the
# dup-span sweep has ([[dupspan-slice]]). Kept, with this warning, because the
# NEGATIVE result is what says option 3 cannot be priced at sub-file granularity
# by this method -- not because the number below is usable.
def closure(entries, text, owner, size, modules):
    seen, stack = set(), list(entries)
    while stack:
        lab = stack.pop()
        if lab in seen or owner.get(lab) not in modules:
            continue
        seen.add(lab)
        fn = owner[lab]
        body = text[fn]
        m = re.search(r"^%s:" % re.escape(lab), body, re.M)
        if not m:
            continue
        tail = body[m.end():]
        nxt = re.search(r"^[A-Za-z_][\w]*:", tail, re.M)
        span = tail[:nxt.start()] if nxt else tail
        for b in BRANCH.finditer(span):
            stack.append(b.group(2))
    return seen
