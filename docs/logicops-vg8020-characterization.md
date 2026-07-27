<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The logical operator layer, characterised against the VG-8020

**Status:** MEASUREMENT RECORD, 2026-07-27. Input to the `EQV`/`IMP` slice that
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) §4.1 makes next.
Produced by [`probes/basic/basic_probe_logicops.py`](../probes/basic/basic_probe_logicops.py)
(`make logicops-characterize`). Reference: `Philips_VG_8020`, built-in MSX-BASIC,
no cartridge.

The decision doc attached a condition to the slice:

> MSX precedence is `NOT` > `AND` > `OR` > `XOR` > `EQV` > `IMP`, with `IMP`
> lowest. **That ordering must be characterised against the VG-8020 before it is
> encoded**, not asserted from the manual — the spec owes a differential row per
> adjacent pair.

This is that characterization. It measures more than the adjacent pairs: **every
ordered pair**, in both directions, so the total order is over-determined rather
than chained through six single observations.

## 1. Method — the model is a generator, the ROM is the oracle

The trap being avoided is the one kwsweep already caught once: **a case that
agrees can agree for the wrong reason** (`PRINT TAB(99999)` matched on both sides
and `TAB(` does not exist). The mirror trap here would be to *assume*
`EQV a b = NOT (a XOR b)`, derive a distinguishing operand triple from that
assumption, and read the precedence off it — confident nonsense if the
assumption is wrong.

So each precedence question is answered from **three measured values**, and the
hypothesis is used only to *search* for operands where the answer is visible:

```
PRINT [x A y B z]     <- U, the question
PRINT [(x A y) B z]   <- L, "A binds tighter"    } both MEASURED on the ROM,
PRINT [x A (y B z)]   <- R, "B binds tighter"    } never computed
```

`L == R` is a real answer — the groupings coincide, so nothing constrains the
pair — and is reported as `UNOBSERVABLE` rather than counted as a pass.

**Calibration.** `AND`/`OR`/`XOR`/`NOT` are already implemented, so every row
built only from those runs on both machines and must agree. If the calibration
battery is red the apparatus is what is broken and no reading from the same run
is trustworthy. It is 100% green throughout the results below.

## 2. Semantics — measured, not assumed

| expression | ROM | expression | ROM |
|---|---|---|---|
| `0 EQV 0` | `-1` | `0 IMP 0` | `-1` |
| `0 EQV -1` | `0` | `0 IMP -1` | `-1` |
| `-1 EQV 0` | `0` | `-1 IMP 0` | `0` |
| `-1 EQV -1` | `-1` | `-1 IMP -1` | `-1` |
| `12 EQV 10` | `-7` | `12 IMP 10` | `-5` |
| `1 EQV 0` | `-2` | `1 IMP 0` | `-2` |

Both are plain 16-bit **bitwise** operators, and the closed forms hold on every
row measured:

* **`EQV a b = NOT (a XOR b)`** (bitwise XNOR — commutative)
* **`IMP a b = (NOT a) OR b`** (bitwise implication — **not** commutative:
  `0 IMP -1` = `-1` but `-1 IMP 0` = `0`)

## 3. Precedence — every ordered pair

Read `A/B` as the expression `x A y B z`. Both directions of each pair were run;
they agree everywhere, which is the point of running both.

| pair | verdict | pair | verdict |
|---|---|---|---|
| `AND`/`OR`, `OR`/`AND` | **`AND` tighter** | `XOR`/`EQV`, `EQV`/`XOR` | **UNOBSERVABLE** |
| `AND`/`XOR`, `XOR`/`AND` | **`AND` tighter** | `XOR`/`IMP`, `IMP`/`XOR` | **`XOR` tighter** |
| `AND`/`EQV`, `EQV`/`AND` | **`AND` tighter** | `EQV`/`IMP`, `IMP`/`EQV` | **`EQV` tighter** |
| `AND`/`IMP`, `IMP`/`AND` | **`AND` tighter** | `OR`/`EQV`, `EQV`/`OR` | **`OR` tighter** |
| `OR`/`XOR`, `XOR`/`OR` | **`OR` tighter** | `OR`/`IMP` | **`OR` tighter** |

The measured total order is therefore

> `NOT` (unary) > `AND` > `OR` > `XOR` ≡ `EQV` > `IMP`

which **confirms the manual's ordering**, with one refinement the manual does not
make and cannot be read off it:

⚠️ **`XOR` and `EQV` are mutually indistinguishable.** They are mutually
associative — `(x XOR y) EQV z` and `x XOR (y EQV z)` are equal for *all* x,y,z,
because both reduce to `x ^ y ^ z ^ -1`. **No operand triple can order them**, so
placing `EQV` one level looser than `XOR` is a free implementation choice, not a
behavioural claim. The same holds for `IMP`/`OR` in the order `x IMP y OR z`
(`(~x|y)|z == ~x|(y|z)`), but the reverse order `x OR y IMP z` *does*
discriminate and settles `OR` > `IMP`.

`IMP/OR` being unobservable in one direction and decisive in the other is exactly
why every ordered pair was measured rather than one direction per pair.

### 3.1 Associativity

Every level is left-associative, but **`IMP` is the only one where that is
observable** — `AND`/`OR`/`XOR`/`EQV` are all associative, so `(a op b) op c`
and `a op (b op c)` coincide and measure nothing.

| expression | `(a op b) op c` | `a op (b op c)` | ROM | verdict |
|---|---|---|---|---|
| `0 IMP 0 IMP 0` | `0` | `-1` | **`0`** | **left-associative** |

### 3.2 The whole chain, end to end

`0 AND 0 OR 0 XOR 0 EQV 0 IMP 1` → ROM **`1`**; full-left grouping `1`, full-right
grouping `0`. The operands were searched for so that the two groupings disagree —
the first chain tried (`1 AND 1 OR 0 XOR 1 EQV 1 IMP 0`) had both groupings equal
to `1` and would have "confirmed" the table while measuring nothing.

## 4. Operand domain — the ROM dictates

The readout is `EQV n 0`, which is injective (`EQV n 0 == NOT n`), so the printed
value names the converted operand exactly. `IMP n -1` was tried first and is
constant `-1` — it would have measured nothing.

| expression | ROM | converted operand |
|---|---|---|
| `2.2 EQV 0` | `-3` | `2` |
| `2.5 EQV 0` | `-3` | `2` |
| `2.7 EQV 0` | `-3` | `2` |
| `3.5 EQV 0` | `-4` | `3` |
| `1.5 EQV 0` | `-2` | `1` |
| `-2.2 EQV 0` | `1` | `-2` |
| `-2.5 EQV 0` | `1` | `-2` |
| `-2.7 EQV 0` | `1` | `-2` |

**Float operands TRUNCATE TOWARD ZERO** — they do not round. `2.7` → `2` and
`-2.7` → `-2`; `2.5` and `3.5` land on `2` and `3`, which rules out both
round-half-up and round-half-to-even. This matches what zerobas already does at
its existing logical/`\`/`MOD` operand sites (`fac_to_int_strict`), so it is a
confirmation rather than a new requirement.

| edge | ROM |
|---|---|
| `32767 IMP 0` | `-32768` |
| `32768 IMP 0` | **`Overflow`** |
| `32767.4 EQV 0` | `-32768` (operand `32767`) |
| `32767.6 EQV 0` | `-32768` (operand `32767` — truncation cannot push it out of range) |
| `-32768 EQV 0` | `32767` |
| `-32769 EQV 0` | **`Overflow`** |
| `1E10 EQV 1` | **`Overflow`** |
| `"A" EQV 1`, `1 EQV "A"` | **`Type mismatch`** |
| `&HF0F0 IMP &H0FF0` | `4095` |

Domain is signed 16-bit `-32768..32767`; outside it, `Overflow`. Because
conversion truncates rather than rounds, an in-range float can never be pushed
out of range by the conversion itself.

## 5. Boundaries with the neighbouring layers

Judged by the same three-measured-values rule.

| question | bare | L | R | verdict |
|---|---|---|---|---|
| `1 = 1 IMP 1 = 0` | `0` | `0` | `-1` | **relational binds tighter than `IMP`** |
| `1 IMP 2 + 3` | `-1` | `-1` | `1` | **arithmetic binds tighter than `IMP`** |
| `1 EQV 2 + 3` | `-5` | `-5` | `-1` | **arithmetic binds tighter than `EQV`** |
| `NOT 1 IMP 2` | `3` | `3` | `1` | **`NOT` binds tighter than `IMP`** |
| `NOT 1 EQV 2` | `3` | `3` | `3` | UNOBSERVABLE |

⚠️ **`NOT` vs `EQV`/`XOR` is unobservable, and the obvious test rows are traps.**
`EQV` and `XOR` *absorb* a complement — `EQV (NOT a) b == NOT (EQV a b)` — so
both groupings agree for every operand pair. The first rows written here
(`NOT 0 EQV 0`, `NOT 0 IMP 0`) printed the same value under both groupings and
would have been reported as confirmations of the ordering while measuring
nothing at all. They were replaced with operands where `L != R` wherever the pair
is observable, and the pairs that stay unobservable are reported as such.

## 6. Two divergences found on the way, neither about `EQV`/`IMP`

Both were surfaced by this probe's **calibration** battery going red — rows built
only from operators zerobas already implements — and both were confirmed
boot-per-case. Both are the silent-wrong-answer class that
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) D-KW-3 names as the
one worth clearing. **Neither is a regression**: both reproduce on `AND`/`XOR`,
which predate all of this. They are recorded here and gated as known-red in
battery 6 — not quietly dropped, and not silently fixed inside an unrelated
slice.

### D-LOG-1 — chained relationals are not parsed

MSX-BASIC chains relational operators left-associatively. zerobas's `ev_rel`
handles exactly one relational operator (plus the two-token `<=`/`>=`/`<>`
merge) and leaves the rest of the chain on the cursor, where `PRINT` resumes and
emits a **second value**.

| expression | reference | zerobas |
|---|---|---|
| `1 = 0 = 0` | `-1` | `0 -1` |
| `1 = 1 = 1` | `0` | `-1 0` |
| `3 = 3 = -1` | `-1` | `-1 0` |
| `1 < 2 = -1` | `-1` | `-1 0` |
| `1 = 1 = 1 = 1` | `0` | `-1 0 0` |
| `(1 = 0) = 0` | `-1` | `-1` ✅ control |

The parenthesised control agrees, which localises the defect to the **chaining**,
not the comparison.

### D-LOG-2 — a string as the LEFT operand of a logical operator is not rejected

| expression | reference | zerobas |
|---|---|---|
| `"A" AND 1` | `Type mismatch` | `A 0` |
| `"A" XOR 1` | `Type mismatch` | `A 1` |
| `"A" EQV 1` | `Type mismatch` | `A-2` |
| `"A" IMP 1` | `Type mismatch` | `A-1` |
| `1 AND "A"` | `Type mismatch` | `type mismatch` ✅ control |
| `1 EQV "A"` | `Type mismatch` | `type mismatch` ✅ control |

`ev_rel`'s `str_eval` probe consumes the string operand and returns it as a
string value; `PRINT` prints it and resumes on what is left. The **right** operand
is rejected correctly, which localises the defect to the LHS probe path. (The
lowercase error wording is a separate, documented divergence.)

Both are **out of scope for the `EQV`/`IMP` slice** and want their own decision.
They sit in `ev_rel`, one layer below the one being restructured.

## 7. Method notes worth keeping

* **Measure every ordered pair, not just the adjacent ones.** `IMP`/`OR` is
  unobservable in one direction and decisive in the other. A chain of six
  single-direction observations would have had a hole in it and no way to notice.
* **A "confirmation" that cannot fail is not a confirmation.** Three separate
  rows here (`NOT 0 EQV 0`, `NOT 0 IMP 0`, and the first whole-chain line) had
  both groupings equal, so they agreed with the hypothesis no matter what the ROM
  did. Every grouping question in this probe now reports `UNOBSERVABLE` when
  `L == R` instead of counting it as a pass — the honest answer, and the one that
  showed the rows needed replacing.
* **Pick a readout that is injective.** `IMP n -1` is constant `-1`; the entire
  rounding investigation would have measured nothing through it. `EQV n 0` names
  the converted operand exactly.
* **A known-red row must not gate the apparatus.** The two §6 divergences are
  excluded from the calibration count and reported in their own battery.
  Otherwise a permanent red makes the "apparatus suspect" warning permanent, and
  a warning that is always on is a warning nobody reads.
