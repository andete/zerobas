# D-PUDOLLAR — `PRINT USING`'s `$$` floating dollar

**Status:** shipped 2026-09-09. **Measurement:** `scratchpad/dollar_probe.py`
(`scratchpad/dollar_run.out` before, `scratchpad/dollar_after.out` after).
**Gate:** `probes/basic/basic_probe_pusing.py`, rows `d.*`.
**Knives:** `scratchpad/pudollar_knives.py`.

D-USING swept `PRINT USING`'s whole format vocabulary — 14 rows — and found the
implementation broadly right, with **three reference splits and no single
oracle**: two string specifiers the CF-3300 refuses are implemented here
(following the VG-8020), while `$$` was resolved the CF-3300's way. Nothing had
chosen either; both were outcomes. This closes the third one and, with it, the
item's actual finding.

## 1. It is a CAPABILITY gap, not a house style

The 2026-09-04 standing ruling — *a purely presentational reference split ships
the VG-8020 value on both targets* — looks like it settles this row and is the
wrong instrument for it. `$$###` is the **floating-dollar** specifier, not a
literal `$` in a fixed field:

| | rendering of `USING"$$###";42` | reading |
|---|---|---|
| VG-8020 | `  $42` | five columns, the pair's two positions reserved, one spent on a `$` that **floats** against the number |
| CF-3300 | `$$ 42` | the two dollars echoed **literally**, the number right-justified in the remaining three |

🎯 **AND THE PROOF IS ONE ROW UP IN THE SAME PROBE.** `USING"**###";42` reads
`***42` on **all three machines**. `**` and `$$` are the same grammatical
construct — a two-character prefix that reserves its own positions and then
fills or floats — and the CF-3300 implements `**` correctly while echoing `$$`.
That is not a style; it is a **missing case in the CF-3300's own vocabulary**,
and its own `**` row is what says so. So this resolves the ordinary way, the way
`&` and `\   \` already did: **follow the reference that implements the
specifier.**

## 2. The rule, measured

Thirteen rows, three machines. The VG-8020's rule is one sentence: **the `$` is
CONTENT, not padding** — it takes a column from the value, sits immediately
before the digits and after any sign, and the pair adds 2 to the field width
exactly as `**` does.

| row | format · value | VG-8020 | CF-3300 | what it pins |
|---|---|---|---|---|
| `d.basic` | `$$###` · 42 | `  $42` | `$$ 42` | the anchor: 5 columns, `$` against the number |
| `s.wide` | `$$#####` · 42 | `    $42` | `$$   42` | the pair reserves exactly 2, whatever the run |
| `s.full` | `$$###` · 12345 | `%$12345` | `$$%12345` | the `$` **overflows the field** — it is content |
| `s.neg` | `$$###` · −42 | ` -$42` | `$$-42` | sign OUTSIDE the `$`, not ` $-42` |
| `s.dec` | `$$##.##` · 3.5 | `  $3.50` | `$$ 3.50` | floats past the decimal field too |
| `s.ovf` | `$$#` · 1234 | `%$1234` | `$$%1234` | the `%` marker survives |
| `s.comma` | `$$#####,` · 12345 | ` $12,345` | `$$12,345` | and past comma grouping |
| `s.plus` | `+$$###` · 42 | `  +$42` | `+$$ 42` | the sign specifier may PRECEDE the pair |
| `s.one` | `$###` · 42 | `$ 42` | `$ 42` | **refs agree**: a lone `$` is a literal |
| `s.last` | `##$` · 42 | `42$` | `42$` | **refs agree**: so is a trailing one |

`s.full` is the row that separates "the `$` is a pad character" from "the `$` is
content", and it is the reason the implementation counts it into the LENGTH
rather than emitting it from the pad loop: counted that way, the ordinary
`jr c,pet_over` fires and the overflow marker costs no code of its own.

## 3. Where the code went, and what it cost

Recognition and width live in `basic/pu-render.inc` (`ptf_dollar`,
`ptf_num_fill`), which is a **sub-ROM page-0 tenant**; the emit lives in
`sub/printusing.asm`'s `pu_emit_tenant`, which D-PUEMIT had already moved
sub-side. So the whole specifier is a sub-ROM change with one resident byte.

**The flag has no home in `PU_FLAGS`, which is FULL** — bit0 trailing separator,
bit1 wrapped, bit2 `**`, bits3–5 the sign specifier, bit6 `.`, bit7 `,` and
D-PUEXP. It rides **`PU_TYPE` bit 2** instead: that byte holds four field types
in bits 0–1 and had six bits free, and the floating dollar is a **modifier on
the numeric type** rather than a type of its own. Every reader therefore masks —
`and $03` for the type, `and $04` for the flag — and that one `or a` → `and $03`
in `basic/printusing.asm` is the entire resident cost.

**Cost: main page 1 130 → 129 B (1 B). Sub page 0 1313 → 1184 B (129 B).**
⚠️ The estimate written before building was ~60 sub-ROM bytes; the measurement is
129. The estimate was short and is recorded as short.

## 4. What is NOT implemented, and why it is written down

Two rows stay divergent. Both were divergent before this change; neither is
regressed by it, and leaving them unnamed is how a denominator rots
([[a-row-written-off-as-out-of-scope-leaves-the-bookkeeping]]).

* **`s.trail` — `USING"###$$";42`.** VG-8020 ` 42`, CF-3300 and zerobas ` 42$$`.
  The reference **consumes** a trailing pair and emits nothing for it. This is
  why `ptf_dollar` requires the pair to be followed by `#`, where `ptf_star`
  requires no such thing: without that test the pair would be consumed here too
  and the row would move to a third answer that matches nobody. The narrower
  recogniser leaves it exactly where it already was.
* **`s.stardol` — `USING"**$$###";42`.** Three machines, three answers:
  VG-8020 `$42$`, CF-3300 `42$$`, zerobas `****$42`. The VG's is **four columns
  wide** where the two prefixes together reserve four and the run is three, so
  it is parsing something this document has not identified. ➡️ **The next row to
  run is `**$###`** — MS-BASIC documents `**$` as the *combined* fill-and-float
  form, which would make `**$$###` a `**$` prefix followed by a literal `$` and
  is the only reading offered so far that produces four columns. Not asserted:
  it is a hypothesis from one observation until that row is run
  ([[a-mechanism-inferred-from-one-observation]]).

## 5. The gate needed a category it did not have

All eight in-scope rows are reference SPLITS, and `basic_probe_pusing.py` scored
only rows where the two references AGREE — splits went to `NO_ORACLE`, printed
and never scored. Pinning `$$` therefore needed a third category, `CHOSEN`,
naming the reference a documented call selected.

🔴 **AND ITS ABSENCE WAS ALREADY COSTING TWO ROWS.** `x.amp` (`&`) and
`x.slash` (`\   \`) have followed the VG-8020 since the verb was written, on
exactly this capability argument — the CF-3300 raises `ERR 5` on two string
specifiers it does not implement — and both sat in `NO_ORACLE`. That is shipped,
deliberate behaviour that **no gate could redden**. They are now `CHOSEN` too, so
the extension pins **nine** rows rather than the seven this change is about.

⚠️ A row may join `CHOSEN` only if the choice is written down where a person can
read it: `$$` here, the two string rows in D-USING. **A split resolved in a
commit message is not resolved.**
