#!/usr/bin/env python3
"""D-SEEDHOLE2 re-verification: drop the four sub-local names from the main seed set."""
import importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
spec = importlib.util.spec_from_file_location("cdc", os.path.join(ROOT, "tools", "check_dead_code.py"))
cdc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdc)

FOUR = {'write_sector', 'fat_read_fat_sector', 'fat_alloc_cluster', 'fat_write_fat_entry'}

syms = cdc.ctc.load_syms('build/basic-reloc.sym')
m = cdc.Spans('basic/main.asm', 'main')
ext = set(m.nodes) & cdc.external_names(['sub', 'tools'])
seeds = {'init'} | ext | {n for n in m.nodes if n.startswith(cdc.PROLOGUE)}
print(f"main spans={len(m.nodes)} ext-seeded={len(ext)} seeds={len(seeds)}")
for n in sorted(FOUR):
    print(f"  {n}: in nodes={n in m.nodes} in ext={n in ext}")

dead0, _ = m.dead(seeds)
print(f"baseline dead (no allowlist filter): {len(dead0)} -> {sorted(dead0)}")

seeds2 = seeds - FOUR
dead1, _ = m.dead(seeds2)
tot = 0
print(f"\nafter dropping the four: {len(dead1)} dead")
for lbl in sorted(dead1, key=lambda l: syms.get(l, 0)):
    sz = m.size(lbl, syms)
    addr = syms.get(lbl)
    reg = '?' if addr is None else ('LOW/P0' if addr < cdc.PAGE1 else 'PAGE1')
    if sz: tot += sz
    print(f"  {lbl:24s} {m.owner.get(lbl,'?'):28s} {'' if addr is None else format(addr,'#06x')} {reg} ~{sz} B")
print(f"TOTAL {tot} B")
