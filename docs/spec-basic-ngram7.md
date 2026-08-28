# D-NGRAM7 — one `gfx_call` for the three graphics-tenant entries

*2026-08-28. `basic/graphics.asm`. Probe `scratchpad/ngram7_probe.py`, arms
`scratchpad/ngram7_knives.py`.*

**Cost: −20 B of main page 1 (315 → 335 B free).** **Rows: 7, DIFF 0/7.**

## 1. The shape

PSET/PRESET (`GFX_OP=1`), LINE/box (3) and PAINT (5) opened with the identical
15 B run: store the op, guard the token cursor across `CALSLT`, point `IX` at
the page-0 tenant, call, restore `HL`, bail if the sub-ROM is absent. 45 B
becomes a 16 B body plus three 3 B calls.

⚠️ **A SHARED TAIL IS A LABEL, NOT A DECISION.** A change in `gfx_call` serves
all three verbs. PAINT alone reads `GFX_POVF` afterwards, and that stays at *its*
site. [[a-shared-tail-is-not-a-decision]]

## 2. The readback had to survive the mode switch

The harness captures a SCREEN 0 text screen, so a row that ends in SCREEN 2
reads `<NO OUTPUT>` on all three sides — three blanks agreeing, which D-NGRAM2
already paid for once. Each row draws in SCREEN 2, captures the pixel with
`POINT` into a variable, returns to SCREEN 0, and prints the variable.

⚠️ At most **four** setup lines: the harness puts the value on line 60 and a
fifth collides with it. It says so and refuses, which is the right behaviour —
the statements are joined with `:` instead.

## 3. 🔴 AN S1 ARM WHOSE EXPECTED COUNT IS ZERO CANNOT TELL A CLEAN TREE FROM A BROKEN MATCHER

S1 failed first time. The cause was not the code: the sweep's instruction keys
**keep the spacing** around `+`/`*`
(`ld ix,subrom_entry_base_p0 + 3*subrom_idx_graphics`), and my pattern had none.
It matched **nothing** — and reported *"0 open-coded runs left"*.

Here that was caught because the arm also expects the *body* to still match
(`want 1`). **But D-NGRAM6's S1 expects zero**, and a typo'd pattern reports zero
just as loudly as a converted tree. That arm now carries a **positive control on
the matcher itself**: the pattern's own first instruction must still be found
somewhere, proving the keys are spelled the way the sweep spells them.

🎯 **The general rule: any arm whose expected count is 0 needs a second
assertion that the instrument can still find *something*.** Otherwise "nothing
is wrong" and "nothing is being looked at" are the same reading.
[[readout-blind-to-its-own-subject]]

## 4. Falsification

| arm | requires | measured |
|---|---|---|
| **S1** | 1 open-coded run left (the body) and exactly 3 calls | ✅ |
| K-N7A | send the tenant op 0 → all 5 subject rows move, both controls hold | ✅ |
