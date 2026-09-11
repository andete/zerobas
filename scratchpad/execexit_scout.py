#!/usr/bin/env python3
# SPDX-License-Identifier: 0BSD
"""D-JUMPLOOP: every path that RETURNS out of `exec`, found rather than guessed.

Joost ruled cut 2 of D-SPMERGE as option (1): the run loop becomes a JUMP loop,
so `exec` must never be `ret`urned from -- at a statement boundary the stack has
to hold frames and nothing else. `ret` is 1 B and `jp rp_after` is 3, so the SITE
COUNT is what sizes the carve, and guessing it from the three control flags misses
`ex_rem`, which ends a line with a bare `ret` and sets no flag at all.

Walks the SOURCE from every stmt_table handler, following jumps, not descending
into calls, and reports each `ret`/`ret cc` reachable at the handler's own depth.
"""
import os, re, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = []
for d in ("basic", "sub"):
    for fn in sorted(os.listdir(os.path.join(ROOT, d))):
        if fn.endswith((".asm", ".inc")):
            SRC.append(os.path.join(d, fn))

# label -> (file, index); lines[(file)] -> list
lines, label = {}, {}
for rel in SRC:
    L = open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read().split("\n")
    lines[rel] = L
    for i, ln in enumerate(L):
        m = re.match(r"^([A-Za-z_][\w]*):", ln)
        if m and m.group(1) not in label:
            label[m.group(1)] = (rel, i)

# statement handlers, from the table
handlers = []
for rel in SRC:
    for ln in lines[rel]:
        m = re.match(r"\s*dw\s+([A-Za-z_]\w*)\s*$", ln.split(";")[0])
        if m and m.group(1) in label:
            handlers.append(m.group(1))
tbl = []
for rel in SRC:
    L = lines[rel]
    for i, ln in enumerate(L):
        if re.match(r"^stmt_table:", ln):
            for j in range(i, min(i + 400, len(L))):
                m = re.search(r"dw\s+([A-Za-z_]\w*)", L[j].split(";")[0])
                if m: tbl.append(m.group(1))
                if re.match(r"^[a-z_]\w*:", L[j]) and j > i: break
if tbl: handlers = tbl

STOP_JP = {"exec", "exec_stmt", "pop_exec", "raise_error", "stmt_error",
           "rp_lp", "rp_exec", "rp_break", "repl"}

# 🔴 A LABEL THAT IS ALSO A `call` TARGET IS AMBIGUOUS, AND THE FIRST CUT OF THIS
# SCOUT REPORTED 38 SITES BECAUSE IT IGNORED THAT. `pch_done` came back as an exec
# exit with TWENTY-FIVE origins -- it is the tail of a CALLED helper, and its `ret`
# returns to that helper's caller, not out of `exec`. A `ret` is only an exec exit
# if the whole chain from the handler is jumps AND no label on it is ever CALLed.
# Anything else is reported separately as AMBIGUOUS rather than counted.
CALLED = set()
for rel in SRC:
    for ln in lines[rel]:
        m = re.match(r"\s*call\s+(?:[a-z]{1,2}\s*,\s*)?([A-Za-z_]\w*)", ln.split(";")[0], re.I)
        if m: CALLED.add(m.group(1))
CONTROL = re.compile(r"^\s*(ret|jp|jr|call)\b\s*(.*)$", re.I)
found = collections.defaultdict(set)

ambig = collections.defaultdict(set)

def walk(start, origin, seen):
    stack = [(start, False)]
    while stack:
        name, tainted = stack.pop()
        if name in seen or name not in label: continue
        seen.add(name)
        rel, i = label[name]
        if rel.startswith("sub/"):
            continue          # a main-ROM `jp` cannot land in the sub-ROM; a same-named
                              # label there is a COLLISION, not a target
        L = lines[rel]
        j = i
        while j < len(L):
            s = L[j].split(";")[0].rstrip()
            j += 1
            body = s.strip()
            if not body: continue
            if re.match(r"^[A-Za-z_]\w*:", body):        # fell into a new label
                body = body.split(":", 1)[1].strip()
                if not body: continue
            m = CONTROL.match(body)
            if not m: continue
            op, arg = m.group(1).lower(), m.group(2).strip()
            if op == "ret":
                (ambig if tainted else found)[(rel, j)].add(origin)
                if not arg: break                        # unconditional: path ends
                continue
            if op == "call":
                continue                                  # returns here; do not descend
            tgt = arg.split(",")[-1].strip()
            cond = "," in arg
            if tgt in STOP_JP:
                if not cond: break
                continue
            if re.match(r"^[A-Za-z_]\w*$", tgt) and tgt in label:
                stack.append((tgt, tainted or tgt in CALLED))
            if not cond: break

for h in handlers:
    walk(h, h, set())

print(f"{len(handlers)} statement handlers walked")
print(f"{len(found)} `ret` site(s) reachable at handler depth -- each must become a jump:\n")
for (rel, ln), origins in sorted(found.items()):
    o = sorted(origins)
    print(f"  {rel}:{ln:<6} {lines[rel][ln-1].split(';')[0].strip():<28} <- {', '.join(o[:4])}"
          + (f" (+{len(o)-4})" if len(o) > 4 else ""))
print(f"\nBYTE COST if each becomes `jp rp_after`: +{2*len(found)} B "
      f"(a conditional `ret cc` -> `jp cc,rp_after` is +1, so this is an upper bound)")
print(f"\n{len(ambig)} AMBIGUOUS site(s) -- reached only through a label that is also a "
      f"`call` target, so the `ret` may belong to that call. NOT counted above; each "
      f"needs reading:")
for (rel, ln), origins in sorted(ambig.items()):
    o = sorted(origins)
    print(f"  {rel}:{ln:<6} {lines[rel][ln-1].split(';')[0].strip():<26} <- {', '.join(o[:3])}"
          + (f" (+{len(o)-3})" if len(o) > 3 else ""))
