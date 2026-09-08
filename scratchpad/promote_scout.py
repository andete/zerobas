#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""PROMOTION — the page-1 carve route that has not been swept.

Route D (jp->jr) is measured out in main page 1 and the dup-span sweep is down to
its one unconvertible site, so the two items parked on page-1 bytes tonight
(D-PARTIAL's shadow, 6 B; the four do-nothing Disk-BASIC keywords, 9 B) are both
blocked on 3 B free. This asks the OTHER question.

Main page 0's low region ($2812-$3FFF) and main page 1 ($4000-$7FFF) are ONE
contiguous, freely inter-callable image; which region a routine lands in is
decided purely by where its `include` sits relative to `__MEAS_LOW_END` in
basic/main.asm. So moving a page-1 routine's SOURCE above that line moves its
BYTES out of page 1 at no cost -- provided nothing about it is position- or
adjacency-dependent. That is a 1:1 conversion of low free space into page-1 free
space, and the low region has the larger balance (14 B vs 3 B, 2026-09-08).

A block is reported PROMOTABLE only if all of these hold:

  * it is not ENTERED by fallthrough -- the instruction before its label is an
    unconditional terminator (shared `_is_terminator`, never a regex);
  * it is not LEFT by fallthrough -- its own last instruction is a terminator;
  * no `jr`/`djnz` crosses its boundary in either direction. `call`/`jp` are
    absolute and survive the move; a relative jump does not;
  * it emits no data (`db`/`dw`/`ds`) -- a table can be read by adjacency, which
    the fallthrough test cannot see;
  * its file is included exactly ONCE (pdfcb-body.inc is included three times,
    so its blocks exist at three addresses and none of them can move alone);
  * it is not inside an `IF`/`ENDIF`, whose arms a build switch selects.

\U0001f534 FALSIFICATION. `--selftest` plants four synthetic blocks -- one clean,
one entered by fallthrough, one with an INBOUND `jr`, one with an OUTBOUND `jr`
-- and asserts the clean one is reported and the other three are refused, each
for its OWN stated reason. Without it "0 promotable" is indistinguishable from a
sweep that parses nothing, which is this project's most-repeated instrument fault
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].
"""
from __future__ import annotations

import importlib.util
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
_spec = importlib.util.spec_from_file_location("ctc", "tools/check_tenant_closure.py")
ctc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctc)

SYM = "build/basic-reloc.sym"
_LBL = re.compile(r'^([A-Za-z_]\w*):')
_REL = re.compile(r'^\s*(jr|djnz)\s+(?:(?:nz|z|nc|c)\s*,\s*)?([A-Za-z_]\w*)', re.I)
_DATA = re.compile(r'^\s*(db|dw|ds|defb|defw|defs|incbin)\b', re.I)
_IFDIR = re.compile(r'^\s*(if|ifdef|ifndef|else|endif)\b', re.I)
_INCLUDE = re.compile(r'^\s*include\s+"([^"]+)"')


def strip(line: str) -> str:
    """Source line minus comment and label, left as bare mnemonic text."""
    s = line.split(';', 1)[0].rstrip()
    m = _LBL.match(s)
    if m:
        s = s[m.end():]
    return s.strip()


def page1_files():
    """Files included AFTER __MEAS_LOW_END, and how many times each is included."""
    main = open("basic/main.asm", encoding="utf-8").read().splitlines()
    cut = next(i for i, l in enumerate(main) if l.startswith("__MEAS_LOW_END:"))
    after, counts = [], {}
    for i, l in enumerate(main):
        m = _INCLUDE.match(l)
        if m:
            counts[m.group(1)] = counts.get(m.group(1), 0) + 1
            if i > cut:
                after.append(m.group(1))
    # nested includes count too (pdfcb-body.inc is pulled in from a page-1 file)
    for f in list(after):
        if os.path.exists(f):
            for l in open(f, encoding="utf-8"):
                m = _INCLUDE.match(l)
                if m:
                    counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return after, counts


def blocks_of(path):
    """[(label, [(lineno, raw)], in_if)] split at every top-level `label:`."""
    out, cur, depth = [], None, 0
    for n, raw in enumerate(open(path, encoding="utf-8"), 1):
        d = _IFDIR.match(raw)
        if d:
            k = d.group(1).lower()
            depth += 1 if k in ("if", "ifdef", "ifndef") else (-1 if k == "endif" else 0)
        m = _LBL.match(raw)
        if m:
            cur = [m.group(1), [], depth > 0]
            out.append(cur)
        if cur is not None:
            body = strip(raw)
            if body:
                cur[1].append((n, body))
    return out


def rel_edges(paths):
    """{target label -> {block label the jr/djnz sits in}} over the given files."""
    out = {}
    for fp in paths:
        blk = None
        for raw in open(fp, encoding="utf-8"):
            m = _LBL.match(raw)
            if m:
                blk = m.group(1)
            r = _REL.match(" " + strip(raw))
            if r:
                out.setdefault(r.group(2), set()).add(blk)
    return out


def units(blks, rel):
    """Merge blocks into CONTIGUOUS routines.

    \U0001f534 SPLITTING AT EVERY LABEL IS THE WRONG GRANULARITY, and the selftest
    is what said so. A routine with an internal branch target becomes two blocks;
    the first is then refused for an "outbound jr" and the second for an "inbound
    jr", and BOTH are movable -- together. So a block is merged with its
    neighbours whenever a relative jump or a fallthrough ties them, and the merge
    is expanded to the whole contiguous index range, because a source move takes a
    span of lines and not a set of them.
    """
    own = {b[0]: i for i, b in enumerate(blks)}
    lo = list(range(len(blks)))
    hi = list(range(len(blks)))
    changed = True
    while changed:
        changed = False
        for i, (lbl, body, _) in enumerate(blks):
            tie = set()
            if body and not ctc._is_terminator(body[-1][1]) and i + 1 < len(blks):
                tie.add(i + 1)                       # falls through into the next
            for _, c in body:
                r = _REL.match(" " + c)
                if r and r.group(2) in own:
                    tie.add(own[r.group(2)])         # relative jump inside the file
            for src in rel.get(lbl, ()):
                if src in own:
                    tie.add(own[src])                # relative jump INTO this block
            for j in tie:
                a, b = min(lo[i], lo[j], i, j), max(hi[i], hi[j], i, j)
                for k in range(a, b + 1):
                    if lo[k] != a or hi[k] != b:
                        lo[k], hi[k] = min(lo[k], a), max(hi[k], b)
                        changed = True
    seen, out = set(), []
    for i in range(len(blks)):
        key = (lo[i], hi[i])
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def refuse(path, blks, counts, syms, rel):
    """Yield (label, size, ok, reason) per contiguous routine in one page-1 file."""
    own = {b[0] for b in blks}
    for a, b in units(blks, rel):
        lbl = blks[a][0]
        body = [ln for k in range(a, b + 1) for ln in blks[k][1]]
        inner = {blks[k][0] for k in range(a, b + 1)}
        nxt = blks[b + 1][0] if b + 1 < len(blks) else None
        s_, e_ = syms.get(lbl), (syms.get(nxt) if nxt else None)
        size = (e_ - s_) if (s_ is not None and e_ is not None and e_ > s_) else None
        why = []
        if counts.get(path, 1) != 1:
            why.append(f"file included {counts.get(path)}x")
        if any(blks[k][2] for k in range(a, b + 1)):
            why.append("inside IF/ENDIF")
        if any(_DATA.match(" " + c) for _, c in body):
            why.append("emits data")
        if a == 0:
            why.append("first block in file (entry unknown)")
        elif not blks[a - 1][1] or not ctc._is_terminator(blks[a - 1][1][-1][1]):
            why.append("entered by fallthrough")
        if not body or not ctc._is_terminator(body[-1][1]):
            why.append("left by fallthrough")
        for k in range(a, b + 1):
            for src in rel.get(blks[k][0], ()):
                if src not in inner:
                    why.append(f"inbound jr from {src}")
                    break
        for _, c in body:
            r = _REL.match(" " + c)
            if r and r.group(2) not in inner:
                why.append(f"outbound {r.group(1).lower()} to {r.group(2)}")
                break
        yield lbl, size, (not why), "; ".join(sorted(set(why))) or "clean"


def selftest() -> int:
    import tempfile
    # \U0001f534 EACH REFUSAL MUST BE GENUINELY UNMERGEABLE. The first fixture
    # put `jr` between two blocks of the same file and expected a refusal; the
    # sweep MERGED them and reported the pair promotable, which is the correct
    # answer. An arm has to be un-mergeable to test the refusal at all.
    src = ("head:\n                ret\n"
           "clean:\n                ld a,1\n                ret\n"
           "pair_a:\n                jr z,pair_b\n                ret\n"
           "pair_b:\n                ret\n"
           "xfile:\n                ret\n"
           "outb:\n                jr far_away\n                ret\n"
           "tailfall:\n                ld a,9\n")
    other = "other:\n                jr xfile\n                ret\n"
    d = tempfile.mkdtemp()
    p = os.path.join(d, "t.asm")
    q = os.path.join(d, "u.asm")
    open(p, "w").write(src)
    open(q, "w").write(other)
    syms = {n: 0x5000 + 8 * i for i, n in enumerate(
        ["head", "clean", "pair_a", "pair_b", "xfile", "outb", "tailfall"])}
    blks = blocks_of(p)
    rel = rel_edges([p, q])
    got = {l: (ok, why) for l, _, ok, why in refuse(p, blks, {p: 1}, syms, rel)}
    fails = []
    if not got.get("clean", (False, "absent"))[0]:
        fails.append(f"clean was refused: {got.get('clean')}")
    if "pair_a" not in got:
        fails.append("pair_a/pair_b were not MERGED into one routine")
    elif not got["pair_a"][0]:
        fails.append(f"the merged jr-pair was refused: {got['pair_a'][1]}")
    if "pair_b" in got:
        fails.append("pair_b is still its own unit -- the merge did not happen")
    if got.get("head", (False, ""))[0]:
        fails.append("the file's first block was not refused")
    for lbl, want in (("xfile", "inbound jr"), ("outb", "outbound jr"),
                      ("tailfall", "left by fallthrough")):
        if lbl not in got:
            fails.append(f"{lbl} vanished into a merge -- arm is inert")
        elif got[lbl][0] or want not in got[lbl][1]:
            fails.append(f"{lbl} not refused for {want!r}: {got[lbl]}")
    if fails:
        print("\U0001f534 SELFTEST FAILED")
        for f in fails:
            print("   ", f)
        return 2
    print("selftest: a clean block IS reported; a jr-connected PAIR merges into "
          "one promotable routine; and first-in-file, cross-file inbound jr, "
          "outbound jr and left-by-fallthrough are each refused for their own "
          "stated reason ✅")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    syms = ctc.load_syms(SYM)
    files, counts = page1_files()
    rel = rel_edges([os.path.join('basic', f) for f in os.listdir('basic')
                     if f.endswith(('.asm', '.inc'))])
    rows, refused = [], 0
    for f in files:
        if not os.path.exists(f):
            continue
        for lbl, size, ok, why in refuse(f, blocks_of(f), counts, syms, rel):
            if ok and size:
                rows.append((size, lbl, f))
            else:
                refused += 1
    rows.sort(reverse=True)
    print(f"page-1 files: {len(files)}   blocks refused: {refused}   "
          f"PROMOTABLE: {len(rows)}")
    if not rows:
        print("\U0001f534 nothing promotable -- and --selftest says that is a "
              "reading, not a parse failure")
        return 1
    tot = 0
    print(f"\n{'size':>5}  {'label':28s} file")
    for size, lbl, f in rows[:40]:
        tot += size
        print(f"{size:5d}  {lbl:28s} {f}")
    print(f"\ntop-40 cumulative: {tot} B movable out of page 1 "
          f"(each byte also SPENDS one low-region byte)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
