<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `SCREEN` — choose the display mode

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. No known divergence.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

`SCREEN m` switches the display to one of the four MSX1 modes: 0 is 40-column
text, 1 is 32-column text, 2 is high-resolution graphics and 3 is multicolour
(low-resolution) graphics. Further arguments set the sprite size, the key
click and two cassette and printer settings. zerobas behaves exactly like the
Philips VG-8020 for every case we have measured, errors included.

## Syntax

```
SCREEN [<mode>] [, [<sprite size>] [, [<key click>] [, [<baud>] [, <printer>]]]]
```

Every argument is a numeric expression and every one may be left out, but at
least one must be present.

## Details

- **The work-area cell `SCRMOD` (`&HFCAF`) holds the mode in use.** Switching
  back to text with `SCREEN 0` clears the screen.
- **Sprite size**, 0 to 3: it becomes the two low bits of the VDP register
  copy `RG1SAV` (`&HF3E0`), and the rest of that register is left alone.
- **Key click**, 0 to 255, stored as given in `CLIKSW` (`&HF3DB`):
  `SCREEN ,,2` stores 2, not 1.
- **Baud**, 1 or 2 (the cassette speed): 0 and 3 are refused on both machines.
  zerobas checks it and otherwise ignores it. **Printer**, 0 to 255: checked
  and ignored.
- **The mode is applied before the later arguments are read.** In
  `SCREEN 2,"A"` the mode changes to 2 and then the `Type mismatch` is raised.
  An error in the mode argument itself changes nothing: after
  `SCREEN 2+0*(1/0)` the mode is still the old one.
- **Fractions are truncated**: `SCREEN 1.6` is mode 1 and `SCREEN 3.6` is
  mode 3 (rounding would have given 4, an error).
- **Back to text for messages and the prompt.** An error in a graphics
  program returns to the last text mode and prints its message there, and
  when a program ends the prompt comes back in the last text mode — `SCREEN 1`
  stays `SCREEN 1`. The function-key line is drawn in both text modes
  ([`KEY`](KEY.md)).
- **The text width is kept per mode** — see [`WIDTH`](WIDTH.md).

### Errors

| you write | you get |
|---|---|
| `SCREEN 4`, `SCREEN -1`, `SCREEN 256` | error 5, `Illegal function call` |
| `SCREEN ,4`, `SCREEN 1,99`, `SCREEN 1,,300`, `SCREEN 1,,,0` | error 5 |
| `SCREEN 32768`, `SCREEN -32769`, `SCREEN 1,70000` | error 6, `Overflow` |
| `SCREEN "1"`, `SCREEN ,"A"`, `SCREEN ,,"A"` | error 13, `Type mismatch` |
| `SCREEN`, `SCREEN ,`, `SCREEN 2,`, `SCREEN 2,,` | error 24, `Missing operand` |
| a sixth argument, even empty: `SCREEN 1,,,,,1`, `SCREEN 1,,,,,` | error 2, `Syntax error` |

## Example

Line 20 switches back to text, which clears the screen — the listing and the
`RUN` line with it — so only the program's own output is left:

```
10 SCREEN 2:M=PEEK(&HFCAF)
20 SCREEN 0:PRINT "Mode was";M
30 SCREEN ,,0:C=PEEK(&HF3DB):SCREEN ,,1
40 PRINT "Click switch";C
50 ON ERROR GOTO 80
60 SCREEN 4
70 END
80 PRINT "Error";ERR:RESUME NEXT
RUN
Mode was 2
Click switch 0
Error 5
```

Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_screen.out`](../../scratchpad/kwdoc_screen.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

None known.

The one rung not yet proven is **RAM usage**: `SCREEN` moves free memory the
same way on both machines, but the set of documented work-area cells each one
writes is not the same.

## What we found, and how

- **The mode was not checked like a number** (fixed 2026-08-10, D-SCRERR).
  `SCREEN 4` and `SCREEN -1` were `Syntax error` instead of
  `Illegal function call`, `SCREEN 70000` quietly switched to mode 0, and a
  bad mode expression switched the screen before reporting its error. Reading
  the mode back from `SCRMOD`, instead of looking at a screen the statement
  had just cleared, is what made these measurable
  ([screenerr-msx1-characterization.md](../screenerr-msx1-characterization.md),
  [spec-basic-screenerr.md](../spec-basic-screenerr.md)).
- **`SCREEN 1,,99` set the sprite size to 99** (fixed with D-SCRERR). An
  omitted argument was not counted, so every argument after it landed one
  slot early. No test could see it until the new range check turned it into
  an error the reference does not raise.
- **Multicolour mode, `SCREEN 3`, refused to draw** (fixed 2026-08-22,
  D-SCREEN3); the drawing statements now work there as on both references.
- **The key click was ignored** until 2026-09-16 (D-SCRCLICK). It had been
  filed as unmeasurable; the work-area cell `CLIKSW` shows it on both
  references.
- **The prompt dropped `SCREEN 1` back to `SCREEN 0`** (fixed 2026-09-26,
  D-SCR1PROMPT); the VG-8020 returns to the last text mode.
- **An error in a graphics program showed no message** (fixed 2026-09-27,
  D-GFXERRMSG): zerobas printed it into the graphics screen and came back to
  text only for the prompt.

## Where it lives

`ex_screen` and `scr_extra` in [basic/screen.asm](../../basic/screen.asm);
the per-argument checks for the sprite size, key click and baud are
`spr_extra_arg` in [basic/graphics.asm](../../basic/graphics.asm). The return
to text is `txt_mode` in [basic/repl.asm](../../basic/repl.asm).

## Related concepts

- [The cassette](../concepts/cassette.md) — files on tape, and how BASIC finds them
- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make screenerr-acceptance` — the mode domain, the argument list and the
  order in which errors and mode changes happen, read through `SCRMOD`.
- `make kwsweep` — one row per form (mode, sprite size, key click) and the
  error rows for {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
