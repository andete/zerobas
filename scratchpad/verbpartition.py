#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Price option 3 of the disk-BASIC relocation: bytes per VERB GROUP.

`spec-diskbasic-relocation-seam.md` §4 records why `seamscout.py`'s branch-
reachability closure cannot do this -- control reaches most of these bodies by
FALLTHROUGH, so a walk over explicit branches reads 194 B against `files.asm`'s
measured 1600. This does it the way that works for a contiguous, address-ordered
assembly file: sort the file's symbols by address, cut at each VERB ENTRY, and
attribute each span to the verb that opens it.

It cross-checks: the partition sums to 1600 B, the same figure `regionscout.py`
and `basic-reloc` give for `files.asm` in main page 1 on 2026-09-15.

⚠️ What the partition CANNOT say: a span between two verb entries belongs to the
verb that opens it only if no OTHER verb jumps into it. The shared helpers are
therefore listed separately -- every label called from OUTSIDE `files.asm` /
`field.asm` -- because those do not move with a verb; they stay, or they need a
provider-side entry point.
"""
import io, os, re
from collections import defaultdict
REPO=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sym={}
for line in io.open(os.path.join(REPO,"build","basic-reloc.sym"),errors="replace"):
    m=re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H",line)
    if m: sym[m.group(1)]=int(m.group(2),16)
owner={}; text={}
d=os.path.join(REPO,"basic")
for fn in sorted(os.listdir(d)):
    if fn.endswith((".asm",".inc")):
        text[fn]=io.open(os.path.join(d,fn),encoding="utf-8",errors="replace").read()
        for m in re.finditer(r"^([A-Za-z_][\w]*):",text[fn],re.M):
            owner.setdefault(m.group(1),fn)
known=sorted(((a,n) for n,a in sym.items() if n in owner),key=lambda t:t[0])
size={}
for i,(a,n) in enumerate(known):
    nx=known[i+1][0] if i+1<len(known) else a
    s=nx-a
    size[n]=s if 0<=s<=4096 else 0
# labels in files/field called from OUTSIDE those two files = SHARED
BR=re.compile(r"^\s+(call|jp|jr)\s+(?:(?:n?[zc]|p[eo]?|m)\s*,\s*)?([A-Za-z_][\w]*)\s*(?:;.*)?$")
shared=set()
for fn,body in text.items():
    if fn in ("files.asm","field.asm"): continue
    for line in body.splitlines():
        m=BR.match(line)
        if m and owner.get(m.group(2)) in ("files.asm","field.asm"):
            shared.add(m.group(2))
# address-ordered partition of files.asm at the verb entries
CUTS=[("chan_gate","infra"),("ex_copy","light"),("disk_error","infra"),
      ("ex_files","light"),("ex_open","channel"),("ex_line","channel"),
      ("ex_close","channel"),("init_filechan","infra"),("ex_kill","light"),
      ("ex_name","light"),("ex_maxfiles","channel"),("ex_merge","channel")]
fs=[(a,n) for a,n in known if owner[n]=="files.asm"]
lo=min(a for a,_ in fs); hi=max(a+size[n] for a,n in fs)
marks=[(sym[c],c,g) for c,g in CUTS if c in sym]
marks.sort()
group=defaultdict(int); per=[]
for i,(a,c,g) in enumerate(marks):
    end = marks[i+1][0] if i+1 < len(marks) else hi
    group[g]+=end-a; per.append((c,g,end-a))
print(f"files.asm partition ({lo:04X}..{hi:04X}, {hi-lo} B; scout total 1600)")
print(f"{'region from':16} {'group':9} {'bytes':>6}")
print("-"*36)
for c,g,b in per: print(f"{c:16} {g:9} {b:6}")
print("-"*36)
for g in ("light","channel","infra"): print(f"{'TOTAL '+g:16} {'':9} {group[g]:6}")
print(f"{'SUM':16} {'':9} {sum(group.values()):6}")
print()
sh=sorted(x for x in shared if owner.get(x)=="files.asm")
print(f"files.asm labels called from OUTSIDE files/field ({len(sh)}): "
      f"{sum(size.get(x,0) for x in sh)} B")
print("   " + ", ".join(f"{x}({size.get(x,0)})" for x in sh))
sh2=sorted(x for x in shared if owner.get(x)=="field.asm")
print(f"field.asm labels called from OUTSIDE files/field ({len(sh2)}): "
      f"{sum(size.get(x,0) for x in sh2)} B")
print("   " + ", ".join(f"{x}({size.get(x,0)})" for x in sh2))
