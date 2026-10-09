<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `HEX$` — a number written in hexadecimal

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`HEX$(n)` returns the hexadecimal digits of `n` as a string, in capitals:
`HEX$(255)` is `"FF"`. It shares its rules with [`OCT$`](OCT$.md) and
[`BIN$`](BIN$.md). zerobas behaves exactly like the Philips VG-8020 for every
case we have measured, errors included.

## Syntax

```
HEX$(<numeric expression>)
```

One argument, always.

## Details

- **The number is read as an unsigned 16-bit value.** Anything from −32768 to
  65535 is accepted; a negative number shows its two's-complement pattern, so
  `HEX$(-1)` and `HEX$(65535)` are both `"FFFF"`.
- **No leading zeros, at least one digit.** `HEX$(0)` is `"0"`; the longest
  result is four characters.
- **A fraction is truncated toward zero first**: `HEX$(-5.7)` is `"FFFB"`, the
  pattern for −5.
- **There is no `&H` in front.** To build a literal that BASIC reads back,
  add it yourself: `"&H"+HEX$(n)`.
- Outside −32768 to 65535 the result is `Overflow` (error 6).

| you write | you get |
|---|---|
| `HEX$(255)` | `"FF"` |
| `HEX$(0)` | `"0"` |
| `HEX$(-1)`, `HEX$(65535)` | `"FFFF"` |
| `HEX$(-5.7)` | `"FFFB"` |
| `HEX$(70000)`, `HEX$(-70000)` | error 6, `Overflow` |
| `HEX$("A")` | error 13, `Type mismatch` |
| `HEX$()`, `HEX$(1,1)` | error 2, `Syntax error` |

The whole set of errors `HEX$` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 PRINT HEX$(255);" ";HEX$(0)
20 PRINT HEX$(-1);" ";HEX$(65535)
30 PRINT HEX$(4096);" ";HEX$(-5.7)
40 PRINT "&H";HEX$(10)
50 ON ERROR GOTO 80
60 PRINT HEX$(70000)
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
FF 0
FFFF FFFF
1000 FFFB
&HA
Error 6
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_hex_s.out`](../../scratchpad/kwdoc_hex_s.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `HEX$` changes free memory by
the same amount on both machines, but the set of work-area cells written
differs ([`kwram_full.out`](../../scratchpad/kwram_full.out)). Nothing a
program can observe through `FRE` differs. No keyword has this rung yet.

## What we found, and how

- **`HEX$` arrived on 2026-07-10** with `OCT$`, `STRING$`, `SPACE$` and
  `INSTR`. Its edge cases (zero, 255, 65535, −1) were captured on the VG-8020
  rather than assumed:
  [spec-basic-string-functions.md](../spec-basic-string-functions.md).
- **`PRINT HEX$("A")` printed `0`** instead of `Type mismatch` (fixed
  2026-07-27). The argument's type was never checked, so a string left a
  meaningless number behind. It was found while measuring the new `BIN$`
  against its siblings: [binfre-vg8020-characterization.md](../binfre-vg8020-characterization.md).
  The three functions now share one body, so the checks are written once.
- **The range check was already right** for `HEX$` (its sibling `OCT$` was
  the one missing it). The 2026-07-28 survey of every string function's
  numeric argument confirmed `HEX$(-1)` and `HEX$(99999)` agree:
  [spec-basic-str-domain.md](../spec-basic-str-domain.md).

## Where it lives

`str_fn_hex` in [basic/str-engine.asm](../../basic/str-engine.asm) is an
entry into `str_fn_radix`, shared with `OCT$` and `BIN$`; it reads the
argument and checks its range with `fac_to_int_addr`. The digits are built by
`sh_hex_build` in [sub/strheap.asm](../../sub/strheap.asm), in the sub-ROM.

## Related concepts

- [Numbers](../concepts/numbers.md) — integers, single and double precision

## Tests that cover it

- `make string-acceptance` — `HEX$` of 0, 255, 65535 and −1 against the
  reference.
- `make str-domain-acceptance` — −1 and the overflow edge.
- `make binfre-acceptance` — `HEX$` as the calibration family for `BIN$`.
- `make kwsweep` — the everyday row and the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
