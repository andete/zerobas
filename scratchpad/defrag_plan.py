#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Plan a disk.rom defrag that gathers free space in ONE pinned region.

Every movable routine (scratchpad/movescout.py's rules, plus: no `jr` / `djnz`
leaving the block, no `*_tmpl`, no reference with arithmetic on its name) is an
ITEM with its EXACT size -- a scratch copy of disk/ gets an end label after each
block and is assembled (movescout's next-symbol size undercounts a block whose
inner labels are unreferenced). Every other pinned region is a BIN whose capacity
is its free bytes plus the items it already holds. Bins are filled largest
first, each by a subset sum over the items left; what is not packed belongs in
the TARGET region. Prints the expected free bytes in the target and the moves
(`move_routine.py NAME PIN`), items leaving the target last. Moves nothing.

    python3 scratchpad/defrag_plan.py TARGETPIN      e.g. 75A5
"""
import glob
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = int(sys.argv[1], 16)
LAB = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):")
END = re.compile(r"^\s+(ret|jp|jr|reti)\b(?!\s+(nz|z|nc|c|po|pe|p|m)\s*,)", re.I)
PIN = re.compile(r"^\s+ds\s+\$([0-9A-Fa-f]{4})\s*-\s*\$", re.I)
JR = re.compile(r"^\s+(jr|djnz)\s+(?:(?:nz|z|nc|c)\s*,\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*$", re.I)


def code(l):
    return l.split(";", 1)[0].rstrip()


files = sorted(glob.glob(os.path.join(REPO, "disk", "*.asm")))
src = {f: open(f, errors="replace").read().split("\n") for f in files}
allsrc = src.copy()
for f in glob.glob(os.path.join(REPO, "basic", "*.inc")):
    allsrc[f] = open(f, errors="replace").read().split("\n")

# candidate blocks: (file, label line, end line exclusive, name)
cands = []
for f, lines in src.items():
    for i, l in enumerate(lines):
        m = LAB.match(l)
        if not m:
            continue
        name = m.group(1)
        if name.startswith(("k_", "__")) or name.endswith("_tmpl"):
            continue
        j = i - 1
        while j >= 0 and not code(lines[j]).strip():
            j -= 1
        if j < 0:
            continue
        pc = code(lines[j])
        if not (END.match(pc) or pc.strip().startswith("ds")):
            continue
        k, last, lastk = i + 1, None, None
        while k < len(lines) and not LAB.match(lines[k]):
            c = code(lines[k])
            if PIN.match(c):
                break
            if c.strip():
                last, lastk = c, k
            k += 1
        if last is None or not END.match(last) or (k < len(lines) and PIN.match(code(lines[k])) and lastk is None):
            continue
        block = lines[i:lastk + 1]
        own = {LAB.match(x).group(1) for x in block if LAB.match(x)}
        if any(JR.match(code(x)) and JR.match(code(x)).group(2) not in own for x in block):
            continue
        inner = own - {name}
        pat = re.compile(r"\b%s\b" % re.escape(name))
        bad = False
        for g, gl in allsrc.items():
            for x in gl:
                c = code(x)
                if LAB.match(c) and LAB.match(c).group(1) == name:
                    continue
                if pat.search(c):
                    if re.search(r"\b%s\b\s*[-+*/]|[-+*/]\s*\b%s\b" % (re.escape(name), re.escape(name)), c) \
                            or not re.match(r"^\s*(call|jp|dw)\b", c, re.I) and not re.match(r"^\s*(call|jp)\s+\w+\s*,", c, re.I):
                        bad = True
                for n in inner:
                    if re.search(r"\b%s\b" % re.escape(n), c) and not (g == f and x in block):
                        bad = True
        if not bad:
            cands.append((f, i, lastk + 1, name))

# exact sizes: a scratch copy with an end label after each block, and a label in front of each pin
work = "/tmp/zerobas/defragplan"
shutil.rmtree(work, ignore_errors=True)
shutil.copytree(os.path.join(REPO, "disk"), work)
ins = {}
for f, i, e, name in cands:
    ins.setdefault(f, []).append((e, f"__end_{name}:"))
for f, lines in src.items():
    out = []
    adds = dict()
    for e, lab in ins.get(f, []):
        adds.setdefault(e, []).append(lab)
    for n, l in enumerate(lines):
        out.extend(adds.get(n, []))
        m = PIN.match(code(l))
        if m:
            out.append(f"__pin_{m.group(1).upper()}_{n}:")
        out.append(l)
    open(os.path.join(work, os.path.basename(f)), "w").write("\n".join(out))
sym = os.path.join(work, "disk.sym")
r = subprocess.run(["pasmo", "-I", work, "--bin", os.path.join(work, "disk.asm"), os.path.join(work, "disk.rom"), sym],
                   cwd=REPO, capture_output=True, text=True)
if r.returncode:
    sys.exit("assemble failed: " + r.stderr[-500:])
S = {}
for l in open(sym):
    p = l.split()
    if len(p) >= 3 and p[1] == "EQU":
        S[p[0]] = int(p[2].rstrip("H"), 16)
pins = sorted({int(n.split("_")[3], 16): S[n] for n in S if n.startswith("__pin_")}.items())  # pin -> where the pad starts
free = {p: p - at for p, at in pins}


def region(a):
    for p, at in pins:
        if a < at or a < p and a >= at:
            return p
    return None


items = []
for f, i, e, name in cands:
    if name in S and f"__end_{name}" in S:
        a, size = S[name], S[f"__end_{name}"] - S[name]
        if size > 0:
            items.append((size, name, region(a)))
if TARGET not in free:
    sys.exit(f"no pin ${TARGET:04X}")
if len(sys.argv) > 2 and sys.argv[2] == "--bin":
    # --bin N: for each region, the FEWEST evictions (its own items, best-fit into
    # the other regions' CURRENT free, never the target / the FDC window) that
    # leave it N bytes free. TARGETPIN names the region to keep out of it.
    N = int(sys.argv[3])
    res = []
    for R in free:
        if R in (TARGET, 0x7FC0):
            continue
        fr = dict(free)
        own = sorted([(s, nm) for s, nm, r in items if r == R], reverse=True)
        moves, got = [], fr[R]
        for s, nm in own:
            if got >= N:
                break
            dsts = [p for p in fr if p not in (R, TARGET, 0x7FC0) and fr[p] >= s]
            if not dsts:
                continue
            d = min(dsts, key=lambda p: fr[p])
            fr[d] -= s
            got += s
            moves.append((s, nm, d))
        if got >= N:
            res.append((len(moves), R, got, moves))
    for nmv, R, got, moves in sorted(res)[:6]:
        print(f"${R:04X}: {got} B with {nmv} move(s): " + ", ".join(f"{nm}({s})->${d:04X}" for s, nm, d in moves))
    sys.exit(0)
cap = {p: free[p] for p in free if p != TARGET and p != 0x7FC0}   # $7FC0: the FDC window
for size, name, reg in items:
    if reg in cap:
        cap[reg] += size
left = sorted(items, reverse=True)
assign = {}
for p in sorted(cap, key=lambda p: -cap[p]):
    c = cap[p]
    # subset sum over the items left (sizes small), preferring an item's own region
    best = {0: []}
    for idx, (size, name, reg) in enumerate(left):
        for s, chosen in sorted(best.items(), reverse=True):
            t = s + size
            if t <= c and (t not in best or (reg == p and not any(left[q][2] == p for q in best[t]))):
                best[t] = chosen + [idx]
    t = max(best)
    for idx in best[t]:
        assign[left[idx][1]] = p
    left = [x for q, x in enumerate(left) if q not in set(best[t])]
    cap[p] = c - t
waste = sum(cap.values())
target_free = free[TARGET] + sum(s for s, n, r in items if r != TARGET and n not in assign) \
    - 0 + sum(s for s, n, r in items if r == TARGET and n in assign)
print(f"items {len(items)}, total free (no FDC window) {sum(v for p, v in free.items() if p != 0x7FC0)} B")
print(f"waste left in other bins: {waste} B")
print(f"target ${TARGET:04X}: {free[TARGET]} -> {target_free} B")
moves = []
for size, name, reg in items:
    dst = assign.get(name, TARGET)
    if dst != reg:
        moves.append((reg == TARGET, size, name, dst, reg))
for into_target_last, size, name, dst, reg in sorted(moves, key=lambda m: (m[3] == TARGET, m[0])):
    print(f"{size:4d}  {name:28s} ${reg:04X} -> ${dst:04X}")
