<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `MOTOR` — switch the cassette motor on or off

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`MOTOR ON` and `MOTOR OFF` switch the relay that drives the cassette
recorder's motor; a bare `MOTOR` flips it.
zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
MOTOR [ON|OFF]
```

## Details

- **Exactly three forms**: `MOTOR ON` starts the motor, `MOTOR OFF` stops it,
  and `MOTOR` alone **toggles** it — from off it starts, from on it stops.
- **Everything else is `Syntax error`** (error 2): `MOTOR 1`, `MOTOR 0`,
  `MOTOR "ON"`, `MOTOR A`, `MOTOR ON,OFF`, `MOTOR ON 1`, and — unlike the
  other statements that take `ON`/`OFF`/`STOP` — `MOTOR STOP`.
- **The rest of the line runs**: `MOTOR ON:A=INP(&HAA) AND 16` works.
- **The motor line can be read back.** It is bit 4 of port `&HAA`:
  `INP(&HAA) AND 16` is 16 with the motor off and 0 with it on, on both
  machines. The machine starts with the motor off. The other bits of that
  port differ between the two machines and have nothing to do with `MOTOR`,
  so only bit 4 is compared.

| you write | the motor bit then reads |
|---|---|
| `MOTOR ON` | 0 (running) |
| `MOTOR OFF` | 16 (stopped) |
| `MOTOR` from off | 0 |
| `MOTOR:MOTOR` from off | 16 |
| `MOTOR ON:MOTOR` | 16 |

The error set the tier sweep checks is {2}, the same on both machines.

## Example

```
10 MOTOR ON:A=INP(&HAA) AND 16
20 MOTOR OFF:B=INP(&HAA) AND 16
30 MOTOR:C=INP(&HAA) AND 16
40 MOTOR OFF
50 PRINT A;B;C
60 ON ERROR GOTO 90
70 MOTOR 2
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 0  16  0
Error 2
```

Line 30's bare `MOTOR` finds the motor off and starts it; line 40 stops it
again.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_motor.out`](../../scratchpad/kwdoc_motor.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `MOTOR` leaves the same amount
of free memory on both machines, but each machine writes some work-area cells
the other does not. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **`MOTOR` arrived on 2026-07-27**, with `LOCATE`, `SWAP`, `TRON` and
  `TROFF`, after its forms were measured on the VG-8020 first
  ([spec-basic-missing-class.md](../spec-basic-missing-class.md) §3.5). The
  measurement is where `MOTOR STOP` being an error came from; zerobas's shared
  `ON`/`OFF`/`STOP` reader accepts `STOP` for every other statement, so
  `MOTOR` turns it away itself.
- **The first tests could not see the motor.** They checked only that each
  form was accepted, which a `MOTOR` that did nothing would also pass. Reading
  the relay back through port `&HAA` from BASIC, on both machines, turned
  them into real checks; a do-nothing `MOTOR` fails six of the eight.
- **The sweep row printed a constant** until 2026-09-15 (D-KWMOTOR); it now
  reads the motor bit for each of the three forms.

## Where it lives

`ex_motor` in [basic/missing.asm](../../basic/missing.asm) reads the form with
the shared `onoff_decode` in [basic/program.asm](../../basic/program.asm) and
calls the BIOS entry `STMOTR`, which `stmotr` in
[tape/tape.asm](../../tape/tape.asm) provides.

## Tests that cover it

- `make missing-acceptance` — the accepted forms, every `Syntax error` form,
  and the motor bit read back after each form, against the VG-8020.
- `make kwsweep` — one motor-bit row per form, and the error rows for {2}.
- `make kwram` — the RAM-usage comparison.
