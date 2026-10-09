<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PAD` — read a touch pad

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PAD(n)` reads a touch pad (a drawing tablet) plugged into a joystick port: is
it being touched, where, and is its button pressed. `n` runs from 0 to 7, four
numbers per port.
zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
PAD(<numeric expression>)
```

One argument, 0 to 7.

## Details

- **Four questions per port** — 0 to 3 for port 1, 4 to 7 for port 2:

  | `n` | answers | value |
  |---|---|---|
  | 0 / 4 | is the pad being touched? | −1 yes, 0 no |
  | 1 / 5 | the X position | 0 to 255 |
  | 2 / 6 | the Y position | 0 to 255 |
  | 3 / 7 | is the pad's button pressed? | −1 yes, 0 no |

- **Ask 0 (or 4) first**, then read the position: in zerobas the touch
  question is what takes a new position reading, following the published MSX
  calling sequence, and `PAD(1)` and `PAD(2)` return what it found.
- **The position is remembered.** When the pen is lifted, the X and Y
  questions keep answering the last position, on both machines.
- **Nothing plugged in reads 0**, for all eight.
- **The argument is truncated toward zero**, then checked: `PAD(7.5)` is
  `PAD(7)`.

| you write | you get |
|---|---|
| `PAD(0)` … `PAD(7)`, nothing plugged in | 0 |
| `PAD(8)`, `PAD(-1)`, `PAD(9)` | error 5, `Illegal function call` |
| `PAD("A")` | error 13, `Type mismatch` |
| `PAD` (no parentheses), `PAD(1,1)` | error 2, `Syntax error` |

The error set the tier sweep checks is {2, 5, 13}, the same on both machines.

## Example

```
10 ON ERROR GOTO 60
20 FOR I=0 TO 7:PRINT PAD(I);:NEXT
30 PRINT
40 PRINT PAD(8)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 0  0  0  0  0  0  0  0
Error 5
```

No touch pad is plugged in, so every question reads 0. A program would
normally wait for a touch with `10 IF PAD(0)=0 THEN 10` and then read
`PAD(1)` and `PAD(2)`.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_pad.out`](../../scratchpad/kwdoc_pad.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**RAM usage** is not yet proven: the RAM comparison has no `PAD` row yet,
because its telling rows need a device plugged in.

## What we found, and how

- **The BIOS routine was a stub** (2026-07-23). zerobas runs on C-BIOS, whose
  touch-pad routine only printed the word `GTPAD` on the screen and answered 0.
  zerobas supplies its own, in its cassette/BIOS patch. One odd reference
  behaviour was reproduced on purpose: an empty port 2 reports the position a
  touched port 1 left behind. Joost ruled on 2026-07-23 to match it, since
  the remembered position makes it come for free.
- **With a real pen, the position and the button were wrong** (fixed
  2026-09-27, D-PADTRACE). The emulator delivers a touch pad's pen only
  through mouse input on its own window, so this could not be tested until a
  small USB board was used to move and click the mouse on 2026-09-26. On the
  VG-8020 the position followed the pen and the button read −1 while held;
  zerobas read 0 for both. Tracing the sound chip's port lines on the
  VG-8020 while the board touched the pad showed how the channel is selected
  and which line carries the button
  ([padtrace_decode.out](../../scratchpad/padtrace_decode.out)); after the
  fix zerobas follows the pen the same way
  ([rigfw_window_touchpad_zb_after_run.out](../../scratchpad/rigfw_window_touchpad_zb_after_run.out)).
- **The button's result is kept, not re-measured on every change** (2026-09-28,
  D-PADWIN). Because the button test needs a visible emulator window, the
  sweep stores its verdict and warns when the touch-pad routine changes.
  Joost ruled that `PAD` *"is very much a leaf command"*, so a stored verdict
  is enough.

## Where it lives

- `ev_ff_pad` in [basic/expr.asm](../../basic/expr.asm) checks the argument
  (`ev_ff_ckpad`), calls the BIOS entry `GTPAD`, and turns the yes/no answers
  into −1 and 0.
- `gtpad` and `gtpad_frame` in [tape/tape.asm](../../tape/tape.asm) are
  zerobas's own version of that BIOS routine.
- Design notes: [spec-basic-input-devices.md](../spec-basic-input-devices.md)
  §9.

## Tests that cover it

- `make input-devices-acceptance` — the grammar, error and truncation rows,
  every `n` with nothing plugged in, and every `n` with an Arkanoid-style pad
  plugged into either port (touch −1, position 255), against the VG-8020.
- `make kwsweep` — the error row (`PAD(9)`), the plugged-device rows, the
  stored button row, and the error rows for {2, 5, 13}.
