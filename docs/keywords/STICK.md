<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `STICK` — the direction of the cursor keys or a joystick

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STICK(n)` returns the direction being pushed, as a number from 0 to 8: 0 when
nothing is pushed, then 1 to 8 clockwise starting from up. `STICK(0)` reads the
cursor keys, `STICK(1)` and `STICK(2)` the joysticks in ports 1 and 2. Its
companion for the fire buttons is [`STRIG`](STRIG.md).
zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
STICK(<numeric expression>)
```

One argument, 0 to 2.

## Details

- **The directions**: 1 up, 2 up-right, 3 right, 4 down-right, 5 down,
  6 down-left, 7 left, 8 up-left; 0 centred.
- **On the cursor keys**, measured with keys held down: up is 1, right 3,
  down 5, left 7, and up and down together cancel to 0.
- **On a joystick**, measured with a real USB joystick: up-right is 2 and
  down-left 6, and `STICK(0)` stays 0 meanwhile.
- **Nothing pushed, or nothing plugged in, reads 0**, for all three.
- **The argument is truncated toward zero**, then checked: `STICK(-0.6)` and
  `STICK(2.6)` are legal.

| you write | you get |
|---|---|
| `STICK(0)`, `STICK(1)`, `STICK(2)` with nothing pushed | 0 |
| `STICK(3)`, `STICK(-1)` | error 5, `Illegal function call` |
| `STICK(40000)` | error 6, `Overflow` |
| `STICK("X")` | error 13, `Type mismatch` |
| `STICK`, `STICK()`, `STICK(0,1)`, `STICK(0)` as a statement | error 2, `Syntax error` |

The errors measured are {2, 5, 6, 13}, the same on both machines.

## Example

```
10 ON ERROR GOTO 60
20 PRINT STICK(0);STICK(1);STICK(2)
30 PRINT STICK(-0.6)
40 PRINT STICK(3)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  0  0
 0
Error 5
```

Nothing is pressed and no joystick is plugged in, so every direction is 0. A
program would normally read `STICK` in a loop, for example
`10 S=STICK(0):IF S=0 THEN 10`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_stick.out`](../../scratchpad/kwdoc_stick.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**RAM usage** is not yet proven: the RAM comparison has no `STICK` row yet,
because its rows need a key held or a joystick pressed.

## What we found, and how

- **`STICK` arrived on 2026-07-23**, with `STRIG`, after both machines were
  measured first ([i1_input_notes.md](../../scratchpad/i1_input_notes.md)).
  The C-BIOS routine it calls already matched the reference's direction table
  exactly, so `STICK` is a thin wrapper. The room for it was made by moving
  `BEEP`'s body into the sub-ROM.
- **Building its tests found a bug in its neighbours.** `PRINT PEEK` with no
  parentheses read 0 on zerobas instead of `Syntax error`, and the same held
  for `VPEEK`, `INP`, `EOF` and `LOF`. Fixed the same day.
- **Joysticks could not be tested until 2026-09-26** (D-RIGFW). The emulator
  the tests run on offers no way to push a joystick from a script, and the
  idle 0 is also what a `STICK` that does nothing returns. A small USB board
  that presents itself as a real joystick closed that gap. Its rows also print
  `STICK(0)` beside `STICK(1)`, so a `STICK` that ignored its argument would
  fail. (The cursor-key form was tested with held keys from the start.)

## Where it lives

`ev_ff_stick` in [basic/expr.asm](../../basic/expr.asm) checks the argument
(`ev_ff_ckstick`) and calls the BIOS routine `GTSTCK`, with interrupts briefly
off, because the interrupt routine also reads the joystick port. Design notes:
[spec-basic-input-devices.md](../spec-basic-input-devices.md).

## Tests that cover it

- `make input-devices-acceptance` — the grammar, error and truncation rows, the
  idle values, and the cursor keys held down, against the VG-8020.
- `make kwsweep` — the idle row, the held-key row, the joystick rows (run when
  the USB board is attached) and the error rows for {2, 5, 13}.
