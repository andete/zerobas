#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SPEEDPROF — where do the cycles go? A PC-sampling profile of the hot loop.
Samples `reg PC` every 5 emulated ms (openMSX `after time`) while the program
runs, symbolises each sample against build/basic-reloc.sym (main ROM) -- a PC in
$4000..$7FFF is attributed to main page 1 unless the sub-ROM is mapped, which
this first cut does not read -- and prints the top routines by sample count.
"""
from __future__ import annotations
import os, sys, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402

def load_syms(path):
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"(\w+)\s+EQU\s+0?([0-9A-Fa-f]+)H", line)
        if not m: continue
        v, name = int(m.group(2), 16), m.group(1)
        # 🔴 AN EQU IS NOT AN ADDRESS. `ev_ff_argtab_len equ $ - ev_ff_argtab` is a
        # LENGTH (~12), and it symbolised every BIOS sample near $000C -- it came
        # back as the profile's top entry twice before I read what it was. Keep only
        # symbols inside the ROM image; anything below the org is BIOS/RAM, and the
        # region tally already says which.
        if name.isupper() or v < 0x2812: continue
        out.append((v, name))
    return sorted(out)

def symbolise(syms, pc):
    lo, hi = 0, len(syms)
    while lo < hi:
        mid = (lo + hi) // 2
        if syms[mid][0] <= pc: lo = mid + 1
        else: hi = mid
    return syms[lo - 1][1] if lo else f"${pc:04X}"

def main() -> int:
    prog = sys.argv[1] if len(sys.argv) > 1 else "FOR I=1 TO 2000:X=I*2+1:NEXT"
    secs = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0
    start = float(sys.argv[3]) if len(sys.argv) > 3 else 22.0   # after the harness has typed the program and RUN
    cfg = probe_sides.sides("zb")["zb"]
    log = probe_tmp.tmp("speedprof.log")
    n = int(secs / 0.005)
    prologue = (f'set ::pf [open "{log}" w]\n'
                f'proc samp {{}} {{ puts $::pf [reg PC] }}\n'
                f'for {{set i 0}} {{$i < {n}}} {{incr i}} {{ after time [expr {{{start} + $i * 0.005}}] samp }}\n'
                f'after time {start + secs + 1} {{ flush $::pf; close $::pf }}\n')
    lines = [f"10 A=TIME:{prog}:B=TIME", '20 PRINT"[sp";B-A;"]"', "RUN"]
    cap = omsx_repl.run_cases(cfg["machine"], [("sp", lines)], batch=False, boot=cfg["boot"], reset=cfg["reset"],
                              prologue=(prologue,), run_gap=secs + 5)[0] or ""
    i = cap.rfind("[sp"); print("jiffies:", cap[i:cap.find("]", i) + 1] if i >= 0 else "<none>")
    pcs = [int(x) for x in open(log).read().split() if x.strip().isdigit()]
    syms = load_syms(os.path.join(REPO, "build", "basic-reloc.sym"))
    hist = collections.Counter(); region = collections.Counter()
    for pc in pcs:
        region["bios/low" if pc < 0x4000 else "page1" if pc < 0x8000 else "ram"] += 1
        hist[("BIOS/ISR" if pc < 0x2812 else symbolise(syms, pc)) if pc < 0x8000 else f"RAM ${pc:04X}"] += 1
    tot = len(pcs); print(f"samples: {tot}  regions: {dict(region)}")
    for name, c in hist.most_common(25):
        print(f"  {100*c/tot:5.1f}%  {c:5}  {name}")
    bios = [pc for pc in pcs if pc < 0x2812]
    if bios:
        pages = collections.Counter(pc >> 8 for pc in bios); exact = collections.Counter(bios)
        print(f"BIOS (< $2812): {len(bios)} samples; top pages:", " ".join(f"${p:02X}xx:{c}" for p, c in pages.most_common(8)))
        print("  top PCs:", " ".join(f"${pc:04X}:{c}" for pc, c in exact.most_common(16)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
