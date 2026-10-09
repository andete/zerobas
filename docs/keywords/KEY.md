<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# `KEY` — function-key texts and the function-key line

> **Status (2026-10-09):** level 3 — happy path ✓ · reasonable time ✓ · common
> errors ✓ · RAM usage not yet proven · every error ✓. One recorded
> difference: one work-area cell reads differently while the key line is on
> (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

Each of the ten function keys types a text when it is pressed: F1 types
`color `, F5 types `run` and Enter, and so on. `KEY n,text` changes the text of
key n, `KEY LIST` prints all ten, and `KEY ON` / `KEY OFF` show or hide the
line at the bottom of the screen that labels F1 to F5. zerobas behaves like the
Philips VG-8020 for every case we have measured.

## Syntax

```
KEY <n>, <string>
KEY LIST
KEY ON
KEY OFF
```

`n` is 1 to 10. `KEY(n) ON`, `KEY(n) OFF` and `KEY(n) STOP` are a different
statement: they control the function-key interrupt used by `ON KEY GOSUB`
([spec-traps-t3-key.md](../spec-traps-t3-key.md)).

## Details

- **The ten texts at power-on**, the VG-8020's:

  | key | text | key | text |
  |---|---|---|---|
  | F1 | `color ` | F6 | `color 15,4,4` + Enter |
  | F2 | `auto ` | F7 | `cload"` |
  | F3 | `goto ` | F8 | `cont` + Enter |
  | F4 | `list ` | F9 | `list.` + Enter + two cursor-ups |
  | F5 | `run` + Enter | F10 | form feed (`CHR$(12)`) + `run` + Enter |

  The National CF-3300 has `color 15,4,7` on F6. zerobas ships the VG-8020's
  text on both its builds, by Joost's rule for differences of style between
  the two reference machines (2026-09-04: *"when there is stylish differences
  (color, screen) between the oracles, pick the VG8020"*).
- **`KEY n,text` keeps at most 15 characters**; a longer text is cut. An empty
  text is allowed. The new text is what the key types from then on.
- **`KEY LIST` prints the ten texts, one per line**, with control characters
  shown as blanks: F10's form feed shows as a leading space.
- **The function-key line** shows the first characters of F1 to F5 on the
  bottom row. It is on at power-on. While it is on, that row is not part of
  the text screen: scrolling stops at row 22 and `LOCATE 0,23` lands on row 22.
  After `KEY OFF` the row is free again and both reach row 23.
- **The line stays put** across [`CLS`](CLS.md), `SCREEN 0` and a
  [`WIDTH`](WIDTH.md) change, appears in `SCREEN 1` too, and follows the width:
  at `WIDTH 40` each label is 7 characters on an 8-column pitch, and narrower
  widths shrink them.

### Errors

| you write | you get |
|---|---|
| `KEY 0,"A"`, `KEY 11,"A"`, `KEY -1,"X"` | error 5, `Illegal function call` |
| `KEY 1,5`, `KEY "A","B"` | error 13, `Type mismatch` |
| `KEY 1` (no text) | error 2, `Syntax error` |
| `KEY LIST 1`, `KEY ON 1`, `KEY OFF 1` | error 2, `Syntax error` |
| `KEY` on its own | error 24, `Missing operand` |

## Example

```
10 KEY 1,"HELLO"
20 KEY LIST
30 ON ERROR GOTO 50
40 KEY 11,"X":END
50 PRINT "Error";ERR:RESUME NEXT
RUN
HELLO
auto
goto
list
run
color 15,4,4
cload"
cont
list.
 run
Error 5
```

The last `run` is F10's, whose first character is a form feed that
`KEY LIST` shows as a blank. Line 10 also changes the F1 label on the
function-key line, which is not part of the output shown here.
Run on the VG-8020 and on zerobas on 2026-10-09; both print exactly this
([`kwdoc_key.out`](../../scratchpad/kwdoc_key.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

## Differences from the reference

**`PEEK(&HF3B1)` reads 23 while the function-key line is on, where the
VG-8020 reads 24.** That cell, `CRTCNT`, is the number of text rows. The
VG-8020 keeps it at 24 and takes the key row off inside its own BIOS print
routine; zerobas runs on a different BIOS and reserves the row by lowering the
cell instead. Every visible effect — scrolling, `LOCATE`, the screen editor —
matches; only a program that `PEEK`s the cell sees the difference. It is
recorded as a deliberate price in [basic/sysvars.inc](../../basic/sysvars.inc).

The one rung not yet proven is **RAM usage**, partly for that reason: the set
of documented work-area cells each machine writes is not the same.

## What we found, and how

- **`KEY n,text` and `KEY LIST` were missing** (shipped 2026-09-10, D-KEYSTR).
  Measuring them showed a bigger gap than the statement: zerobas had no
  function-key texts at all, where the references hold ten defaults at power-on.
  All 160 bytes were read from both references, which is how the F6
  difference and the hidden control characters were found
  ([spec-basic-keystr-scout.md](../spec-basic-keystr-scout.md)).
- **A bare `KEY` was `Syntax error`** where both references say
  `Missing operand` (fixed 2026-09-07, D-BAREFIX).
- **`KEY ON` drew nothing** (fixed 2026-09-17, D-FNKLINE and D-SCROLLBOUND).
  The BIOS zerobas runs on paints no function-key line, so `KEY ON` and
  `KEY OFF` had nothing to switch. Joost chose to draw it ourselves
  (2026-09-17: *"go with option c for KEY"*); the layout was measured from the
  VG-8020's screen first, and the row was then reserved so that scrolling and
  `LOCATE` stop above it.
- **The line was hidden at power-on** (fixed 2026-09-25, D-KEYBOOT), although
  the VG-8020 shows it from the first screen.
- **`CLS`, `SCREEN 0` and `WIDTH` erased it, `SCREEN 1` never showed it, and it
  ignored `WIDTH`** (all fixed 2026-09-26: D-KEYCLS, D-KEYSCR1, D-KEYWIDTH). The
  layout rule for every width was measured over 24 widths.
- **A test that agreed on a blank.** The first attempt to test `KEY ON` read a
  fixed spot on the screen and passed on both machines — because both had a
  space there. The tests now read where the cursor stops, which does not depend
  on the screen layout.

## Where it lives

`ex_key`, `key_on`, `key_off` and `key_repaint` in
[basic/screen.asm](../../basic/screen.asm) parse the statement and keep the
key row reserved. The texts, `KEY LIST` and the drawing of the line are the
key-string tenant in [sub/keystr.asm](../../sub/keystr.asm).

## Related concepts

- [Interrupts and traps](../concepts/interrupts-and-traps.md) — what runs between statements
- [ROM layout](../concepts/rom-layout.md) — how zerobas is put together
- [The screen editor](../concepts/screen-editor.md) — typing, fixing and re-entering lines
- [Screen modes](../concepts/screen-modes.md) — the four MSX1 displays

## Tests that cover it

- `make keystr-acceptance` — the range of `n`, the empty text, and `KEY LIST`
  after power-on, after an assignment and after a 20-character text.
- `make kwsweep` — `KEY LIST` after an assignment, F1 pressed after
  `KEY 1,...` (the text it types comes back through `INKEY$`), `KEY ON` and
  `KEY OFF` read through where `LOCATE 0,23` lands, and the error rows for
  {2, 5, 13}.
- `make kwram` — the RAM-usage comparison.
