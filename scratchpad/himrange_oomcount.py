#!/usr/bin/env python3
"""How many string scalars OOM the chain under a LEGAL CLEAR ceiling (zb)."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT); sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import omsx_repl
ZB = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
# generate up to 200 distinct string names: A-Z, then A0..A9,B0..,...
names = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"]
for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    for d in "0123456789":
        names.append(c+d)
names = names[:200]
# each line: X$="1"; after every 20, PRINT a marker of how many done
lines = ['CLEAR 200,33800']
for i,n in enumerate(names):
    lines.append(f'{n}$="1"')
    if (i+1) % 20 == 0:
        lines.append(f'PRINT"<{i+1}:";FRE("");">"')
caps = omsx_repl.run_cases(ZB, [("direct", lines)], batch=True,
                           reset=("NEW","CLS"), boot=8.0, step=4.0, timeout=300.0)
txt = "".join(caps[0] or [])
# print the last ~12 non-blank screen lines
keep=[l.rstrip() for l in txt.split("\n") if l.strip()]
for l in keep[-15:]:
    print(repr(l))
