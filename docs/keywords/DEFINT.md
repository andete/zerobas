<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `DEFINT` — make variables integers by their first letter

> **Spec:** DRAFT 1 (2026-11-25) — 62 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kdeftype.py`](../../probes/basic/spec/kdeftype.py), with the other three
> `DEF` type statements' cases); every rule is executable and every recorded output is read by one. Goldfish
> pass 1 acted on (2026-11-25: every rule pinned by a control of its own, 33 more cases); not yet
> re-reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-11-25):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error: one difference, the variable
> entry's layout (D-VARLAYOUT).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`DEFINT A-C` makes every variable whose name starts with `A`, `B` or `C`, and
has no type suffix, an integer — as if you had written `A%`, `B%`, `C%`.
Its siblings do the same for the other types: [`DEFSNG`](DEFSNG.md) (single
precision), [`DEFDBL`](DEFDBL.md) (double precision) and
[`DEFSTR`](DEFSTR.md) (string). This page holds the rules all four share.
zerobas gives the Philips VG-8020's values and errors in
every case we have measured; the variable table is laid out differently
(see Differences).

## Syntax

```
DEFINT <letter>[-<letter>][,<letter>[-<letter>]...]
```

A single letter (`DEFINT I`), a range (`DEFINT A-C`), or a list of either
(`DEFINT A-C,I,N`).

## Details

Rules shared by all four `DEF` type statements:

- **Without any `DEF`, an unsuffixed variable is double precision.** `A=1/3`
  prints `.33333333333333`, fourteen digits, the same as `A#`.
- **Only the first letter counts**, and only for names without a suffix. A
  suffix always wins: after `DEFINT A`, `A#` is still double.
- **The type is looked up every time a name is used**, not when the variable
  was created. So `A=7:DEFINT A:PRINT A` prints 0: the `A` that holds 7 is the
  double one, and the `A` you now name is a new integer.
- **The last `DEF` for a letter wins**: `DEFINT A:DEFDBL A` leaves `A` double.
- **What ends an item is `,`, `:` or the end of the line**, nothing else.

For `DEFINT` itself:

- **A value stored in an integer variable loses its fraction**: after
  `DEFINT A`, `A=1.7` stores 1.
- **Loop and `READ` variables follow the rule too**: `DEFINT I:FOR I=1 TO 3:NEXT`
  leaves `I` at 4.

### Errors

Every malformed `DEF` statement is `Syntax error` (error 2) — the only error
the VG-8020 raises for any of the four, in either form:

| you write | why |
|---|---|
| `DEFINT 5`, `DEFINT 1` | not a letter |
| `DEFINT A-`, `DEFINT A-1` | the range has no end letter |
| `DEFINT Z-A` | a reversed range |
| `DEFINT` | nothing to declare |
| `DEFINT AB`, `DEFINT AC=7` | something glued to the item |

## Example

```
10 DEFINT A-C,N
20 A=1.7:N=7/2:D=1.7:B#=1.5
30 PRINT A;N;D;B#
40 ON ERROR GOTO 70
50 DEFINT Z-A
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 1  3  1.7  1.5
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_defint.out`](../../scratchpad/kwdoc_defint.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

`A` and `N` are integers, `D` is outside the declared letters and stays double,
and `B#` keeps its own suffix.

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/defint_rules.py`](../../probes/basic/spec/defint_rules.py), model in
[`kdeftype_model.py`](../../probes/basic/spec/kdeftype_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does. The model is an
INTERPRETER: it runs each case's own statements -- the `DEF` list, the type of a name at each use, an assignment's
conversion -- and predicts the record from the laws the rules state; it holds no per-case answers.

**Evidence.** One probe, [`probes/basic/spec/kdeftype.py`](../../probes/basic/spec/kdeftype.py), on the shared
RAM-record harness, typed as two programs: FX (the first run's cases) and FY (goldfish pass 1's). Each case is a line
run from a fresh `CLEAR`, with `ON ERROR` and `RESUME NEXT` so a statement after an error still runs; the record keeps
the first and the last error, the type byte before each named variable (`PEEK(VARPTR(v)-3)`; VARPTR refuses a variable
that does not exist, recorded as "none"), a number the case leaves in `WV#` -- which starts at -77, so a value the case
never wrote shows -- and the case's own index, set at the end of its line, so a line the machine refused when it was
typed (the first run lost one that way) cannot pass for its predecessor. Every probe variable carries a suffix, so a
case's `DEFSTR A-Z` cannot retype the probe. Run file [`scratchpad/KDT_run1.out`](../../scratchpad/KDT_run1.out)
(2026-11-25).
- **[KDT FX *i*]** (DEFINT), the case's statements:
  3: `DEFINT A:A=1.7:WV#=A`, reads A
  4: `DEFINT A:A=-1.7:WV#=A`, reads A
  5: `DEFINT A:A=2.5:WV#=A`, reads A
  6: `DEFINT A-C:B=1.7:WV#=B`, reads A, B, D
  7: `DEFINT A,C:B=1.7:C=1.7:WV#=B`, reads A, B, C
  8: `DEFINT A-C,X-Z:Y=1.7:D=1.7:WV#=Y`, reads Y, D
  9: `DEFINT A-A:A=1.7:WV#=A`, reads A
  10: `DEFINT A:A#=1.5:A!=2.5:WV#=A#`, reads A
  11: `A=7:DEFINT A:WV#=A`, reads A
  12: `A=7:DEFINT A:A=3:DEFDBL A:WV#=A`, reads A
  13: `DEFINT A:DEFDBL A:A=1.7:WV#=A`, reads A
  14: `DEFINT I:FOR I=1 TO 3:NEXT:WV#=I`, reads I
  15: `DEFINT A:RESTORE n+5:READ A:WV#=A` (line n+5: `DATA 2.6`), reads A
  16: `DEFINT A:A=40000`, reads A
  17: `DEFINT A:A=-32768:WV#=A`, reads A
  18: `DEFINT A:DIM A(2):A(1)=1.7:WV#=A(1)`
  19: `DIM A(2):DEFINT A:A(1)=1.7:WV#=A(1)`
  20: `defint a:a=1.7:WV#=A`, reads A
  21: `DEFINT A:CLEAR 300,&HBF00:A=1.7:WV#=A`, reads A
  22: `DEFINT A:WV#=A+0.5`, reads A
  23: `DEFINT 5`
  24: `DEFINT A-`
  25: `DEFINT A-1`
  26: `DEFINT Z-A:Z=1.7:WV#=Z`, reads Z
  27: `DEFINT`
  28: `DEFINT AB`
  29: `DEFINT AC=7`, reads C
  30: `DEFINT A B`
  31: `DEFINT A,`
  32: `DEFINT A-B-C`
  33: `DEFINT A$`
  34: `DEFINT A:B=1.7:WV#=B`, reads A, B
  52: `DEFINT A,5:A=1.7:WV#=A`, reads A
  53: `DEFINT A-C,Z-A:B=1.7:WV#=B`, reads B
  54: `DEFINT A - C:B=1.7:WV#=B`, reads B
  55: `DEFINT A ,B:B=1.7:WV#=B`, reads B
  56: `DEFINT AB:A=1.7:WV#=A`, reads A
  57: `DEFINT A-CD:B=1.7:WV#=B`, reads B
- **[KDT FY *i*]** (DEFINT, goldfish pass 1), the case's statements:
  0: `DEFINT A:A=32767.9:WV#=A`, reads A
  1: `DEFINT A:A=32768`, reads A
  2: `DEFINT A:A=-32768.5:WV#=A`, reads A
  3: `DEFINT A:A=-32769`, reads A
  4: `DEFINT A:A=40000:WV#=A+.5`, reads A
  5: `DEFINT A:A=5:A=40000:WV#=A`, reads A
  6: `DEFINT A:AB=1.7:BA=1.7:WV#=AB+BA`
  7: `DEFINT A:ABC=1:ABD=2:WV#=ABC`
  8: `DEFINT A:A%=5:WV#=A`, reads A
  11: `DEFINT A-:A=1.7:WV#=A`, reads A
  12: `DEFINT A B:A=1.7:WV#=A`, reads A
  13: `DEFINT A,:A=1.7:WV#=A`, reads A
  14: `DEFINT A$:A=1.7:WV#=A`, reads A
  15: `DEFINT A-B-C:B=1.7:WV#=B`, reads B
  16: `DEFINT A, B:B=1.7:WV#=B`, reads B
  17: `DEFINT A :A=1.7:WV#=A`, reads A
  22: `DEFINT I:FOR I=1.7 TO 3:NEXT:WV#=I`, reads I
  26: `DIM A(2):A(1)=1.7:DEFINT A:WV#=A(1)`
  27: `DIM A(2):A(1)=1.7:DEFINT A:A(1)=3:DEFDBL A:WV#=A(1)`
  28: `DIM A(2):DEFINT A:DIM A(2)`
  29: `DEFINT X:DEF FNB(X)=X:WV#=FNB(1.7)`
  30: `DEFINT A:DEF FNA(X)=X/2:WV#=FNA(3)`
  31: `DEFINT A-Z:CLEAR:Z=1.7:WV#=Z`, reads Z
  32: `DEFINT A:A=1/0`, reads A

**Controls** ([`kdeftype_controls.py`](../../probes/basic/spec/kdeftype_controls.py)): each changes ONE law of the interpreter and runs over the reference's cases; every rule has at least one of its own: “a list stands only if ALL of it is good” is FALSE on 8 of the 62 cases R-INT-LIST selects (e.g. KDT FX 52); “a reversed range is swapped, not an error” is FALSE on 2 of the 62 cases R-INT-LIST selects (e.g. KDT FX 26); “CLEAR keeps the DEF table” is FALSE on 2 of the 62 cases R-INT-LIST selects (e.g. KDT FX 21); “a variable keeps the type it was made with” is FALSE on 3 of the 11 cases R-INT-NAME selects (e.g. KDT FX 10); “a suffixed name is a variable apart from the unsuffixed one” is FALSE on 10 of the 11 cases R-INT-NAME selects (e.g. KDT FX 10); “an integer rounds (half away from zero)” is FALSE on 16 of the 31 cases R-INT-STORE selects (e.g. KDT FX 3); “an integer floors (towards minus infinity)” is FALSE on 2 of the 31 cases R-INT-STORE selects (e.g. KDT FX 4); “the variable is made only after its value is checked” is FALSE on 5 of the 31 cases R-INT-STORE selects (e.g. KDT FX 16); “the type byte FOLLOWS the name -- zerobas's order” is FALSE on 40 of the 40 cases R-INT-ENTRY selects (e.g. KDT FX 3).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/defint_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/defint_rules.py --write` -->

**4 rules; 4 hold on the reference. Of the 434 recorded outputs (each case's first and last error, the type byte before each named variable (PEEK(VARPTR(v)-3); $EE: VARPTR refused the name) and the number the case left in WV#): 434 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. The letters

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-INT-LIST** `DEFINT` takes a list of items separated by `,`: a letter, or a range `X-Y` (spaces allowed anywhere between the parts). Every letter of the list now gives an unsuffixed name that type; the last `DEF` for a letter wins, and `CLEAR` puts every letter back to double. Each item is applied as soon as it is read: a bad item later in the list, or text glued to it (`DEFINT AB`, `DEFINT A-CD`), is error 2 (Syntax error) but the items before it -- and the glued item itself -- stand -- but a range cut off after its dash (`DEFINT A-`) applies nothing. Anything else -- no item, a digit, a range without its end letter or written backwards, a suffix, a trailing comma -- is error 2 too. | 62 | ✓ | ✓ |
| **R-INT-NAME** Only an unsuffixed name follows the table, through its FIRST letter, and the table is read at every USE of a name, not when the variable was made: after `A=7:DEFINT A`, `A` names a new integer variable (0) beside the double one, which `DEFDBL A` names again. A suffix always wins, and a suffixed name IS the unsuffixed one of the same type (`A%` is `A` after DEFINT A). Two characters are significant (ABC is ABD). An ARRAY follows the same lookup: after DEFINT A, `A(1)` names a new integer array beside the double one, so DIM A again is no error. A DEF FN parameter and a DEF FN name follow the table too (FNA after DEFINT A returns an integer). | 11 | ✓ | ✓ |

#### 2. Storing a value

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-INT-STORE** An integer variable keeps the whole part, cut TOWARDS ZERO (1.7 -> 1, -1.7 -> -1, 2.5 -> 2), and the range is tested AFTER the cut: 32767.9 and -32768.5 fit, 32768 and -32769 are error 6 (Overflow). FOR (its start too), READ and array elements store the same way. An assignment makes its variable BEFORE the value is worked out (`A=1/0` leaves A), so after an error a NEW variable exists holding its type's zero and an existing one keeps its value; reading a name never makes it. | 31 | ✓ | ✓ |

#### 3. The variable table

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-INT-ENTRY** The byte just before a variable's two name bytes, `PEEK(VARPTR(v)-3)`, is its type: 2 integer, 3 string, 4 single, 8 double (the published MSX variable entry: type, two name bytes, value). | 40 | ✓ | ✗ 40: KDT FX 3, KDT FX 4, KDT FX 5, KDT FX 6, KDT FX 7, KDT FX 8 … (+34) |

<!-- RULES END -->

## Differences from the reference

- **The variable's entry is laid out differently** (rule R-INT-ENTRY; D-VARLAYOUT, filed
  2026-11-25). Every value, error and type agrees; but the byte before a variable's two name
  bytes -- `PEEK(VARPTR(v)-3)`, the type in the published MSX layout -- is the name's first
  letter on zerobas (the type follows the name there). Only a program that PEEKs before the
  value can see it.

The one rung not yet proven is **RAM usage**: `DEFINT` uses the same amount of
free memory on both machines, but the two machines write different cells of
the documented work area while doing it, and one cell ends on a different
value.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] A `DEF` inside a running `DEF FN` body; the array entry's header (D-VARLAYOUT); `ERASE`
  after a `DEF` change.

## What we found, and how

- **The spec run (2026-11-25, D-KWSPEC) agreed on every value and error, and found the
  entry layout** (D-VARLAYOUT): the type byte sits after the name on zerobas. It also pinned
  what the page had only said: an integer is cut towards zero (-1.7 -> -1, 2.5 -> 2), a list is
  applied item by item (`DEFINT A,5` and `DEFINT AB` leave A an integer), and an assignment
  makes its variable before the value is checked.
- **The four `DEF` statements arrived on 2026-07-12**, together with typed
  variables. A review the same day found that a `DEFINT` loop or `READ`
  variable was stored as one type and read back as another, so it read 0; that
  was fixed the same day.
- **`DEFINT` was stored differently from the reference** (fixed 2026-08-18 and
  2026-08-19, D-DEFINTTOK and D-DEFTYPETOK). zerobas stored it as `DEF` plus
  the letters `INT`, and had no entry at all for the other three; the reference
  stores each as a single token of its own. For `DEFSTR` the missing entry also
  changed how the argument after it was read. All four now store the
  reference's bytes, argument included.
- **`DEFINT AC=7` ran `C=7`** (fixed 2026-08-31, D-DEFCORNER). After an item,
  zerobas accepted anything as its end and ran the rest as a new statement.
  `DEFINT AB` had agreed with the reference all along — both said
  `Syntax error` — but for a different reason, which a row designed to tell the
  two apart exposed: [spec-basic-defcorner.md](../spec-basic-defcorner.md).
- **The test checks the effect, not the parse** (2026-09-12, D-KWDRAIN): it
  expects 1, not 1.7, so a `DEFINT` that parsed and did nothing fails. The
  range row (2026-09-14) checks a letter only the range covers.

## Where it lives

`ex_deftype` in [basic/usr.asm](../../basic/usr.asm) serves all four
statements; it hands the line to the sub-ROM routine `deftype_tenant` in
[sub/deftype.asm](../../sub/deftype.asm), which reads which statement it was
from the token, checks the letters and fills the 26-entry type table. Each
variable reference consults that table (`deftbl_lookup` in
[basic/vars.asm](../../basic/vars.asm)).

## Related concepts

- [Variables](../concepts/variables.md) — names, types, arrays, and where they live

## Tests that cover it

- `make float-acceptance` — the type rules: default double, ranges, lists,
  suffix wins, redeclaration, and the loop/`READ` regression rows.
- `make kwsweep` — the single-letter and range rows, and the error rows
  `DEFINT 5` and `DEFINT A-` (2).
- `make kwram` — the RAM-usage comparison.
