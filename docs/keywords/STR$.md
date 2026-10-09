<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `STR$` — a number as text

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STR$(n)` returns the text `PRINT` would show for `n`, without the space
`PRINT` puts after a number. Its inverse is [`VAL`](VAL.md):
`VAL(STR$(1.5))` is 1.5. zerobas behaves exactly like the Philips VG-8020 for
every case we have measured, errors included.

## Syntax

```
STR$(<numeric expression>)
```

One argument, always.

## Details

- **A non-negative number keeps its leading space**; a negative one starts
  with `-`. So `STR$(5)` is `" 5"` (two characters) and `STR$(-34)` is
  `"-34"`.
- **There is no trailing space.** `PRINT` adds one after every number;
  `STR$` does not.
- **Fractions and large numbers are written the way `PRINT` writes them**:
  `STR$(1.5)` is `" 1.5"` and `STR$(1E9)` is `" 1000000000"`; `STR$(.5)` and
  `STR$(1E-5)` read `.5` and `1E-05`.
- **A string argument** (`STR$("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`STR$()`, `STR$(1,1)`), is `Syntax error`
  (error 2).

| you write | you get |
|---|---|
| `STR$(5)` | `" 5"` |
| `STR$(-34)` | `"-34"` |
| `STR$(1.5)` | `" 1.5"` (length 4) |
| `STR$(0)` | `" 0"` (length 2) |
| `STR$(1E9)` | `" 1000000000"` (length 11) |
| `STR$("A")` | error 13, `Type mismatch` |
| `STR$()`, `STR$(1,1)` | error 2, `Syntax error` |

The whole set of errors `STR$` can raise is {2, 13}, the same on both
machines.

## Example

```
10 PRINT "<";STR$(5);">"
20 PRINT "<";STR$(-34);">"
30 PRINT "<";STR$(1.5);">"
40 PRINT LEN(STR$(0));LEN(STR$(1E9))
50 PRINT VAL(STR$(1.5))+1
60 ON ERROR GOTO 90
70 PRINT STR$("A")
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
< 5>
<-34>
< 1.5>
 2  11
 2.5
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_str_s.out`](../../scratchpad/kwdoc_str_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `STR$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`STR$` handled only whole numbers** (fixed 2026-08-30, D-STRFLT). Any
  other number was silently cut to an integer: `STR$(1.5)` gave 1, and
  `STR$(.5)` and `STR$(1E9)` gave 0. `PRINT`'s own number formatter was
  already right, so the fix was to reuse it rather than write a second one:
  [spec-basic-strflt.md](../spec-basic-strflt.md). The gap had been found the
  day before by D-VAL, which measured `VAL` and `STR$` together:
  [spec-basic-val.md](../spec-basic-val.md).
- **The trailing space was invisible to the tests.** The usual test prints
  `"[";STR$(x);"]"` and the screen reader strips spaces, so `" 1.5"` and
  `"1.5 "` look the same there. The rule is pinned two other ways: a fence
  (`"<"+STR$(1.5)+">"` must read `< 1.5>`) and the length (4, 2 and 11 for
  `1.5`, `0` and `1E9`). A deliberately broken build that kept `PRINT`'s
  trailing space moved exactly those rows and no others.

## Where it lives

`str_fn_str` in [basic/str-engine.asm](../../basic/str-engine.asm). A whole
number is formatted by `pu_fmt_int` in
[basic/printusing.asm](../../basic/printusing.asm); any other number by
`flt_fmt` in [basic/float.asm](../../basic/float.asm), the formatter `PRINT`
uses.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make string-acceptance` — `STR$(42)`, `STR$(-3)` and `STR$` inside
  concatenations.
- `make kwsweep` — the everyday row and the error rows for {2, 13}.
- `make kwram` — the RAM-usage comparison.
- The fraction, size and space rows are in
  [`scratchpad/strflt_probe.py`](../../scratchpad/strflt_probe.py), which no
  `make` target runs.
