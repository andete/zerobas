# D-MATHACC — `ATN` and `EXP` scored against truth, and the filed item was wrong three ways

**2026-09-01.** `TODO.md` carried:

> **`ATN(1)`, `EXP(-100)` and `EXP(100)` differ in the LAST DIGIT only.** …
> A mathpack rounding question. 🤖 AUTONOMOUS — the references settle it.

Every clause of that is wrong, including the marker's premise. **The references
do not settle it — they are the less accurate side.** Closed with no code change.

## The instrument: a truth column, not a differential

A differential says two implementations disagree. It cannot say who is wrong, and
this item is *entirely* a question of who is wrong. So every row is scored
against a 60-digit `decimal` oracle (Euler's arctangent series; `Decimal.exp()`),
reported as **signed error in units of the last place** of the 14-significant-digit
result MSX BASIC prints. 38 rows: 26 `ATN`, 10 `EXP`, 2 controls.

## What it found

### `EXP` — zerobas is right and the references are badly wrong

| row | correctly rounded | references (ulp) | zerobas (ulp) |
|---|---|---|---|
| `EXP(1)` | `2.7182818284590` | −2.5 | **−0.5** |
| `EXP(2)` | `7.3890560989307` | −6.5 | **−0.5** |
| `EXP(10)` | `22026.465794807` | −6.7 | **+0.3** |
| `EXP(-10)` | `4.5399929762485E-05` | +11.1 | **+0.1** |
| `EXP(50)` | `5.1847055285871E+21` | −73.7 | **+0.3** |
| `EXP(-50)` | `1.9287498479639E-22` | **+330.8** | **−0.2** |
| `EXP(100)` | `2.6881171418161E+43` | −74.4 | **−0.4** |
| `EXP(-100)` | `3.7200759760208E-44` | +100.6 | **−0.4** |

zerobas is within **±0.5 ulp on all ten** `EXP` rows. The references reach
**330.8 ulp**. "Differ in the last digit only" is not a description of a 330-ulp
error — it describes which printed *column* first differs, which is not the same
thing and is why the item read as trivial for a month.

🔴 **AND THE IMPLIED FIX WOULD HAVE BEEN A REGRESSION.** Matching the references
here means adopting a 330-ulp error. That is exactly the mistake recorded two
items above in the same file, where **D-EXPNEG "fixed" the negative tail to match
the references and was reverted in full**.

### `ATN` — no defect, and my own first reading was wrong

`ATN(1)` alone looks damning: truth `.78539816339745`, references `+0.2 ulp`,
zerobas `+1.2 ulp`. On one argument zerobas is simply worse.

**Twelve arguments still said that. Twenty-six refuted it.**

| | arguments |
|---|---|
| zerobas 1 ulp **worse** | `0.1`, `0.75`, `1`, `-0.75`, `-1` |
| zerobas 1–2 ulp **better** | `0.3`, `0.4` (2 ulp), `0.8`, `0.9`, `1.25` |
| equal magnitude, opposite sign | `3` |
| identical | the remaining 15 |

Five worse, five better, neither correctly rounded (both are −1.9 ulp at
`ATN(1.5)`). This is not a bias, it is two implementations rounding differently
in the last place.

**Totals over all 38 rows — rows ≥ 0.5 ulp from truth:**

| VG-8020 | CF-3300 | zerobas |
|---|---|---|
| 23 | 23 | **16** |

## Two hypotheses of mine, both refuted by widening the denominator

1. *"zerobas's `ATN` is 1 ulp high; the references are right; fix it."* True of the
   filed argument and of eleven others. **False as a rule** — the extra fourteen
   arguments found five where zerobas is the better one.
2. *"The error is one-sided (+1 ulp in magnitude, never −1), so it lives in the
   final rounding rather than the polynomial."* That was the reason to widen the
   sweep, and the sweep killed it: `ATN(0.4)` is **2 ulp better** on zerobas and
   `ATN(3)` lands on the opposite side.

🎯 **A SPOT FINDING ROTS THE WAY A RANKING DOES.** One argument was enough to file
a defect and would have been enough to "fix" one that does not exist. The
denominator is what turned a defect into a non-finding.

## The oracle failed first, and plausibly

The first run printed `ATN(100)` as `1.0623664808539` in a column headed
*correctly rounded*, while all three machines agreed on `1.5607966601082`. **The
machines were right and the grader was wrong.** Euler's series converges on
`z = x²/(1+x²)`, which is `0.9999` at `x = 100`; the loop hit its iteration cap
and **returned the truncated sum**, which is a perfectly plausible arctangent.

Fixed two ways, both needed: range reduction (`|x| > 1` via
`atan(x) = π/2 − atan(1/x)`, so the series is only ever asked for `|x| ≤ 1`), and
**refusing instead of returning** when it does not converge. Verified against a
50-digit `π/4` literal and by `atan(x) + atan(1/x) = π/2`.
[[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]

## Disposition

**Nothing to fix; the item is closed.** `EXP` is a deliberate divergence in
zerobas's favour, the same class as `docs/spec-basic-mathpack-slice2.md` §12.9,
now backed by ten rows instead of two. `ATN` is a wash. Rows live in
`scratchpad/mathacc_probe.py` — re-runnable, with the truth column, so the next
reader gets the measurement rather than the impression.
