#!/usr/bin/env python3
"""D-DUPSPAN2 FOLLOW-UP — is a cross-region alias REACHABLE from a tenant?

docs/spec-basic-dupspan2.md §6 deferred 43 B of position-independent dup-span
carve because the aliases CROSS the low <-> page-1 boundary. Main low
($2812-$3FFF) is switched OUT under a sub page-0 tenant and main page 1
($4000-$7FFF) under a page-1 tenant, so:

  * a LOW label aliased to a PAGE-1 address is fatal iff some PAGE-1 tenant
    reaches it -- it would jump into bytes that are not mapped;
  * a PAGE-1 label aliased to a LOW address is fatal iff some PAGE-0 tenant
    reaches it.

"Reaches" is a transitive question and this asks it with the tree's OWN graph
builders, the same ones check_tenant_closure.py gates with -- so this is a
PRE-FLIGHT for that gate, not a second opinion competing with it.

🔴 THE POINT IS NOT THE 43 B. The spec filed a suspicion that the GATE may be
blind here, because D-PINDATA's rule filters `equ` names as VALUES rather than
LOCATIONS. `--knife` answers that by measurement instead: it names a label that
IS reachable, so aliasing it away must make `make basic-reloc` RED. A gate whose
knife stays green is a gate this carve may not lean on.
"""
from __future__ import annotations
import glob
import os
import re
import sys
from collections import deque

sys.path.insert(0, "tools")
from check_tenant_closure import (build_callgraph, load_syms,      # noqa: E402
                                  seeds_from_inc)

# The eleven deferred aliases, from tools/dupspan_indep.py (no --samereg).
# (alias, canonical, bytes)  -- direction is read from the addresses.
CROSS = [
    ("exps_print",    "ems_print",      12),
    ("vsf_wb_int",    "asw_wb_int",      7),
    ("elas_err",      "ems_err_pop1",    4),
    ("exf_syn",       "ems_err_pop1",    4),
    ("ex_def_err",    "ee_synerr_pop",   3),
    ("exps_fallback", "ems_fallback",    3),
    ("inpc_synpop",   "ex_let_err",      3),
    ("flt_int_result","evsgn_settype",   3),
    ("dc_finish",     "ed_done",         3),
    ("rl_break",      "lgb_eof",         2),
    ("affn_found",    "cal_srv_ret",     2),
    ("cut_lp",        "zf_lp",           1),
]
PAGE1 = 0x4000


def closure(graph, seeds):
    seen, q = set(seeds), deque(seeds)
    while q:
        n = q.popleft()
        for t in graph.get(n, ()):
            if t not in seen:
                seen.add(t)
                q.append(t)
    return seen


def main() -> int:
    syms = load_syms("build/basic-reloc.sym")
    main_graph = build_callgraph(sorted(glob.glob("basic/*.asm")))

    # WHO CAN REACH MAIN CODE, and from which side.
    # (a) page-1 tenants enter main through sub/basic-resident-abi.inc's symbols
    #     and may then only stay BELOW $4000.
    p1_seeds = [s for s in seeds_from_inc("sub/basic-resident-abi.inc")]
    reach_from_p1 = closure(main_graph, p1_seeds)

    # (b) Can a page-0 tenant reach main PAGE 1 at all? 🔴 THE FIRST DRAFT OF
    #     THIS BLOCK PRINTED A HARDCODED `0` UNDER A LOOP THAT APPENDED NOTHING
    #     -- a constant wearing the clothes of a reading, and EIGHT of the twelve
    #     verdicts below rest on it. It is measured now.
    #
    #     The sub build can only name a MAIN address that some included file
    #     DEFINES for it; anything else is an undefined symbol and pasmo refuses
    #     the build. So the question is decidable by enumeration: collect every
    #     main-address equate the sub assembly unit is given, and ask how many
    #     are >= $4000.
    main_imports = {}
    for f in sorted(glob.glob("sub/*.inc")):
        for ln in open(f, errors="ignore"):
            m = re.match(r"^\s*([A-Za-z_]\w*)\s+equ\s+0?([0-9A-Fa-f]+)H\s*$",
                         ln.split(";", 1)[0].strip(), re.I)
            if m and m.group(1) in syms:
                main_imports[m.group(1)] = int(m.group(2), 16)
    p1_visible = {n: a for n, a in main_imports.items() if a >= PAGE1}
    print(f"  page-1 tenant ABI seeds: {len(p1_seeds)} "
          f"({', '.join(sorted(p1_seeds))})")
    print(f"  main labels reachable from them: {len(reach_from_p1)}")
    print(f"  MAIN addresses the sub build is given at all: {len(main_imports)}"
          f"  ({', '.join(f'{n}=${a:04X}' for n, a in sorted(main_imports.items()))})")
    print(f"  ...of which are in main PAGE 1 (>= $4000): {len(p1_visible)}"
          f"{'  -> ' + str(p1_visible) if p1_visible else '  -> a page-0 tenant has no main page-1 address to call'}\n")
    if p1_visible:
        print("  ⚠️ the 'no page-0 tenant can reach main page 1' premise below is "
              "FALSE on this tree; every p1->low verdict needs a real walk.")

    verdicts = []
    for alias, canon, n in CROSS:
        if alias not in syms or canon not in syms:
            verdicts.append((alias, canon, n, "ABSENT", "not in the sym file"))
            continue
        a_low = syms[alias] < PAGE1
        c_low = syms[canon] < PAGE1
        if a_low == c_low:
            verdicts.append((alias, canon, n, "NOT-CROSS", "same region now"))
            continue
        if a_low:                       # LOW label -> PAGE-1 address
            hot = alias in reach_from_p1
            why = ("REACHED from a page-1 tenant's ABI closure"
                   if hot else "not in the page-1 tenant closure")
            verdicts.append((alias, canon, n, "FATAL" if hot else "SAFE", why))
        else:                           # PAGE-1 label -> LOW address
            verdicts.append((alias, canon, n, "SAFE",
                             "no page-0 tenant can reach main page 1 at all"))
    good = 0
    for alias, canon, n, v, why in verdicts:
        if v == "SAFE":
            good += n
        print(f"  {alias:16s} equ {canon:16s} {n:3d} B  {v:9s} {why}")
    print(f"\n  {good} B of the {sum(n for _,_,n in CROSS)} B is SAFE by this walk")
    print("  ⚠️ a PRE-FLIGHT, not the gate: make basic-reloc runs "
          "check_tenant_closure.py three ways and IT is the authority")
    return 0


if __name__ == "__main__":
    sys.exit(main())
