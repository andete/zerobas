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
    return seen or True          # an EMPTY span emits nothing either


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
    cut = 0
    for order in m.seq.values():
        for a, b in zip(order, order[1:]):
            if a in donly and b in m.edges.get(a, set()):
                m.edges[a].discard(b); cut += 1
    new_dead, _ = m.dead(seeds)
    extra = sorted(set(new_dead) - set(base_dead), key=lambda l: syms[build].get(l, 0))
    tot = sum(m.size(l, syms[build]) or 0 for l in extra)
    print(f"\n=== {build} ===")
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
