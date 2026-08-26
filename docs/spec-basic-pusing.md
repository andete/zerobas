<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PUSING — `PRINT USING` had two answers where the references have five, and the fix is a CARVE

Status: **✅ SHIPPED.** 2026-08-26, on `054a17f`. **18 rows × 3 machines,
references unanimous on all 18, 13 DIFF → 0, at −6 B.**
`scratchpad/pusing_probe.py` (`pusing_base.out`, `pusing_r2.out`,
`pusing_r3.out`, `pusing_after.out`). Predictions pinned in
`pusing_predictions.md` before each of the three rounds.

Opened by D-MISSOP3, which measured exactly two of these rows.

---

## 1. The readout has an EFFECT column, and the slice needed it

`[ERR L]`, where `L` is `CSRLIN` taken immediately after the statement with the
cursor parked at row 5. **`L`=5 means nothing was printed; `L`=6 means one line
was.**

An error code alone cannot tell a silent *no-op* from a silent *print*, and this
verb's whole job is printing. Every reference error row reads `L`=5 — **nothing
is emitted before the raise** — which is what says the fix must reject *before*
`pu_emit_tail`, not after.

---

## 2. The measured rule set — five answers, not two

| condition | reference | zerobas before |
|---|---|---|
| no format at all (EOL or `:`) | **24** Missing operand | 2 |
| format present, **not a string** | **13** Type mismatch | 2 |
| format present, separator absent **or `,`** | **2** Syntax error | *proceeded* |
| `;`, no values, format **HAS** a field | **24** Missing operand | *silent, printed* |
| `;`, format has **NO** field (values or not) | **5** Illegal function call | *printed the literal* |
| `;`, values, format has a field | **0** | 0 ✅ |

🔴 **`,` IS NOT A SEPARATOR HERE, THOUGH IT IS BETWEEN VALUES.**
`PRINT USING"##",5` is ERR 2 on both references and printed here;
`PRINT USING"##";1,2` is fine on all three. **Two commas, two grammatical
positions, two answers** — and they were measured separately (§4).

---

## 3. 🔴 THE NARROWING ROWS REFUTED MY RULE — IN THE OPPOSITE DIRECTION FROM D-ONLIST

Round 1 predicted two rules and added `u.lit` / `u.litsemi` to **keep the fix
narrow**: a field-less format is complete on its own, so `pu_has_field` is the
right discriminator. **All three round-1 misses are those narrowing rows.**

| row | I predicted refs | refs ACTUALLY |
|---|---|---|
| `u.fmtsemi` `PRINT USING"##";` | `2 5` | **`24 5`** |
| `u.lit` `PRINT USING"abc"` | `0 6` | **`2 5`** |
| `u.litsemi` `PRINT USING"abc";` | `0 6` | **`5 5`** |

🎯 **THIS IS D-ONLIST'S LESSON WITH THE SIGN FLIPPED.** There the references were
**lazier** than I assumed, and the *must-not-move* rows stopped me shipping three
regressions. Here they are **stricter**, and the same instinct stopped me
shipping a fix that would have closed 2 rows, left 11, and called the item
closed. **The rows you add to bound a fix are worth as much when they widen it as
when they narrow it** — and you cannot know which in advance, which is the whole
argument for adding them before the design rather than after.

`pu_literal_only` — *"literal-only format: emit the whole format, swallow any
value list, newline. Rare/degenerate but kept well-defined"* — implements
behaviour **neither reference has.**

---

## 4. 🎯 THE ROW THAT DECIDED A BLOCK WAS DEAD

`pu_literal_only` had **exactly one** incoming jump. Round 2 existed for one row:

| row | statement | refs |
|---|---|---|
| `u.litval` | `PRINT USING"abc";5` | **`5 5`** |

A field-less format errors **in every case**, so once that jump became
`jp nc,pu_ifc` the block was unreachable — **`make deadcode` would have refused
the build until it went.** The gate is what turns *"this is now wrong"* into
*"this cannot be left behind"*.

⚠️ **AND ROUND 2's OWN MISS IS THE COMMA.** `u.comma` was written down as a
**control** and predicted `0 6`; it is `2 5`. A row filed as a control is still a
prediction.

Round 3 then bounded the fix with two rows that had to be measured **separately**
rather than inferred from `u.comma`:

| row | statement | refs | zb | |
|---|---|---|---|---|
| `u.valcomma` | `PRINT USING"##";1,2` | `0 6` | `0 6` | ✅ `,` **is** valid between VALUES — `pu_msep_chk` untouched |
| `u.chan` | `OPEN"CRT:"…:PRINT#1,USING"##";5` | `0 6` | `0 6` | ✅ the `PRINT#` entry needs no separate work |

`ex_print_using` is shared by `PRINT`, `LPRINT` and `PRINT#`; without `u.chan`
the fix would have changed two verbs with rows for only one.

---

## 5. The fix — −6 B, because the deletion outweighs the additions

```
ex_print_using:  or  a / cp COLON  ->  loc_missing        +9 B   (24)
                 jp nc,stmt_error  ->  type_mismatch_error  0 B   (13)
  separator:     ';' only, ',' and EOL -> stmt_error       -3 B   (2)
  field test:    jr nc,pu_literal_only -> jp nc,pu_ifc    +13 B   (5, +24 check)
  pu_ifc:        ld a,5 / jp raise_error                   +5 B
  DELETE pu_literal_only / pu_lo_skip / pu_lo_end         -30 B
```

**Main page 1: 83 → 89 B**, read from clean — the arithmetic exactly. ROM
`24d8e393` → `71f79f1e`, `sub.rom` unmoved.

🎯 **THE EOL TEST IS WHAT SPLITS THE OLD SHARED TAIL.** `str_eval` declines both
for *"nothing is here"* and for *"this is not a string"*, and the references
answer **24** and **13**. Taking the missing case off the front means an `NC`
below can only mean the second — no flag, no second test.

⚠️ **`pu_main`'s OWN END-OF-LIST TEST CANNOT SERVE AS THE NO-VALUES CHECK.** It is
also reached from `pu_msep` after a **trailing** separator, which is legal and
suppresses the newline. The new check sits before `pu_main`'s first entry only.

---

## 6. 🔬 Knives — 4 of 5 EXACT, one cut per rule

`scratchpad/pusing_knives.py` / `pusing_knives.out`. Five cuts, one per rule the
slice introduced. Restore byte-exact (`71f79f1e`), `sub.rom` unmoved throughout.

| knife | re-merges | predicted | moved | |
|---|---|---|---|---|
| K-PU1 | missing format → the field-less raiser | `u.none` → `5 5` | 1 | ✅ |
| K-PU2 | non-string format → `stmt_error` | `u.num`, `u.numsemi` → `2 5` | 2 | ✅ |
| K-PU3 | `,` accepted as the format separator | `u.comma` → `24 5` | 1, to **`0 6`** | 🔴 |
| K-PU4 | field-less format → `loc_missing` | 3 rows → `24 5` | 3 | ✅ |
| K-PU5 | `;`-with-no-values test removed | `u.fmtsemi` → `0 6` | 1 | ✅ |

🎯 **K-PU5 IS THE ONE THAT MATTERS MOST AND IT LANDED**: it restores the exact
silent completion that opened this slice, so the row reporting the defect really
is the row the fix serves.

🔴 **K-PU3's MISS IS MINE, NOT THE KNIFE'S.** It moved exactly the one row
predicted — the cut is correctly scoped — but to `0 6`, not the `24 5` I wrote
down. With `,` accepted again, `PRINT USING"##",5` simply *proceeds and prints*:
the format has a field and a value follows, so there is nothing to be missing.
`24 5` would need the value to be absent too. **I predicted the row and not the
mechanism**, which is the same error in miniature as predicting a rule from a
neighbouring row — and `u.comma` is now the second time this one row has been
predicted wrong (§4).

⚠️ **K-PU3's FIRST DRAFT JUMPED TO A LABEL THAT DOES NOT EXIST.** Its cut is
*"stop rejecting"*, and there was no existing non-error target to land on, so the
cut has to introduce its own. A knife that cannot assemble is not a lenient
knife, it is no knife — the anchor check caught it before any build.

---

## 7. What this does NOT establish

* **`LPRINT USING` has no row.** It shares `ex_print_using` and `u.chan` covers
  the `PRINT#` entry, but the printer path is untested here.
* A **trailing** separator after values (`PRINT USING"##";1;`) is unmeasured —
  it is the newline-suppression case and this slice did not touch `PU_FLAGS`.
* The FIELD grammar itself (`#`, `!`, `&`, `\`, `+`, `.`, `^^^^`) is untouched
  and unmeasured by this slice; only the head is.
* Formats longer than `PU_FMTMAX` clamp, and what either reference does at that
  boundary is not measured.
