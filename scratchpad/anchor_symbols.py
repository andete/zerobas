# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""anchor_symbols.py -- the CONTENT-GONE half of the line-anchor audit.

scratchpad/anchor_audit_all.py repairs an anchor when the content the author
cited still exists somewhere: a pure content match, no judgement. It leaves the
anchors whose cited LINE was deleted, because moving a number cannot repair a
pointer to something gone.

Some of those are still decidable, on a DIFFERENT and explicitly WEAKER
invariant. When the citation is a markdown link whose LINK TEXT is exactly a
symbol name -- [`raise_error_hl`](../basic/interp.asm:873) -- the author has
STATED what they meant, and if that symbol has exactly one definition site in the
target today, the anchor belongs there. This does NOT prove the author meant the
definition line rather than some line inside the body; it proves they meant the
symbol. That is a smaller claim than the content match, and it is why this runs
as a separate tool with its own output rather than being folded into the other.
"""
import json, re, sys, collections

rows = json.load(open('scratchpad/anchor_rows_all.json'))
CITE = re.compile(r'((?:\.\./)*[A-Za-z0-9_./-]+\.(?:asm|inc|py|md)):(\d+)')
# [`sym`](path:N) or [sym](path:N) -- the link TEXT immediately before the target
LINK = re.compile(r'\[`?([A-Za-z_][A-Za-z0-9_]*)`?\]\(([^)]*?):(\d+)\)')

def defs_in(path, sym):
    """Definition lines of `sym` in `path`, by the target language's own form."""
    try: lines = open(path, encoding='utf-8').read().split('\n')
    except Exception: return []
    out=[]
    for i,l in enumerate(lines,1):
        s=l.rstrip()
        if path.endswith(('.asm','.inc')):
            if re.match(r'^%s:' % re.escape(sym), s): out.append(i)
            elif re.match(r'^%s\s+equ\s' % re.escape(sym), s, re.I): out.append(i)
        elif path.endswith('.py'):
            if re.match(r'^\s*(def|class)\s+%s\b' % re.escape(sym), s): out.append(i)
            elif re.match(r'^%s\s*=' % re.escape(sym), s): out.append(i)
    return out

gone=[r for r in rows if r[4]=='CONTENT-GONE']
tally=collections.Counter(); plan=[]
for f,i,t,n,st,_,cited in gone:
    try: line=open(f,encoding='utf-8').read().split('\n')[i-1]
    except Exception: tally['citing-line-unreadable']+=1; continue
    cands={m.group(1) for m in LINK.finditer(line)
           if m.group(2).split('/')[-1]==t.split('/')[-1] and int(m.group(3))==n}
    if not cands: tally['no-symbol-in-link-text']+=1; continue
    hits={c:defs_in(t,c) for c in cands}
    uniq={c:v[0] for c,v in hits.items() if len(v)==1}
    if len(uniq)==1:
        sym,ln=next(iter(uniq.items()))
        if ln==n: tally['already-at-the-definition']+=1
        else: tally['SYMBOL-RESOLVABLE']+=1; plan.append([f,i,t,n,ln,sym,cited])
    elif not uniq: tally['symbol-absent-or-not-a-definition']+=1
    else: tally['several-symbols-resolve']+=1

print("CONTENT-GONE anchors under this weaker test: %d" % len(gone))
for k,v in tally.most_common(): print("  %-34s %4d" % (k,v))
print("  %-34s %4d" % ('SYMBOL-RESOLVABLE', len(plan)))
json.dump(plan, open('scratchpad/anchor_symbol_plan.json','w'))
for p in plan[:12]:
    print("    %s:%d -> %s:%d  (symbol `%s`)" % (p[0],p[1],p[2],p[4],p[5]))
