<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `POKE` — write one byte to memory

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`POKE address,value` stores one byte, 0 to 255, at a memory address. It is the
writing half of [`PEEK`](PEEK.md). zerobas checks both arguments the way the
Philips VG-8020 does and refuses — writing nothing — wherever the VG-8020
refuses.

## Syntax

```
POKE <address>,<value>
```

Both arguments are required. There are no optional forms.

## Details

- **The address range is −32768 to 65535**, as for [`PEEK`](PEEK.md):
  `POKE -12288,7` writes the byte at `&HD000`. Values of 32768 and up wrap by
  −65536, then truncate toward zero; outside the range is `Overflow`
  (error 6).
- **The value is a byte, 0 to 255.** `POKE &HD000,256` and `POKE &HD000,-1`
  are `Illegal function call` (error 5) and leave the byte untouched.
- **Overflow beats the range check:** `POKE 99999,256` is error 6, not 5.
- **A missing value** (`POKE &HD000,`) is `Missing operand` (error 24) and
  writes nothing. A bare `POKE` is also error 24; `POKE &HD000` (no comma) and
  `POKE &HD000,1,1` are `Syntax error` (error 2).
- **A string in either place** is `Type mismatch` (error 13).
- **`POKE` writes anywhere**, the BASIC work area included; nothing stops
  it. The MSX standard work area (`$F380` and up) holds published
  variables at published addresses on both; zerobas's own working storage at
  `$E000`–`$F37F` is not the VG-8020's, so what a POKE there does differs.

| you write | you get |
|---|---|
| `POKE &HD000,65` | the byte at `&HD000` is 65 |
| `POKE &HD000,256`, `POKE &HD000,-1` | error 5, `Illegal function call`, nothing written |
| `POKE 65536,1`, `POKE -32769,1`, `POKE 99999,256` | error 6, `Overflow` |
| `POKE "A",1`, `POKE &HD000,"A"` | error 13, `Type mismatch` |
| `POKE &HD000,`, `POKE` | error 24, `Missing operand` |
| `POKE &HD000`, `POKE &HD000,1,1` | error 2, `Syntax error` |

The whole set of errors `POKE` can raise is {2, 5, 6, 13, 24}, the same on both
machines.

## Example

```
10 POKE -12288,7
20 PRINT PEEK(&HD000)
30 POKE &HD000,PEEK(&HD000)*2
40 PRINT PEEK(&HD000)
50 ON ERROR GOTO 90
60 POKE &HD000,256
70 POKE &HD000,
80 PRINT PEEK(&HD000):END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 7
 14
Error 5
Error 24
 14
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_poke.out`](../../scratchpad/kwdoc_poke.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: a `POKE` statement uses the same
amount of free memory on both machines, but the VG-8020 writes a few work-area
cells along the way that zerobas does not.

## What we found, and how

- **A missing value wrote a zero** (fixed 2026-08-23, D-MISSOPFIX). `POKE
  &HE000,` completed silently and turned the byte into 0, where both references
  stop with `Missing operand`. It turned out to be one rule at sixteen places
  in the language (D-MISSOP), and the fix closed all four that wrote memory:
  [spec-basic-missop.md](../spec-basic-missop.md).
- **An out-of-range value was written anyway** (fixed 2026-09-08, D-RAWVAL).
  The value was read with the address rule, which wraps, and then cut to its
  low byte: `POKE x,256` wrote 0 and `POKE x,-1` wrote 255 with no error. Both
  references raise error 5 and write nothing. `OUT` and `VPOKE` had the same
  fault: [spec-basic-rawval.md](../spec-basic-rawval.md).

## Where it lives

`do_poke` in [basic/poke.asm](../../basic/poke.asm), entered from `ex_poke` in
[basic/interp.asm](../../basic/interp.asm). The value check is the shared
`eval_byte_checked`.

## Related concepts

- [The memory map](../concepts/memory-map.md) — where BASIC keeps things in RAM

## Tests that cover it

- `make intarg-acceptance` — the address and value ranges, each row reading the
  byte back to see whether anything was written.
- `make kwsweep` — the everyday row (read back through `PEEK`) and the error
  rows for {2, 5, 6, 13, 24}.
- `make kwram` — the RAM-usage comparison.
