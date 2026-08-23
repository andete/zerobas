# D-CLRFIX — predictions, written BEFORE the BEFORE-run

Baseline: `4db8010` + the two TODO commits, ROMs `59f0a082` / `490ffc49` /
`5ea13c71`. Main page 1 was **1 B free** on 2026-08-23.

## The design, priced from the source before any measurement

Two open items, one file, and 🔴 **the second one's fix is a CARVE**:

1. **`CLEAR ,200`** — `ex_clear`'s `cp ',' / jr z,clr_himem` (4 B) accepts a
   form NEITHER reference has. **DELETE IT: −4 B.** `eval_int16_checked` then
   sees the `,` as an empty operand, `ev_f_empty` sets the deferred FPERR=4,
   and `eval_int16_checked`'s OWN `call check_expr_errors` raises it as **ERR 2
   at `ex_clear`'s depth — before `POOLSIZE` is stored and before the wipe.**
2. **`CLEAR 200,`** — `clr_himem`'s bare `call eval` has no FPERR test.
   **ADD `call check_expr_errors`: +3 B**, between the `eval` and the
   `ld (HIMEM),de`, so the error is raised before the store AND before
   `clr_done` falls into `clear_vars`. It preserves DE and HL.

💰 **NET −1 B: main page 1 should go 1 B → 2 B free.** Two defects closed and
the wall left LOOSER than it was found.

⚠️ `clr_himem` has exactly ONE incoming jump instruction — the one being
deleted. After the carve it is reached by FALLTHROUGH only (`jr nz,clr_done`
above it). `clr_done` is a SHARED TAIL: `basic/files.asm:1740` also `jp`s to it.
Neither is being changed.

## Predicted rows — `scratchpad/clrfix_probe.py`, 13 rows × 3 machines

| row | statement | refs PREDICTED | zb BEFORE (predicted) | zb AFTER (predicted) |
|---|---|---|---|---|
| `q.trail`  | `CLEAR 200,`       | `24 0` (measured) | `UNTRAPPED Missing operand in 30` (measured) | `24 0` |
| `q.kcolon` | `CLEAR 200,:A=1`   | `24 0` (measured) | `UNTRAPPED Missing operand in 30` (measured) | `24 0` |
| `q.comma`  | `CLEAR ,200`       | `2 0` (measured)  | `0 0` (measured) | `2 0` |
| `q.commak` | `CLEAR ,200:A=1`   | `2 0`  | `0 0` | `2 0` |
| `q.conly`  | `CLEAR ,`          | `2 0`  | `0 0` | `2 0` |
| `q.div`    | `CLEAR 200,1/0`    | `11 0` | `11 0` **or** UNTRAPPED | `11 0` |
| `q.str`    | `CLEAR 200,"x"`    | `13 0` | `13 0` **or** `0 0` | `13 0` |
| `q.ovf`    | `CLEAR 200,70000`  | `0 0`  | `0 0` | `0 0` |
| `q.ok`     | `CLEAR 200`        | `0 0`  | `0 0` | `0 0` UNMOVED |
| `q.both`   | `CLEAR 200,&H9000` | `0 0`  | `0 0` | `0 0` UNMOVED |
| `q.bare`   | `CLEAR`            | `0 0`  | `0 0` | `0 0` UNMOVED |
| `q.kbare`  | `CLEAR:A=1`        | `0 0`  | `0 0` | `0 0` UNMOVED |
| `t.notrap` | `A=1/0`, no CLEAR  | `11 0` | `11 0` | `11 0` UNMOVED |

**PREDICT 5 DIFF before → 0 after** (`q.trail`, `q.kcolon`, `q.comma`,
`q.commak`, `q.conly`).

### Where I am NOT confident, and why the rows exist anyway

* 🔴 **`q.conly` (`CLEAR ,`) is a GUESS on the reference side.** Both slots
  dangle at once. It could be ERR 2 (the leading comma decides) or ERR 24 (the
  trailing one does). **D-LINERR's lesson is that slots do not inherit verdicts**
  — LINE's colour slot is 24 and its box slot, one field along, is 2. If it comes
  back 24, the deletion in (1) is still right and this row needs its own answer.
* 🔴 **`q.div` / `q.str` / `q.ovf` are the DENOMINATOR, not the subject.** They
  ask whether the unguarded HIMEM slot defers the OTHER fault codes too. I
  predict `q.div`/`q.str` already answer correctly here — `eval` raises a
  division by zero and a type mismatch through paths that are NOT deferred —
  but 🎯 **if any of them is UNTRAPPED before the fix, the class is wider than
  the two filed items and the same 3 B closes all of it.**
* ⚠️ **`q.ovf` (`CLEAR 200,70000`) I predict COMPLETES on all three**, because
  `clr_himem` uses bare `eval` with no int16 coercion — 70000 truncates into DE
  and is stored. If the references raise ERR 6, that is a THIRD defect in the
  same slot and it is NOT closed by this fix.

## Predicted rows — `scratchpad/clrfix_himem.py`, 7 rows × 3 machines

| row | statement | refs PREDICTED | zb BEFORE | zb AFTER |
|---|---|---|---|---|
| `h.none`  | *(no CLEAR)*       | `SAME` | `SAME` | `SAME` control |
| `h.ok`    | `CLEAR 200`        | `SAME` | `SAME` | `SAME` control |
| `h.set`   | `CLEAR 200,&H9000` | `->36864` | `->36864` | `->36864` control |
| `h.trail` | `CLEAR 200,`       | `SAME` (measured) | `62336->0` (measured) | **`SAME`** |
| `h.comma` | `CLEAR ,200`       | `SAME` | **`->200`** | **`SAME`** |
| `h.div`   | `CLEAR 200,1/0`    | `SAME` | `SAME` | `SAME` |
| `h.str`   | `CLEAR 200,"x"`    | `SAME` | ??? | `SAME` |
| `h.ovf`   | `CLEAR 200,70000`  | `->4464` | `->4464` | `->4464` |

🔴 **`h.comma` is the row that says the leading-comma defect WRITES too**, and
it has never been run. If it comes back `SAME` before the fix, the silent-write
class has one member here, not two.
⚠️ `h.ovf`'s `->4464` is 70000 mod 65536 — a prediction about TRUNCATION, and if
the references answer `SAME` they are raising ERR 6 where we truncate.

---

# 🔴 AMENDED after the BEFORE-run — the design changed because the class did

`scratchpad/clrfix_before.out` (13 rows, 8 DIFF), `scratchpad/clrfix_char_before.out`
(3 rows, 3 DIFF), `scratchpad/clrfix_himem_before2.out` (10 rows, 7 DIFF).

## What the baseline refuted

* 🔴 **MISS — `q.div` and `q.str`.** I predicted the HIMEM slot already handled
  a division-by-zero and a type fault correctly. Both are **UNTRAPPED** here.
  The slot has **no guard of any kind**: it defers every code, stores, wipes the
  trap in `clear_vars`, and aborts into a machine with no handler.
* 🔴 **MISS — `q.ovf` on the REFERENCE side.** I predicted `0 0` (truncation) on
  all three. Both references answer **ERR 6**. There is no int16 coercion in the
  HIMEM slot at all — a THIRD defect, unfiled before today.
* 🔴 **MISS — `q.commak` (`CLEAR ,200:A=1`) is `UNTRAPPED Out of memory`**, not
  `0 0`. 🎯 **And it refutes a claim in the source.** `basic/clear.asm:89` calls
  HIMEM *"record-only today"* and says *"No allocator consults HIMEM yet"*.
  `basic/str-engine.asm:133` `heap_reset` — **called by `clear_vars`, which
  `CLEAR` itself calls** — reads it: `FRETOP := min(HIMEM,TXTMAX)`. Setting
  HIMEM to 200 is what makes the very next `A=1` fail.
* ✅ HIT — `q.conly`'s reference half (`2 0`): the LEADING comma decides, and the
  slot does not inherit the trailing comma's 24.
* 🔴 **MISS — `q.conly`'s zerobas half.** I predicted `0 0`; it is
  `UNTRAPPED Missing operand`, because the accepted leading comma runs the
  dangling HIMEM slot.

## 🔴 And two findings nobody asked for

1. **`docs/clearpool-vg8020-characterization.md` §2.4 / §2.8 record REFERENCE
   readings for a statement the reference REFUSES.** `z.hd000`
   (`CLEAR ,&HD000`) is **ERR 2 on both**. So §2.4's *"`CLEAR 500 : CLEAR
   ,&HD000` → 500"* reads 500 because the second statement **never ran**, and
   `z.seq` shows it aborts the program: `UNTRAPPED Syntax error in 30` on both
   references — untrapped because `CLEAR 500` had already killed the handler,
   which is D-CLRTRAP's `t.after` firing again. **Three rows agree for the wrong
   reason, and `basic/str-engine.asm` `heap_reset`'s design comment cites them**
   (*"it still makes `CLEAR ,himem` keep its size (characterization §2.8)"*).
   The DESIGN is unaffected — deriving the boundary sub-side is still right for
   its own reasons — but its stated JUSTIFICATION is about a form that does not
   exist. Invert, do not delete [[a-fix-falsifies-the-justification-beside-it]].
2. **`z.neg` (`CLEAR 200,-1`) is ERR 5 on both references — a FOURTH defect —
   and it refutes the obvious fix for itself.** The pool argument next door
   rejects negatives with `bit 7,d / jp nz,gb_illegal`. **That test is WRONG
   here**: `CLEAR 200,&H9000` is ACCEPTED on all three (`h.set` → `->36864`) and
   `&H9000` has bit 15 set exactly as `-1` does. So HIMEM's domain is not a sign
   test; it is a RANGE, and its edges are unmeasured. **OUT OF SCOPE, FILED.**

## ✅ The amended design — and it is CHEAPER, not dearer

1. **DELETE `cp ',' / jr z,clr_himem` — −4 B.** Unchanged from above.
2. **`clr_himem`: `call eval` → `call eval_int16_checked` — 0 B, not +3 B.**
   That routine *is* `eval` + `check_expr_errors` + `get_int16_checked`, so one
   3-byte call for three: the FPERR guard (trap + write), the type fault, AND
   the ERR 6 the references raise on 70000. Its header states HL and DE survive
   and that the interposed frame is SP-safe.
   ⚠️ `&H9000` is **-28672** as a signed int16, so `|x| <= 32767` and `h.set`
   must keep answering `->36864`. That is the control this change could break.

💰 **NET −4 B. Main page 1 should go 1 B → 5 B free.**

## Amended predictions — 16 ERR rows, 10 HIMEM rows

**ERR: 11 DIFF → 1.** Closing `q.trail` `q.kcolon` `q.comma` `q.commak`
`q.conly` `q.div` `q.str` `q.ovf` `z.hd000` `z.seq`; **`z.neg` STAYS RED** and
is filed. Specifically: `q.div` → `11 0`, `q.str` → `13 0`, `q.ovf` → `6 0`,
`q.commak` → `2 0`, `z.seq` → `UNTRAPPED Syntax error in 30` (the trap really is
already dead there, so matching the reference means being untrapped too).

**HIMEM: 7 DIFF → 1.** `h.trail` `h.comma` `h.div` `h.str` `h.ovf` `h.hd000` all
→ `SAME`; **`h.neg` STAYS `->65535`** and is filed with `z.neg`.

**Controls that must not move:** `q.ok` `q.both` `q.bare` `q.kbare` `t.notrap`
`h.none` `h.ok` `h.set`.

---

# Knife predictions scored — round 1: **2 of 4**, and both misses are one omission

`scratchpad/clrfix_knives_round1.out`.

* ✅ **K-CF1 EXACT — 9 predicted, 9 moved.** Reverting the SWAP alone reddens
  `q.trail` `q.kcolon` `q.div` `q.str` `q.ovf` and `h.trail` `h.div` `h.str`
  `h.ovf`, and leaves every leading-comma row green.
* ✅ **K-CF2 EXACT — 7 predicted, 7 moved.** Restoring the CARVE alone reddens
  `q.comma` `q.commak` `q.conly` `z.hd000` `z.seq` and `h.comma` `h.hd000`, and
  leaves every trailing-comma row green.
  🎯 **The two sets are DISJOINT, which is the claim "this is two fixes, not
  one" — measured.** A differential could never have separated them: both halves
  landed in one commit and every row went green together.
* 🔴 **K-CF3 MISS, and K-CF4 MISS — the SAME omitted row, `h.neg`.** Both knives
  stop `CLEAR 200,-1` reaching `ld (HIMEM),de`, so its write row goes
  `->65535` → `SAME` in step with `z.neg`. The knives did exactly what they were
  designed to do; my prediction sets were short by one row each.
  🎯 **THE PATTERN IN THE MISS: every other ERR row in the file is predicted
  together with its HIMEM twin. The one row I omitted the twin for is the one
  row this slice does not fix** — the row I had written off as "out of scope,
  ignore". **Out of scope for the FIX is not out of scope for the DENOMINATOR**,
  and a row written off stops being carried in the bookkeeping while continuing
  to move.
* 🎯 **And the corrected K-CF3 is sharper than the version I predicted.** It
  turns **both** of the slice's surviving red rows green at once — `z.neg`
  `5 0` and `h.neg` `SAME`, matching the references on the ERR *and* on the
  write — while breaking `q.both` and `h.set`. That is
  [[a-case-that-agrees-can-agree-for-the-wrong-reason]] demonstrated on the
  exact rows the next slice will have to fix, and it is the reason §5 declines
  to guess HIMEM's domain.

Round 2 re-runs all four with the corrected sets; round 1 is kept.
