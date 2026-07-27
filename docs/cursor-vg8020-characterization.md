<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `CSRLIN` / `POS` / `TAB(` / `SPC(`, characterised against the VG-8020

**Status:** MEASUREMENT RECORD, 2026-07-27. Input to step 2 of
[`decision-kwgaps-slicing.md`](decision-kwgaps-slicing.md) §4.3 — the
cursor/`PRINT` cluster, **four of the eight SILENT-GAP words**. Produced by
[`probes/basic/basic_probe_cursor.py`](../probes/basic/basic_probe_cursor.py)
(`make cursor-characterize`). Reference: `Philips_VG_8020`.

`TAB(` is the word that started the whole sweep: `PRINT TAB(99999)` raises
ERR 6 on **both** sides, for structurally different reasons, so a differential
*agreed* while the feature was entirely absent.

## 1. Method — two readouts, and one that was deliberately refused

`CSRLIN` and `POS` return **numbers**, read through the `[...]` bracket
convention. `TAB(` and `SPC(` produce **whitespace**, which a value readout
cannot see at all, so they are measured by **position**: each case starts with
`CLS` and the probe reports the `(row, col)` where a marker landed on the
40×24 SCREEN 0 grid.

**The readout that was refused:** `PRINT TAB(10);POS(0)` — asking the ROM where
it put the cursor. `POS` is one of the four words under test, so a wrong `POS`
and a wrong `TAB(` could cancel and read as correct. The screen grid is an
*independent* instrument; `POS` is measured **against** it, never **with** it.

### 1.1 The instrument had to be pinned before anything could be compared

The calibration battery came back **0/6** on the first run — `PRINT "X"` landed
at column 2 on the reference and column 1 on zerobas. Not a bug in either: the
two machines **boot at different text widths** (§5, D-CUR-2), and SCREEN 0
centres the text area, so every absolute column was offset. Comparing columns
across two different widths would have measured the width difference and called
it a `TAB(` divergence.

Every positional row therefore pins `WIDTH 40` first, at which the two grids
agree exactly (margin 0, wrap at 40) — verified, not assumed.

## 2. `CSRLIN` — bare pseudo-variable, 0-based row

| case | ROM |
|---|---|
| `CLS:PRINT CSRLIN` (home) | `0` |
| after one `PRINT` | `1` |
| after two | `2` |
| `X=CSRLIN` then print `X` | `0` |
| `CSRLIN+10` at home | `10` |
| `CSRLIN(0)` | `2 0` — **two items** |

It takes **no argument and no parentheses**: `CSRLIN(0)` parses as `CSRLIN`
followed by a separate parenthesised item `(0)`, and prints both. It is an
ordinary numeric value — assignable and usable in arithmetic.

## 3. `POS(n)` — function, parentheses required, argument ignored

| case | ROM |
|---|---|
| `CLS:PRINT "[";POS(0);"]"` | `1` (the `[` was already emitted) |
| `PRINT "AB";"[";POS(0)` | `3` |
| `PRINT "ABCDE";"[";POS(0)` | `6` |
| `X=POS(0)` at home | `0` |
| `POS(1)` / `POS(99)` / `POS(-1)` / `POS(1+1)` | `1` / `1` / `1` / `1` |
| `POS` without parentheses | **`Syntax error`** |

Returns the **0-based cursor column**. The argument is *parsed but discarded* —
`-1` and `99` give the same answer as `0`, so it is a true dummy, not a
selector.

## 4. `TAB(` and `SPC(` — measured at `WIDTH 40`

| case | marker at | reading |
|---|---|---|
| `TAB(10)` | `0,10` | absolute column, 0-based |
| `TAB(0)` / `TAB(1)` | `0,0` / `0,1` | |
| `"AB";TAB(10)` | `0,10` | absolute, not relative |
| `"ABCDE";TAB(5)` | `0,5` | already **at** the target → no move |
| `"ABCDEFGHIJ";TAB(3)` | `0,10` | already **past** → **no move, and no newline** |
| `TAB(10)` with no separator | `0,10` | separator optional |
| `TAB(10),` | `0,14` | a following `,` advances normally |
| `TAB(10.7)` | `0,10` | **truncates toward zero** |
| `TAB(39)` | `0,39` | last column |
| `TAB(45)` | `1,5` | **wraps modulo width** |
| `TAB(5);TAB(12)` | `0,12` | |
| `SPC(5)` | `0,5` | **relative** — emit n spaces |
| `SPC(0)` | `0,0` | |
| `"AB";SPC(5)` | `0,7` | relative, not absolute |
| `SPC(5.7)` | `0,5` | truncates |
| `SPC(39)` / `SPC(45)` | `0,39` / `1,5` | ordinary line wrap |
| `SPC(5);TAB(12)` | `0,12` | |

**The one that a value-shaped test could never have found:** `TAB(` to a column
the cursor has already passed does **nothing at all** — it does not emit a
newline and does not move to that column on the next row. That is only visible
as a position.

Float arguments **truncate toward zero**, matching what the logical operators do
([`logicops-vg8020-characterization.md`](logicops-vg8020-characterization.md) §4)
— the same `fac_to_int_strict` protocol, not a new rule.

### 4.1 Range and scope

| case | ROM |
|---|---|
| `TAB(255)` / `SPC(255)` | fine |
| `TAB(256)` / `SPC(256)` | **`Illegal function call`** |
| `TAB(-1)` / `SPC(-1)` | **`Illegal function call`** |
| `TAB(99999)` / `SPC(99999)` | **`Overflow`** — the int16 conversion fires first |
| `PRINT TAB(10)` with nothing after | legal: pads, item list ends |
| `X=TAB(5)` | **`Syntax error`** |
| `X=SPC(5)` | **`Syntax error`** |
| `IF TAB(5)=0 THEN` | **`Syntax error`** |

Valid range is **0..255**; both are **`PRINT`-only** — anywhere else is a syntax
error, not a type error.

## 5. Two divergences found on the way, neither about these four words

Both surfaced from the **calibration** battery — rows that use none of the four.

### D-CUR-1 — the `PRINT` comma-zone advance uses a different rule

Comma zones are 14 columns apart on both. They differ on **when a zone is
refused** and the line wraps instead.

Three items cannot tell the two candidate rules apart: zone 3 starts at column
28, and `28+14 = 42` exceeds every legal SCREEN 0 width, so both rules predict a
wrap at every width. **Zone 2 discriminates**, because `14+14 = 28` lands inside
the legal range:

| `WIDTH` | 30 | 29 | **28** | **27** | 24 | 20 | 16 |
|---|---|---|---|---|---|---|---|
| reference | 14 | 14 | **14** | **wrap** | wrap | wrap | wrap |
| zerobas | 14 | 14 | 14 | 14 | 14 | 14 | 14 |

The reference's boundary is exactly at 28 = 14 + 14:

> **reference:** advance to the next zone only if `zone_start + 14 <= width`
> — the **whole** zone must fit.
> **zerobas:** advance if `zone_start < width` — only the **start** must fit.

Visible at every default-ish width: at `WIDTH 40`, `PRINT "A","B","C"` puts `C`
on the next line on the reference and at column 28 on zerobas.

### D-CUR-2 — the boot text width differs

**Reference boots `WIDTH 37`; zerobas boots `WIDTH 39`.** Measured from where a
41-character line wraps and where the left margin sits, on both. This changes the
column layout of every program that does not set `WIDTH` itself.

Both are `PRINT`/console divergences, not keyword gaps. D-CUR-1 lands in
`print_comma_zone` — the routine `SPC(` is meant to share `pcz_pad` with — so it
is naturally in scope for the slice; D-CUR-2 is a console-init question and is
not.

## 6. Method notes worth keeping

* **Pin the instrument before comparing absolute quantities.** Six calibration
  rows red at the start of the run was the probe working: two machines at
  different text widths cannot have their columns compared, and the whole
  positional battery would otherwise have reported a systematic off-by-one as a
  `TAB(` bug.
* **Never measure a feature with another unimplemented feature.** `POS` as the
  readout for `TAB(` would have let two wrongs cancel.
* **Use a marker that cannot appear in the typed line.** An early version marked
  with a literal `"X"`; on a case that had lost its `CLS`, the grid search found
  the `X` in the **echoed command** and reported a confident, entirely wrong
  column. The marker is now `CHR$(35)` — emitted as `#`, never present in the
  source text, so matching the echo is *impossible* rather than merely unlikely.
* **The same applies to the error readout.** The `[...]` bracket convention
  cannot be used on rows that may error, because the echo itself contains `[`
  and `]` — a span search happily returned a slice of the typed command
  (`";X;"`) and called it the answer. Error rows read the text *after* the echo,
  and therefore must **not** begin with `CLS`, which erases the echo they anchor
  on. The first version of that battery led with `CLS` and reported
  `<no result>` for all eleven rows.
* **Pick the case that can discriminate the rule, not the case you thought of
  first.** The three-item comma row was the obvious test and could not
  distinguish the two candidate rules at any legal width. The two-item row puts
  the boundary inside the observable range and settles it in one sweep.
