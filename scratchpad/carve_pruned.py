#!/usr/bin/env python3
"""STRICT vs PLUMBING-PRUNED legality.

tools/carve_scout.py classifies `subrom_call` / `subrom_absent_error` /
`vars_reset` as re-expressible plumbing when reached DIRECTLY -- a tenant IS the
sub-ROM, so it does not make those calls. But the walk still traverses THROUGH
them, and their downstream escapes are then counted as fatal.

basic/field.asm is the case that exposes it: FIVE of its six fatal escapes are

    fld_lookup -> subrom_absent_error -> print_msg -> print_crlf -> pchar -> CHPUT

i.e. the "the sub-ROM is missing" diagnostic, which cannot fire in code that is
ITSELF the sub-ROM. If the plumbing does not exist in a tenant, neither does
that path.

⚠️ PRUNED IS A CEILING, NOT A VERDICT. It answers "what would remain if the
plumbing were re-expressed" and nothing else -- every survivor is still a real
blocker, and the re-expression itself has a cost the scout does not price.
"""
import importlib.util, glob, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location("swm", "scratchpad/carve_legality_sweep.py")
swm = importlib.util.module_from_spec(spec); spec.loader.exec_module(swm)
cs = swm.cs
syms = swm.load(); assert len(syms) > 2000
sources = sorted(glob.glob("basic/*.asm"))
graph = cs.build_callgraph(sources); data = cs.build_datagraph(sources)
span = cs.sizes_by_symbol(syms)
p1 = {n for n, a in syms.items() if cs.PAGE1 <= a < 0x8000}
PLUMB = set(cs.DEFAULT_PLUMBING)
pruned = {k: [t for t in v if t not in PLUMB] for k, v in graph.items()}

print(f"{'file':28} {'B':>5}  strict-fatal  pruned-fatal   surviving blockers")
rows = []
for f in sources:
    moved = cs.labels_in([f]); in_p1 = {n for n in moved if n in p1}
    if not in_p1: continue
    ext = sorted({t for s, tg in graph.items() if s not in moved
                  for t in tg if t in in_p1})
    if not ext: continue
    def fatal(g):
        cl = cs.reachable(g, ext)
        esc = [n for n in cl if n in syms and syms[n] < cs.PAGE1]
        inner = cs.reachable({k: v for k, v in g.items()
                              if k in moved or k in ext}, ext)
        ind = [n for n in esc if not any(n in g.get(m, ()) for m in inner)]
        dirs = [n for n in esc if n not in ind and n not in PLUMB]
        return ind, dirs
    s_ind, _ = fatal(graph)
    p_ind, p_dir = fatal(pruned)
    size = sum(span.get(n, 0) for n in in_p1)
    rows.append((len(p_ind) + len(p_dir), -size, f, size, len(s_ind),
                 len(p_ind), sorted(set(p_ind) | set(p_dir))))
for tot, _, f, size, si, pi, blk in sorted(rows):
    names = ", ".join(blk[:4]) + ("..." if len(blk) > 4 else "")
    print(f"{f:28} {size:5}  {si:12}  {pi:12}   {names if blk else '-- NONE --'}")
