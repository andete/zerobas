#!/usr/bin/env python3
"""Does a DATA-ONLY span confer liveness by fallthrough on whatever follows it?

The span model's fallthrough rule is "the previous span's last code line is not
an unconditional terminator". A `db "CAS:",0` is not a terminator, so every
label following a live data table is unconditionally live -- nothing ever runs
off the end of a table. Measure how much that hides.
"""
import importlib.util, re
spec = importlib.util.spec_from_file_location("cdc", "tools/check_dead_code.py")
cdc = importlib.util.module_from_spec(spec); spec.loader.exec_module(cdc)

# a line that EMITS DATA or is an assembler directive -- never an executed
# instruction that could fall through into the next label
EMPTY_TOO = '--empty-too' in __import__('sys').argv

DATA = re.compile(r'^\s*(db|dw|ds|defb|defw|defs|equ|org|IF\b|IFDEF|IFNDEF|ELSE|ENDIF|'
                  r'MACRO|ENDM|END)\b', re.IGNORECASE)
LBLEQU = re.compile(r'^\s*[A-Za-z_]\w*\s+equ\b', re.IGNORECASE)


def data_only(lines):
    """True if the span emits only data/directives -- no executable instruction."""
    seen = False
    for c in lines:
        t = c.strip()
        if not t or re.match(r'^[A-Za-z_]\w*:', t):
            continue
        t2 = re.sub(r'^[A-Za-z_]\w*:\s*', '', t)
        if not t2:
            continue
        seen = True
        if not (DATA.match(t2) or LBLEQU.match(t2) or DATA.match(t)):
            return False
    # 🔴 `return seen or True` UNTIL 2026-08-28 — which classifies an EMPTY span as
    # data-only and cuts its fallthrough edge. That is §12.1's demonstration (this
    # script's own commit is titled "the obvious fix reports 27 KB in a 22 KB
    # ROM"), NOT the §12.5 measurement TODO.md cites from it. Re-run today the old
    # line gave main 1195 findings / 28820 B and sub 124 / 1444 B — the catastrophe,
    # not the 1 finding / 4 B and 4 / 97 B the item quotes.
    # An empty span is an ALTERNATE ENTRY POINT and its "fallthrough" IS the
    # routine; only a span that actually EMITS DATA can be cut. Pass --empty-too to
    # reproduce §12.1 deliberately.
    if not seen:
        return EMPTY_TOO
    return True


ABI = set(re.findall(r'^(\w+)\s+equ', open('sub/basic-resident-abi.inc').read(), re.M))
syms = {'main': cdc.ctc.load_syms('build/basic-reloc.sym'),
        'sub': cdc.ctc.load_syms('build/sub.sym')}

for top, build in [('basic/main.asm', 'main'), ('sub/sub.asm', 'sub')]:
    m = cdc.Spans(top, build)
    pro = {n for n in m.nodes if n.startswith(cdc.PROLOGUE)}
    if build == 'main':
        seeds = {'init'} | ABI | (set(m.nodes) & cdc.external_names(['tools'])) | pro
    else:
        t = cdc.ctc.page0_seeds('sub/sub.asm') + cdc.ctc.page1_seeds('sub/sub.asm')
        seeds = set(t) | pro

    base_dead, _ = m.dead(seeds)

    # how many spans are DATA-ONLY, and how many fallthrough edges leave one?
    donly = {n for n, l in m.nodes.items() if data_only(l)}
    # 🔴 A FALLTHROUGH EDGE AND A REFERENCE EDGE TO THE SAME TARGET ARE THE SAME
    # ENTRY IN `edges`, AND DISCARDING ONE DISCARDS BOTH. Found 2026-08-28:
    # `stmt_table` is a `dw` dispatch table whose NEXT span in source order is
    # `ex_sep` -- and which contains `dw ex_sep`. Cutting "the fallthrough" also
    # cut the dispatch entry, and `ex_sep` (main's only finding, 4 B) was an
    # artifact of this apparatus, not dead code. `em_ill_direct` is the same shape
    # via `em_table`. So a target that the span ALSO NAMES keeps its edge: the
    # reference is real however the fallthrough is judged.
    cut = kept = 0
    for order in m.seq.values():
        for a, b in zip(order, order[1:]):
            if a in donly and b in m.edges.get(a, set()):
                if any(re.search(r'\b%s\b' % re.escape(b), l) for l in m.nodes.get(a, [])):
                    kept += 1          # named in the span: a REFERENCE, not a fallthrough
                    continue
                m.edges[a].discard(b); cut += 1
    new_dead, _ = m.dead(seeds)
    extra = sorted(set(new_dead) - set(base_dead), key=lambda l: syms[build].get(l, 0))
    tot = sum(m.size(l, syms[build]) or 0 for l in extra)
    print(f"\n=== {build} ===")
    print(f"  (kept {kept} edge(s) whose target the span NAMES -- reference, not fallthrough)")
    print(f"  spans={len(m.nodes)}  DATA-ONLY spans={len(donly)}  "
          f"fallthrough edges cut={cut}")
    print(f"  dead before={len(base_dead)}  after={len(new_dead)}  "
          f"NEW={len(extra)}  bytes={tot}")
    for l in extra[:25]:
        a = syms[build].get(l)
        reg = '?' if a is None else ('LOW/P0' if a < cdc.PAGE1 else 'PAGE1')
        print(f"    {l:26s} {m.owner.get(l,'?'):30s} "
              f"{'' if a is None else format(a,'#06x')} {reg} ~{m.size(l,syms[build])} B")
    if len(extra) > 25:
        print(f"    ... and {len(extra)-25} more")
