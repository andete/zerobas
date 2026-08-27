#!/usr/bin/env python3
"""Scout: a literal BOUND TO A NAME that the build already resolves.

Founding defect (D-DUPSPAN2 §5.2): `LOW_CEILING = 0x3FE5` in
tools/gen_resident_abi.py, under a comment naming `__MEAS_LOW_END`.  The build
measures that label on every run; the literal never tracked it, 65 B stale.

SHAPE, not "any number near any word": an ASSIGNMENT whose ANCHOR is a build
symbol.  The anchor is either
  (a) the assigned name itself      `TXTTAB = 0xF676`
  (b) a symbol named in the same line's comment or the comment block above it
      `LOW_CEILING = 0x3FE5   # __MEAS_LOW_END`
Verdicts: DIFFER = the literal is already wrong.  AGREE = it is right today and
nothing makes it stay right.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_syms(path):
    syms, pat = {}, re.compile(r"^(\S+)\s+EQU\s+([0-9A-Fa-f]+)H", re.I)
    for line in open(os.path.join(ROOT, path)):
        m = pat.match(line.strip())
        if m:
            syms.setdefault(m.group(1), int(m.group(2), 16))
    return syms

SYMS = {}
for p in ("build/basic-reloc.sym", "build/sub.sym"):
    for k, v in load_syms(p).items():
        SYMS.setdefault(k, v)

# NAME = 0x1234 / $1234 / 1234h / 4660   (python), one literal, whole RHS
PY_ASSIGN = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"
    r"(0x([0-9A-Fa-f]{1,4})|\$([0-9A-Fa-f]{1,4})|([0-9A-Fa-f]{1,4})[hH]|(\d{1,5}))"
    r"\s*(?:#(.*))?$")
# name: equ $1234   (asm)
ASM_EQU = re.compile(
    r"^\s*([A-Za-z_.][A-Za-z0-9_.]*)\s*:?\s+equ\s+"
    r"(\$([0-9A-Fa-f]{1,4})|0x([0-9A-Fa-f]{1,4})|([0-9A-Fa-f]{1,4})[hH]|(\d{1,5}))"
    r"\s*(?:;(.*))?$", re.I)
IDENT = re.compile(r"\b(__?[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*)\b")

def value(m):
    hx = m.group(3) or m.group(4) or m.group(5)
    return int(hx, 16) if hx else int(m.group(6))

def sources():
    for d in ("tools", "probes"):
        for dp, _, fns in os.walk(os.path.join(ROOT, d)):
            for fn in sorted(fns):
                if fn.endswith(".py"):
                    yield os.path.relpath(os.path.join(dp, fn), ROOT), PY_ASSIGN, "#"
    for d in ("basic", "sub"):
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for dp, _, fns in os.walk(p):
            for fn in sorted(fns):
                if fn.endswith((".asm", ".inc")):
                    yield os.path.relpath(os.path.join(dp, fn), ROOT), ASM_EQU, ";"

RADIUS = int(os.environ.get("RADIUS", "3"))
assigns = 0
rows = []
for rel, pat, cmt in sources():
    lines = open(os.path.join(ROOT, rel), errors="replace").read().splitlines()
    for i, line in enumerate(lines):
        m = pat.match(line)
        if not m:
            continue
        assigns += 1
        name, val, trail = m.group(1), value(m), (m.group(7) or "")
        # comment block immediately above
        above = []
        for j in range(i - 1, max(-1, i - 1 - RADIUS), -1):
            s = lines[j].strip()
            if s.startswith(cmt):
                above.append(s)
            else:
                break
        anchors = []
        if name in SYMS:
            anchors.append((name, "name"))
        for n in IDENT.findall(trail + " " + " ".join(above)):
            if n in SYMS and n != name:
                anchors.append((n, "comment"))
        for n, how in anchors[:1]:          # one anchor per assignment
            rows.append((rel, i + 1, name, val, n, SYMS[n], how, line.strip()))

differ = [r for r in rows if r[3] != r[5]]
agree = [r for r in rows if r[3] == r[5]]
print(f"assignments scanned : {assigns}")
print(f"build symbols       : {len(SYMS)}")
print(f"anchored            : {len(rows)}   AGREE {len(agree)}   DIFFER {len(differ)}")
print()
for tag, rs in (("DIFFER", differ), ("AGREE", agree)):
    print(f"=== {tag} ({len(rs)})")
    for rel, ln, name, val, n, sv, how, src in rs:
        print(f"  {rel}:{ln}  {name}={val:#06x}  anchor {n}={sv:#06x} ({how})")
    print()
