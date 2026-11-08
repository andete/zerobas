#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Which disk.rom routines in an address range can MOVE to a hole elsewhere?

A routine is movable when (1) nothing falls into it -- the instruction before its
label is an unconditional ret / jp / jr, (2) every reference to its label is a
`call`, a `jp`, or a `dw` (no `jr` / `djnz`, which would go out of reach), (3)
it ends -- before the next top-level label -- in an unconditional ret / jp / jr,
and (4) no label INSIDE it (a top-level label it falls into) is referenced at
all. Size comes from build/disk.sym (the next symbol's address). It prints the
candidates with their size, the file:line, and every reference, so each one can
be read before it is moved; it moves nothing.

    python3 scratchpad/movescout.py LO HI      e.g. 782B 7F7C
"""
import glob, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
lo, hi = (int(x, 16) for x in sys.argv[1:3])

sym = {}
for line in open(os.path.join(REPO, "build", "disk.sym")):
    p = line.split()
    if len(p) >= 2:
        try:
            sym[p[0].rstrip(":")] = int(p[-1].rstrip("H").lstrip("$"), 16)
        except ValueError:
            pass
addrs = sorted(set(sym.values()))

src = {}
for f in glob.glob(os.path.join(REPO, "disk", "*.asm")) + glob.glob(os.path.join(REPO, "basic", "*.inc")):
    src[f] = open(f, errors="replace").read().splitlines()

LAB = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
END = re.compile(r"^\s+(ret|jp|jr|reti)\b(?!\s+(nz|z|nc|c|po|pe|p|m)\s*,)", re.I)


def code(l):
    return l.split(";", 1)[0].rstrip()


def refs(name):
    out = []
    pat = re.compile(r"\b%s\b" % re.escape(name))
    for f, lines in src.items():
        for i, l in enumerate(lines, 1):
            c = code(l)
            if pat.search(c) and not LAB.match(c):
                out.append((os.path.relpath(f, REPO), i, c.strip()))
    return out


for f, lines in src.items():
    if not f.endswith(".asm"):
        continue
    for i, l in enumerate(lines):
        m = LAB.match(l)
        if not m or m.group(1) not in sym:
            continue
        name = m.group(1)
        a = sym[name]
        if not (lo <= a < hi) or name.startswith(("k_", "__")):
            continue
        # (1) nothing falls in: the previous code line ends unconditionally
        j = i - 1
        while j >= 0 and not code(lines[j]).strip():
            j -= 1
        if j >= 0 and not END.match(code(lines[j])) and not code(lines[j]).strip().startswith("ds"):
            continue
        # (3) it ends unconditionally before the next top-level label; (4) inner labels unreferenced
        k, last, inner_ok = i + 1, None, True
        while k < len(lines) and not LAB.match(lines[k]):
            if code(lines[k]).strip():
                last = code(lines[k])
            k += 1
        if last is None or not END.match(last):
            continue
        nxt = [x for x in addrs if x > a]
        size = (nxt[0] - a) if nxt else None
        rs = refs(name)
        if any(re.search(r"\b(jr|djnz)\b", c) for _, _, c in rs):
            continue
        if not rs:
            continue
        print(f"{size:3} B  {name:28} {os.path.relpath(f, REPO)}:{i + 1}  ${a:04X}")
        for r in rs:
            print(f"        {r[0]}:{r[1]}  {r[2]}")
