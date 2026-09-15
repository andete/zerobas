#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CHANPRICE -- what would it cost to move the CHANNEL verbs into disk.rom?

The FAT-light four were cheap for a reason that is easy to miss: each body was
"evaluate one name, run one dirverb op, return a disposition". Three call-back
sites, all of them ONCE PER STATEMENT. The channel verbs are not obviously that
shape -- ex_close LOOPS over a channel list calling `eval` and four channel
helpers per iteration -- so this counts the sites before anything moves, the way
0b priced the call itself before any verb followed it.

WHAT IT MEASURES, per verb, from the SOURCE and the symbol file:
  * every `call`/`jp`/`jr` target in the verb's span;
  * which of those resolve to main PAGE 1 (a call-back, 7 B and 0.156 ms) versus
    page 0 (free, page 0 stays mapped) versus RAM (free, always mapped);
  * whether a page-1 site sits inside a BACKWARD branch -- i.e. in a loop, where
    the per-call cost multiplies by the iteration count.

⚠️ IT IS A STATIC COUNT AND SAYS SO. A span "belongs to" the verb that opens it
only if nothing else jumps in (the relocation-seam spec's own caveat), and a
backward branch is a necessary but not sufficient sign of a loop. This ranks
candidates; it does not authorise a move.
"""
from __future__ import annotations
import os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "basic", "files.asm")
SYM = os.path.join(REPO, "build", "basic-reloc.sym")
PAGE1 = 0x4000

# the channel group, from disk/docs/spec-diskbasic-relocation-seam.md §4
VERBS = ["ex_open", "ex_close", "ex_maxfiles", "ex_merge", "ex_line", "ex_input"]

CALL = re.compile(r"^\s+(call|jp|jr)\s+(?:[a-z]{1,2},)?([A-Za-z_]\w*)\s*(?:;.*)?$")
LABEL = re.compile(r"^([A-Za-z_]\w*):")


def load_syms():
    out = {}
    for line in open(SYM):
        m = re.match(r"(\S+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line.strip())
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def spans(lines):
    """label -> (first line index, last line index before the next top label)."""
    marks = [(i, m.group(1)) for i, l in enumerate(lines) if (m := LABEL.match(l))]
    out = {}
    for n, (i, name) in enumerate(marks):
        out[name] = (i, marks[n + 1][0] if n + 1 < len(marks) else len(lines))
    return out, [name for _, name in marks]


def main() -> int:
    if not os.path.exists(SYM):
        print(f"INSTRUMENT FAULT: no {SYM} -- run `make basic-reloc` first")
        return 2
    syms = load_syms()
    lines = open(SRC).read().splitlines()
    sp, order = spans(lines)

    print(f"{'verb':14s} {'bytes':>6s} {'sites':>6s} {'page1':>6s} {'looped':>7s}  distinct page-1 callees")
    for verb in VERBS:
        if verb not in sp:
            print(f"{verb:14s} (absent -- already moved?)")
            continue
        # the verb's own span plus every local label it falls into, up to the
        # next VERB label: the relocation-seam partition's own unit.
        start = order.index(verb)
        end = start + 1
        while end < len(order) and order[end] not in VERBS:
            end += 1
        lo = sp[order[start]][0]
        hi = sp[order[end - 1]][1]
        local = set(order[start:end])
        sites, p1, looped = 0, {}, 0
        for i in range(lo, hi):
            m = CALL.match(lines[i].split(";", 1)[0] + "\n")
            if not m:
                continue
            tgt = m.group(2)
            if tgt in local:            # an internal branch, not a dependency
                if tgt in sp and sp[tgt][0] < i:
                    pass                # backward internal branch = a loop marker
                continue
            sites += 1
            a = syms.get(tgt)
            if a is None or a < PAGE1:
                continue                # page 0 or RAM: free from disk.rom
            p1[tgt] = p1.get(tgt, 0) + 1
            # inside a loop? any backward branch to a local label at or before here
            for j in range(lo, i):
                mm = CALL.match(lines[j].split(";", 1)[0] + "\n")
            back = any((mb := CALL.match(lines[k].split(";", 1)[0] + "\n"))
                       and mb.group(2) in local and sp.get(mb.group(2), (1 << 30,))[0] <= i <= k
                       for k in range(i, hi))
            if back:
                looped += 1
        # 🔴 PRINT "?" RATHER THAN 0 WHEN THE SPAN CANNOT BE RESOLVED. The first
        # cut silently reported ex_merge as 0 bytes, because the label after its
        # span is an `equ` with no address of its own -- and a 0 in a size column
        # reads as "free", which is the opposite of the truth.
        a0 = syms.get(verb)
        a1 = next((syms[order[k]] for k in range(end, len(order))
                   if order[k] in syms and syms[order[k]] > (a0 or 0)), None)
        nb = f"{a1 - a0:6d}" if (a0 and a1) else "     ?"
        print(f"{verb:14s} {nb} {sites:6d} {sum(p1.values()):6d} {looped:7d}  "
              + ", ".join(sorted(p1)[:6]) + ("..." if len(p1) > 6 else ""))
    print()
    print("A page-1 site costs 7 B and 0.156 ms EACH TIME IT RUNS. `looped` is the")
    print("count sitting inside a backward branch, where that multiplies by the")
    print("iteration count -- the FAT-light four had ZERO of those.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
