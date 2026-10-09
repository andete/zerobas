<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `INP` — read a byte from an I/O port

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: an interrupt can change what a PSG read returns on the
> reference, never here (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`INP(port)` reads one byte from a Z80 I/O port and returns it, 0 to 255. It is
the reading half of [`OUT`](OUT.md); [`WAIT`](WAIT.md) reads a port in a loop.
zerobas performs a plain port read, and checks its argument exactly as the
Philips VG-8020 does.

## Syntax

```
INP(<port>)
```

One argument, always.

## Details

- **The port number goes through the address rule** (−32768 to 65535, as for
  [`PEEK`](PEEK.md)). So `INP(256)` and `INP(-1)` are accepted on both
  machines; past the range is `Overflow` (error 6).
- **A string argument** (`INP("A")`) is `Type mismatch` (error 13).
- **No argument, or two** (`INP()`, `INP(1,2)`) is `Syntax error` (error 2).
- **What a port returns is the hardware's business.** Ports that both
  machines have read the same: `INP(&HA8)`, the primary slot register, reads
  240 on both. A port the two machines wire differently is not compared.
- **Reading the sound chip (PSG):** select a register with `OUT &HA0,r`, then
  `INP(&HA2)` returns its contents. See *Differences* for why the example
  below waits for a clock tick first.

| you write | you get |
|---|---|
| `INP(&HA2)` after `OUT &HA0,0:OUT &HA1,123:OUT &HA0,0` | `123` |
| `INP(256)`, `INP(-1)` | a value, no error |
| `INP("A")` | error 13, `Type mismatch` |
| `INP()`, `INP(1,2)` | error 2, `Syntax error` |
| `INP(99999)` | error 6, `Overflow` |

The error set recorded for `INP`'s every-error rung is {2, 13}; the `Overflow`
row is measured separately, by the argument-range gate. Both machines agree on
all three.

## Example

```
10 T=TIME
20 IF TIME=T THEN 20
30 OUT &HA0,0:OUT &HA1,123
40 OUT &HA0,0:A=INP(&HA2)
50 PRINT A
60 ON ERROR GOTO 100
70 PRINT INP("A")
80 PRINT INP()
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
 123
Error 13
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_inp.out`](../../scratchpad/kwdoc_inp.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**A PSG read can be overtaken by the interrupt on the VG-8020, and not here.**
The VG-8020's 50 Hz interrupt service selects PSG register 14 (the joystick
port) to scan the joystick. If that interrupt lands between a program's
`OUT &HA0,r` and its `INP(&HA2)`, the program reads register 14 instead of r:
a sweep row that had just written 123 to register 0 read 191 (`$BF`, the idle
joystick port) once. zerobas's interrupt leaves the register select alone.
Lines 10–20 of the example wait for a clock tick so that the select and the
read land well inside one frame on both machines. This was recorded on
2026-09-24 (D-PSGLATCH) and deliberately not filed as work: matching it would
mean reproducing a race.

The one rung not yet proven is **RAM usage**: an `INP` uses the same amount of
free memory on both machines, but the work-area cells each one writes along
the way differ.

## What we found, and how

- **The test could not see the value** (D-KWBATCH3). INP's only row
  was `INP(&HA8)>0`, which any wrong non-zero byte passes. A second row writes
  a known byte into the PSG and reads it back.
- **That read-back agreed by luck** (found and fixed 2026-09-24,
  D-PSGLATCH). Every row that selected a PSG register and read it back was
  racing the reference's interrupt, as described above. All eleven such rows
  now wait for a clock tick first.

## Where it lives

`ev_ff_inp` in [basic/expr.asm](../../basic/expr.asm), reached through the
one-argument function path `ev_ff_arg_in`; the argument check is
`ev_ff_ckaddr`, shared with [`PEEK`](PEEK.md).

## Tests that cover it

- `make intarg-acceptance` — the argument range.
- `make kwsweep` — the slot-register row, the PSG read-back row, and the error
  rows for {2, 13}.
- `make kwram` — the RAM-usage comparison.
