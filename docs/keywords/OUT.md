<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `OUT` — write a byte to an I/O port

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence in
> `OUT` itself; one recorded difference when a program reads back the sound
> chip (see [`INP`](INP.md)).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`OUT port,value` sends one byte, 0 to 255, to a Z80 I/O port. It is the
writing half of [`INP`](INP.md). zerobas performs a plain port write, and
checks its two arguments exactly as the Philips VG-8020 does — which, it
turned out, means checking them *differently*.

## Syntax

```
OUT <port>,<value>
```

Both arguments are required.

## Details

- **The port wraps; the value does not.** The port number goes through the
  address rule (−32768 to 65535), so `OUT 256,1`, `OUT 40000,0` and
  `OUT -1,0` are all accepted on both machines; `OUT 99999,0` is `Overflow`
  (error 6).
- **The value is a byte, 0 to 255.** `OUT &H2F,256` and `OUT 0,-1` are
  `Illegal function call` (error 5); `OUT 0,40000` and `OUT 0,99999` are
  `Overflow` (error 6).
- **A string in either place** is `Type mismatch` (error 13).
- **A bare `OUT`** is `Missing operand` (error 24); `OUT &H2F` (no value) and
  `OUT &H2F,1,1` are `Syntax error` (error 2).
- **What a port does with the byte is the hardware's business.** The sound chip
  (PSG) is the usual target: `OUT &HA0,r` selects register r and `OUT &HA1,v`
  writes it; `INP(&HA2)` reads it back.

| you write | you get |
|---|---|
| `OUT &HA0,0:OUT &HA1,77` | PSG register 0 holds 77 |
| `OUT 256,1`, `OUT -1,0` | accepted |
| `OUT &H2F,256`, `OUT 0,-1` | error 5, `Illegal function call` |
| `OUT 99999,0`, `OUT 0,40000` | error 6, `Overflow` |
| `OUT "A",1`, `OUT &H2F,"A"` | error 13, `Type mismatch` |
| `OUT` | error 24, `Missing operand` |
| `OUT &H2F`, `OUT &H2F,1,1` | error 2, `Syntax error` |

The error set recorded for `OUT`'s every-error rung is {2, 5, 13, 24}; the
`Overflow` rows are measured separately, by the argument-range gate. Both
machines agree on all of them.

## Example

```
10 T=TIME
20 IF TIME=T THEN 20
30 OUT &HA0,0:OUT &HA1,77
40 OUT &HA0,0:PRINT INP(&HA2)
50 ON ERROR GOTO 90
60 OUT &H2F,256
70 OUT &H2F
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 77
Error 5
Error 2
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_out.out`](../../scratchpad/kwdoc_out.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

Lines 10–20 wait for a clock tick, so that selecting and reading the register
cannot be split by the VG-8020's interrupt; [`INP`](INP.md) explains why.

## Differences from the reference

None known in `OUT` itself.

Reading a PSG register back after an `OUT` can, on the VG-8020, return
register 14 instead when an interrupt lands in between; zerobas's interrupt
never changes the register select. Recorded on 2026-09-24 (D-PSGLATCH) and not
filed as work — the details are on the [`INP`](INP.md) page.

The one rung not yet proven is **RAM usage**: an `OUT` uses the same amount of
free memory on both machines, but the work-area cells each one writes along
the way differ.

## What we found, and how

- **An out-of-range value was sent anyway** (fixed 2026-09-08, D-RAWVAL). The
  value was read with the address rule, which wraps, and cut to its low byte:
  `OUT 0,256` sent 0 and `OUT 0,-1` sent 255 with no error, where both
  references raise error 5. The same fault was in `POKE` and `VPOKE`.
- **…and the obvious tidy-up would have been wrong.** The port looks like the
  same oversight, but the references *accept* `OUT 256,0` and `OUT -1,0`. An
  older measurement table had a single column for both arguments and recorded
  the port's answers as if they were the value's; measuring each position
  separately is what showed the two rules
  ([spec-basic-rawval.md](../spec-basic-rawval.md)).
- **The first sweep row never looked** (D-KWBREADTH). It only selected a PSG
  register and printed a marker; a second row writes a value and reads it back
  through the PSG, so an `OUT` that sent nothing fails.

## Where it lives

`do_out` in [basic/vdpio.asm](../../basic/vdpio.asm), entered from `ex_out` in
[basic/interp.asm](../../basic/interp.asm). The value check is the shared
`eval_byte_checked`; [`WAIT`](WAIT.md) sits beside it and shares its argument
shape.

## Tests that cover it

- `make intarg-acceptance` — the port and value ranges, in both positions.
- `make kwsweep` — the everyday row, the PSG read-back row and the error rows
  for {2, 5, 13, 24}.
- `make kwram` — the RAM-usage comparison.
