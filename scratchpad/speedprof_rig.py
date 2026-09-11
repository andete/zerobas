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
    # 🔴 SAMPLE ONLY WHILE THE PROGRAM IS ACTUALLY RUNNING. The first two tables this
    # rig produced were both dominated by `$11A0` at 54-68% and both were ARTEFACTS:
    # the window outlived the program, and every sample after it landed on the READY
    # prompt's HALT. That read as "62.4% of the loop is BIOS/ISR" and sent a whole
    # slice after `BREAKX`, which turned out to be worth 0.3% (D-BRKFRAME). So the
    # program now RAISES A MARKER in the free RAM at MARK for exactly its own run, the
    # sampler records it beside each PC, and out-of-run samples are DISCARDED, not
    # averaged in. The rig REFUSES a window that mostly missed.
    prologue = (f'set ::pf [open "{log}" w]\n'
                f'proc samp {{}} {{ puts $::pf [reg PC] }}\n'
                f'for {{set i 0}} {{$i < {n}}} {{incr i}} {{ after time [expr {{{start} + $i * 0.005}}] samp }}\n'
                f'after time {start + secs + 1} {{ flush $::pf; close $::pf }}\n')
    lines = [f"10 A=TIME:{prog}:B=TIME", '20 PRINT"[sp";B-A;"]"', "RUN"]
    cap = omsx_repl.run_cases(cfg["machine"], [("sp", lines)], batch=False, boot=cfg["boot"], reset=cfg["reset"],
                              prologue=(prologue,), run_gap=secs + 5)[0] or ""
    i = cap.rfind("[sp"); print("jiffies:", cap[i:cap.find("]", i) + 1] if i >= 0 else "<none>")
    raw = [int(x) for x in open(log).read().split() if x.strip().isdigit()]
    # 🔴 DISCARD THE IDLE TAIL. The first two tables this rig produced were both
    # dominated by a single BIOS PC at 54-68% and both were ARTEFACTS: the window
    # outlived the program and every later sample landed on the READY prompt's HALT,
    # which is ONE PC and so symbolises as one enormous BIOS entry. That read as
    # "62.4% of the loop is BIOS/ISR" and sent a slice after `BREAKX`, which a direct
    # A/B then measured at 0.3% (D-BRKFRAME). Idle is a CONSTANT PC, and running code
    # never is, so a long constant run at either END of the sequence is the prompt:
    # trim it, say how much was trimmed, and REFUSE what is left if it is too thin.
    # (A marker byte POKEd from BASIC was tried first and is NOT the fix: the Tcl side
    # never saw it. The POKE is fine -- `POKE &HE21F,7` reads back 7 on zerobas and on
    # the CF-3300 -- so the suspect is `debug read memory 0xE21F`, left OPEN and not
    # asserted, because the guard below needs no marker at all.)
    # Idle is not a CONSTANT PC -- the prompt cycles a few addresses around its
    # HALT -- so contiguity is the wrong test and a trim on it finds nothing. What
    # idle IS: one BIOS PC holding a share no executing code ever holds. In a window
    # that fits the run, $11A0 does not reach the top SIXTEEN; in one that overruns
    # by half, it is 54.6% on its own. So: take the most-sampled PC, and if it is
    # BIOS and >=15%, it is the prompt -- drop those samples and say so out loud.
    top_pc, top_n = collections.Counter(raw).most_common(1)[0]
    idle = top_pc if (top_pc < 0x2812 and top_n >= 0.15 * len(raw)) else None
    pcs = [pc for pc in raw if pc != idle] if idle is not None else raw
    if idle is None:
        print(f"idle check: no single BIOS PC over 15% — the window fits the run "
              f"(top PC ${top_pc:04X}, {100 * top_n / len(raw):.1f}%)")
    else:
        print(f"⚠️  IDLE DISCARDED: ${idle:04X} held {100 * top_n / len(raw):.1f}% of "
              f"{len(raw)} samples — that is the READY prompt, not the program.")
        print(f"    The window OVERRAN the run by about that much. {len(pcs)} samples "
              f"kept; narrow start/secs to measure the run alone.")
    if len(pcs) < 200:
        print("=" * 74)
        print("APPARATUS FAILURE -- the window missed the program: NOTHING MEASURED")
        print("=" * 74)
        print(f"  window : {start}s .. {start + secs}s, {len(raw)} samples, {len(pcs)} in the run")
        print(f"  the run: {cap[cap.rfind('[sp'):].split(']')[0] + ']' if '[sp' in cap else '<never finished>'} frames")
        print("  Move the start/secs arguments inside the run, or make the program")
        print("  longer, and re-run. Refused instead of measured.")
        return 1
    syms = load_syms(os.path.join(REPO, "build", "basic-reloc.sym"))
    hist = collections.Counter(); region = collections.Counter()
    for pc in pcs:
        region["bios/low" if pc < 0x4000 else "page1" if pc < 0x8000 else "ram"] += 1
        hist[("BIOS/ISR" if pc < 0x2812 else symbolise(syms, pc)) if pc < 0x8000 else f"RAM ${pc:04X}"] += 1
    tot = len(pcs)
    print(f"samples: {tot} in-run of {len(raw)} taken  regions: {dict(region)}")
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
