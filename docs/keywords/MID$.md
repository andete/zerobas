<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `MID$` — characters from the middle of a string, or overwrite them

> **Spec:** DRAFT 1 (2026-11-23) — the FUNCTION form, 1021 cases, measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kslice.py`](../../probes/basic/spec/kslice.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
> Goldfish pass 1 (test writer) 2026-11-24: 23 findings, 13 measured (105 new cases, KS MX and KS FY), 4 moved
> to open, 6 wording; zerobas agrees in every new case.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error not yet proven. An extra
> argument, and a statement target that is not a variable, are `Syntax error`
> as on the VG-8020 (since 2026-10-27).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MID$` is two things with one name. As a **function**, `MID$(a$,p,n)` returns
`n` characters of `a$` starting at position `p` (counting from 1), and
`MID$(a$,p)` returns everything from `p` to the end. As a **statement**,
`MID$(A$,p,n)=b$` overwrites characters of the variable `A$` in place, without
changing its length. zerobas behaves like the Philips VG-8020 in every case we
have measured.

## Syntax

```
MID$(<string expression>,<position>[,<count>])          function
MID$(<string variable>,<position>[,<count>])=<string>    statement
```

## Details

### The function

- **Positions count from 1.** `MID$("ABCDEF",2,3)` is `"BCD"`.
- **Without a count, it runs to the end**: `MID$("hello",3)` is `"llo"`.
- **Asking for more than is there is fine**: the result just stops at the end.
  A position past the end gives `""`.
- **The position must be 1 to 255** — the one argument in the string family
  that starts at 1, so `MID$(a$,0)` is an error while `MID$(a$,255)` is not.
- **The count must be 0 to 255.**
- Each number is truncated toward zero and then checked in two steps: outside
  −32768 to 32767 → `Overflow` (error 6); otherwise out of range →
  `Illegal function call` (error 5). So −32768.5 and 32767.9 are error 5, and
  −32769 is error 6, for the position and for the count.
- **Arguments are checked left to right**, each completely before the next is
  even evaluated: `MID$(a$,70000,-1)` is error 6 (the position fails first),
  `MID$(a$,0,32768)` is error 5, and `MID$(a$,0,"A")` and `MID$(a$,0,1/0)` are
  5 too. A number as the string is 13 before anything else (`MID$(5,1/0)` is
  13).
- **Each number is checked as soon as it is read**, before the rest of the
  call: `MID$(a$,0,1,1)` and `MID$(a$,2,256,1)` are error 5, not 2.
- **A missing, empty or extra argument** (`MID$(a$)`, `MID$(a$,,1)`,
  `MID$(a$,1,)`, `MID$()`, `MID$(a$,1,1,1)`) is `Syntax error` (error 2).
- **Spaces are allowed** before and after the parenthesis and before and after
  the commas: `MID$ (a$,2,2)`, `MID$( a$ ,2 ,2 )` and `MID$(a$, 2, 2)` all
  give characters 2-3.
- **The string is any string expression**, and the result an ordinary string:
  a literal, a concatenation, an array element or another `MID$`
  (`MID$(MID$(a$,2),2,2)` is characters 3-4) as the source; the result can be
  concatenated, compared, passed to another function or stored in an array
  element, and `A$=MID$(A$,2)` slices the old value.

### The statement

[A] The statement is not measured by the spec probe yet (Open): this section and the statement rows of the
errors table rest on the earlier measurements cited under "What we found", not on a rule.

- **The length of `A$` never changes.** The number of characters replaced is
  the smallest of: the count (if given), the length of `b$`, and the room left
  in `A$` from position `p`. Characters outside that span are untouched.
  `A$="HELLO":MID$(A$,4)="WXYZ"` makes `"HELWX"`.
- **`p` must be 1 to 255 and no more than `LEN(A$)`**; a position past the end
  of `A$` is error 5. The count must be 0 to 255.
- **The target can be an array element**: `MID$(A$(1),1,2)="XY"` works.
- **A string that came from `READ` is copied before it is changed**, so the
  `DATA` line in the program is left as it was.
- **A space before the `=`** is allowed.

### Errors

| situation | error | evidence |
|---|---|---|
| truncated position 0, negative, or 256 and up; truncated count negative or 256 and up | 5 `Illegal function call` | R-MID-POS, R-MID-COUNT |
| statement: position past the end of `A$` (`A$="AB":MID$(A$,3)="X"`) | 5 `Illegal function call` | [A] statement |
| a number outside −32768 to 32767 (`MID$(a$,70000,1)`) | 6 `Overflow` | R-MID-POS, R-MID-COUNT |
| a number where a string belongs, or a string where a number belongs | 13 `Type mismatch` | R-MID-TYPE |
| statement: the target is a numeric variable (`MID$(A,1,1)="X"`) | 13 `Type mismatch` | [A] statement |
| statement: a number on the right (`MID$(A$,1)=5`) | 13 `Type mismatch` | [A] statement |
| statement: nothing after `=` (`MID$(A$,2)=`) | 24 `Missing operand` | [A] statement |
| a missing or empty argument (`MID$(a$)`, `MID$(a$,,1)`, `MID$(a$,1,)`, `MID$()`) | 2 `Syntax error` | R-MID-SYNTAX |
| statement: a missing argument (`MID$(A$)="X"`), or no `=` | 2 `Syntax error` | [A] statement |
| an extra argument (`MID$(a$,1,1,1)`) | 2 `Syntax error` | R-MID-SYNTAX |
| statement: a target that is not a variable (`MID$(5,1)="X"`) | 2 `Syntax error` | [A] statement |

## Example

```
10 A$="ABCDEF"
20 PRINT MID$(A$,2,3);" ";MID$(A$,4)
30 PRINT LEN(MID$(A$,9))
40 MID$(A$,2,3)="XYZ":PRINT A$
50 MID$(A$,5)="12345":PRINT A$
60 ON ERROR GOTO 90
70 PRINT MID$(A$,0)
75 MID$(A$,7)="X"
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
BCD DEF
 0
AXYZEF
AXYZ12
Error 5
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_mid_s.out`](../../scratchpad/kwdoc_mid_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/mid_s_rules.py`](../../probes/basic/spec/mid_s_rules.py), model in
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
- **[KS MID L*l* P*p* M*m*]**: `R$=MID$(S$,P,M)`, or `R$=MID$(S$,P)` where *m* is `-`, with `S$` = `CHR$(1)` ...
  `CHR$(`*l*`)` (every byte its own position), *l* in 0, 1, 5, 255; `P` and `M` double variables, *p* in -1, 0,
  .9, 1, 1.9, 2, 3, 5, 6, 254, 255, 255.9, 256, 32768, 70000 and *m* in -1, -.9, 0, .9, 1, 2, 3, 4, 5, 254, 255,
  255.9, 256, 32768.
- **[KS FX *i*]**: a fixed expression, `S$` = `CHR$(1)` ... `CHR$(5)`; the list, with what each one separates, is
  `FX` in the probe.
- **[KS MX L5 P*p* M*m*]** (goldfish pass 1, 2026-11-24): as KS MID at *l* = 5, at the 16-bit edges: *p* in
  -70000, -32769, -32768.5, -32768, -32767, 32767, 32767.9, 2 and *m* in `-`, 2, -1E10, -70000, -32769, -32768.5,
  -32768, -32767, 32767, 32767.9, 70000 (the position's edges with every count, the count's edges with P = 2).
- **[KS FY *i*]** (goldfish pass 1): a fixed statement, `S$` rebuilt as `CHR$(1)` ... `CHR$(5)` before each, the
  list `FY` in the probe: a space after each comma, empty operands, a bad number before an extra argument,
  `MID$(5,1/0)`, `MID$(S$,-32769,"A")` and `MID$(S$,-32769,1/0)`, nesting, a literal source, the result as a
  temporary, in an array element and assigned to its own source.
- The MX and FY records also hold `S$`'s position-weighted sum, so a source changed without changing its length
  and sum is seen in the case itself. The rival rules these cases separate are run by
  [`kslice_controls.py`](../../probes/basic/spec/kslice_controls.py): each is FALSE on some reference case.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/mid_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/mid_s_rules.py --write` -->

**14 rules; 14 hold on the reference. Of the 8273 recorded outputs (each case's error, the result's length, first and last byte and two checksums, the source's length and sum (and, in the MX and FY groups, its position-weighted sum)): 8273 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. MID$(a$, P [, M]) -- the function

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-MID-SLICE** The position P and the count M are truncated toward zero. With P from 1 to 255 and M from 0 to 255 the result is the M characters of a$ from position P (counting from 1), or the rest of a$ when fewer are left; a position past the end gives "". | 397 | ✓ | ✓ |
| **R-MID-REST** Without a count, MID$(a$,P) is everything from position P to the end ("" past the end). | 37 | ✓ | ✓ |
| **R-MID-POS** The position is checked first, completely: truncated, below -32768 or above 32767 is error 6, otherwise outside 1 to 255 is error 5, whatever the count is (MID$(S$,0,32768) is 5, MID$(S$,70000,-1) is 6). Truncation comes before the overflow test: -32768.5 and 32767.9 are 5, as are -32768 and 32767; -32769 is 6. Position 0 is an error; position 255 is not, at any length. | 438 | ✓ | ✓ |
| **R-MID-COUNT** With a valid position, the count is checked as LEFT$'s: truncated first, error 6 below -32768 or above 32767, else error 5 outside 0 to 255 (-32768.5 and -32768 are 5, -32769 is 6; 32767 and 32767.9 are 5, 32768 is 6). Nothing is assigned on an error. | 117 | ✓ | ✓ |
| **R-MID-SRC** The source string is left as it was, in every case, error or not (unless the result is assigned to the source itself: R-MID-ALIAS). | 1019 | ✓ | ✓ |
| **R-MID-TYPE** A number as the string, or a string as the position or the count, is error 13 -- the string's type is checked before the position is even evaluated (MID$(5,0) and MID$(5,1/0) are 13). | 5 | ✓ | ✓ |
| **R-MID-ORDER** The position is checked before the count is even evaluated: a bad position wins over a count of the wrong type and over a count that fails to compute (MID$(S$,0,"A") and MID$(S$,0,1/0) are 5; MID$(S$,70000,"A"), MID$(S$,-32769,"A") and MID$(S$,-32769,1/0) are 6). | 5 | ✓ | ✓ |
| **R-MID-OWNERR** A position or count that fails to compute raises its own error (1/0: error 11). | 2 | ✓ | ✓ |
| **R-MID-SYNTAX** No position, an empty position or count (MID$(S$,,1), MID$(S$,1,)), no argument at all, or a fourth argument is error 2 (Syntax error) -- an empty argument is not 24 (Missing operand). | 5 | ✓ | ✓ |
| **R-MID-EARLY** Each number is range-checked as soon as it is read, before the rest of the call is parsed: MID$(S$,0,1,1) and MID$(S$,2,256,1) are error 5, not 2. | 2 | ✓ | ✓ |
| **R-MID-FORMS** Spaces before the parenthesis, around the arguments and after the commas are allowed (MID$ (S$,2,2) and MID$(S$, 2, 2) are characters 2-3), and the string may be an expression (MID$(S$+S$,4,4) is characters 4-7 of the ten). | 4 | ✓ | ✓ |
| **R-MID-EXPR** MID$ works on its string argument's value: a literal (MID$("ABCDEF",2,3) is "BCD"), an array element, and MID$ nested in itself, the inner result being the outer source (MID$(MID$(S$,2),2,2) is characters 3-4). | 3 | ✓ | ✓ |
| **R-MID-USE** The result is an ordinary string value, used without being assigned -- concatenated (MID$(S$,2,2)+"X"), compared (MID$(S$,2,2)=CHR$(2)+CHR$(3) is true), the argument of another function (STRING$(2,MID$(S$,3,1)) is two CHR$(3)) -- or assigned to an array element, it is the same characters. | 4 | ✓ | ✓ |
| **R-MID-ALIAS** Assigned to its own source (S$=MID$(S$,2), S$=MID$(S$,2,2)), the result is taken from the OLD value, and S$ then holds exactly the result. | 2 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

No known difference in what `MID$` answers. The spec probe measures the
extra argument (`MID$(S$,1,1,1)`, KS FX 30: error 2 on both machines,
R-MID-SYNTAX). The status line's *every error* rung is the every-error
sweep's, which has no row for that case; the gate row `me-extra` of
`make missing-acceptance` (under Tests) covers it there.

The rung **RAM usage** is not yet proven either: `MID$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)).

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] The position and count as integer or single variables, or as constants (`2%`, `&H2`, `2!`): the matrix
  passes doubles.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is
  assumed.
- [A] Whether the result shares the source's bytes or is a copy (it is not visible to a program except through
  `FRE` and `VARPTR`'s address), and how much string space a slice needs: the details' "room only for the slice"
  sentence rests on an earlier, separate measurement
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)), not on a rule here.
- [A] A source string that points into the program text: one literal was measured (`MID$("ABCDEF",2,3)`, KS FY
  26); a `READ` string, and a literal with an error, were not.
- [A] Errors 14 (Out of string space) and 15 (String too long) from the string argument or the result: not
  measured. The errors MID$ itself raises are {2, 5, 6, 13}; an argument that fails to compute raises its own.
- [A] The source check (R-MID-SRC) reads the source's length and byte sum; the MID and FX groups record no more,
  so a source permuted in place would pass there (a later case's result would usually show it, but not the last
  case of each length). The MX and FY cases also record its position-weighted sum.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] **The statement** `MID$(A$,P[,M])=b$`: not measured by this probe. Its details above rest on the earlier
  measurements the "What we found" section cites; its rules come with the statement's own probe.

## What we found, and how

- **An extra argument, or a statement target that is not a variable, was
  error 13 here and error 2 on the VG-8020** (fixed 2026-10-27, D-MIDEXTRA,
  found by the every-error sweep,
  [`t6enum_b4.out`](../../scratchpad/t6enum_b4.out)). `PRINT MID$("AB",1,1,1)`
  and `MID$(5,1)="X"` are `Syntax error` there; a numeric variable as the
  target (`MID$(A,1)="X"`) stays `Type mismatch` on both
  ([`midextra_run.out`](../../scratchpad/midextra_run.out), from
  [`midextra_probe.py`](../../scratchpad/midextra_probe.py)).
- **The statement arrived on 2026-07-10**, as a handler of its own; the
  function is a different piece of code, so tests of one do not reach the
  other: [spec-basic-mid-statement.md](../spec-basic-mid-statement.md).
- **Out-of-range numbers were accepted silently**, in both forms (fixed
  2026-07-28, D-MISS-2). The statement was broken both ways:
  `MID$(A$,1,256)="X"` performed the assignment and `MID$(A$,1,99999)="X"`
  silently did nothing, where the reference raises; seven other cases gave
  `Syntax error` instead of 5 or 6. The function's position was also found to
  be the family's only 1-based argument:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **An array element could not be the target** (fixed 2026-08-08, D-LVFIX):
  `MID$(A$(1),1,2)="XY"` was a syntax error on zerobas and works on both
  references: [lvsites-msx1-characterization.md](../lvsites-msx1-characterization.md).
- **The statement's right-hand side gave the wrong error** (fixed
  2026-08-26, D-MIDOP): nothing after `=` is 24 on the reference, a number is
  13, and zerobas said 2 for both:
  [spec-basic-midop.md](../spec-basic-midop.md).
- **Spaces** (fixed 2026-09-08, D-MIDSPACE, and 2026-09-09, D-FNSPACE):
  `MID$(A$,2) ="X"` raised error 2 and left `A$` unchanged, and
  `MID$ ("ABCDE",2,2)` was a syntax error
  ([`midspace_after.out`](../../scratchpad/midspace_after.out),
  [`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A slice of a big string ran out of string space** where the reference had
  room (fixed 2026-09-26, D-SLICEOOM): zerobas copied the whole source first
  ([`sliceoom_run.out`](../../scratchpad/sliceoom_run.out)).
- **`READ` strings began pointing at the program text** (2026-10-07,
  D-READREF), as on the references. `MID$` now copies such a string out before
  writing into it; on the VG-8020 a re-`READ` and `LIST` show the original.
- **A space in front of the string argument was a Type mismatch** (fixed
  2026-10-31, D-ARGSPACE). Both reference machines accept `MID$( "ABCDE",2,2)`; zerobas
  stepped past the delimiter without skipping the spaces after it
  ([`argspace_run.out`](../../scratchpad/argspace_run.out),
  [`argspace_after.out`](../../scratchpad/argspace_after.out)).

## Where it lives

- The function: `str_fn_mid` in
  [basic/str-engine.asm](../../basic/str-engine.asm), sharing its opening
  (`str_arg_open`) with `LEFT$` and `RIGHT$`. The position is checked by
  `eval_pos_arg` and the count by `eval_byte_arg`, both in
  [basic/interp.asm](../../basic/interp.asm).
- The statement: `ex_mid_stmt` in the same file reads the target and the
  numbers; `mid_own` copies a `READ` string out first; the bytes are written
  by `sh_mid_store` in [sub/strheap.asm](../../sub/strheap.asm), in the
  sub-ROM.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — both forms' ranges, both error kinds, and the
  left-to-right order.
- `make string-acceptance` — the statement's overwrite rules (count longer
  than `b$`, `b$` longer than the room, empty `b$`, count 0) against the
  reference.
- `make readref-acceptance` — `MID$` into a `READ` string leaves the program
  alone.
- `make kwsweep` — all three forms (`MID$("hi",2,1)`, `MID$("hello",3)`, the
  statement) and the error rows.
- `make kwram` — the RAM-usage comparison.
- `make missing-acceptance`, row `me-extra` — the extra argument and the
  target that is not a variable.
- `make argspace-acceptance` — a space in front of the string argument.
