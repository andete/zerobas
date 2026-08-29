# D-NGRAM8 — `str_arg_snap` for LEFT$/RIGHT$/MID$, and the decline a `call` broke

*2026-08-28. `basic/str-engine.asm`. Probe `scratchpad/ngram8_probe.py`, arms
`scratchpad/ngram8_knives.py`.*

**Cost: −8 B net of the page-0 low region (106 → 114 B free)** — 12 B of carve
minus 4 B the decline needs back. **Rows: 17, 5 DIFF, all pre-existing.**

## 1. The carve

LEFT$, RIGHT$ and MID$ all open identically: evaluate the source expression,
decline if it is not a string, snapshot it into an owned temp before the count
argument is evaluated. Three identical runs → one body plus three 3 B calls.

## 2. 🔴 A `call` MOVED THE DECLINE ONE FRAME DEEPER, AND THE DECLINE STOPPED DECLINING

Open-coded, `jp nc,str_eval_no` ran in the **verb's** frame, so `str_eval_no`'s
`ret` declined out of LEFT$/RIGHT$/MID$ entirely. Behind a `call` it runs one
frame deeper, and that `ret` lands back **inside** the verb, just after the call
— the verb carries on as though nothing happened.

`pop af` before the jump restores the original stack shape. **+4 B, and not
optional.** [[a-shared-tail-is-not-a-decision]]

## 3. 🎯 THE TARGETED PROBE MISSED IT, AND WHY

A 12-row differential against both oracles ran *before* the battery and read
**0 DIFF**. `penderr-acceptance` caught the regression instead. Two reasons, and
both are fixable rather than inherent:

**(a) An existing DIFF row masks a new breakage on the same path.** The probe
*had* decline rows — `LEFT$(5,2)` — but they were already `DIFF` (the known
ERR 2 / ERR 13 divergence, §4). When the decline itself broke they still read
`ERR 2`, so nothing changed in the report. A row that is already failing cannot
report a *second*, different failure.

**(b) The missing axis was ORDER, and the missing shape was the ASSIGNMENT.**
What separates a working decline from a broken one is a fault raised *before* it.
Porting `penderr`'s row was not enough on its own: `PRINT LEFT$(0*(1/0)+1)` reads
identically on HEAD, the shipped tree **and a deliberately broken one**. Only
`Q2$=LEFT$(0*(1/0)+1)` — the assignment — separates them.

Measured three ways (HEAD / shipped / decline deliberately broken), the probe now
carries three rows that read **ERR 11, ERR 11, ERR 2**. It would have caught this
in ~40s instead of a 430s battery.

## 4. The divergence: found, attributed, and NOT fixed

`LEFT$(5,2)` answers ERR 2 where both references answer ERR 13 — pre-existing
(verified by reverting the carve). **Both obvious fixes are wrong, measured:**

* a direct `jp type_mismatch_error` **overrides a fault already pending**;
* a *deferred* `type_mismatch_set` is worse — at that instant the argument has
  **not been evaluated**, so nothing is pending, the type mismatch is armed
  first, and first-error-wins then **blocks** the real fault the numeric re-drive
  raises.

`penderr-acceptance` row `o.pt.left` caught both. The reference evaluates the
expression and reports what *it* raises; only a clean expression is a type
mismatch. That is a change to what happens **after** the decline, not inside
`str_arg_snap`. Filed.

## 5. K-N8B is a genuine null

Removing the snapshot moves nothing, with the ROM provably changed. Rows were
built to break it — a computed source (`A$+B$`) and counts that really allocate
(`LEN(B$+B$)`); the first attempt used `LEN("XY")`, which allocates nothing.
⚠️ Absence of a witnessing row is **absence of evidence**, not proof it is dead.
