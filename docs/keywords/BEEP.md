<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `BEEP` — sound one short beep

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`BEEP` sounds one short, fixed tone and then carries on with the program.
zerobas makes the same tone as the Philips VG-8020, with the same sound-chip
(PSG) settings, and raises the same error, in every case we have measured.

## Syntax

```
BEEP
```

No arguments, ever. There are no other forms.

## Details

- **The tone is fixed**: channel A of the sound chip, a tone period of 85
  (about 1316 Hz), volume 7, for about two screen frames, then silence.
  These values come from a register trace of the VG-8020
  ([spec-basic-audio-beep.md](../spec-basic-audio-beep.md)).
- **Afterwards the mixer is reset, not restored.** The mixer register (which
  channels are audible) ends with the three tone channels on and noise off,
  even when a program had set something else with `SOUND 7,…` before the beep.
  The volume of channel A ends at 0, even when a program had set it with
  `SOUND 8,…`. Both machines do this.
- **It leaves the tone period set.** After a `BEEP`, register 0 of the sound
  chip reads 85 on both machines, whatever it held before. The example below
  shows this.
- **`BEEP` stops music.** If a `PLAY` is still playing in the background, `BEEP`
  stops it, on both machines. `SOUND`, even a write to the mixer, does not.
- **Anything after `BEEP`** other than `:` or the end of the line is
  `Syntax error` (error 2): `BEEP 1`.
- `PRINT CHR$(7)` also beeps, but that is the screen driver's bell, a separate
  path; this page is about the statement.

The whole set of errors `BEEP` can raise is {2}, the same on both machines.

## Example

```
10 ON ERROR GOTO 90
20 SOUND 0,0
30 BEEP
40 T=TIME
50 IF TIME=T THEN 50
60 OUT &HA0,0:PRINT INP(&HA2)
70 BEEP 1
80 END
90 PRINT "Error";ERR:RESUME NEXT
RUN
 85
Error 2
```

Line 60 selects register 0 of the sound chip (port `&HA0`) and reads it back
(port `&HA2`). Lines 40–50 wait for the next clock tick first, because the
VG-8020's interrupt routine selects a different sound-chip register every
tick; reading straight after a tick leaves no room for it to get in between.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_beep.out`](../../scratchpad/kwdoc_beep.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `BEEP` leaves the same amount of
free memory on both machines, but each machine writes some work-area cells the
other does not. Nothing a program can observe through `FRE` differs.

## What we found, and how

- **zerobas makes the tone itself** (2026-07-21). The obvious route was to
  call the BIOS's beep routine, but on the C-BIOS that zerobas runs on, a
  register trace of that routine showed no sound-chip activity at all. So `BEEP` writes the sound chip
  directly, with the values traced from the VG-8020.
- **The first build restored the mixer wrongly** (fixed 2026-07-21, the day it
  was built). It wrote back `$38` instead of `$B8`. The emulator's register
  trace could not see this, because it reports those two bits the same either
  way; a host-side unit test that captures the literal bytes written caught it.
- **`BEEP` did not stop a playing `PLAY`** (fixed 2026-09-03, D-GICINI). Both
  references stop the music at a `BEEP`; zerobas played on. The same fix made
  an aborted program stop its music, as described on the [`PLAY`](PLAY.md)
  page.
- **The sweep row used to print a constant** (2026-09-14, D-KWBREADTH). The
  first `BEEP` row printed a fixed marker, which a `BEEP` that did nothing
  would also print. Its rows now read the sound chip back; the one that scores
  is the tone period the example shows, because the mixer reading turned out
  to depend on how quickly the next statement runs.

## Where it lives

`ex_beep` in [basic/sound.asm](../../basic/sound.asm) stops any music
(`psg_silence`, same file) and then calls the body, `beep_tenant` in
[sub/beep.asm](../../sub/beep.asm), which lives in the sub-ROM. It moved there
on 2026-07-23 to make room for `STICK` and `STRIG`.

## Tests that cover it

- `make beep-acceptance` — the register trace against the VG-8020, including
  `BEEP:BEEP` and mixer and volume values set by `SOUND` before the beep.
- `make gicini-acceptance` — `BEEP` stops background music.
- `make kwsweep` — the everyday row, the tone-period row, and the error row
  for {2}.
- `make kwram` — the RAM-usage comparison.
