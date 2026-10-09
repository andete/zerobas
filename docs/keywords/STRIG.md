<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `STRIG` — is the space bar or a fire button pressed?

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`STRIG(n)` returns −1 while a trigger is held down and 0 when it is not.
`STRIG(0)` is the space bar; `STRIG(1)` to `STRIG(4)` are the fire buttons of
the two joystick ports. It is the companion of [`STICK`](STICK.md), which
reads the direction.
zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
STRIG(<numeric expression>)              (a function)
STRIG(<numeric expression>) ON|OFF|STOP  (a statement, for ON STRIG GOSUB)
```

## Details

- **The triggers**: 0 the space bar; 1 button A of port 1, 2 button A of
  port 2; 3 button B of port 1, 4 button B of port 2.
- **The answer is −1 or 0**, BASIC's own true and false, so
  `IF STRIG(0) THEN …` works directly.
- **The argument picks the button, not just the port**: with button B of
  port 1 held, `STRIG(3)` is −1 and `STRIG(1)` stays 0.
- **Nothing pressed, or nothing plugged in, reads 0**, for all five.
- **The argument is truncated toward zero**, then checked: `STRIG(4.9)` is
  `STRIG(4)`, not an error.
- **As a statement**, `STRIG(n) ON`, `OFF` and `STOP` switch the trap that
  `ON STRIG GOSUB` installs, so a press can jump to a subroutine while the
  program runs. A bare `STRIG(0)` as a statement is `Syntax error` and
  `STRIG(5) ON` is `Illegal function call`. The trap's own rules are in
  [spec-traps-t2-strig.md](../spec-traps-t2-strig.md).

| you write | you get |
|---|---|
| `STRIG(0)` … `STRIG(4)` with nothing pressed | 0 |
| `STRIG(0)` with the space bar held | −1 |
| `STRIG(5)`, `STRIG(-1)` | error 5, `Illegal function call` |
| `STRIG("A")` | error 13, `Type mismatch` |
| `STRIG` (no parentheses), `STRIG(1,1)` | error 2, `Syntax error` |

The error set the tier sweep checks is {2, 5, 13}, the same on both machines.

## Example

```
10 ON ERROR GOTO 70
20 FOR I=0 TO 4:PRINT STRIG(I);:NEXT
30 PRINT
40 PRINT STRIG(4.9)
50 PRINT STRIG(5)
60 END
70 PRINT "Error";ERR:RESUME NEXT
RUN
 0  0  0  0  0
 0
Error 5
```

Nothing is pressed and no joystick is plugged in, so every trigger reads 0.
A program would normally wait for a press with
`10 IF STRIG(0)=0 THEN 10`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_strig.out`](../../scratchpad/kwdoc_strig.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**RAM usage** is not yet proven: the RAM comparison has no `STRIG` row yet,
because its rows need a key held or a button pressed.

## What we found, and how

- **`STRIG` arrived on 2026-07-23**, with `STICK`, after both machines were
  measured first ([i1_input_notes.md](../../scratchpad/i1_input_notes.md)).
  The BIOS returns `&HFF` for pressed; zerobas widens that to −1, as the
  reference does.
- **The statement form followed two days later** (2026-07-25, with the
  `ON STRIG GOSUB` trap). Until then `STRIG(1) ON` was a `Syntax error` here,
  while the VG-8020 accepts it.
- **Joystick buttons could not be tested until 2026-09-26** (D-RIGFW). The
  emulator the tests run on offers no way to press a joystick button from a
  script, and the idle 0 is also what a `STRIG` that does nothing returns. A
  small USB board that presents itself as a real joystick closed that gap; its
  rows print the other buttons beside the pressed one, so a `STRIG` that read
  the wrong button would fail. (The space bar was tested held down from the
  start.)

## Where it lives

- The function: `ev_ff_strig` in [basic/expr.asm](../../basic/expr.asm)
  checks the argument (`ev_ff_ckstrig`) and calls the BIOS routine `GTTRIG`.
- The statement: `ex_strig_stmt` in
  [basic/program.asm](../../basic/program.asm); the trap is polled from the
  timer interrupt in [basic/traps.asm](../../basic/traps.asm).
- Design notes: [spec-basic-input-devices.md](../spec-basic-input-devices.md).

## Tests that cover it

- `make input-devices-acceptance` — the grammar, error and truncation rows, the
  idle values, and the space bar held down, against the VG-8020.
- `make strig-trap-acceptance` — `ON STRIG GOSUB` with `STRIG(n) ON/OFF/STOP`.
- `make kwsweep` — the held-space-bar row, the joystick rows (run when the USB
  board is attached) and the error rows for {2, 5, 13}.
