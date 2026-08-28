# D-NGRAM5 — one `goto_take_bc` for GOSUB / ON..GOTO / ON..GOSUB

*2026-08-28. `basic/program.asm`. Probe `scratchpad/ngram5_probe.py`, arms
`scratchpad/ngram5_knives.py`.*

**Cost: −24 B of main page 1 (275 → 299 B free).** Low region unchanged.
**Rows: 9, DIFF 0/9** against both references.

## 1. The shape

The identical 15 B run stood at three sites — `ex_gosub`, `eon_goto`,
`eon_gosub`:

    call find_line_bc / jp nc,ex_goto_undef
    ld (GOTOTGT),hl / ld a,1 / ld (GOTOFLAG),a / ret

🎯 **The last site KEEPS the code and is simply labelled**, so the third jump
costs nothing: two `jp`s replace two 15 B runs. All three enter with `BC` = the
target line and any pushed frame already made.

⚠️ **THIS IS NOW A SHARED TAIL, AND A SHARED TAIL IS A LABEL, NOT A DECISION.** A
change sited in `goto_take_bc` serves all three verbs; anything that should apply
to one of them belongs at that site, above the jump.
[[a-shared-tail-is-not-a-decision]]

## 2. 🔴 THE SUCCESS ROWS WERE VACUOUS, AND THE KNIFE IS WHAT SAID SO

The first row set wrote `ON 1 GOTO 60` and expected the harness's value line to
print. **But the setup lines sit at 20/30/… and the value line *is* 60 — so
falling through lands in exactly the same place as taking the jump.** Four rows
that could not tell the two apart, all green.

K-N5A broke the arming half outright (`ld a,1` → `xor a`, so `GOTOFLAG` is never
set) and **moved zero rows.**

🎯 **AND THE GUARD IS WHAT MADE THAT READABLE.** D-KNIFEROM shipped hours
earlier; the runner reported `ROM 06ef1f67 → a57e2aef`, so this was a genuine
*"the cut reached the artifact and reddened nothing"* rather than an inert cut.
Without it, the honest reading would have been *"cannot tell"* — and the likely
reading would have been *"the arm is fine"*.

The fix is a line **between** the jump and its target that only runs when the
jump is not taken:

    A=1 : ON 1 GOTO 60      <- line 20
    A=2                     <- line 30, skipped iff the transfer happened
    ...A                    <- line 60

Jump taken → `1`; fallen through → `2`. All three machines read `1`.

## 3. Falsification — the two halves, separated

| arm | requires | measured |
|---|---|---|
| **S1** (static) | exactly 1 open-coded run (the body itself) and exactly 2 jumps to it | ✅ |
| K-N5A | break the ARMING half → only the 4 transfer rows move | **exactly those 4** |
| K-N5B | break the FAILING half → only the 3 undefined-line rows move | **exactly those 3** |

A perfect mirror, and that is the point: an arm that moved *everything* would
prove the body is reached and say nothing about **which instructions carry which
verdict**. S1 is static for the reason D-NGRAM3 established — a site left
open-coded behaves identically at runtime.
