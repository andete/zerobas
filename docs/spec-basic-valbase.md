# D-VALBASE — `VAL("&HFF")` is 255, and the rule was measured before a line was written

*2026-08-30. `sub/strheap.asm` (`sh_val_parse`), `basic/str-engine.asm`
(`ev_ff_val` glue). Probe `scratchpad/val_probe.py`, arms
`scratchpad/valbase_knives.py`.*

**Cost: 17 B of the low region** (119 → 102 B free) **+ 126 B of sub page 0**
(2329 → 2203 B free). Page 1 unchanged. **Rows: 49, DIFF 20 → 14.**

## 1. The first third of D-VAL

D-VAL measured `VAL`/`STR$` as integer-only and split the gap three ways:
**base literals**, **fractions**, **exponents**. This slice takes the base
literals, which need no float pack at all — just an integer accumulate in the
parser that already exists.

## 2. The rule, measured first

Nine edge cases were added to the probe and read off both references **before any
code was written**, because the shape of the fix depends on all of them:

| shape | references |
|---|---|
| `&HFF` · `&hff` · `&HFFZZ` · `"  &HFF"` | **255** — case-insensitive, stops at the first invalid digit, leading spaces fine |
| `&O17` · `&B101` | **15** · **5** |
| `&HFFFF` | **-1** — the accumulator is a *signed* int16 |
| `&H1FFFF` | **ERR 6** — overflow past 16 bits |
| `&H` · `&HZZ` · `&O9` · `&B2` | **0** — a prefix with no valid digit is **not** an error |
| `&` · `&17` | **ERR 2** — `&` not followed by H/O/B |
| `-&H10` | **0** — a sign before a base literal does not apply |

🎯 **That last row cost nothing to honour.** The `&` test sits *before* the sign
test, so a leading `-` consumes itself and the digit scan then meets `&` and
stops — 0 falls out for free.

⚠️ **And `VAL` "never raises" is not true here.** Two of these shapes *do* raise,
which is why the glue needed a refusal path at all.

## 3. Two bugs, and how each was caught

**A register clobber, caught by tracing — not by a row.** The first draft used
`C` as scratch for both the max digit *and* the shift count, so `C` no longer
held the packed base constant on the **second** digit. I found it reading the
register flow before running anything. The count now goes on the stack, freeing
`B` to carry the digit across the shifts, and `C` survives untouched.
[[a-scratch-register-that-was-the-callers-value]]

**Inverted error codes, caught immediately by rows.** The refusal path wrote the
*MSX* error numbers and added 3 to reach the `SH_ERR` codes — which swapped them,
so `VAL("&")` raised Overflow and `VAL("&H1FFFF")` raised Syntax error. The
cleverness bought nothing; explicit constants replaced it.

## 4. Falsification

| arm | requires | measured |
|---|---|---|
| K-VB1 | disable the `&` dispatch → every base row collapses | **exactly 10** |
| K-VB2 | swap the refusal codes → the shipped bug returns | **exactly 3**, and in the way it was first seen |
| K-VB3 | clobber the packed constant → the traced bug becomes a row | **8 rows**, `&HFF` → **15** |

🔴 **K-VB3's first version was a designed no-op.** It inserted `pop af / push af`
— which leaves the stack exactly as it found it — and reported `moved 0`,
indistinguishable from a cut with nothing to say. Only the arm's declared
expectation (`want ANY`, because a corruption is not a redirect) caught it. The
cut now destroys `C` directly after the restore, which is what the bug did, and
`&HFF` → 15 is that bug's signature: first digit parsed, second rejected against
a max of 0. [[popraise-slice]]

🎯 K-VB3 exists because **the register bug was found by reading**. Turning that
reading into a row is what stops the next person "simplifying" the register
discipline back into the bug.

## 5. What remains

The other two thirds of D-VAL — **fractions** and **exponents** (plus `STR$` of
any non-integer) — still diverge, 14 rows. Those need the float scanner, and
D-VAL §5.2 has the design: `tk_float` with a ~9 B scratch and a variant entry
that returns, rather than the whole tokeniser and ~256 B of new RAM.
