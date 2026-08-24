#!/usr/bin/env python3
"""Measure applicability of the opcode-swallow multi-entry trick.

The pattern that can be merged: two+ labels whose ENTIRE body is a single
`ld <reg>,<imm>` followed by an unconditional jump (`jp`/`jr`) to the SAME
target. Those preambles set one register to different constants and fall into a
shared body -- exactly what a `db <ld-opcode>` swallow chains together, turning
each merged `jr target` (2 B) into a 1-byte fake opcode that eats the next
`ld reg,imm`. Saving: ~1 B per merged preamble, at the cost of clobbering a
scratch register and defeating a straight disassembly.

Scans main-image source. A CANDIDATE is a (target, set-register) group of >=2
such preambles. Reports the group, so the readability-vs-byte call is a human's.
"""
import glob, re, os, collections
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LBL   = re.compile(r'^([A-Za-z_]\w*):')
LDIMM = re.compile(r'^\s*ld\s+([abcdehl]|bc|de|hl|ix|iy)\s*,\s*([^;]+?)\s*(;.*)?$', re.I)
UJMP  = re.compile(r'^\s*(jp|jr)\s+([A-Za-z_]\w*)\s*(;.*)?$', re.I)

# collect, per file, the sequence of (label, [instruction lines]) blocks
groups = collections.defaultdict(list)   # (target,reg) -> [(file,label,const)]
for f in sorted(set(glob.glob("basic/*.asm")) | set(glob.glob("basic/*.inc"))):
    cur_label = None; body = []
    def flush(lbl, body):
        # a preamble: exactly one ld reg,imm then one unconditional jump
        insns = [b for b in body if b]
        if len(insns) == 2:
            m1 = LDIMM.match(insns[0]); m2 = UJMP.match(insns[1])
            if m1 and m2:
                reg = m1.group(1).lower(); const = m1.group(2).strip()
                tgt = m2.group(2)
                groups[(tgt, reg)].append((f, lbl, const))
    lines = open(f, errors="ignore").read().split("\n")
    for raw in lines:
        code = raw.split(";",1)[0].rstrip()
        m = LBL.match(code)
        if m:
            if cur_label is not None:
                flush(cur_label, body)
            cur_label = m.group(1)
            rest = code[m.end():].strip()
            body = [rest] if rest else []
        elif cur_label is not None:
            s = code.strip()
            if s: body.append(s)
    if cur_label is not None:
        flush(cur_label, body)

cands = {k: v for k, v in groups.items() if len(v) >= 2}
print(f"trampoline preambles found: {sum(len(v) for v in groups.values())}")
print(f"MERGEABLE groups (>=2 sharing target+register): {len(cands)}")
saved = 0
for (tgt, reg), members in sorted(cands.items(), key=lambda x: -len(x[1])):
    print(f"\n  target {tgt}  via ld {reg},_  ({len(members)} entries, ~{len(members)-1} B):")
    for f, lbl, const in members:
        print(f"      {lbl:24} ld {reg},{const:8}  [{f}]")
    saved += len(members) - 1
print(f"\n  ~{saved} B nominal IF every group merges AND a scratch reg is free "
      f"AND the\n  clarity cost is accepted. Each is a hand judgement, not a sweep.")
