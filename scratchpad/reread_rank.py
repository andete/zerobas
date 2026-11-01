#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-REREAD's candidate ranking (2026-11-01): label-to-label spans of the routines
z80flow knows (build/contracts.json -- run `make contracts` first) in
build/basic-reloc.sym, largest first, minus every routine NAMED in
scratchpad/reread_sample.md or scratchpad/reread_reviewed.md (one batch's reviewed
names per line). A span runs to the next z80flow routine label, so it can hold
several internal labels -- or a data label (err_syntax). The ranking rots with every
carve: re-run it, never quote it.

    make contracts && python3 scratchpad/reread_rank.py
"""
import re,json,subprocess
sym={}
for ln in open('build/basic-reloc.sym'):
    m=re.match(r'(\S+)\s+EQU\s+0?([0-9A-F]+)H',ln)
    if m: sym[m.group(1)]=int(m.group(2),16)
# code labels: those defined with ':' in basic/ sources
labs=set()
loc={}
for f in subprocess.check_output(['git','ls-files','basic/']).decode().split():
    if not f.endswith(('.asm','.inc')): continue
    for i,ln in enumerate(open(f,errors='replace'),1):
        m=re.match(r'^([A-Za-z_]\w*):',ln)
        if m: labs.add(m.group(1)); loc.setdefault(m.group(1),f"{f}:{i}")
addrs=sorted((a,n) for n,a in sym.items() if n in labs and 0x2781<=a<0x8000)
done=open('scratchpad/reread_sample.md').read()+open('scratchpad/reread_reviewed.md').read()
c=json.load(open('build/contracts.json'))['rows']
ncall={k.split(' [')[0]:v['ncall'] for k,v in c.items()}
rout=set(ncall)
# span from a ROUTINE label to the next routine label
ra=[(a,n) for a,n in addrs if n in rout]
out=[]
for (a,n),(b,_) in zip(ra,ra[1:]):
    out.append((b-a,a,n))
out.sort(reverse=True)
k=0
for sz,a,n in out:
    if re.search(r'(?<![\w])'+re.escape(n)+r'(?![\w])',done): continue
    reg='LOW' if a<0x4000 else 'P1'
    print(f"{sz:5d} ${a:04X} {reg:3s} calls={ncall.get(n,0):3d} {n:28s} {loc.get(n,'')}")
    k+=1
    if k>=40: break
