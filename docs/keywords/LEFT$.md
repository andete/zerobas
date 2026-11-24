<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `LEFT$` — the first characters of a string

> **Spec:** DRAFT 1 (2026-11-23) — 169 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kslice.py`](../../probes/basic/spec/kslice.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 14 findings, 9 measured (14 new cases, KS FY), 3 moved to open, 2
> wording; zerobas agrees in every new case.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`LEFT$(a$,n)` returns the first `n` characters of `a$`. Its mirror is
[`RIGHT$`](RIGHT$.md), and [`MID$`](MID$.md) takes characters from the
middle. zerobas behaves exactly like the Philips VG-8020 for every case we
have measured, errors included.

## Syntax

```
LEFT$(<string expression>,<count>)
```

Both arguments are required.

## Details

- **A count larger than the string gives the whole string**; a count of 0
  gives `""`.
- **The count must be 0 to 255.** It is truncated toward zero, then checked
  in two steps, the same as [`CHR$`](CHR$.md):
  1. outside −32768 to 32767 → `Overflow` (error 6);
  2. inside that range but outside 0 to 255 → `Illegal function call`
     (error 5).
- **A number as the string, or a string as the count**, is `Type mismatch`
  (error 13). The string's type is checked before the count is even
  evaluated: `LEFT$(5,-1)` is error 13, not 5, and `LEFT$(5,1/0)` is 13, not
  11. If the string argument itself fails to compute (`LEFT$(1/0,1)`), that
  error wins.
- **A missing, empty or extra argument** (`LEFT$(a$)`, `LEFT$(a$,)`,
  `LEFT$()`, `LEFT$(a$,1,1)`) is `Syntax error` (error 2); an empty count is
  not `Missing operand`.
- **The count is checked as soon as it is read**, before the rest of the call:
  `LEFT$(a$,256,1)`, and `LEFT$(a$,256` with no closing parenthesis, are
  error 5, not 2.
- **Spaces are allowed** before the parenthesis, after it and around the
  comma: `LEFT$ (a$,2)` and `LEFT$( a$ , 2 )` give what `LEFT$(a$,2)` gives.
  The count may be an integer, hex or single constant (`2%`, `&H2`, `2!`).
- **The string is any string expression**, and the result an ordinary string:
  a literal, a concatenation, an array element or another slice
  (`LEFT$(RIGHT$(a$,4),2)` is characters 2-3) as the source; the result can be
  concatenated, compared or stored in an array element, and
  `A$=LEFT$(A$,2)` slices the old value.
- **A short slice of a long string needs room only for the slice.** With
  little string space left, `LEFT$` of a 50-character string still works as
  on the reference.

| you write (`a$` = `"ABCDE"`) | you get |
|---|---|
| `LEFT$(a$,2)` | `"AB"` |
| `LEFT$(a$,9)`, `LEFT$(a$,255)` | `"ABCDE"` |
| `LEFT$("ABC",9)` | `"ABC"` |
| `LEFT$(a$,0)` | `""` |
| `LEFT$(a$,-1)`, `LEFT$(a$,256)` | error 5, `Illegal function call` |
| `LEFT$(a$,70000)` | error 6, `Overflow` |
| `LEFT$(5,1)`, `LEFT$(a$,"A")` | error 13, `Type mismatch` |
| `LEFT$(a$)`, `LEFT$(a$,)`, `LEFT$()`, `LEFT$(a$,1,1)` | error 2, `Syntax error` |

The errors `LEFT$` itself raises are {2, 5, 6, 13}, the same on both
machines. An argument that fails to compute raises its own error instead
(`1/0`: 11, R-LEFT-OWNERR), and so can the string expression (a
concatenation past 255 characters: 15; not measured here).

## Example

```
10 A$="ABCDE"
20 PRINT LEFT$(A$,2)
30 PRINT LEFT$(A$,9);LEN(LEFT$(A$,0))
40 ON ERROR GOTO 80
50 PRINT LEFT$(A$,256)
60 PRINT LEFT$(A$,70000)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
AB
ABCDE 0
Error 5
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_left_s.out`](../../scratchpad/kwdoc_left_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/left_s_rules.py`](../../probes/basic/spec/left_s_rules.py), model in
[`kslice_model.py`](../../probes/basic/spec/kslice_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kslice.py`](../../probes/basic/spec/kslice.py), typed on both
machines; run file [`scratchpad/KSL_run1.out`](../../scratchpad/KSL_run1.out) (2026-11-23; zerobas's side on that
day's build). Each case's result is read through `VARPTR` and `PEEK`, never through a string function: its length,
first and last byte, the sum of its bytes and the sum of (position x byte), plus the source string after the call.
Before every case the result variable holds `CHR$(250)`, so an error, which assigns nothing, cannot read as a
result.
- **[KS LR LEFT$ L*l* N*n*]**: `R$=LEFT$(S$,N)` with `S$` = `CHR$(1)` ... `CHR$(`*l*`)` (every byte its own
  position, so the first n, the last n and any other n bytes all differ), *l* in 0, 1, 2, 5, 255, and `N` a double
  variable holding *n*: -1E10, -70000, -32769, -32768.5, -32768, -32767, -1, -.9, -.1, 0, .1, .9, 1, 1.5, 2, 3,
  4, 5, 6, 254, 255, 255.9, 256, 32767, 32767.9, 32768, 70000, 1E10.
- **[KS FX *i*]**: a fixed expression, `S$` = `CHR$(1)` ... `CHR$(5)`; the list, with what each one separates, is
  `FX` in the probe.
- **[KS FY *i*]** (goldfish pass 1, 2026-11-24): a fixed statement, `S$` rebuilt as `CHR$(1)` ... `CHR$(5)` before
  each, the list `FY` in the probe: empty operands, the count's range before the closing parenthesis, `2!`,
  nesting that separates "the inner result" from "the original source", `LEFT$(5,1/0)`, a literal source, the result
  as a temporary, in an array element and assigned to its own source. Its record also holds `S$`'s
  position-weighted sum, so a source changed without changing its length and sum is seen in the case itself.
- The rival rules these cases separate are run by
  [`kslice_controls.py`](../../probes/basic/spec/kslice_controls.py): each is FALSE on some reference case.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/left_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/left_s_rules.py --write` -->

**12 rules; 12 hold on the reference. Of the 1366 recorded outputs (each case's error, the result's length, first and last byte and two checksums, the source's length and sum (and, in the MX and FY groups, its position-weighted sum)): 1366 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. LEFT$(a$, n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-LEFT-SLICE** The count is truncated toward zero; from 0 to 255 the result is the first min(count, LEN(a$)) characters of a$, in order: 0 gives "", a count past the end the whole string. (.9 gives "" and 1.5 one character: truncation, not rounding.) | 75 | ✓ | ✓ |
| **R-LEFT-ERR5** A truncated count from -32768 to -1, or from 256 to 32767, is error 5 (Illegal function call), and nothing is assigned. -32768.5 and 32767.9 are 5: the count is truncated BEFORE the range test. | 35 | ✓ | ✓ |
| **R-LEFT-ERR6** A truncated count below -32768 or above 32767 is error 6 (Overflow), and nothing is assigned. | 30 | ✓ | ✓ |
| **R-LEFT-SRC** The source string is left as it was, in every case, error or not (unless the result is assigned to the source itself: R-LEFT-ALIAS). | 168 | ✓ | ✓ |
| **R-LEFT-TYPE** A number as the string, or a string as the count, is error 13 (Type mismatch). The string's type is checked before the count is even evaluated: a number as the string with count -1, 70000 or 1/0 is still 13 (not 5, 6 or 11). | 5 | ✓ | ✓ |
| **R-LEFT-OWNERR** An argument that fails to compute raises its own error (1/0 as either argument: error 11). | 2 | ✓ | ✓ |
| **R-LEFT-SYNTAX** A missing count, an empty one (LEFT$(S$,)), no argument at all, or a third argument is error 2 (Syntax error) -- an empty count is not 24 (Missing operand). | 4 | ✓ | ✓ |
| **R-LEFT-EARLY** The count is range-checked as soon as it is read, before the rest of the call is parsed: LEFT$(S$,256,1) and the unclosed LEFT$(S$,256 are error 5, not 2. | 2 | ✓ | ✓ |
| **R-LEFT-FORMS** A space before the parenthesis and spaces around the arguments are allowed, and the count may be an integer (`2%`), hex (`&H2`) or single (`2!`) constant: each gives what LEFT$(S$,2) gives. | 5 | ✓ | ✓ |
| **R-LEFT-EXPR** The string may be any string expression, and LEFT$ works on its value: a literal (LEFT$("ABC",9) is "ABC"), a concatenation (S$+S$, 7: the first 7 of the ten), an array element, and the function nested in itself or in its mirror, the inner result being the outer source (LEFT$(RIGHT$(S$,4),2) is characters 2-3, LEFT$(LEFT$(S$,2),4) characters 1-2). | 6 | ✓ | ✓ |
| **R-LEFT-USE** The result is an ordinary string value, used without being assigned -- concatenated (LEFT$(S$,2)+"X" is those two characters and X), compared (LEFT$(S$,2)=CHR$(1)+CHR$(2) is true and LEFT$(S$,2)=CHR$(1)+CHR$(3) false) -- or assigned to an array element, it is the same characters. | 4 | ✓ | ✓ |
| **R-LEFT-ALIAS** Assigned to its own source (S$=LEFT$(S$,2)), the result is taken from the OLD value, and S$ then holds exactly the result. | 1 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `LEFT$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] The count as an integer or single VARIABLE at the range edges: the matrix passes doubles; `2%`, `&H2` and
  `2!` were measured at one value only.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is
  assumed.
- [A] Whether the result shares the source's bytes or is a copy (it is not visible to a program except through
  `FRE` and `VARPTR`'s address), and how much string space a slice needs: the details' "room only for the slice"
  sentence rests on an earlier, separate measurement
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)), not on a rule here.
- [A] A source string that points into the program text: one literal was measured (`LEFT$("ABC",9)`, KS FY 24);
  a `READ` string, and a literal with an error, were not.
- [A] Errors 14 (Out of string space) and 15 (String too long) from the string argument or the result: not
  measured.
- [A] The source check (R-LEFT-SRC) reads the source's length and byte sum; the LR and FX groups record no more,
  so a source permuted in place would pass there (a later case's result would usually show it, but not the last
  case of each length). The FY cases also record its position-weighted sum.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).

## What we found, and how

- **Out-of-range counts were accepted silently** (fixed 2026-07-28,
  D-MISS-2). `LEFT$`, `RIGHT$`, `MID$` and `CHR$` computed an answer from a
  count the VG-8020 rejects. The two-step rule above, and its exact boundary
  (−32768 is error 5, not 6), come from that measurement:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **`PRINT LEFT$(5,2)` said `Syntax error`** where both references say
  `Type mismatch` (fixed 2026-08-29, D-LEFTTM). The error was armed without
  looking at the argument; the reference evaluates the argument and reports
  what it raises, so `LEFT$(0*(1/0)+1)` is `Division by zero` (error 11):
  [spec-basic-lefttm.md](../spec-basic-lefttm.md).
- **A space before the parenthesis or the comma was a syntax error** (fixed
  2026-09-09, D-FNSPACE). Both reference machines accept
  `LEFT$ ("ABCDE",2)` and `LEFT$("ABCDE" ,2)`
  ([`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A slice of a big string ran out of string space** where the reference
  had room (fixed 2026-09-26, D-SLICEOOM). zerobas copied the whole source
  before slicing it, needing 53 bytes where the reference needs 3. Now only
  the result is allocated, for a plain variable and for an array element
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)).
- **A space in front of the string argument was a Type mismatch** (fixed
  2026-10-31, D-ARGSPACE). Both reference machines accept `LEFT$( "ABCDE",2)`; zerobas
  stepped past the delimiter without skipping the spaces after it
  ([`argspace_run.out`](../../scratchpad/argspace_run.out),
  [`argspace_after.out`](../../scratchpad/argspace_after.out)).

## Where it lives

`str_fn_left` in [basic/str-engine.asm](../../basic/str-engine.asm). It
shares its opening (`str_arg_open`) with `RIGHT$` and `MID$`, and its count
clamp (`str_lr_count`) with `RIGHT$`. The count is checked by the shared
`eval_byte_arg` in [basic/interp.asm](../../basic/interp.asm). The slice is
made by `she_snap_slice` and `she_slice_new` in
[sub/strheap.asm](../../sub/strheap.asm).

## Tests that cover it

- `make str-domain-acceptance` — the count's range, both error kinds, and
  the order of checks.
- `make string-acceptance` — `LEFT$` among the core string verbs, including
  `LEFT$` of a concatenation.
- `make kwsweep` — the everyday row and the error rows for {2, 5, 6, 13}.
- `make kwram` — the RAM-usage comparison.
- `make argspace-acceptance` — a space in front of the string argument.
