<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SPACE$` — a string of spaces

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
  (error 14) — on both machines. After `CLEAR 600`, `LEN(SPACE$(255))` is 255.
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

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SPACE$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

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

## Tests that cover it

- `make str-domain-acceptance` — the count's range, both error kinds and the
  −32768 boundary.
- `make string-acceptance` — `SPACE$(0)` and `SPACE$(3)` against the reference.
- `make kwsweep` — the length row, the content row (`[ 32  32 ]`) and the
  error rows for {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
