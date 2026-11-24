<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `STRING$` — a character repeated a number of times

> **Spec:** DRAFT 1 (2026-11-24) — 664 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstr.py`](../../probes/basic/spec/kstr.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Goldfish pass 1 (test writer) 2026-11-24:** 14 findings, 8 measured, 1 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. An empty fill string
> is `Illegal function call` as on the VG-8020 (since 2026-10-27). One
> divergence found on 2026-11-24 by the spec probe (a space before the closing
> parenthesis after a string fill, a variable or a literal): see Differences.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STRING$(n,c)` returns `n` copies of one character. The character is given
either as a code (`STRING$(3,65)` is `"AAA"`) or as a string, whose first
character is used (`STRING$(3,"*")` is `"***"`). [`SPACE$`](SPACE$.md) is the
special case for spaces. zerobas behaves like the Philips VG-8020 in every case
we have measured except one: a space between a string fill and the closing
parenthesis (see Differences).

## Syntax

```
STRING$(<count>,<character code>)
STRING$(<count>,<string expression>)
```

Which form you wrote is decided by the type of the second argument.

## Details

- **Only the first character of a string is used**: `STRING$(3,"xyz")` is
  `"xxx"`.
- **The count must be 0 to 255**, and so must a character code. Outside
  −32768 to 32767 either one is `Overflow` (error 6); otherwise out of range
  it is `Illegal function call` (error 5). There is no silent clamp.
- **A long result needs string space.** The string space a program starts
  with is the same 200 bytes as after `CLEAR 200`: `STRING$(255,"A")` is
  `Out of string space` (error 14), and with one short string already there
  199 characters fit and 200 do not — on both machines, with or without
  `CLEAR 200`. What counts is the space left beside every other string, the
  variable's old value included until the result is assigned: with exactly 5
  bytes free, `STRING$(5,65)`, `STRING$(5,"A")` and `STRING$(5,S$)` fit and
  the same with 6 is error 14. After `CLEAR 600` it is 255 characters.
- **A string as the count** (`STRING$("A","A")`) is `Type mismatch`
  (error 13).
- **A missing or extra argument** (`STRING$(2)`, `STRING$()`,
  `STRING$(2,"A","A")`) is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis, after it, before the comma
  and after it, and before the closing parenthesis: `STRING$ (2,65)`,
  `STRING$(2, "AB")` and `STRING$(2,"AB" )` are all `"AA"` on the VG-8020
  (zerobas: the last is a `Syntax error`, see Differences).
- **The count is checked first**, before the fill is even evaluated:
  `STRING$(-1,1/0)` is error 5, not 11, and a string as the count is
  `Type mismatch` before the fill is looked at: `STRING$("A",1/0)` is 13. With a valid count, a bad code is an
  error even when the count is 0 (`STRING$(0,256)` is error 5), and so is an
  empty fill string (`STRING$(0,"")`).

| you write | you get |
|---|---|
| `STRING$(3,65)` | `"AAA"` |
| `STRING$(3,"*")` | `"***"` |
| `STRING$(-1,"A")`, `STRING$(256,"A")` | error 5, `Illegal function call` |
| `STRING$(2,-1)`, `STRING$(2,256)` | error 5, `Illegal function call` |
| `STRING$(99999,65)`, `STRING$(5,99999)` | error 6, `Overflow` |
| `STRING$("A","A")` | error 13, `Type mismatch` |
| `STRING$(2)`, `STRING$()`, `STRING$(2,"A","A")` | error 2, `Syntax error` |
| `STRING$(2,"")` | error 5 — but `STRING$(2,""` (no closing parenthesis) is error 2 |

The set of errors the T6 enumeration measured for `STRING$` is {2, 5, 13},
and each has a matching case; the `Overflow` above comes from the separate
range measurements and agrees too. Beyond it the probe measured 14 (`Out of string space`, R-STRING-ROOM), which
the enumeration does not reach because it runs with room to spare, and an argument's own error (`1/0`:
11, R-STRING-OWNERR), which belongs to the expression, not to `STRING$`.

## Example

```
10 PRINT STRING$(5,"*")
20 PRINT STRING$(3,65);STRING$(3,"xyz")
30 PRINT LEN(STRING$(0,"A"))
40 ON ERROR GOTO 70
50 PRINT STRING$(256,"A")
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
*****
AAAxxx
 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_string_s.out`](../../scratchpad/kwdoc_string_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/string_s_rules.py`](../../probes/basic/spec/string_s_rules.py), model in
[`kstr_model.py`](../../probes/basic/spec/kstr_model.py), run by
[`tools/spec_rules.py`](../../tools/spec_rules.py); [docs/spec-method.md](../spec-method.md) §3a,
[the keyword plan](spec-plan.md)) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Evidence.** One probe, [`probes/basic/spec/kstr.py`](../../probes/basic/spec/kstr.py) (the strings region's
second, on the shared RAM-record harness [`ramrec.py`](../../probes/basic/spec/ramrec.py)), typed on both
machines; run file [`scratchpad/KST_run1.out`](../../scratchpad/KST_run1.out) (2026-11-24; zerobas's side on that
day's build). Before every case the string result variable `R$` holds `CHR$(250)` and the numeric one `R` holds
-12345, so an error, which assigns nothing, cannot read as a result, and a result written to the wrong kind of
variable is seen. A string result is read through `VARPTR` and `PEEK`, never through a string function: its length,
first and last byte, the sum of its bytes and the sum of (position x byte); a numeric result as its variable's own
8 bytes (a double), decoded exactly. The source strings `S$` and `T$` are built byte by byte in string space and
read back after every case the same way as a string result: length, first and last byte, both sums (until goldfish
pass 1 the length and the sum only, which a keyword that reordered a source's bytes would have passed).
- **[KST STRN N*n* C*c*]**: `R$=STRING$(N,C)`, *n* in the 28 counts -1E10, -70000, -32769, -32768.5, -32768, -32767, -1, -.9, -.1, 0, .1, .9, 1, 1.5, 2, 3, 4, 5, 6, 254, 255, 255.9, 256, 32767, 32767.9, 32768, 70000, 1E10, and *c* in the 17 codes -1E10, -32769, -32768.5, -32768, -1, -.9, 0, .9, 1, 65, 65.9, 255, 255.9, 256, 32767.9, 32768, 70000: every pair, so which of the two is checked first is seen (run as two groups, STRN and STRN2, the codes split 9 / 8, so the records fit below the work area; the case ids are the same).
- **[KST STRS N*n* F*f*]**: `R$=STRING$(N,S$)`, the same 28 counts, `S$` one of five fill strings: "" (E), `CHR$(0)` (Z0), `CHR$(7)+CHR$(8)+CHR$(9)` (P789), `CHR$(255)+CHR$(1)+CHR$(2)` (P255) and a 255-character string `CHR$(1)` ... `CHR$(255)` (L255).
- **[KST OS STRING$ N*n*]**: `R$=STRING$(N,65)` after `CLEAR 200`, *n* 150, 190, 195 to 201, 255.
- **[KST OSD STRING$ N*n*]**: the same with no `CLEAR` at all (the string space a program starts with), *n* 198 to 200.
- **[KST FR *i*]**: a fixed statement after `CLEAR 200` with exactly *k* bytes of string space left free: a filler `X$` of `FRE("")`-*k* spaces is made first, `R` records `FRE("")` just before the statement (the check requires it to be *k*), `R$` holds its one-character `CHR$(250)`, `S$` = `"ABCDE"`; the list is `FR` in the probe.
- **[KST FX *i*]**: a fixed statement, `S$` = `"ABCDE"`, `T$` = `"CD"` (both in string space); the list, with what
  each one separates, is `FX` in the probe.

**Controls** ([`kstr_controls.py`](../../probes/basic/spec/kstr_controls.py)): the code checked before the count is FALSE on 58 of the 476 count x code cases; an empty fill allowed when the count is 0 on 5 of the 140 fill-string cases; the fill evaluated before the count's type on the 1 case that separates them (KST FX 118); a fixed limit of 199 characters whatever else is in the string space on 3 of the 6 FR cases; the sources left reversed (same length and sum) on all 119 cases with a source longer than one character.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/string_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/string_s_rules.py --write` -->

**13 rules; 13 hold on the reference. Of the 11288 recorded outputs (each case's error, the string result's length, first and last byte and two checksums, the numeric result's 8 bytes (in FR: FRE("") before the statement), the two source strings' length, first and last byte and two checksums): 11288 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. STRING$(n, code) and STRING$(n, a$)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-STRING-CODE** STRING$(n,code): both numbers are truncated toward zero; with both from 0 to 255 the result is n copies of the character with that code ("" for 0). | 120 | ✓ | ✓ |
| **R-STRING-FILL** STRING$(n,a$): with n from 0 to 255 and a$ not empty, the result is n copies of a$'s first character; the rest of a$ is not used. | 60 | ✓ | ✓ |
| **R-STRING-COUNT** The count is checked first, as LEFT$'s: truncated, error 6 outside -32768 to 32767, else error 5 outside 0 to 255, whatever the second argument is (STRING$(-1,70000) is 5, STRING$(70000,-1) is 6). Nothing is assigned on an error. | 286 | ✓ | ✓ |
| **R-STRING-CODERANGE** With a valid count, the code is checked the same way: error 6 outside -32768 to 32767, else 5 outside 0 to 255 -- also when the count is 0, which needs no character. | 135 | ✓ | ✓ |
| **R-STRING-EMPTY** With a valid count, an empty fill string is error 5 (Illegal function call) -- also when the count is 0. | 15 | ✓ | ✓ |
| **R-STRING-ORDER** The count is checked before the second argument is even evaluated, and before the closing parenthesis is looked for: STRING$(-1,1/0), STRING$(-1,5+"A") and STRING$(-1,"A" (unclosed) are all error 5. | 3 | ✓ | ✓ |
| **R-STRING-TYPEORDER** A string as the count is error 13 before the second argument is evaluated: STRING$("A",1/0) is 13, not 11. With a valid count, a fill that fails on its own type (STRING$(2,5+"A")) is 13 too. | 2 | ✓ | ✓ |
| **R-STRING-ROOM** A result needs string space for all its characters, and the variable's old value still holds its own until the result is assigned. After CLEAR 200, and in the string space a program starts with (no CLEAR: the same 200 bytes), with R$'s one-character old value the only other string, a result of 199 characters fits and one of 200 or more is error 14 (Out of string space), nothing assigned. With exactly k bytes free (FRE("") just before, other strings in the space) a result of up to k characters fits and a longer one is error 14: at k = 5, STRING$(5, fill) fits and STRING$(6, fill) is 14, the fill a code, a literal or a string variable. | 19 | ✓ | ✓ |
| **R-STRING-TYPE** A string as the count is error 13 (Type mismatch), checked before the code's range (STRING$("A",256) is 13); assigning the result to a numeric variable is 13 too. | 4 | ✓ | ✓ |
| **R-STRING-OWNERR** An argument that fails to compute raises its own error (1/0 as the count or the code: error 11). | 2 | ✓ | ✓ |
| **R-STRING-SYNTAX** No fill, no argument, a third argument, or no closing parenthesis (after an empty fill) is error 2 (Syntax error): the parenthesis is checked before the empty fill. | 5 | ✓ | ✓ |
| **R-STRING-FORMS** Spaces before the parenthesis, around the arguments, and before or after a string fill (a variable or a literal in the program text) are allowed; an integer count and a hex code are numbers like any other; the fill may be a literal (STRING$(2,"AB") is "AA") or a string expression (T$+S$: T$'s first character). | 13 | ✓ | ✗ 2: KST FX 114, KST FX 116 |
| **R-STRING-KEEP** The source strings are left as they were, in every case, error or not (S$ and T$ read back after every case: length, first and last byte, the sum and the sum of position x byte). | 664 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

- **A space before the closing parenthesis after a string fill** (rule
  R-STRING-FORMS, cases KST FX 114 and 116; [D-CLOSESPACE](../../todo/open/D-CLOSESPACE.md)).
  `STRING$(2,S$ )` and `STRING$(2,"AB" )` are `"AA"` on the VG-8020 and `Syntax error` (error 2) here: after a
  string variable and after a literal alike.
  After a code (`STRING$( 2 , 65 )`) the space is accepted by both.

The rung not yet proven is **RAM usage**: `STRING$` changes free memory
by the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)).

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] String space at other `CLEAR` sizes than 200 (and the default, which is 200): the room rule is measured there,
  and at 0 and 5 bytes free beside other strings (FR).
- [A] The sources kept (R-STRING-KEEP) are compared by their digest -- length, first and last byte, the sum and the sum of position x byte -- not byte for byte, and not by where they lie: a string's address is not kept by BASIC itself (garbage collection moves strings), so it is not a rule.
- [A] Only five fill strings were measured (their later bytes all differ from the first).
- [A] "After `CLEAR 600` it is 255 characters" (the details) rests on D-SPCLAMP's measurement
  ([spec-basic-spclamp.md](../spec-basic-spclamp.md)); here 255 characters fit after `CLEAR 2000`.

## What we found, and how

- **An empty fill string was error 2 here and error 5 on the VG-8020** (fixed
  2026-10-27, D-STRINGEMPTY, found by the every-error sweep,
  [`t6enum_b2.out`](../../scratchpad/t6enum_b2.out)). An empty string has no
  first character, which the reference treats as a bad value; a missing
  closing parenthesis still wins as `Syntax error`
  ([`stringempty_run.out`](../../scratchpad/stringempty_run.out), from
  [`stringempty_probe.py`](../../scratchpad/stringempty_probe.py)).
- **`STRING$` arrived on 2026-07-10.** Its first run against the VG-8020
  caught `PRINT STRING$(…)` answering `Type mismatch`, because the `PRINT`
  item reader had no case for it; a review the same day caught a negative
  count being clamped instead of refused:
  [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **A malformed `STRING$` call could hang the machine** (fixed 2026-07-17),
  filling the screen with ` 0`; it is now a `Syntax error`.
- **Out-of-range counts and codes went through without the reference's
  error** (fixed 2026-07-19, D-F2-2). Both numbers are now checked as bytes,
  0 to 255: [spec-basic-df2-2-intarg-coercion.md](../spec-basic-df2-2-intarg-coercion.md).
- **The documents still described a clamp** on 2026-08-29; measuring it again
  (D-SPCLAMP) showed zerobas already agreed with both references at every
  point. The run also showed that at the starting string space the
  255-character case fails on space, not on the limit, on all three machines —
  so the limit itself is tested after `CLEAR 600`:
  [spec-basic-spclamp.md](../spec-basic-spclamp.md).
- **`STRING$ (2,65)` and `STRING$(2 ,65)` were syntax errors** (fixed
  2026-09-09, D-FNSPACE)
  ([`fnspace_after2.out`](../../scratchpad/fnspace_after2.out)).
- **A space in front of the string argument was a Type mismatch** (fixed
  2026-10-31, D-ARGSPACE). Both reference machines accept `STRING$(2, "AB")`; zerobas
  stepped past the delimiter without skipping the spaces after it
  ([`argspace_run.out`](../../scratchpad/argspace_run.out),
  [`argspace_after.out`](../../scratchpad/argspace_after.out)).

## Where it lives

`str_fn_string` in [basic/str-engine.asm](../../basic/str-engine.asm) reads
the count, then tries the second argument as a string and, failing that, as a
number. Both numbers are checked by the shared `get_byte_arg` in
[basic/interp.asm](../../basic/interp.asm). The characters are written by
`sh_fill` in [sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — the count's and the code's ranges, both error
  kinds, and the int16 boundary.
- `make string-acceptance` — the code and string forms and a 100-character
  result, against the reference.
- `make kwsweep` — the everyday row (`STRING$(3,"x")`) and the error rows for
  {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
- `make missing-acceptance`, row `se-empty` — the empty fill string, and the
  missing parenthesis that outranks it.
- `make argspace-acceptance` — a space in front of the string argument.
