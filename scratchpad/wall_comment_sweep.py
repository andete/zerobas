#!/usr/bin/env python3
"""The same class in ASM COMMENTS: `NAME equ <expr>   ; $XXXX ...`

The expression is authoritative -- the assembler resolves it.  The `$XXXX` in
the comment beside it is a HAND COPY, and nothing checks it.  When the base of
a chain moves, every downstream comment in the chain is silently wrong.
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(path):
    syms, pat = {}, re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.I)
    for line in open(os.path.join(ROOT, path)):
        m = pat.match(line.strip())
        if m: syms.setdefault(m.group(1), int(m.group(2), 16))
    return syms

TABLES = {"basic": load("build/basic-reloc.sym"), "sub": load("build/sub.sym")}

# NAME equ <anything>   ; ... $XXXX ...
ROW = re.compile(r"^\s*([A-Za-z_.][A-Za-z0-9_.]*)\s*:?\s+equ\s+([^;]+?)\s*;(.*)$", re.I)
ADDR = re.compile(r"\$([0-9A-Fa-f]{4})\b")

files = []
for d in ("basic", "sub"):
    for dp, _, fns in os.walk(os.path.join(ROOT, d)):
        for fn in sorted(fns):
            if fn.endswith((".asm", ".inc")):
                files.append(os.path.relpath(os.path.join(dp, fn), ROOT))

equ_rows = annotated = 0
agree, differ, unknown = [], [], []
for rel in sorted(files):
    for i, line in enumerate(open(os.path.join(ROOT, rel), errors="replace").read().splitlines()):
        m = ROW.match(line)
        if not m: continue
        equ_rows += 1
        name, expr, cmt = m.group(1), m.group(2).strip(), m.group(3)
        addrs = ADDR.findall(cmt)
        if not addrs: continue
        annotated += 1
        claimed = int(addrs[0], 16)          # the FIRST $XXXX in the comment
        vals = {t: tb[name] for t, tb in TABLES.items() if name in tb}
        if not vals:
            unknown.append((rel, i + 1, name, claimed, expr, cmt.strip()))
        elif claimed in vals.values():
            agree.append((rel, i + 1, name, claimed, vals))
        else:
            differ.append((rel, i + 1, name, claimed, vals, expr, cmt.strip()))

print(f"asm files            : {len(files)}")
print(f"`equ` rows with a ;  : {equ_rows}")
print(f"  ... annotated $XXXX: {annotated}")
print(f"AGREE {len(agree)}   DIFFER {len(differ)}   NOT-IN-SYM {len(unknown)}")
print()
print(f"=== DIFFER ({len(differ)}) — the comment claims an address the build does not give")
for rel, ln, name, claimed, vals, expr, cmt in differ:
    got = " ".join(f"{t}=${v:04X}" for t, v in vals.items())
    print(f"  {rel}:{ln}  {name}: comment says ${claimed:04X}, build says {got}")
    print(f"      equ {expr}   ; {cmt[:64]}")
print()
print(f"=== NOT-IN-SYM ({len(unknown)}) — name absent from both tables")
for rel, ln, name, claimed, expr, cmt in unknown[:40]:
    print(f"  {rel}:{ln}  {name} (${claimed:04X})   equ {expr}")
