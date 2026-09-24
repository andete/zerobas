#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Carve scout: repeated ADJACENT INSTRUCTION PAIRS in main's own sources.

The route [[carve-routes-measured-shut]] records as the one clone_scout cannot
see (it prices label-BLOCKS). A pair repeated at n sites, b bytes long, folds
into `call helper` (3 B) at a net of n*(b-3) - (b+1). Excluded: pairs that touch
the stack or SP (push/pop/ret/ex (sp)/ld sp), relative jumps (jr/djnz), and
anything in a `*.inc` that sub/ also includes (a shared body is two ROMs).
Sizes are ESTIMATED from the mnemonic -- a ranking, never a price: build it.
"""
import os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main_files():
    out = []
    for l in open(os.path.join(ROOT, "basic", "main.asm")):
        m = re.match(r'\s*include\s+"([^"]+)"', l.split(";")[0])
        if m:
            out.append(m.group(1))
    shared = set()
    for f in os.listdir(os.path.join(ROOT, "sub")):
        if f.endswith(".asm"):
            for l in open(os.path.join(ROOT, "sub", f), errors="replace"):
                m = re.match(r'\s*include\s+"(basic/[^"]+)"', l.split(";")[0])
                if m:
                    shared.add(m.group(1))
    return [f for f in out if f.endswith(".asm") or f not in shared], shared

R8 = set("abcdehl")
def size(ins):
    t = ins.lower().replace(" ", "")
    op = re.match(r"[a-z]+", t).group(0)
    arg = t[len(op):]
    ix = "ix" in arg or "iy" in arg
    if op in ("call", "jp"):
        return 1 if arg in ("(hl)", "(ix)", "(iy)") else 3
    if op in ("ret", "nop", "scf", "ccf", "cpl", "daa", "exx", "di", "ei", "halt",
              "rla", "rra", "rlca", "rrca"):
        return 1
    if op in ("inc", "dec"):
        return (2 if ix else 1) + (1 if "+" in arg and ix else 0)
    if op == "ex":
        return 1
    if op in ("add", "adc", "sub", "sbc", "and", "or", "xor", "cp"):
        a = arg.split(",")[-1]
        if op in ("adc", "sbc") and arg.startswith("hl,"):
            return 2
        if op == "add" and arg[:2] in ("hl", "ix", "iy"):
            return 2 if ix else 1
        if a in R8 or a == "(hl)":
            return 1
        if ix:
            return 3
        return 2
    if op == "ld":
        d, _, s = arg.partition(",")
        if d in R8 and (s in R8 or s == "(hl)") or d == "(hl)" and s in R8:
            return 1
        if d == "a" and s in ("(bc)", "(de)") or s == "a" and d in ("(bc)", "(de)"):
            return 1
        if d in ("bc", "de", "hl", "sp") and s.startswith("("):
            return 3 if d == "hl" else 4
        if s in ("bc", "de", "hl", "sp") and d.startswith("("):
            return 3 if s == "hl" else 4
        if d in ("ix", "iy") or s in ("ix", "iy"):
            return 4
        if ix:
            return 3 if (d in R8 or s in R8) else 4
        if d in ("bc", "de", "hl"):
            return 3
        if d == "a" and s.startswith("(") or s == "a" and d.startswith("("):
            return 3
        if d == "(hl)":
            return 2
        return 2
    if op in ("bit", "set", "res", "rl", "rr", "rlc", "rrc", "sla", "sra", "srl"):
        return 4 if ix else 2
    if op in ("in", "out"):
        return 2
    if op in ("ldir", "lddr", "ldi", "ldd", "cpir", "cpi", "neg", "im", "reti", "retn"):
        return 2
    return None

BAD = re.compile(r"^(push|pop|ret|reti|retn|jr|djnz|rst|halt)\b|\bsp\b|^ex\s*\(sp\)|^db\b|^dw\b|^ds\b|^defs\b|^defb\b|^defw\b|^if\b|^endif\b|^else\b|^org\b|^equ\b", re.I)

def main():
    files, shared = main_files()
    pairs = collections.defaultdict(list)
    for f in files:
        p = os.path.join(ROOT, f)
        prev = None
        for n, raw in enumerate(open(p, errors="replace"), 1):
            line = raw.split(";")[0].rstrip()
            if not line.strip():
                continue
            if re.match(r"^[A-Za-z_.][\w.]*:?", line) and not line[0].isspace():
                prev = None           # a label: a pair may not straddle an entry
                rest = re.sub(r"^[A-Za-z_.][\w.]*:?", "", line).strip()
                if not rest or re.match(r"equ\b", rest, re.I):
                    continue
                line = " " + rest
            ins = re.sub(r"\s+", " ", line.strip())
            if re.match(r"(include|if|else|endif|macro|endm)\b", ins, re.I):
                prev = None
                continue
            if BAD.search(ins) or size(ins) is None:
                prev = None           # excluded or unsizable: breaks the chain
                continue
            if prev is not None:
                a, b = prev[0], ins
                if not re.match(r"^jp\b(?!\s*\()", a, re.I):   # nothing may follow an unconditional jp
                    pairs[(a.lower(), b.lower())].append(f"{f}:{n}")
            prev = (ins, n) if size(ins) is not None else None
    rows = []
    for (a, b), sites in pairs.items():
        if len(sites) < 3:
            continue
        sz = size(a) + size(b)
        tail = re.match(r"^jp\b", b)
        # a pair ending in `jp X` folds as `jp helper` at each site: saves size(a)
        net = len(sites) * (size(a) if tail else sz - 3) - (sz + (0 if tail else 1))
        if net > 0:
            rows.append((net, len(sites), sz, a, b, sites))
    rows.sort(reverse=True)
    print(f"main files scanned: {len(files)} (shared bodies excluded: {len(shared)})")
    print(f"{'net':>4} {'n':>3} {'b':>2}  pair")
    for net, n, sz, a, b, sites in rows[:25]:
        print(f"{net:4} {n:3} {sz:2}  {a}  /  {b}    e.g. {', '.join(sites[:3])}")
    if not rows:
        print("no pair nets > 0")
    return 0

if __name__ == "__main__":
    sys.exit(main())
