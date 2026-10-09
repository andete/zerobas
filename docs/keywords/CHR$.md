<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `CHR$` — the character with a given code

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
- **A space before the parenthesis is allowed**: `CHR$ (65)` is `"A"`.
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

The whole set of errors `CHR$` can raise is {2, 5, 6, 13}, the same on both
machines.

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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `CHR$` uses the same amount of
free memory on both machines, but the VG-8020 also writes a few work-area cells
that zerobas does not, and zerobas writes one the VG-8020 does not. Nothing a
program can observe through `FRE` or the documented variables differs.

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
