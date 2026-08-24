#!/usr/bin/env python3
"""Name the EXACT escapes for the near-miss files the legality sweep surfaced.

⚠️ Written after an inline version reported `entries=0` for all six files -- its
own symbol regex had matched nothing, so every closure was empty and every file
printed as clean. A 0/0 reads as converged. This imports the sweep's loader so
the two cannot disagree, and ASSERTS the entry set is non-empty.
"""
import importlib.util, glob, os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sw = importlib.util.spec_from_file_location("sw", "scratchpad/carve_legality_sweep.py")
sw = importlib.util.module_from_spec(sw); sw.__name__ = "sw"
sw.__loader__.exec_module(sw) if False else None
spec = importlib.util.spec_from_file_location("swm", "scratchpad/carve_legality_sweep.py")
swm = importlib.util.module_from_spec(spec); spec.loader.exec_module(swm)
cs = swm.cs

syms = swm.load()
assert len(syms) > 2000, f"symbol load failed: {len(syms)}"
sources = sorted(glob.glob("basic/*.asm"))
graph = cs.build_callgraph(sources); data = cs.build_datagraph(sources)
span = cs.sizes_by_symbol(syms)
p1 = {n for n, a in syms.items() if cs.PAGE1 <= a < 0x8000}

for f in ["basic/playsvc.asm", "basic/fat.asm", "basic/initext.asm",
          "basic/subrom-boot.asm", "basic/list.asm", "basic/field.asm"]:
    moved = cs.labels_in([f]); in_p1 = {n for n in moved if n in p1}
    ext = sorted({t for s, tg in graph.items() if s not in moved
                  for t in tg if t in in_p1})
    assert ext, f"{f}: no external entries -- would report a vacuous clean"
    closure = cs.reachable(graph, ext)
    esc = [n for n in closure if n in syms and syms[n] < cs.PAGE1]
    inner = cs.reachable({k: v for k, v in graph.items()
                          if k in moved or k in ext}, ext)
    direct = [n for n in esc if any(n in graph.get(m, ()) for m in inner)]
    indirect = [n for n in esc if n not in direct]
    print(f"\n=== {f}  ({sum(span.get(n,0) for n in in_p1)} B in page 1, "
          f"{len(ext)} external entries, closure {len(closure)})")
    for n in sorted(direct):
        tag = ("plumbing" if n in cs.DEFAULT_PLUMBING
               else ("BIOS" if syms[n] < cs.LOWREGION else "BLOCKER"))
        print(f"    direct   {tag:9} {n} @ ${syms[n]:04X}")
    for n in sorted(indirect)[:8]:
        p = cs.shortest_path(graph, ext, n)
        print(f"    THRU-P1  {n} @ ${syms[n]:04X}  via "
              f"{' -> '.join(p[:6]) if p else '?'}")
    if not direct and not indirect:
        print("    (no escapes at all)")
