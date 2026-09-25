#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""MAKING ROOM lever A scout: which call-site IDIOMS in main's own sources match
a published MSX BIOS RST contract (Joost 2026-09-25, "B first, then A").

  RST 08h SYNCHR  "expect char": (HL) must be the byte after the RST, then CHRGTR,
                  else Syntax error. Idiom: call skip_comma|skip_spaces+cp X,
                  a flag-branch to an error, then an advance.
  RST 10h CHRGTR  inc hl, skip spaces, A=char; Z at 00/':', CF on a digit.
                  Idiom: call inc_skip -- SAFE only where the NEXT instruction
                  does not read Z/C before setting them.
  RST 18h OUTDO   output A, all registers preserved.  Idiom: call pchar.
  RST 20h DCOMPR  compare HL,DE -> Z/C, HL/DE preserved.
                  Idiom: or a / sbc hl,de / add hl,de.
Counts only -- a site's context (register liveness, the exact error) still
needs reading before any conversion. Shared *-body.inc files are excluded.
"""
import os, re, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def files():
    out = []
    for l in open(os.path.join(ROOT, "basic", "main.asm")):
        m = re.match(r'\s*include\s+"([^"]+)"', l.split(";")[0])
        if m and m.group(1).endswith(".asm"):
            out.append(m.group(1))
    return out

READS = re.compile(r"^(jr|jp|ret|call)\s+(z|nz|c|nc)\b|^(adc|sbc|rla|rra|rl|rr)\b|^ccf\b", re.I)
SETS = re.compile(r"^(cp|or|and|xor|sub|add|inc|dec|bit|scf|neg)\b", re.I)

def main():
    stats = collections.Counter()
    samples = collections.defaultdict(list)
    for f in files():
        lines = []
        for n, raw in enumerate(open(os.path.join(ROOT, f), errors="replace"), 1):
            c = raw.split(";")[0].strip()
            if c:
                lines.append((n, re.sub(r"\s+", " ", c.lower())))
        for i, (n, c) in enumerate(lines):
            nxt = lines[i + 1][1] if i + 1 < len(lines) else ""
            nx2 = lines[i + 2][1] if i + 2 < len(lines) else ""
            if c == "call inc_skip":
                if READS.match(nxt):
                    stats["CHRGTR: inc_skip, next READS flags"] += 1
                    samples["chrgtr-reads"].append(f"{f}:{n} -> {nxt}")
                else:
                    stats["CHRGTR: inc_skip, safe"] += 1
            if c == "call pchar":
                stats["OUTDO: call pchar"] += 1
            if c == "or a" and nxt == "sbc hl,de" and nx2 == "add hl,de":
                stats["DCOMPR: or a/sbc/add idiom"] += 1
            m = re.match(r"call (skip_comma|skip_spaces)$", c)
            if m:
                cp = m.group(1) == "skip_comma" or re.match(r"cp ", nxt)
                j = i + (1 if m.group(1) == "skip_comma" else 2)
                br = lines[j][1] if j < len(lines) else ""
                if cp and re.match(r"(jp|jr) nz,\w*(err|syntax|stmt_error|missop)", br):
                    stats["SYNCHR: expect-char + error branch"] += 1
                    samples["synchr"].append(f"{f}:{n} {c} / {br}")
    for k, v in sorted(stats.items()):
        print(f"{v:4}  {k}")
    for k in ("synchr", "chrgtr-reads"):
        print(f"\n{k} samples:")
        for s in samples[k][:8]:
            print("   ", s)
    return 0

if __name__ == "__main__":
    sys.exit(main())
