<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PDL` — the position of a paddle

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PDL(n)` reads paddle number `n`, a turning knob plugged into a joystick port,
and returns its position as a number from 0 to 255. Each port can carry six
paddles, so `n` runs from 1 to 12.
zerobas behaves like the Philips VG-8020 in every case we have measured,
errors included.

## Syntax

```
PDL(<numeric expression>)
```

One argument, 1 to 12.

## Details

- **Odd numbers are port 1, even numbers port 2**: paddles 1, 3, 5, 7, 9, 11
  are the six of port 1, and 2, 4, … 12 the six of port 2.
- **No paddle reads 255.** With nothing plugged in, every `PDL(1)` to
  `PDL(12)` is 255, not 0.
- **A paddle in its centre position reads 128**, on both machines (measured
  with the emulator's paddle device plugged into port 1).
- **0 is not a paddle number**: `PDL(0)` is `Illegal function call`.
- **The argument is truncated toward zero**, then checked: `PDL(12.6)` is
  `PDL(12)` and reads 255, while `PDL(0.6)` is `PDL(0)` and an error.
- **A string argument** is `Type mismatch` (error 13), not error 5 — even
  though it would also be out of range.

| you write | you get |
|---|---|
| `PDL(1)` … `PDL(12)`, nothing plugged in | 255 |
| `PDL(1)`, a centred paddle in port 1 | 128 |
| `PDL(0)`, `PDL(13)`, `PDL(0.6)` | error 5, `Illegal function call` |
| `PDL("A")` | error 13, `Type mismatch` |
| `PDL` (no parentheses) | error 2, `Syntax error` |

The error set the tier sweep checks is {2, 5, 13}, the same on both machines.

## Example

```
10 ON ERROR GOTO 60
20 PRINT PDL(1);PDL(2);PDL(12)
30 PRINT PDL(12.6)
40 PRINT PDL(0)
50 END
60 PRINT "Error";ERR:RESUME NEXT
RUN
 255  255  255
 255
Error 5
```

No paddle is plugged in, so every paddle reads 255.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_pdl.out`](../../scratchpad/kwdoc_pdl.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

**RAM usage** is not yet proven: the RAM comparison has no `PDL` row yet,
because its telling row needs a paddle plugged in.

## What we found, and how

- **The BIOS routine was a stub** (2026-07-23). zerobas runs on C-BIOS, whose
  paddle routine only printed the word `GTPDL` on the screen. zerobas supplies
  its own, in its cassette/BIOS patch: it pulses the port and counts how long
  the paddle answers. The counting speed is set so a centred paddle reads
  exactly 128, the reference's value.
- **The first build returned the paddle number itself** (fixed the same day).
  The tool that assembles the final ROM copied zerobas's earlier BIOS
  additions but not the two new entries (this one and `PAD`'s), so C-BIOS's
  stub was still in place.
- **The first sweep row could not tell a real `PDL` from a fake** (2026-09-15,
  D-KWPLUG). It read the empty-port 255, which a `PDL` answering 255 to
  everything would also give. A row with a paddle plugged in, reading 128, was
  added.

## Where it lives

- `ev_ff_pdl` in [basic/expr.asm](../../basic/expr.asm) checks the argument
  (`ev_ff_ckpdl`) and calls the BIOS entry `GTPDL`.
- `gtpdl` in [tape/tape.asm](../../tape/tape.asm) is zerobas's own version of
  that BIOS routine.
- Design notes: [spec-basic-input-devices.md](../spec-basic-input-devices.md)
  §9.

## Tests that cover it

- `make input-devices-acceptance` — the grammar, error and truncation rows,
  every paddle number with nothing plugged in, and every paddle number with a
  paddle or a touch pad plugged into either port, against the VG-8020.
- `make kwsweep` — the empty-port row, the plugged-paddle row and the error
  rows for {2, 5, 13}.
