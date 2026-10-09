<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PEEK` — read one byte of memory

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PEEK(address)` returns the byte stored at a memory address, 0 to 255. It is
the reading half of [`POKE`](POKE.md). `PEEK` itself behaves exactly like the
Philips VG-8020 in every case we have measured; what you *find* at a given
address is a different question, because zerobas's RAM layout is not the
VG-8020's everywhere (see *Differences*).

## Syntax

```
PEEK(<address>)
```

One argument, always.

## Details

- **The address range is −32768 to 65535.** Negative addresses count down from
  the top of memory: `PEEK(-12288)` reads the same byte as `PEEK(&HD000)`. A
  value of 32768 or more is first wrapped by −65536 and then truncated toward
  zero — the same rule [`POKE`](POKE.md) and [`TIME`](TIME.md) use.
- **Outside that range is `Overflow`** (error 6): `PEEK(65536)`,
  `PEEK(-32769)`, `PEEK(70000)`.
- **A string argument** (`PEEK("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`PEEK()`, `PEEK(1,2)`) is `Syntax error` (error 2).
- **The published MSX work-area variables live at their published addresses.**
  For example `PEEK(&HF41C)+256*PEEK(&HF41D)` is `CURLIN`, the number of the
  line being run, on both machines (65535 in direct mode). Joost ruled on
  2026-09-24 that every published variable the VG-8020 writes and zerobas did
  not is to be maintained at its published address — *"All 29"*. That work is
  partly done ([spec-basic-addr29.md](../spec-basic-addr29.md)).

| you write | you get |
|---|---|
| `PEEK(&HD000)` after `POKE &HD000,66` | `66` |
| `PEEK(65536)`, `PEEK(-32769)` | error 6, `Overflow` |
| `PEEK("A")` | error 13, `Type mismatch` |
| `PEEK()`, `PEEK(1,2)` | error 2, `Syntax error` |

The whole set of errors `PEEK` can raise is {2, 6, 13}, the same on both
machines.

## Example

```
10 POKE &HD000,66
20 PRINT PEEK(&HD000);PEEK(-12288)
30 PRINT PEEK(&HF41C)+256*PEEK(&HF41D)
40 ON ERROR GOTO 80
50 PRINT PEEK(70000)
60 PRINT PEEK("A")
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
 66  66
 30
Error 6
Error 13
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_peek.out`](../../scratchpad/kwdoc_peek.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known in `PEEK` itself.

What a `PEEK` *reads* can differ. Below `$F380`, the MSX standard work area,
zerobas keeps its own working storage (`$E000`–`$F37F`) and its own memory
layout, so a program that PEEKs an undocumented address will not find the
VG-8020's contents there. Inside the standard work area, the cells zerobas
maintains are at their published addresses; the remaining ones from the
"All 29" list are open RAM-usage (TIER 4) work.

The one rung not yet proven is **RAM usage**: a `PEEK` uses the same amount of
free memory on both machines, but the VG-8020 writes a few work-area cells
along the way that zerobas does not.

## What we found, and how

- **The test only asked a yes/no question.** The first sweep row read
  `PEEK(0)>=0`, which is true of every possible byte, so a broken `PEEK`
  would have passed it. A second row (D-KWBATCH7) reads back the exact byte a
  `POKE` just wrote.
- **`CURLIN` was never written** (fixed 2026-09-24, D-CURLIN). zerobas tracked
  the running line with its own pointer, so `PEEK(&HF41C)` read whatever the
  cell held. Joost ruled *"Yes, maintain CURLIN"*; it now reads the line
  number, as on both references.
- **More published cells moved to their addresses on 2026-09-25** (D-ADDR29):
  the variable/array pointers `VARTAB`, `ARYTAB` and `STREND`, the colour cell
  `ATRBYT`, and `DAC`, the number accumulator a [`USR`](USR.md) routine reads.

## Where it lives

The one-argument function path `ev_ff_arg_in` in
[basic/expr.asm](../../basic/expr.asm); the address check is `ev_ff_ckaddr`,
shared with [`INP`](INP.md).

## Tests that cover it

- `make intarg-acceptance` — the address range and its errors.
- `make kwsweep` — the everyday row, the read-back row, the `CURLIN` row and
  the error rows for {2, 6, 13}.
- `make kwram` — the RAM-usage comparison.
