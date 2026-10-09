<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `OCT$` — a number written in octal

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`OCT$(n)` returns the octal (base-8) digits of `n` as a string: `OCT$(8)` is
`"10"`. It follows exactly the rules of [`HEX$`](HEX$.md) and
[`BIN$`](BIN$.md), in base 8. zerobas behaves exactly like the Philips
VG-8020 for every case we have measured, errors included.

## Syntax

```
OCT$(<numeric expression>)
```

One argument, always.

## Details

- **The number is read as an unsigned 16-bit value**, −32768 to 65535; a
  negative number shows its two's-complement pattern, so `OCT$(-1)` is
  `"177777"`.
- **No leading zeros, at least one digit.** `OCT$(0)` is `"0"`; the longest
  result is six characters.
- **A fraction goes through the same conversion as `HEX$`'s**, which
  truncates toward zero (measured on `HEX$` and `BIN$`).
- **There is no `&O` in front**; add it yourself to build a literal.
- Outside −32768 to 65535 the result is `Overflow` (error 6).

| you write | you get |
|---|---|
| `OCT$(8)` | `"10"` |
| `OCT$(0)` | `"0"` |
| `OCT$(-1)` | `"177777"` |
| `OCT$(65536)`, `OCT$(70000)`, `OCT$(-70000)` | error 6, `Overflow` |
| `OCT$("A")` | error 13, `Type mismatch` |
| `OCT$()`, `OCT$(1,1)` | error 2, `Syntax error` |

The whole set of errors `OCT$` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 PRINT OCT$(8);" ";OCT$(0)
20 PRINT OCT$(511);" ";OCT$(-1)
30 ON ERROR GOTO 60
40 PRINT OCT$(70000)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
10 0
777 177777
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_oct_s.out`](../../scratchpad/kwdoc_oct_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `OCT$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`OCT$` arrived on 2026-07-10** with `HEX$`, `STRING$`, `SPACE$` and
  `INSTR`: [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **`OCT$` had no range check at all** (fixed 2026-07-27). `OCT$(65536)`
  printed `0` — the number cut to 16 bits — where the VG-8020 says
  `Overflow`. `HEX$` had the check and `OCT$` simply did not: the two were
  near-copies, and the five bytes that differed were exactly the missing
  check. `OCT$("A")` also printed `0` instead of `Type mismatch`. Both were
  found while measuring `BIN$` against its siblings, and the three now share
  one body: [binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md),
  [spec-basic-binfre.md](../spec-basic-binfre.md).

## Where it lives

`str_fn_oct` in [basic/str-engine.asm](../../basic/str-engine.asm) is an
entry into `str_fn_radix`, shared with `HEX$` and `BIN$`; it reads and checks
the argument. The digits are built by `sh_oct_build` in
[sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Tests that cover it

- `make string-acceptance` — `OCT$` of 8, 0 and −1 against the reference.
- `make str-domain-acceptance` — −1 and the overflow edge.
- `make binfre-acceptance` — the `OCT$(65536)` and type rows.
- `make kwsweep` — the everyday row and the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
