# D-ARGOPEN — one prologue for LEFT$ / RIGHT$ / MID$, and the knife that changed the design

*2026-08-30. `basic/str-engine.asm`. Probe `scratchpad/ngram8_probe.py` (24
rows), knives `scratchpad/argopen_knives.py`. Low region **66 -> 107 B free**
(a reading; run `make basic-reloc`).*

## 1. The duplicate

`str_fn_left`, `str_fn_right` and `str_fn_mid` open with the same 16
instructions: the `(` test, both empty-argument tests, `str_arg_snap`, the `,`
test, and the temp-address capture. Only what follows differs — LEFT$/RIGHT$
evaluate a 0-based count, MID$ a 1-based position.

🔴 **The byte-level ranking sees two sites, not three.** `str_fn_mid` spells the
same four exits with `jp` where the others use `jr`, so the spans are not
byte-identical and `ngram_sweep` reports a 2-site / 16 B run. The third site is
~33 B the ranking cannot see. **Grep the idiom, then check the jump form** —
[[grep-the-idiom-beats-the-clone-ranking]].

## 2. 🔴 The bail is the design, and the first design was unwitnessable

Every exit in the run is an **outward** jump: `str_arg_empty` ends
`jp str_eval_no`, which declines out of the *verb* by returning to the verb's
caller. Behind a `call`, that `ret` lands back inside the helper instead
([[factoring-a-run-into-a-helper]] — the same fault as `tcr_ovf`, fixed hours
earlier in `sub/tkfloat.asm`).

The obvious repair is the one already standing 200 lines above in `sas_decline`:
`pop af` to discard the helper's own return address, so the bail runs at the
verb's depth. **That was written, and it is correct, and its knife moved ZERO
rows.**

🎯 **Not because it was wrong — because it cannot be witnessed.** That bail's
only outcome is a *deferred error*, and every path that reports one resets `SP`.
The frame damage is erased before any row reads anything.
[[a-guard-witnessed-only-by-a-deferred-error]]

So the shape changed: `str_arg_open` returns **CF clear** and each caller does
its own `jr/jp nc,str_arg_empty`, at the depth the open-coded copies had. **6
bytes more, and a guard a row can see.** That is the shape the TODO item filed
that morning had named as the safe one — and then not the one first implemented.

## 3. Why `sas_decline`'s pop *is* witnessed, and needs a second one

A **decline is not an error.** `str_eval_no` returns CF clear so the caller can
retry the operand numerically, and that retry is visible: `LEFT$(5,2)` answers
`Type mismatch`. K-AO1 moves 8 rows.

And because `str_arg_snap`'s three call sites are now **one**, its decline is two
frames deep, so it discards two return addresses. ⚠️ **Correct only while that
count is one** — arm S1 pins it.

## 4. The arms, and the three mistakes they caught

| | |
|---|---|
| S1 | 1 `call str_arg_snap`, 3 `call str_arg_open`, 0 open-coded copies, 3 caller guards |
| K-AO1 | `sas_decline` back to one frame -> **8 / 8** |
| K-AO2 | drop all three caller guards -> **1 / 1** |

🔴 **S1's first version counted its own documentation.** `src.count("nc,str_arg_empty")` returned
4; the fourth was the comment explaining the guard. It now matches an
instruction, anchored to line start. **Second time in one session** — the grep
that cleared `FOUTBUF` for D-STRFLT listed `sub/strheap.asm` as a writer for a
comment written an hour earlier.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

🔴 **K-AO1 was "corrected" from 8 to 2 using a number taken on a superseded
build.** The first run measured 2 — but that tree still had `str_arg_open`
discarding its own return address, so *two* frame errors were cancelling and six
rows stayed put. Re-measured on the shipping shape it is 8, which is what the
original prediction said. **A measurement is scoped to the tree it was taken
on.**

🔴 **K-AO2 predicted 4 and measured 1, and the 1 is a finding about the family.**
With the guard gone the verb evaluates the malformed tail — and `LEFT$("AB")`,
`MID$("AB")` and `RIGHT$()` all leave the cursor on a `)`, whose evaluation
raises the **same** deferred ERR 2 the guard would have. The answer converges
whichever path produced it. Only `LEFT$"AB"` separates them, because with no `(`
the cursor is on a string literal. One witnessed row is what the CF-return
shape's 6 bytes buy over the `pop af` shape's zero — and that is still the right
trade.

## 5. Verification

`scratchpad/ngram8_probe.py` **0 DIFF of 24** (four malformed-call rows added
here). `make penderr-acceptance` 61/61, `o.pt.left` — the row that caught the
original frame bug — reading 11 on all three. `make unit-test` ALL 59 PASSED.
Full battery green.
