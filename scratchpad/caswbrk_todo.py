#!/usr/bin/env python3
"""D-CASWBRK: the TODO.md entry (D-LOADERRRET's tape-write sites), anchored."""
import sys
p = "TODO.md"
s = open(p).read()
old1 = """      ➡️ **Left on this item:** the tape OPEN / SAVE
      header WRITES (STOP mid-write -- 🔬 TRIED 2026-10-08 and NOT READABLE with"""
new1 = """      ➡️ **Left on this item:** ~~the tape OPEN / SAVE
      header WRITES~~ (✅ D-CASWBRK, 2026-10-11 -- below; 🔴 the parenthesis that
      follows was WRONG: the press DOES land in a write, in its DATA) (STOP mid-write -- 🔬 TRIED 2026-10-08 and NOT READABLE with"""
old2 = """      (✅ D-CASTYPE, the same day -- below: the arm is unreachable now.)
"""
new2 = """      (✅ D-CASTYPE, the same day -- below: the arm is unreachable now.)
      ✅ **D-CASWBRK (2026-10-11): Ctrl-STOP BREAKS A TAPE WRITE -- 19 IN THE LINE,
      AS ON THE VG-8020; zerobas's TAPOUT NEVER LOOKED AT THE KEYBOARD.** The
      08 note's "the press does not land" was the RIG: a break one second in falls
      in the ~7 s header LEADER, which the VG-8020 does not break either, and a
      16 KB BSAVE outlived the capture. Diagnosed first
      ([`caswbrk_diag.py`](scratchpad/caswbrk_diag.py)): the rig's control
      (`Break in 15` on a FOR loop, both) lands; a CSAVE is still writing at 6 s
      ([`caswbrk_diag2.out`](scratchpad/caswbrk_diag2.out)); a Ctrl-STOP in the
      DATA of a 2 KB BSAVE / a 1.6 KB CSAVE / a PRINT # loop is `19 in 15` on the
      VG-8020 and ran to the end here
      ([`caswbrk_diag3.out`](scratchpad/caswbrk_diag3.out),
      [`caswbrk_diag4.out`](scratchpad/caswbrk_diag4.out)); STOP ALONE does not
      break it -- an 8 KB BSAVE under a STOP press every 4 s completed
      ([`caswbrk_diag5.out`](scratchpad/caswbrk_diag5.out)).
      🔧 tape/tape.asm: TAPOUT asks `BREAKX` ($00B7, C-BIOS's own CTRL+STOP test)
      before each byte -- a fixed 113 T at the byte boundary when STOP is up,
      compensated by its own `CAS_BYTECOMP` (+8 iterations); the waveform trace
      moved by −3 T at the byte boundaries and nowhere else
      ([before](scratchpad/caswbrk_castrace_before.out) /
      [after](scratchpad/caswbrk_castrace.out)). Paid for by `cas_baud`, which
      tested CS120 for nothing (a CS120 match and no match both gave 1200): 41 →
      15 B. 🔴 MY FIRST CUT DID NOT FIT: I read 55 B free after `tape_end`, and
      island 4 (`err_msgtab`) starts AT `tape_end` -- `build_mainrom.py` refused
      it. Tape region: 12 B left before island 4.
      BASIC: the tenant's tape engines take `sv_tape_err` (SV_STAT 19; sub/save.asm),
      `sv_tenant` raises it (not via DISKOP_ERR, where a stale 19 would turn a
      later tape INPUT #'s end into 19); SAVE's / OPEN's header and the block flush
      (`cas_flush_block`, whose carry was ignored) go to `dpl_dio`.
      🔴 **AND THE KEY THAT BROKE THE WRITE BROKE THE HANDLER TOO:** ours then read
      `Break in 90` -- the run loop polls the key's LEVEL, and the key was still
      down at the handler's first statement. The VG-8020 runs the handler and
      latches the break only ~0.73 s after the abort, then every ~60 ms, like key
      repeat (an INTFLG write watchpoint,
      [`caswbrk_hold_tap.out`](scratchpad/caswbrk_hold_tap.out)): the press is
      CONSUMED. TAPOUT now waits for the release before returning carry; a press
      shorter than ~0.7 s reads the same on both
      ([`caswbrk_hold_tap05.out`](scratchpad/caswbrk_hold_tap05.out),
      [`_tap09`](scratchpad/caswbrk_hold_tap09.out)). A key held longer still
      breaks the VG-8020's handler and not ours -- a recorded difference (docs).
      And a tape SAVE in a program reads **`19 in 65535`** on the VG-8020 (it
      leaves the run before writing; the handler is still taken): `cas_ascii_save`
      sets DIRECTF (`CURLINE := dir_line` first: ERL 0, a miss).
      Gate **`caswbrk-acceptance`** ([`basic_probe_caswbrk.py`](probes/basic/basic_probe_caswbrk.py),
      [`caswbrk_gate.out`](scratchpad/caswbrk_gate.out)): dcsave pcsave pbsave
      psave pprint pleader pctl phold, 8/8 (psave after the DIRECTF cut,
      [`caswbrk_psave.out`](scratchpad/caswbrk_psave.out)). 🔪
      [`caswbrk_knives.out`](scratchpad/caswbrk_knives.out): K-CW1 (no BREAKX)
      → the six write rows, K-CW2 (no wait) → five (`Break in 90`), K-CW3 (no
      DIRECTF) → psave, K-CW4 (sv_tenant's 19) → the tenant's four, K-CW5 (the
      flush) → psave pprint -- each exactly. Its first two runs were VOID, both my
      apparatus: the probe called IN-PROCESS, so the refcache (ROM identity
      memoised per process) served every cut reading; and that instant run let
      the next cut land in the same second as the last build, which `make` did
      not see (knife_guard refused it as inert). A process per reading and a
      clean build per cut now.
      🔮 Scored: the rig lands (HIT); a CSAVE takes seconds (HIT); a break at
      1 s / 3 s is 19 on the VG-8020 (MISS -- the leader); ours `19 in 15` after
      the BIOS fix (MISS -- `Break in 90`); the byte boundary within ±10 T (HIT,
      −3); the tape code ~40 B (HIT, +44 -- but the room was not there); the
      0.5 s hold no Break on the VG-8020 (HIT); the gate 8/8 first time (MISS:
      psave); the knives 5/5 (HIT). Main page 1 −14 B, sub page 1 −4 B.
      ➡️ **Not measured, the READ twin:** a LOAD / CLOAD broken in its DATA (not
      the search, D-CASBRK). zerobas's TAPIN does not ask BREAKX either; the
      VG-8020's answer is unmeasured. Filed as D-CASRBRK (TIER 3), below.
"""
for old, new in ((old1, new1), (old2, new2)):
    n = s.count(old)
    if n != 1:
        sys.exit(f"REFUSE: anchor found {n}x: {old[:60]!r}")
    s = s.replace(old, new)
open(p, "w").write(s)
print("ok")
