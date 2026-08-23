#!/usr/bin/env python3
"""D-CLRFIX: close both CLEAR items in TODO.md and open the one that is left."""
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = "TODO.md"
s = open(p).read()

OLD_A = """      does not. Harmless today only because `clear.asm` calls HIMEM
      *"record-only"*. 💰 Main page 1, 4 B free on 2026-08-23 — unpriced.
"""
NEW_A = """      does not.
      ✅ **CLOSED 2026-08-23 (D-CLRFIX,
      [`docs/spec-basic-clrfix.md`](docs/spec-basic-clrfix.md)) AT ZERO BYTES**:
      `clr_himem`'s `call eval` became `call eval_int16_checked`, which IS
      `eval` + `check_expr_errors` + `get_int16_checked` — one 3-byte call
      replacing another. The raise now happens before `ld (HIMEM),de` and before
      `clear_vars`, so the trap survives and nothing is written.
      🔴 **AND THE ITEM UNDERSTATED THE CLASS BY A FACTOR OF FIVE.** The slot had
      no guard of ANY kind: `CLEAR 200,1/0` and `CLEAR 200,"x"` were untrapped
      too, and `CLEAR 200,70000` completed where both references answer ERR 6
      (no int16 coercion at all). Seven statements wrote HIMEM, not one.
      🔴 **AND THE "harmless today, record-only" CLAUSE ABOVE IS FALSE** — it was
      copied from a comment in `basic/clear.asm` that is itself false and is now
      inverted there. `basic/str-engine.asm` `heap_reset`, called from
      `clear_vars`, computes `FRETOP := min(HIMEM,TXTMAX)`. Row `q.commak`
      (`CLEAR ,200:A=1`) answered **`Out of memory`** because of it.
"""
assert s.count(OLD_A) == 1, "item A anchor"
s = s.replace(OLD_A, NEW_A)
s = s.replace("- [ ] 🔴 **`CLEAR 200,` RAISES THE RIGHT ERROR AND LOSES THE TRAP, *AND* IT",
              "- [x] ✅ **CLOSED — `CLEAR 200,` RAISED THE RIGHT ERROR AND LOST THE TRAP, *AND* IT", 1)

OLD_B = """- [ ] 🔴 **`CLEAR ,200` IS `Syntax error` ON BOTH REFERENCES AND COMPLETES
      SILENTLY HERE.** Filed 2026-08-23, D-CLRTRAP §3.3, row `q.comma`: refs
      **`2`**, zb **`0`**. [`basic/clear.asm`](basic/clear.asm)'s
      `cp ',' / jr z,clr_himem` accepts a "string space omitted" form that
      neither reference has — own design, and it was found by a row written as a
      *control* for a form I had assumed was legal. 🎯 **The prediction miss is
      the lesson: I read `clr_himem`'s EXISTENCE as evidence about the
      LANGUAGE.** Unpriced; main page 1.
"""
NEW_B = """- [x] ✅ **CLOSED 2026-08-23 — `CLEAR ,200` WAS `Syntax error` ON BOTH
      REFERENCES AND COMPLETED SILENTLY HERE, AND THE FIX IS A CARVE**
      (D-CLRFIX, [`docs/spec-basic-clrfix.md`](docs/spec-basic-clrfix.md) §2).
      Filed 2026-08-23, D-CLRTRAP §3.3. 💰 **DELETING
      [`basic/clear.asm`](basic/clear.asm)'s `cp ',' / jr z,clr_himem` is −4 B**,
      and the leading comma then reaches the POOL argument's
      `eval_int16_checked`, whose own `check_expr_errors` raises the references'
      ERR 2 at `ex_clear`'s depth — before `POOLSIZE` is stored and before the
      wipe. **The right answer out of machinery that was already there.**
      🎯 The original lesson stands and got worse: I read `clr_himem`'s
      EXISTENCE as evidence about the LANGUAGE — and so had a characterization
      document. 🔴 **`docs/clearpool-vg8020-characterization.md` §2.4 / §2.8
      record REFERENCE readings for `CLEAR ,&HD000`, which is ERR 2 on both
      machines**: the pool reads "unchanged" because the statement NEVER RAN.
      Row `z.seq` runs §2.4's line verbatim and both references answer
      `UNTRAPPED Syntax error in 30`. Three vacuous rows, annotated in place, and
      `basic/str-engine.asm` `heap_reset` cited them for a benefit to a form the
      language does not have.

- [ ] 🔴 **`CLEAR 200,-1` IS `Illegal function call` ON BOTH REFERENCES AND
      COMPLETES HERE, WRITING `HIMEM = 65535` — AND THE OBVIOUS FIX IS
      REFUTED.** Filed 2026-08-23 by D-CLRFIX §5, rows `z.neg` (`5 0` vs `0 0`)
      and `h.neg` (`SAME` vs `->65535`), `scratchpad/clrfix_probe.py` /
      `scratchpad/clrfix_himem.py`. The last divergent row of that slice's 26,
      and the only member of D-MISSOP's silent-write class still live at CLEAR.
      🔴 **DO NOT COPY THE POOL ARGUMENT'S TEST.** Two lines up, CLEAR's
      *string-space* argument rejects negatives with `bit 7,d / jp nz,gb_illegal`.
      **That is WRONG for HIMEM**: `&H9000` has bit 15 set exactly as `-1` does,
      and `CLEAR 200,&H9000` is ACCEPTED on all three machines (row `h.set`,
      `->36864`). **HIMEM's domain is a RANGE, not a sign**, and its edges are
      unmeasured — guessing one would repeat D-CIRCDOM's blessed-domain mistake.
      📏 **What is needed first is a characterization sweep against both
      references**: where the accept/reject boundary sits between `&H9000` and
      `-1`, whether it is absolute (a RAM top) or relative (below the current
      ceiling / above the program), and what a value BELOW the program text does.
      🎯 **Knife K-CF3 already shows how easy it is to get this wrong**:
      narrowing the coercion to a byte turns BOTH red rows green — matching the
      references on the ERR *and* on the write — while breaking `q.both` and
      `h.set`. A fix for this row that does not keep `h.set` at `->36864` is not
      a fix. 💰 Unpriced; main page 1, which D-CLRFIX left at 5 B free
      (2026-08-23).
"""
assert s.count(OLD_B) == 1, "item B anchor"
s = s.replace(OLD_B, NEW_B)
open(p, "w").write(s)
print("TODO.md patched")
