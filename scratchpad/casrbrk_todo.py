#!/usr/bin/env python3
"""D-CASRBRK: close the TODO item, anchored."""
import sys
p = "TODO.md"
s = open(p).read()
old = """- [ ] 🔍 **D-CASRBRK — A TAPE *READ* BROKEN WITH Ctrl-STOP IN ITS DATA (filed
      2026-10-11 from D-CASWBRK, the write twin)**"""
new = """- [x] ✅ **D-CASRBRK — A TAPE *READ* BROKEN WITH Ctrl-STOP IN ITS DATA (filed
      2026-10-11 from D-CASWBRK, the write twin; FIXED THE SAME DAY -- at the end)**"""
if s.count(old) != 1:
    sys.exit("REFUSE header")
s = s.replace(old, new)
old2 = """      BREAKX test per byte in TAPIN is ~7 B. The read path is edge-timed, not
      cycle-counted, so the test belongs where TAPIN waits for the start bit.
"""
new2 = old2 + """      ✅ **FIXED 2026-10-11 -- 19 FOR EVERY READ VERB, IN THE LEADER AND IN THE
      DATA, AS ON THE VG-8020.** Measured first
      ([`casrbrk_diag.py`](scratchpad/casrbrk_diag.py)): a BLOAD broken in its
      data is `19 in 15` on the VG-8020, read on to the end here; a LOAD of an
      ASCII file broken anywhere is an UNTRAPPED `Device I/O error` there (the
      program, handler and all, is gone at `Found:`), here the lines read so far
      were kept, silently ([`casrbrk_diag.out`](scratchpad/casrbrk_diag.out),
      [`_diag2`](scratchpad/casrbrk_diag2.out); my first binary tape loaded at
      &H8000, over the program -- `Syntax error in 12592` on both, void).
      🔧 tape/tape.asm: `cas_stop` (BREAKX, then wait for the release -- the
      consumed-press rule of D-CASWBRK, shared with TAPOUT's) at TAPIN's entry;
      paid for by folding `cas_latch` + the two inline level reads into
      `cas_level` (−5 B). A test at TAPION's relock was tried and DROPPED: its
      knife moved nothing, TAPIN catches every break first
      ([run 1](scratchpad/casrbrk_knives_run1.out)). Tape region: 4 B left before
      island 4 (2026-10-11).
      BASIC: BLOAD's data arms go to `bl_tape_dio` (19), and its SIX ADDRESS
      READS, which ignored CF, are a loop that tests it (−18 B, sub page 1) --
      🔴 broken there, BLOAD loaded the tape over garbage addresses and the
      screen came back as noise (`bb2`). The ASCII loader took a cut read for
      the end: `cal_getbyte` marks a read PAST the latched end (a clean file
      always meets its Ctrl-Z first) and `cas_ascii_drive` raises 19 after it
      puts the hook back (LOAD and MERGE); `cas_in_getbyte` raises it for
      INPUT # (it said 55). `cas_ascii_load` replaces the program BEFORE the
      blocks are read, with DIRECTF set, as the VG-8020 does at `Found:`
      (ours said `in 22`, and trapped a break the reference cannot).
      🔴 Two misses of my own on the way: the drive's first check returned the
      `cp 3` carry on success, so EVERY clean LOAD read `load error`; and one
      edit script refused on an anchor taken from a comment-stripped view.
      Gate **`casrbrk-acceptance`** ([`basic_probe_casrbrk.py`](probes/basic/basic_probe_casrbrk.py),
      [`casrbrk_gate.out`](scratchpad/casrbrk_gate.out)): bnb bb2 bb8 bhold anb
      ab2 ab8 ab15 cnb cb8 mb8 inb ib8, 13/13. 🔪
      [`casrbrk_knives.out`](scratchpad/casrbrk_knives.out) +
      [run 1](scratchpad/casrbrk_knives_run1.out): K-CR1 (TAPIN's test) → the
      nine broken rows, K-CR3 (BLOAD's address loop) → bb2, K-CR4 (BLOAD's data
      arm) → bb8 bhold, K-CR5 (the drive's raise) → ab8 ab15 mb8, K-CR6
      (INPUT #'s raise) → ib8 -- each exactly.
      🔮 Scored: the VG-8020 breaks a read (HIT); ours reads on (HIT); MERGE
      trapped `E19 in 15` (MISS -- untrapped, MERGE lets go of the program too);
      ib8 E55 here (HIT); the leader rows diverge (HIT, two of them); K-CR1 first
      run (MISS -- TAPION caught two rows), K-CR2 → ab2 (MISS -- nothing),
      K-CR3..6 (HIT). Main page 1 −8 B, sub page 1 +18 B (clean build, 2026-10-11).
"""
if s.count(old2) != 1:
    sys.exit("REFUSE body")
s = s.replace(old2, new2)
open(p, "w").write(s)
print("ok")
