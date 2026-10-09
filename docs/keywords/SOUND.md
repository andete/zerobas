<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SOUND` — write one register of the sound chip

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SOUND r,v` writes the value `v` into register `r` of the MSX sound chip (the
PSG, an AY-3-8910 type). Registers 0–13 set tone periods, noise, the mixer,
volumes and the envelope. It is the low-level way to make sound; [`PLAY`](PLAY.md)
is the musical one and [`BEEP`](BEEP.md) the simplest.
zerobas writes the same bytes as the Philips VG-8020 and raises the same
errors in every case we have measured.

## Syntax

```
SOUND <register>,<value>
```

Both arguments are numeric expressions. Both are required.

## Details

- **Registers 0 to 13 only.** Registers 14 and 15 are the chip's I/O ports
  (joystick and cassette lines) and are refused, as is anything higher.
- **The value is a byte, 0 to 255**, written whole to every register except 7.
- **Register 7, the mixer, keeps its top two bits.** Those bits set the
  direction of the chip's two I/O ports; `SOUND` replaces only the low six.
  So `SOUND 7,255` leaves the register reading 191 (`&HBF`), and `SOUND 7,192`
  leaves 128 (`&H80`). The example shows the first.
- **Variables work** for both arguments: `V=12:SOUND 8,V`.
- **`SOUND` happens at once.** It is one register write; there is no queue.
- **`SOUND` does not touch `PLAY`'s music.** A `PLAY` still playing in the
  background keeps playing after a `SOUND`, even after a write to the mixer —
  unlike [`BEEP`](BEEP.md), which stops it.

| you write | you get |
|---|---|
| `SOUND 0,123` | register 0 holds 123 |
| `SOUND 7,255` | register 7 holds 191 |
| `SOUND 14,0`, `SOUND 255,0`, `SOUND -1,0` | error 5, `Illegal function call` |
| `SOUND 0,256`, `SOUND 0,-1` | error 5, `Illegal function call` |
| `SOUND 99999,0`, `SOUND 0,99999` | error 6, `Overflow` |
| `SOUND "A",0` | error 13, `Type mismatch` |
| `SOUND 8` (no value) | error 2, `Syntax error` |
| `SOUND` (nothing) | error 24, `Missing operand` |

## Example

```
10 ON ERROR GOTO 100
20 SOUND 0,123:SOUND 7,255
30 R=0:GOSUB 70:PRINT V;
40 R=7:GOSUB 70:PRINT V
50 SOUND 7,184:SOUND 14,0
60 END
70 T=TIME
80 IF TIME=T THEN 80
90 OUT &HA0,R:V=INP(&HA2):RETURN
100 PRINT "Error";ERR:RESUME NEXT
RUN
 123  191
Error 5
```

The subroutine at 70 reads a register back: it selects it on port `&HA0` and
reads it on port `&HA2`. It waits for a clock tick first because the
VG-8020's interrupt routine selects a different register every tick.
Line 50 puts the mixer back to its usual value, 184.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_sound.out`](../../scratchpad/kwdoc_sound.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SOUND` leaves the same amount of
free memory on both machines, but the VG-8020 writes some work-area cells that
zerobas does not (and, in one of the two test programs, the other way round).
Nothing a program can observe through `FRE` differs.

## What we found, and how

- **Registers 14 and 15 are refused, not ignored** (2026-07-21, when `SOUND`
  was built). The design draft said they were silently masked; the VG-8020
  raises `Illegal function call` for them, so zerobas does too.
- **The mixer's top two bits are kept** (2026-07-21). Reading the register back
  after `SOUND 7,255` and `SOUND 7,192` showed the VG-8020 never changes them.
- **A variable value went to the wrong register** (fixed 2026-09-27, D-SNDVAR).
  `V=12:SOUND 8,V` left register 8 at 0, because looking up the variable
  overwrote the register number zerobas was holding. Every test until then used
  literal numbers, which is why none noticed.
- **The sweep row used to print a constant** (2026-09-14, D-KWBREADTH). It now
  reads the written byte back out of the chip, so a `SOUND` that wrote nothing
  fails it.

## Where it lives

`ex_sound` in [basic/sound.asm](../../basic/sound.asm). The argument checks are
the shared byte-argument routine `get_byte_arg` in
[basic/interp.asm](../../basic/interp.asm). Design notes:
[spec-basic-audio-play.md](../spec-basic-audio-play.md) §2.1.

## Tests that cover it

- `make sound-acceptance` — every register and value edge above, the mixer
  mask, and the variable-argument rows, read back from the chip, against the
  VG-8020.
- `make gicini-acceptance` — `SOUND` leaves background music alone.
- `make kwsweep` — the everyday row, the read-back row, and the error rows for
  {2, 5, 13, 24}.
- `make kwram` — the RAM-usage comparison.
