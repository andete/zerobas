#!/usr/bin/env python3
"""bufaudit.py -- STATIC audit for Joost's (b) ONE SHARED BUFFER ruling (2026-09-24).

Read-only over OUR OWN source (disk/*.asm and the basic/*.inc bodies disk.asm
includes). For every root (a hook handler in hook_tab, the pinned kernel ABI
entries) it computes the label-level call closure and reports which labels in it
name a sector-buffer symbol. Over-approximates on purpose: any call/jp/jr/djnz
target and any `ld rr,<code label>` is an edge, and a label with no terminating
instruction falls through to the next one. An edge it misses is a hole in the
audit; an edge it adds only makes the answer more conservative.
"""
import re, sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_tree(path, seen):
    out = []
    path = os.path.normpath(path)
    if path in seen:
        return out
    seen.add(path)
    for i, raw in enumerate(open(path, encoding='utf-8', errors='replace')):
        line = raw.split(';', 1)[0].rstrip('\n')
        m = re.match(r'\s*include\s+"([^"]+)"', line, re.I)
        if m:
            inc = m.group(1)
            for base in (os.path.dirname(path), os.path.join(ROOT, 'disk'), ROOT):
                p = os.path.join(base, inc)
                if os.path.exists(p):
                    out += read_tree(p, seen)
                    break
            else:
                sys.exit(f'REFUSE: include {inc!r} from {path} not found')
            continue
        out.append((os.path.relpath(path, ROOT), i + 1, line))
    return out

LINES = read_tree(os.path.join(ROOT, 'disk', 'disk.asm'), set())
if len(LINES) < 5000:
    sys.exit(f'REFUSE: only {len(LINES)} lines read -- the include walk failed')

# equates, and which of them are derived from a buffer symbol
EQU = {}
for f, n, l in LINES:
    m = re.match(r'^([A-Za-z_][\w]*)\s*:?\s+equ\s+(.*)$', l, re.I)
    if m:
        EQU[m.group(1)] = m.group(2).strip()
BUF = {'SECTOR_BUF', 'WBUF', 'FAT_DBUF', 'FAT_MBUF', 'FSECTOR_BUF', 'FWBUF',
       'DBUF_PTR', 'MBUF_PTR', 'DSKBUF_PTR'}
changed = True
while changed:
    changed = False
    for k, v in EQU.items():
        if k not in BUF and any(re.search(r'\b%s\b' % b, v) for b in BUF):
            BUF.add(k); changed = True
BUFRE = re.compile(r'\b(%s)\b' % '|'.join(sorted(BUF, key=len, reverse=True)))

# label blocks
blocks, order, cur = {}, [], None
for f, n, l in LINES:
    m = re.match(r'^([A-Za-z_][\w]*):', l)
    if m and not re.match(r'^[A-Za-z_]\w*\s*:?\s+equ\b', l, re.I):
        cur = m.group(1)
        order.append(cur)
        blocks[cur] = {'where': f'{f}:{n}', 'ins': []}
        l = l[m.end():]
    if cur and l.strip():
        blocks[cur]['ins'].append((f, n, l.strip()))
LABELS = set(blocks)
TERM = re.compile(r'^(jp|jr)\s+[^,]+$|^ret$|^reti$|^retn$|^jp\s+\((hl|ix|iy)\)$', re.I)

def edges(lbl):
    out = set()
    ins = blocks[lbl]['ins']
    for f, n, t in ins:
        m = re.match(r'^(call|jp|jr|djnz)\s+(?:\w+\s*,\s*)?([A-Za-z_]\w*)\s*$', t, re.I)
        if m and m.group(2) in LABELS:
            out.add(m.group(2))
        m = re.match(r'^ld\s+(hl|de|bc|ix|iy)\s*,\s*([A-Za-z_]\w*)\s*$', t, re.I)
        if m and m.group(2) in LABELS:
            out.add(m.group(2))
    last = ins[-1][2] if ins else ''
    real = [x for x in ins if not re.match(r'^(db|dw|ds|defs|defb|defw)\b', x[2], re.I)]
    lastreal = real[-1][2] if real else ''
    if not TERM.match(lastreal):
        i = order.index(lbl)
        if i + 1 < len(order):
            out.add(order[i + 1])
    return out

E = {l: edges(l) for l in blocks}

def closure(root):
    seen, st = set(), [root]
    while st:
        x = st.pop()
        if x in seen: continue
        seen.add(x); st += E.get(x, ())
    return seen

def touches(lbl):
    return sorted({m.group(1) for f, n, t in blocks[lbl]['ins'] for m in BUFRE.finditer(t)})

# roots: hook_tab pairs
roots = []
tab = False
for f, n, l in LINES:
    if l.startswith('hook_tab:'): tab = True; continue
    if tab:
        m = re.match(r'\s*dw\s+(\w+)\s*,\s*(\w+)', l)
        if m: roots.append((m.group(1), m.group(2)))
        elif re.match(r'\s*dw\s+0\s*$', l): break
extra = sys.argv[1:]
for r in extra: roots.append(('(arg)', r))
if len(roots) < 15:
    sys.exit(f'REFUSE: hook_tab yielded {len(roots)} roots')

print(f'lines read {len(LINES)}, labels {len(LABELS)}, buffer symbols {sorted(BUF)}')
for hook, h in roots:
    c = closure(h)
    t = {l: touches(l) for l in c if touches(l)}
    syms = sorted({s for v in t.values() for s in v})
    print(f'\n{hook:9s} -> {h:12s} closure {len(c):4d} labels; touching {len(t):3d}: {",".join(syms) or "-"}')
    for l in sorted(t)[:12]:
        print(f'      {l:28s} {blocks[l]["where"]:28s} {",".join(t[l])}')
    if len(t) > 12: print(f'      ... {len(t)-12} more')
