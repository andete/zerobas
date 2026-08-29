# D-NGRAM9 — one `str_target_parse`, and ERR 2 where both references say ERR 13

*2026-08-28. `basic/interp.asm` (helper), `files.asm`, `input.asm`,
`str-engine.asm`. Probe `scratchpad/ngram9_probe.py`, arms
`scratchpad/ngram9_knives.py`.*

**Cost: +16 B net** — low 114 → 134 B free, page 1 335 → 331 (the helper is
page-1, one site was low). **Rows: 8, DIFF 2 → 0.** The divergence fix is **0 B**.

## 1. The carve

INPUT#'s variable list, LINE INPUT and the MID$ statement all ran the identical
13 B sequence: require the `$` suffix, raise without it, parse the reference
(array element included), raise a deferred numeric fault from the subscript.

🟢 **BOTH BAILS NEVER RETURN**, and that was *checked, not assumed*: `stmt_error`
and `fp_runtime_error` each reset SP from `SAVSTK`, so unlike D-NGRAM8's decline
there is no `ret` whose depth a `call` could change. That check exists because
D-NGRAM8 got it wrong the day before.

## 2. The divergence: 0 B, three sites at once

`MID$(A,1,1)="X"` and `LINE INPUT A` with a numeric `A` answered **ERR 2 Syntax
error**; both references answer **ERR 13 Type mismatch**. Pre-existing, verified
against HEAD.

Because the three sites had just become one, the fix is a single retargeted
`jp z` — **0 B**, and the wall reads 134 B free before and after.

⚠️ **A DIRECT RAISE IS SAFE HERE AND WAS NOT IN D-NGRAM8.** This test is the
*first* thing the statement does, so no fault can already be pending for it to
override. That is the exact trap D-NGRAM8 fell into twice, and the difference is
positional, not stylistic.

🎯 **AND THE GATES THAT COULD BREAK WERE RUN BEFORE THE SUITE.** `stmt_error`
also stores `ERRMARK $DD`, which `missing.asm` reads, so `missing-acceptance`,
`stmtpend-acceptance` and `penderr-acceptance` were run directly after the
change — 60/60 and 61/61, green — rather than waiting 430s to find out.

## 3. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** | 0 open-coded runs, exactly 3 calls, **matcher alive** | ✅ |
| K-N9A | restore the old target → exactly the 2 numeric-target rows return to ERR 2 | **exactly those 2** |
| K-N9B | break the deferred-fault bail | **0 rows — structurally null, below** |

## 4. 🔴 K-N9B IS NULL FOR A STRUCTURAL REASON, NOT A MISSING ROW

Nop the `jp nz,fp_runtime_error` and **nothing moves**, ROM provably changed.
The reason is not row coverage: that bail changes **when** the fault is raised,
not **whether**. With it gone the fault stays pending and `exec_stmt`'s
boundary check raises the same ERR 11 a few instructions later — the machine's
observable behaviour is identical, so no differential row *can* separate them.

⚠️ That makes those three `jp nz,fp_runtime_error` a **9 B candidate**, filed and
not taken. *"No row can see it"* is a statement about the row set only when the
difference is observable at all — and here it may genuinely not be. Reading the
`exec_stmt` contract settles this one, not another knife.

## 5. One row is vacuous and is labelled as such

`INPUT#1,A` reads **ERR 59 on all three sides** — the channel check fires before
the type check, so it never reaches the site it was written for. The `inp_readvar`
site is therefore witnessed by **S1 only**, and that is said here rather than
left to look like coverage.
