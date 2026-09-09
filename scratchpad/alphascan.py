#!/usr/bin/env python3
"""How far are the 19 hand-written alphabets from the ROM's own messages?"""
import ast, glob, os, sys
sys.path.insert(0, "probes/lib")
import errmsg_alphabet as EA
LOWER = {m.lower(): m for m in EA.MESSAGES}

for p in sorted(glob.glob("probes/basic/*.py")) + sorted(glob.glob("probes/**/*.py", recursive=True)):
    src = open(p, encoding="utf-8", errors="replace").read()
    if '"Type mismatch"' not in src and "'Type mismatch'" not in src:
        continue
    try:
        t = ast.parse(src)
    except SyntaxError:
        continue
    lits = set()
    for n in ast.walk(t):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if v.lower() in LOWER or (" " in v and v[:1].isalpha() and len(v) < 40):
                lits.add(v)
    case = sorted(v for v in lits if v not in EA.MESSAGES and v.lower() in LOWER)
    unk = sorted(v for v in lits if v.lower() not in LOWER)
    has = "<UNREADABLE" in src
    print(f"{os.path.relpath(p):<46} UNREADABLE={'yes' if has else 'NO '}  "
          f"case-drift={len(case)}")
    for v in case:
        print(f"      \U0001f534 {v!r} -> ROM says {LOWER[v.lower()]!r}")
