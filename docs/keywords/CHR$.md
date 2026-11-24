<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `CHR$` — the character with a given code

> **Spec:** DRAFT 1 (2026-11-24) — 43 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstr.py`](../../probes/basic/spec/kstr.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Goldfish pass 1 (test writer) 2026-11-24:** 5 findings, 3 measured, 1 moved to open.
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`CHR$(n)` returns a one-character string whose character code is `n`, 0 to 255.
It is the inverse of `ASC`: `ASC(CHR$(n)) = n`.
zerobas behaves exactly like the Philips VG-8020 for every case we have
measured, errors included.

## Syntax

```
CHR$(<numeric expression>)
```

One argument, always. There are no optional forms.

## Details

- **The argument is truncated toward zero first, then checked.** `CHR$(65.7)`
  is `"A"`, `CHR$(255.9)` is character 255 and `CHR$(-0.5)` is character 0 —
  all legal.
- **Two checks, in this order:**
  1. outside the integer range −32768 to 32767 → `Overflow` (error 6);
  2. inside that range but outside 0 to 255 → `Illegal function call` (error 5).

  So `CHR$(-32768)` and `CHR$(256)` are error 5, while `CHR$(-32769)` and
  `CHR$(70000)` are error 6.
- **A string argument** (`CHR$("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`CHR$()`, `CHR$(65,1)`) is `Syntax error` (error 2).
- **Spaces are allowed** before the parenthesis, after it and around the argument: `CHR$ (65)`, `CHR$( 65)`
  and `CHR$( 65 )` are `"A"`.
- **The one-character result needs string space**: with the string space full (`FRE("")` 0), `CHR$(65)` is
  `Out of string space` (error 14) on both machines; one free byte is enough.
- **The result is a string**, so `A=CHR$(65)` is `Type mismatch`.
- **Every code is a real character**, 0 and 255 included: `LEN(CHR$(0))` is 1.
  What *printing* a control character does (`CHR$(7)` beeps, `CHR$(12)` clears
  the screen, `CHR$(27)` starts an escape sequence) is the screen driver's
  business, not `CHR$`'s.

| you write | you get |
|---|---|
| `CHR$(65)` | `"A"` |
| `CHR$(65.7)` | `"A"` |
| `CHR$(-0.5)`, `CHR$(0)` | character 0 (length 1) |
| `CHR$(256)`, `CHR$(-1)`, `CHR$(-32768)` | error 5, `Illegal function call` |
| `CHR$(32768)`, `CHR$(-32769)` | error 6, `Overflow` |
| `CHR$("A")` | error 13, `Type mismatch` |
| `CHR$()`, `CHR$(65,1)` | error 2, `Syntax error` |

The whole set of errors `CHR$` can raise is {2, 5, 6, 13}, plus 14 (`Out of string space`) when the string
space is full (R-CHR-ROOM), the same on both machines.

## Example

```
10 FOR I=65 TO 69:A$=A$+CHR$(I):NEXT
20 PRINT A$
30 PRINT LEN(CHR$(0));ASC(CHR$(65.7))
40 ON ERROR GOTO 70
50 PRINT CHR$(256)
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
ABCDE
 1  65
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_chr_s.out`](../../scratchpad/kwdoc_chr_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/chr_s_rules.py`](../../probes/basic/spec/chr_s_rules.py), model in
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
- **[KST NUM CHR$ N*n*]**: `R$=CHR$(N)`, `N` a double variable holding *n*: -1E10, -70000, -32769, -32768.5, -32768, -32767, -1, -.9, -.1, 0, .1, .9, 1, 1.5, 2, 3, 4, 5, 6, 254, 255, 255.9, 256, 32767, 32767.9, 32768, 70000, 1E10.
- **[KST FR *i*]**: a fixed statement after `CLEAR 200` with exactly *k* bytes of string space left free: a filler `X$` of `FRE("")`-*k* spaces is made first, `R` records `FRE("")` just before the statement (the check requires it to be *k*), `R$` holds its one-character `CHR$(250)`, `S$` = `"ABCDE"`; the list is `FR` in the probe.
- **[KST FX *i*]**: a fixed statement, `S$` = `"ABCDE"`, `T$` = `"CD"` (both in string space); the list, with what
  each one separates, is `FX` in the probe.

**Controls** ([`kstr_controls.py`](../../probes/basic/spec/kstr_controls.py)): rounding in place of truncation is FALSE on 6 of the 28 matrix cases; `INT` in place of truncation on 3; a one-character result that needs no room on 1 of the 2 FR cases.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/chr_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/chr_s_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 731 recorded outputs (each case's error, the string result's length, first and last byte and two checksums, the numeric result's 8 bytes (in FR: FRE("") before the statement), the two source strings' length, first and last byte and two checksums): 731 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. CHR$(n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-CHR-VALUE** The argument is truncated toward zero; from 0 to 255 the result is the one character whose code is n. (-.9 and .9 give CHR$(0), 255.9 gives CHR$(255): truncation, not rounding, and not INT.) | 15 | ✓ | ✓ |
| **R-CHR-ERR5** A truncated argument from -32768 to -1, or from 256 to 32767, is error 5 (Illegal function call), and nothing is assigned. -32768.5 and 32767.9 are 5: the argument is truncated BEFORE the range test. | 7 | ✓ | ✓ |
| **R-CHR-ERR6** A truncated argument below -32768 or above 32767 is error 6 (Overflow), and nothing is assigned. | 6 | ✓ | ✓ |
| **R-CHR-ROOM** The one-character result needs one byte of string space: with FRE("") 0 (the string space filled, R$'s one-character old value still in it) CHR$(65) is error 14 (Out of string space), nothing assigned; with 1 byte free it fits. | 2 | ✓ | ✓ |
| **R-CHR-TYPE** A string as the argument is error 13 (Type mismatch), and so is assigning the result to a numeric variable: the result is a string. | 2 | ✓ | ✓ |
| **R-CHR-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-CHR-SYNTAX** No argument, a second argument, or no closing parenthesis is error 2 (Syntax error). | 3 | ✓ | ✓ |
| **R-CHR-FORMS** Spaces before the parenthesis, after it and around the argument are allowed, and so are an integer, a hex and a single argument: each gives what CHR$(65) gives (65.9! is truncated to 65). | 7 | ✓ | ✓ |
| **R-CHR-KEEP** The source strings are left as they were, in every case, error or not (S$ and T$ read back after every case: length, first and last byte, the sum and the sum of position x byte). | 43 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CHR$` uses the same amount of
free memory on both machines, but the VG-8020 also writes a few work-area cells
that zerobas does not, and zerobas writes one the VG-8020 does not. Nothing a
program can observe through `FRE` or the documented variables differs.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] The sources kept (R-CHR-KEEP) are compared by their digest -- length, first and last byte, the sum and the sum of position x byte -- not byte for byte, and not by where they lie: a string's address is not kept by BASIC itself (garbage collection moves strings), so it is not a rule.
- [A] The argument as an integer or single VARIABLE at the range edges: the matrix passes doubles; `65%`, `&H41` and `65.9!` were measured at one value only.
- [A] What PRINTING a control character does is the screen's, not `CHR$`'s (the details), and is not measured here.

## What we found, and how

- **Out-of-range codes used to be accepted silently** (fixed 2026-07-28,
  D-MISS-2). zerobas took the low byte of the argument, so `CHR$(256)` was
  character 0 and `CHR$(-1)` was character 255, where the VG-8020 raises
  error 5 or 6. This had been written down as a deliberate leniency; measuring
  it showed it was a wrong answer. The two-check rule above, and its exact
  boundaries (−32768 is error 5, not 6), come from that measurement:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).
- **`CHR$ (65)` with a space was a syntax error** (fixed 2026-09-09,
  D-FNSPACE). Both reference machines accept a space between a function name
  and its parenthesis.
- **`CHR$()` returned garbage** (fixed 2026-07-13, D-F2-3); it is now
  `Syntax error`, as on the reference.
- **Deep nesting crashed.** `LEN(CHR$(ASC(…)))` twelve levels deep crashed
  zerobas, while the references go 32 deep (fixed 2026-09-12, D-SPMERGE, which
  merged two stacks).
- **The tests had a blind spot.** `CHR$` shares its string-building code with
  other functions, and a deliberately broken build showed no `CHR$` test
  noticed (2026-08-28, D-NGRAM4). Rows were added; a broken `CHR$` now fails
  the gates.

### Related, but not about `CHR$`

`PRINT CHR$(27);"Y";` followed by two more characters is an escape sequence
that moves the cursor. The VG-8020 then carries on printing; zerobas's screen
driver leaves the rest of the line invisible. That is a screen-driver
difference, filed as a TIER 6 item in [TODO.md](../../TODO.md).

## Where it lives

`str_fn_chr` in [basic/str-engine.asm](../../basic/str-engine.asm); the
argument check is the shared `eval_byte_arg` in
[basic/interp.asm](../../basic/interp.asm), which `LEFT$`, `RIGHT$`, `MID$`,
`STRING$` and `SPACE$` use too.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — the range and truncation rules.
- `make kwsweep` — the everyday row (`CHR$(65)`), the error rows for
  {2, 5, 6, 13}, and the deliberately-broken-build check.
- `make kwram` — the RAM-usage comparison.
