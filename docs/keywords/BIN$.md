<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `BIN$` — a number written in binary

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BIN$(n)` returns the binary digits of `n` as a string: `BIN$(5)` is `"101"`.
It is the base-2 member of a family with [`HEX$`](HEX$.md) and
[`OCT$`](OCT$.md), and all three follow the same rules. zerobas behaves exactly
like the Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
BIN$(<numeric expression>)
```

One argument, always.

## Details

- **The number is read as an unsigned 16-bit value.** Anything from −32768 to
  65535 is accepted; a negative number shows its two's-complement pattern, so
  `BIN$(-1)` and `BIN$(65535)` are the same string, sixteen `1`s.
- **No leading zeros, at least one digit.** `BIN$(0)` is `"0"`, `BIN$(2)` is
  `"10"`, and the longest result is 16 characters.
- **A fraction is truncated toward zero first**: `BIN$(5.7)` is `"101"`, and
  `BIN$(-5.7)` is the pattern for −5.
- **The result is an ordinary string**: it can be concatenated
  (`"<"+BIN$(5)+">"` is `<101>`) and assigned like any other.
- **`BIN` without the `$` is not this function** — it is an ordinary array
  name, as on the reference.

| you write | you get |
|---|---|
| `BIN$(5)` | `"101"` |
| `BIN$(0)` | `"0"` |
| `BIN$(255)` | `"11111111"` |
| `BIN$(-1)`, `BIN$(65535)` | `"1111111111111111"` |
| `BIN$(-32768)`, `BIN$(32768)` | `"1000000000000000"` |
| `BIN$(65536)`, `BIN$(-32769)` | error 6, `Overflow` |
| `BIN$("A")` | error 13, `Type mismatch` |
| `BIN$`, `BIN$()`, `BIN$(1,1)` | error 2, `Syntax error` |

The whole set of errors `BIN$` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 PRINT BIN$(5);" ";BIN$(0)
20 PRINT BIN$(255)
30 PRINT BIN$(-1)
40 PRINT LEN(BIN$(256));BIN$(5.7)
50 ON ERROR GOTO 80
60 PRINT BIN$(65536)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
101 0
11111111
1111111111111111
 9 101
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_bin_s.out`](../../scratchpad/kwdoc_bin_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `BIN$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`BIN$` did not exist until 2026-07-27**, and nothing said so: `BIN$(5)`
  was read as an element of a string array named `BIN$` and quietly gave `""`.
  It was one of the last two keywords that answered wrongly without an error.
  Its whole contract was measured first on the reference, using `HEX$` and
  `OCT$` as calibration because they share its rules:
  [binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md),
  [spec-basic-binfre.md](../spec-basic-binfre.md).
- **Sixteen digits did not fit the buffer its siblings use.** `HEX$` and
  `OCT$` build their digits in an 8-byte buffer; a full-width `BIN$` needs 16.
  That was measured (`LEN(BIN$(65535))` is 16 on the reference) before the
  code was written, not discovered afterwards.
- **Adding it fixed two bugs in its siblings** (same day): `HEX$("A")` printed
  `0` instead of `Type mismatch`, and `OCT$(65536)` printed `0` instead of
  `Overflow`. The three functions now share one body, so the type check and
  the range check are written once.

## Where it lives

`str_fn_bin` in [basic/str-engine.asm](../../basic/str-engine.asm) is an
entry into `str_fn_radix`, the body `HEX$` and `OCT$` share; it reads and
checks the argument. The digits are built by `sh_bin_build` in
[sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Tests that cover it

- `make binfre-acceptance` — the digit patterns, sign, truncation, length and
  the error rows.
- `make kwsweep` — the everyday row and the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
