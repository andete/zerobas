#!/usr/bin/env python3
"""Prototype of D-SEEDHOLE2's fix (6), validated against the tree before it ships."""
import importlib.util, os, re, sys
spec = importlib.util.spec_from_file_location("cdc", "tools/check_dead_code.py")
cdc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdc)

RESIDENT_ABI = os.path.join('sub', 'basic-resident-abi.inc')
_ABI_EQU = re.compile(r'^\s*([A-Za-z_]\w*)\s+equ\b', re.IGNORECASE)
ABI_FLOOR = 8

def resident_abi_names():
    if not os.path.exists(RESIDENT_ABI):
        sys.exit(f"FAIL: {RESIDENT_ABI} is missing")
    names = []
    for ln in open(RESIDENT_ABI):
        m = _ABI_EQU.match(ln.split(';', 1)[0])
        if m: names.append(m.group(1))
    if len(names) < ABI_FLOOR:
        sys.exit(f"FAIL: {RESIDENT_ABI} yielded {len(names)} imports (floor {ABI_FLOOR})")
    return names

def sub_visible_equates(s):
    out = set()
    for f in s.files:
        for ln in open(f, errors='ignore'):
            m = _ABI_EQU.match(ln.split(';', 1)[0])
            if m: out.add(m.group(1))
    return out

def assert_sub_resolves_locally(m, s, abi):
    named = set(m.nodes) & cdc.external_names(['sub'])
    local = set(s.nodes) | sub_visible_equates(s)
    escapes = sorted(n for n in named if n not in abi and n not in local)
    return named, escapes

m = cdc.Spans('basic/main.asm', 'main')
s = cdc.Spans('sub/sub.asm', 'sub')
abi = resident_abi_names()
print(f"ABI imports parsed: {len(abi)}")
missing = [n for n in abi if n not in m.nodes]
print(f"ABI names that are NOT main labels: {missing}")
named, escapes = assert_sub_resolves_locally(m, s, set(abi))
print(f"main labels named in sub/ code: {len(named)}; ESCAPES: {len(escapes)} -> {escapes}")

pro = {n for n in m.nodes if n.startswith(cdc.PROLOGUE)}
tools_seeds = set(m.nodes) & cdc.external_names(['tools'])
seeds = {'init'} | set(abi) | tools_seeds | pro
syms = cdc.ctc.load_syms('build/basic-reloc.sym')
dead, _ = m.dead(seeds)
print(f"\nNEW seed set: {len(seeds)} seeds -> {len(dead)} dead")
for l in sorted(dead, key=lambda l: syms.get(l, 0)):
    a = syms.get(l)
    print(f"   {l:26s} {m.owner.get(l,'?'):28s} {'' if a is None else format(a,'#06x')} ~{m.size(l,syms)} B")
