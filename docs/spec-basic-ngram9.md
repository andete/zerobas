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
| K-N9B | **retarget** the deferred-fault bail → `s.mid.sub` moves ERR 11 → ERR 13 | **exactly that 1** |
| K-N9C | **nop** the deferred-fault bail → asserted **0**, cause named (§4) | **0** |

## 4. 🔴 THE "STRUCTURALLY NULL" VERDICT WAS WRONG — D-N9BAIL, 2026-08-29

**What this section used to say.** Nop the `jp nz,fp_runtime_error` and nothing
moves, ROM provably changed; the bail changes *when* the fault is raised, not
*whether*; `exec_stmt`'s boundary check raises the same ERR 11 a few
instructions later; so no differential row *can* separate them, and the three
`jp nz,fp_runtime_error` are a **9 B candidate**, filed and not taken.

**Every clause of that is false, and one row settles it.** Do not nop the jump —
**retarget** it (`fp_runtime_error` → `type_mismatch_error`) and rebuild:

| row | HEAD | bail retargeted | bail nopped |
|---|---|---|---|
| `s.mid.sub` | `ERR 11 AT 30` | **`ERR 13 AT 30`** | `ERR 11 AT 30` |

The bail is **reached and taken**. The nop's zero came from a **second cause of
green inside the same statement** — and not the one that was written down.
`ex_mid_stmt`'s very next act after the target parse is `eval_pos_arg` →
`eval_byte_arg` → `get_byte_arg` → `get_int16_checked`, whose last instruction is
`jp check_fperr_only`. That re-raises the still-pending FPERR **before**
`exec_stmt`'s boundary is ever reached, which is why even the *line number* never
moved: `AT 30` both ways, where the boundary story predicts `AT 60`.

🔴 **And that cover is MID$'s alone.** The other two callers reach their
`check_expr_errors` only *after* their side effects:

| site | first act after `str_target_parse` | fault checked |
|---|---|---|
| `ex_mid_stmt` (str-engine.asm) | `eval_pos_arg` → `check_fperr_only` | **before any effect** |
| `inpc_line` (input.asm) | `read_line`, `tgt_store_str` | after both |
| `inp_readvar` (files.asm) | `read_into_strscr`, `tgt_store_str` | after both |

So removing it makes `LINE INPUT A$(0*(1/0))` **wait on the keyboard** where both
references raise at once, and makes both sites store through a `TGT_ADDR` that
`tgt_parse` never wrote on this path — it returns from `tp_ary`'s `ret nz`, ahead
of `tp_set`'s `ld (TGT_ADDR),de`, so the address is whatever the last resolved
target left there.

🎯 **The carve is DECLINED. The 3 B stays** — and note the filed price was itself
stale: D-NGRAM9 had already collapsed the three sites into one `jp`, so the
candidate was never 9 B after this slice shipped.

🎯 **The apparatus lesson is the general one.** A knife that prints `moved 0` for
a *masked* cut and for a *plant that never reached the ROM* is not telling you
which. K-N9C keeps the nop, and its zero is now **asserted with the cause named**;
K-N9B is the live arm that proves the bail is taken. Both are scored against an
explicit expected row set rather than against "did anything move".
[[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 5. One row is vacuous and is labelled as such

`INPUT#1,A` reads **ERR 59 on all three sides** — the channel check fires before
the type check, so it never reaches the site it was written for. The `inp_readvar`
site is therefore witnessed by **S1 only**, and that is said here rather than
left to look like coverage.
