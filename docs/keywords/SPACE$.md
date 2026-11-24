<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->
<!-- example: reference=VG-8020 disk=no -->

# `SPACE$` — a string of spaces

> **Spec:** DRAFT 1 (2026-11-24) — 49 cases measured on the Philips VG-8020 (BASIC's reference) and on
> zerobas, by typed BASIC ([`kstr.py`](../../probes/basic/spec/kstr.py)); every rule is executable and
> every recorded output is read by one. Not yet reviewed ([the keyword plan](spec-plan.md)).
>
> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SPACE$(n)` returns a string of `n` spaces, 0 to 255. It is the same as
`STRING$(n," ")`; see [`STRING$`](STRING$.md) for any other fill character.
zerobas behaves exactly like the Philips VG-8020 for every case we have
measured, errors included.

## Syntax

```
SPACE$(<numeric expression>)
```

One argument, always.

## Details

- **`SPACE$(0)` is the empty string.**
- **The count must be 0 to 255.** There is no silent clamp: outside −32768 to
  32767 it is `Overflow` (error 6); otherwise below 0 or above 255 it is
  `Illegal function call` (error 5).
- **A long result needs string space.** In the string space a program starts
  with, a 255-space string does not fit and is `Out of string space`
  (error 14) — on both machines. After `CLEAR 200`, with one short string
  already there, 199 spaces fit and 200 do not, on both. After `CLEAR 600`,
  `LEN(SPACE$(255))` is 255.
- **A string argument** (`SPACE$("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`SPACE$()`, `SPACE$(1,1)`), is `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `SPACE$(3)` | `"   "` |
| `SPACE$(0)` | `""` |
| `SPACE$(-1)`, `SPACE$(256)`, `SPACE$(300)` | error 5, `Illegal function call` |
| `SPACE$(32768)`, `SPACE$(99999)` | error 6, `Overflow` |
| `SPACE$("A")` | error 13, `Type mismatch` |
| `SPACE$()`, `SPACE$(1,1)` | error 2, `Syntax error` |

The set of errors the T6 enumeration measured for `SPACE$` is {2, 5, 13}, the
same on both machines; the `Overflow` above comes from the separate range
measurements and agrees too.

## Example

```
10 PRINT "[";SPACE$(3);"]"
20 PRINT LEN(SPACE$(0));ASC(SPACE$(1))
30 ON ERROR GOTO 70
40 PRINT SPACE$(256)
50 PRINT SPACE$(32768)
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
[   ]
 0  32
Error 5
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_space_s.out`](../../scratchpad/kwdoc_space_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## The specification

Reference: the Philips VG-8020's MSX BASIC. Ours: zerobas on the diskless machine
(`C-BIOS_MSX1_EU_REPACK_NODISK`).

**How to read the rules below.** Every rule is a sentence AND a check
([`probes/basic/spec/space_s_rules.py`](../../probes/basic/spec/space_s_rules.py), model in
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
read back after every case.
- **[KST NUM SPACE$ N*n*]**: `R$=SPACE$(N)`, `N` a double variable holding *n*: -1E10, -70000, -32769, -32768.5, -32768, -32767, -1, -.9, -.1, 0, .1, .9, 1, 1.5, 2, 3, 4, 5, 6, 254, 255, 255.9, 256, 32767, 32767.9, 32768, 70000, 1E10.
- **[KST OS SPACE$ N*n*]**: the same after `CLEAR 200` (the string space a program starts with), *n* 150, 190, 195 to 201, 255: where the space runs out.
- **[KST FX *i*]**: a fixed statement, `S$` = `"ABCDE"`, `T$` = `"CD"` (both in string space); the list, with what
  each one separates, is `FX` in the probe.

**Controls** ([`kstr_controls.py`](../../probes/basic/spec/kstr_controls.py)): rounding in place of truncation is FALSE on 6 of the 28 matrix cases.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/basic/spec/space_s_rules.py -- do not edit; `python3 tools/spec_rules.py probes/basic/spec/space_s_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 539 recorded outputs (each case's error, the string result's length, first and last byte and two checksums, the numeric result's 8 bytes, the two source strings' lengths and sums): 539 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. SPACE$(n)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-SPACE-VALUE** The argument is truncated toward zero; from 0 to 255 the result is n spaces ("" for 0). (-.9 and .9 give "", 255.9 gives 255 spaces: truncation, not rounding, and not INT.) | 15 | ✓ | ✓ |
| **R-SPACE-ERR5** A truncated argument from -32768 to -1, or from 256 to 32767, is error 5 (Illegal function call), and nothing is assigned. -32768.5 and 32767.9 are 5: the argument is truncated BEFORE the range test. | 7 | ✓ | ✓ |
| **R-SPACE-ERR6** A truncated argument below -32768 or above 32767 is error 6 (Overflow), and nothing is assigned. | 6 | ✓ | ✓ |
| **R-SPACE-ROOM** A result needs string space for all its characters: after CLEAR 200, with R$'s one-character previous value the only other string, a result of 199 characters fits and one of 200 or more is error 14 (Out of string space), nothing assigned. | 10 | ✓ | ✓ |
| **R-SPACE-TYPE** A string as the argument is error 13 (Type mismatch), and so is assigning the result to a numeric variable: the result is a string. | 2 | ✓ | ✓ |
| **R-SPACE-OWNERR** An argument that fails to compute raises its own error (1/0: error 11). | 1 | ✓ | ✓ |
| **R-SPACE-SYNTAX** No argument, a second argument, or no closing parenthesis is error 2 (Syntax error). | 3 | ✓ | ✓ |
| **R-SPACE-FORMS** Spaces before the parenthesis and around the argument are allowed, and so are an integer, a hex and a single argument: each gives what SPACE$(3) gives. | 5 | ✓ | ✓ |
| **R-SPACE-KEEP** The source strings are left as they were, in every case, error or not (S$ and T$ read back after every case). | 49 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SPACE$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## On later generations (MSX2, MSX2+)

[A] Not measured yet: the probe has not run on the MSX2 / MSX2+ references (spec-method §4).

## Open (not measured)

- [A] Direct mode: every case ran inside a program.
- [A] An argument's own error was measured with one kind (`1/0`, error 11); that any error of the argument wins is assumed.
- [A] Which work-area cells the call writes (the RAM-usage rung, [`kwram_full.out`](../../scratchpad/kwram_full.out)).
- [A] String space at other `CLEAR` sizes, and with other strings in it: the room rule is measured at one setup.
- [A] "After `CLEAR 600`, `LEN(SPACE$(255))` is 255" (the details) rests on D-SPCLAMP's measurement
  ([spec-basic-spclamp.md](../spec-basic-spclamp.md)); here 255 spaces fit after `CLEAR 2000`.
- [A] The argument as an integer or single VARIABLE at the range edges: `3%` and `&H3` were measured at one value only.

## What we found, and how

- **`SPACE$` arrived on 2026-07-10.** Its first run against the VG-8020
  caught a fill loop that wrote 256 bytes past its buffer, before the slice
  was closed: [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **Out-of-range counts went through without the reference's error**; the
  first design clamped them on purpose (fixed 2026-07-19, D-F2-2). The count
  is now checked as a byte, 0 to 255, with the reference's two errors:
  [spec-basic-df2-2-intarg-coercion.md](../spec-basic-df2-2-intarg-coercion.md).
- **The documents still described a clamp** a month later; measuring it again
  on 2026-08-29 (D-SPCLAMP) showed zerobas already agreed with both references
  at every point, and only the documentation changed. That run also showed
  why a boundary test needs `CLEAR`: at the starting string space, the
  255-character case fails on string space on all three machines, which hides
  whether 255 itself is allowed:
  [spec-basic-spclamp.md](../spec-basic-spclamp.md).
- **The tests could not see the content.** The everyday test read only
  `LEN(SPACE$(3))`, which a `SPACE$` returning `"xxx"` would pass. A row now
  reads the first and last character codes (32 and 32).

## Where it lives

`str_fn_space` in [basic/str-engine.asm](../../basic/str-engine.asm) reads
the count and checks it with the shared `get_byte_arg` in
[basic/interp.asm](../../basic/interp.asm). The spaces are written by
`sh_fill` in [sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM — the
same fill `STRING$` and `CHR$` use.

## Related concepts

- [Strings and string space](../concepts/strings-and-string-space.md) — where string values live

## Tests that cover it

- `make str-domain-acceptance` — the count's range, both error kinds and the
  −32768 boundary.
- `make string-acceptance` — `SPACE$(0)` and `SPACE$(3)` against the reference.
- `make kwsweep` — the length row, the content row (`[ 32  32 ]`) and the
  error rows for {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
