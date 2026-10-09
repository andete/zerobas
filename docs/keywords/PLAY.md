<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `PLAY` — play music in the background

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: what `PLAY(n)` reads on the very statement after a `PLAY`
> (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`PLAY "mml"` plays music written in MML, a small music language of note
letters and commands, on up to three voices of the sound chip at once. The
statement returns straight away and the music plays on in the background
while the program runs. `PLAY(n)` asks whether a voice is still playing.
zerobas plays the same notes, at the same pitch, volume and length, as the
Philips VG-8020, and raises the same errors, in every case we have measured.

## Syntax

```
PLAY <string>[,<string>[,<string>]]
PLAY(<voice>)                        (a function: is it playing?)
```

Each string is any string expression (`PLAY A$,B$` works) and drives one
voice: the first channel A, the second B, the third C. An empty string `""`
leaves that voice alone, so `PLAY "","","C"` plays on the third voice only.

## Details

### The MML commands

| command | meaning | refused (error 5) |
|---|---|---|
| `A`–`G` | a note; `#` or `+` raises it, `-` lowers it; a number after it is its length | — |
| `N` n | a note by number, 1–96 (`N1` is C#1, `N96` is C9) | `N97` |
| `R` | a rest, with an optional length | `R0` |
| `O` n | octave, 1–8 | `O9` |
| `L` n | default note length, 1–64 (bigger is shorter); a `.` after a length dots it | `L0` |
| `T` n | tempo, 32–255 | `T31` |
| `V` n | volume, 0–15 | `V16` |
| `S` n | envelope shape | `S16` |
| `M` n | envelope period, 1–65535 | `M0` |
| `X` var`;` | play the MML held in a string variable, then carry on | `X` with no `;` |

- **An accidental stays inside its octave.** `C-` in octave 4 is the B at the
  top of octave 4, not the B below it, and `B#` is the C at the bottom of the
  same octave. Both machines do this at every octave.
- **A number too big for its command is refused**, even when it would wrap
  round to a legal value: `T65568` is error 5, not `T32`. `M65535` is legal.
- **`&` (tie), `>` and `<` (octave up and down) are not MSX1 MML.** Both
  references refuse them with error 5, and so does zerobas.
- **`X` runs a sub-string like a subroutine**: the outer string continues
  after it, and settings made inside it (an `O7`, say) stay in force after it.
  `X` may be nested. An undefined variable is an empty string; a numeric one is
  `Type mismatch` (13); a string that includes itself ends in `Out of memory`
  (7), which `ON ERROR` can trap.
- **The music outlives the program.** A clean `END` leaves it playing, and so
  do `NEW` and a trapped error. An *untrapped* error or `STOP` stops
  it and silences the sound chip; `CONT` does not bring it back. `BEEP` stops
  it too; `SOUND` does not.
- **A `PLAY` that names fewer voices than are playing** leaves the others
  playing: `PLAY "C"` while voice 2 is busy does not cut voice 2 off.

### `PLAY(n)`

- `PLAY(0)` is −1 if **any** voice is playing, 0 if all are quiet.
- `PLAY(1)`, `PLAY(2)`, `PLAY(3)` ask about voice 1, 2, 3.
- The argument is truncated toward zero: `PLAY(3.7)` is `PLAY(3)`.
- `PLAY(4)` and `PLAY(-1)` are `Illegal function call` (error 5).

### Errors

| situation | error |
|---|---|
| a value out of range, an unknown command letter (`PLAY "H"`), `&`, `>`, `<` | 5 `Illegal function call` |
| a number instead of a string (`PLAY 5`, `PLAY "C",5`) | 13 `Type mismatch` |
| `X` naming a numeric variable (`PLAY "XA;"`) | 13 `Type mismatch` |
| `X` sub-strings that include themselves | 7 `Out of memory` |
| nothing after `PLAY`, or a trailing comma (`PLAY "A",`) | 24 `Missing operand` |
| an empty slot before a comma (`PLAY ,"E"`), or four strings | 2 `Syntax error` |

## Example

```
10 ON ERROR GOTO 100
20 PLAY "T120O4L8CDEFG","O3L2C"
30 FOR I=1 TO 9:NEXT
40 FOR I=0 TO 3:PRINT PLAY(I);:NEXT
50 PRINT
60 IF PLAY(0) THEN 60
70 PRINT PLAY(0)
80 PLAY "V16C"
90 END
100 PRINT "Error";ERR:RESUME NEXT
RUN
-1 -1 -1  0
 0
Error 5
```

Two voices are given, so `PLAY(0)`, `PLAY(1)` and `PLAY(2)` read −1 and
`PLAY(3)` reads 0. Line 60 waits until the music has finished.

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_play.out`](../../scratchpad/kwdoc_play.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`PLAY(n)` on the very next statement after a `PLAY`.** At every `PLAY` the
VG-8020 marks all three voices busy in its work area, and its interrupt then
clears the idle ones within a tick; zerobas marks only the voices it was given.
So a read on the very next statement can differ: with line 10
`PLAY "L1CDEFGAB"` and line 20 `PRINT PLAY(0);PLAY(1);PLAY(2);PLAY(3)`, the
VG-8020 prints `-1 -1 -1  0` and zerobas `-1 -1  0  0`. Any statement at all in
between (`FOR I=1 TO 1:NEXT` is enough) and both machines agree, which is why
the example has line 30. Joost ruled on 2026-09-27 to **decline** reproducing
this window; it stays a stated difference.

The one rung not yet proven is **RAM usage**: the work-area cells written
differ between the machines, and in the last comparison (2026-10-01) three of
the ten test programs also showed a different amount of free string space.

## What we found, and how

- **`PLAY(n)` did not exist** (added 2026-08-28, D-PLAYFN). `PLAY(0)` was
  `Missing operand`. Measuring it showed that `n = 0` means "any voice" rather
  than "the first voice" — two rules that agreed until a program played only
  the second or the third voice — and that the argument is truncated, not
  rounded.
- **Too-large numbers slipped through** (fixed 2026-08-31, D-PLAYCORNER).
  `T65568` wrapped round to `T32` and played; `M0` was accepted. Both
  references refuse all of them.
- **Accidentals at the edge of an octave played the wrong note** (fixed
  2026-08-31, D-CLAMPPITCH). zerobas borrowed from the next octave; a trace of
  the sound chip showed the reference stays inside the octave.
- **A shorter `PLAY` cut another voice off** (fixed 2026-08-31, D-MUSICF): the
  other voice stopped advancing but kept sounding, forever.
- **An aborted program kept playing forever** (fixed 2026-09-03, D-GICINI). An
  untrapped error, `STOP`, or a `BEEP` stops the music on both references.
  zerobas had a note in the code deferring this to a later slice; the later
  slice shipped and the note was never revisited.
- **`N` was a semitone flat, and `>` and `<` were accepted** (fixed 2026-09-15,
  D-KWPLAY). Both came out of designing rows that read the sound chip's
  registers while a note plays, rather than only asking `PLAY(n)` whether
  something is playing.
- **`X` substring execution arrived on 2026-09-24** (D-PLAYX12), the last
  missing piece of MSX1 MML. Joost ruled the shape: *"Tenant walks the
  chain"* — the music parser looks the variable up itself.

## Where it lives

- `ex_play` and the `PLAY(n)` function `ev_f_play` in
  [basic/play.asm](../../basic/play.asm).
- The MML parser, `play_parse_tenant`, in
  [sub/playparse.asm](../../sub/playparse.asm) (a sub-ROM routine), with
  `pt_number` for the number checks and `pt_cmd_x` for `X`.
- The background player, `play_service`, in
  [basic/playsvc.asm](../../basic/playsvc.asm), run from the timer interrupt.
- `psg_silence` in [basic/sound.asm](../../basic/sound.asm) stops the music
  on an abort and on `BEEP`.
- Design notes: [spec-basic-audio-play.md](../spec-basic-audio-play.md) and
  [spec-basic-playfn.md](../spec-basic-playfn.md); where they disagree with
  this page, this page is current.

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements

## Tests that cover it

- `make play-acceptance` — MML parsing and errors, and the `PLAY(n)` values,
  against the VG-8020.
- `make play-trace-acceptance` — the sound chip's registers, frame by frame,
  while music plays.
- `make gicini-acceptance` — what stops the music and what does not.
- `make kwsweep` — one row per MML command, each reading the sound chip back,
  and the error rows.
- `make kwram` — the RAM-usage comparison.
