<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: reference=VG-8020 disk=no -->

# The screen editor — typing, fixing and re-entering lines

> **Status (2026-10-09):** every editing behaviour measured so far agrees with
> the VG-8020, and with the CF-3300 wherever it was asked too: typing, the cursor
> keys, INS / DEL / BS, the CTRL editing keys, TAB, the function keys, and reading
> a line that spans several rows back when RETURN is pressed. No TIER 1–3 item
> is open. The one visible difference is the prompt, which reads `ZB` by
> decision (below).
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

On an MSX there is no separate input line: **the screen is the editor**. What
you type goes onto the screen at the cursor, the cursor keys move freely over
everything that is shown, and nothing happens until you press RETURN. Then BASIC
reads the line the cursor is on **back off the screen** and treats it as if it
had just been typed: a numbered line is stored, anything else runs at once.

That is why the usual way to change a program line is to `LIST` it, move the
cursor up onto it, type over the mistake and press RETURN — and why pressing
RETURN on an old command further up the screen runs it again. The unit BASIC
reads is the **logical line**: one line of text that may cover several screen
rows, because typing (or printing) past the right edge carries on in the next
row.

zerobas reads the screen the same way, with the same keys. The same editor
serves the prompt, `INPUT`, `LINE INPUT` and `AUTO`.

## How it works

### Rows and logical lines

The text screen is a grid of rows. The VG-8020 starts in `SCREEN 0` with 37
columns (`WIDTH 37`), centred on the screen; zerobas starts at 37 too.
`WIDTH` changes the count, up to 40. While the function-key line is shown
(`KEY ON`, the power-on state) the bottom row belongs to it, not to the text.

Which rows belong together is **not** something the screen itself shows. MSX
keeps a table for it in the published work area: `LINTTB` (`$FBB2`), one byte
per row, where **0 means "this row continues onto the next"** and anything else
means "a line ends here". A character typed or printed past the last column
sets the row's entry to 0. Text written straight into video memory with `VPOKE`
does not, so a full row that was `VPOKE`d is a line on its own even though it
looks exactly like a wrapped one. Scrolling moves the table along with the rows.

### What RETURN does

1. From the cursor's row, step **up** while the row above continues onto this
   one: that is the first row of the logical line.
2. Read the rows **down** to the one that ends the line, all of each row.
3. On the row where input began, start at the column where it began, so the
   `? ` of `INPUT` or the number `AUTO` printed is not part of the answer.
4. Drop blank cells at the end (an empty cell and a typed space look the same).
5. Keep at most **254 characters**; the rest is dropped, without an error.
6. Move the cursor to the start of the row below the line's **last** row, then
   hand the text over: to `INPUT`, to the program store, or to be run.

RETURN can be pressed anywhere in the line; the result is the same. Insert
mode ends.

### The keys

| key | code | what it does |
|---|---|---|
| ← → ↑ ↓ | 29 28 30 31 | move the cursor anywhere on the text screen; ends insert mode |
| HOME | 11 | cursor to the top-left corner; the screen stays |
| SHIFT+HOME (CLS) | 12 | clear the screen |
| INS | 18 | switch insert mode on or off |
| DEL | 127 | delete the character under the cursor; the rest of the line moves left |
| BS | 8 | delete the character left of the cursor; the rest moves left |
| TAB | 9 | type spaces up to the next 8-column stop (overwriting, or inserting in insert mode) |
| CTRL+E | 5 | erase from the cursor to the end of the logical line |
| CTRL+U | 21 | erase the whole logical line; the cursor goes to its start |
| CTRL+B / CTRL+F | 2 / 6 | to the start of the previous / next word |
| CTRL+N | 14 | to just after the last character of the logical line |
| CTRL+C | 3 | abandon the line: nothing is stored or run |
| SELECT, ESC | 24, 27 | nothing |
| RETURN | 13 | read the logical line (above) |

A CTRL+letter key gives the letter's code minus 64, so CTRL+H is the same code
as BS, CTRL+K as HOME, CTRL+R as INS and CTRL+M as RETURN; zerobas's editor
acts on the code, whichever key produced it.

The details that make these keys work as a unit:

- **Insert mode** pushes the rest of the logical line to the right as you type.
  When the line's last row is full the overflow spills into a new row: a blank
  continuation row is used if there is one; otherwise the rows below move down
  to make room, and on the bottom row the screen scrolls up. The cursor then
  shows only its bottom three pixel rows instead of a full block. RETURN, the
  cursor keys, HOME, CLS and the CTRL keys end insert mode; BS does not, and
  TAB keeps it on.
- **A word** for CTRL+B and CTRL+F is a run of letters and digits. These two
  keys move over the whole screen, not only the current line.
- **CTRL+U inside `INPUT`** erases only back to where the answer began; the
  `? ` stays.
- **The function keys type their text** as if it had been typed: F1 types
  `color `, F5 types `run` and RETURN, and SHIFT+F1 to SHIFT+F5 give F6 to
  F10. The texts, `KEY n,text` and the function-key line are on
  [`KEY`](../keywords/KEY.md).
- **The cursor is a block**: the character under it, drawn inverted.

### Around the edges

- **After a graphics program** the prompt, and an `INPUT` inside the program,
  switch back to the last text mode (`SCREEN 0` or `SCREEN 1`) before reading a
  line. `SCREEN 1` typed at the prompt stays.
- **Re-entering a line runs it again, every time.** A line like `A=A+1:PRINT A`
  re-entered three times prints 1, 2, 3.
- **A cursor key inside `INPUT`** may wander onto other rows of the answer and
  edit them; the answer is still the whole logical line, `? ` excluded.

## Example

A wrapped `PRINT` marks its first row as continuing; the next row ends the
line:

```
10 CLS
20 PRINT STRING$(40,"a");"b"
30 A=PEEK(&HFBB2):B=PEEK(&HFBB3)
40 PRINT A=0;B=0
RUN
aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
b
-1  0
```

`-1` is "true": row 1's entry is 0 (it continues), row 2's is not. The program
prints the comparison rather than the values, because the non-zero value
differs (below). Run on the VG-8020 and on zerobas on 2026-10-09; both print
exactly this
([`kwdoc_screen-editor.out`](../../scratchpad/kwdoc_screen-editor.out), from
[`kwdoc_examples.py`](../../scratchpad/kwdoc_examples.py)).

The editing keys cannot be typed by that checker; the gates below cover them.

## Differences from the reference

- **The prompt reads `ZB`, not `Ok`.** Joost kept it on 2026-09-01 as the sign
  that this is not the reference machine, and on 2026-09-24 gave it the
  reference's layout: *"the ZB prompt stays, but it should have the crlf like
  the OK prompt of the reference."* So it sits alone on its row, like `Ok`, and
  appears in the same places (after a command or an error, not after a stored
  line). The one place an editing key notices: CTRL+B from the start of a line
  lands on `ZB` where the reference lands on `Ok`.
- **`LINTTB`'s non-zero values differ.** The VG-8020 stores a countdown (24, 23,
  …); zerobas stores 1. Only zero / non-zero has a meaning, and that agrees; a
  program that `PEEK`s the table sees different numbers.
- **Not measured on the reference:** CTRL with the keys outside the main block
  (keypad, cursor and special keys); CTRL+F from one row of a wrapped line to
  the next (the reading was not valid on either machine); how many rows the
  longest logical line can take.

## What we found, and how

- **zerobas used to have a line buffer, not a screen editor.** RETURN gave the
  characters typed since the prompt; the cursor keys were thrown away, so a
  typo fixed with ← came out wrong (`A=1`, ←, `2` gave `A=12` instead of `A=2`).
  The screen editor shipped on 2026-09-11 (D-SCREDIT), after its shape was
  scouted (D-EDITSCOUT, 2026-08-26) and its boundary rule measured (D-EDITLINE,
  2026-09-07).
- **Where a line starts cannot be seen on the screen.** Two screens that look
  identical — a full row of `'` written by a wrapping `PRINT`, and the same row
  written by `VPOKE` — give opposite answers on both references when the row
  below is re-entered: the first row is part of the line (and its `'` turns the
  rest into a remark), the second is not. That is `LINTTB`, and C-BIOS already
  kept it, so the "bookkeeping cost" first feared turned out to be zero.
- **C-BIOS's scroll lost a mark**, and a wrap on the bottom row could be
  re-entered as two separate lines; older rows could also inherit a stale
  "continues" mark. Both were one defect in the scroll and were fixed in the
  C-BIOS patch set on 2026-10-06 (D-LINTTBWRAP, D-LINTTBSTALE).
- **INS did nothing and DEL deleted the wrong character** — half of it in
  C-BIOS's key table, which gave INS and DEL no code at all. Insert mode, DEL
  and BS that pull the line together, the insert-mode cursor and the
  bottom-row case landed on 2026-09-26 (D-INSMODE, D-INSBOTTOM), together with
  the block cursor (D-CURSORBLOCK) and a HOME key that no longer cleared the
  screen (D-HOMEKEY).
- **CTRL+letter typed the lowercase letter** (CTRL+E put an `e` in the line), so
  no CTRL editing key could ever reach the editor. Fixed in the key decoding,
  then the five CTRL keys and TAB were measured and built on 2026-10-05
  (D-CTRLKEYS, D-EDCTRL). CTRL+C aborting a line was added earlier, on
  2026-09-07 (D-CTRLC).
- **Two predictions missed the good way** on 2026-10-06: SHIFT+F1 to F5 were
  expected to fail and already worked (D-EDFKEY), and cursor keys inside a
  long `INPUT` answer were expected to diverge and agreed (D-EDINPUTCSR).

## How zerobas does it

The wait for a key stays in the main ROM: `read_line` in
[basic/repl.asm](../../basic/repl.asm) records the row and column where input
began, waits inside the BIOS `CHGET` with interrupts on (so `PLAY` and the
`ON … GOSUB` traps keep running while you type), and hands each key to the
editor. The CTRL editing keys are handled right there, by `ek_ctrl` in
[basic/edctrl.asm](../../basic/edctrl.asm); every other key goes, one per call,
to `readline_tenant` in [sub/readline.asm](../../sub/readline.asm), which lives
in the sub-ROM. It echoes ordinary characters and the cursor keys through the
BIOS `CHPUT`, implements insert mode and DEL / BS by shifting the cells of the
logical line, TAB as spaces typed through the same path, and on RETURN walks
`LINTTB`, reads the cells back with `RDVRM` and leaves the text in the line
buffer. The cell arithmetic both use is in
[basic/edscreen.asm](../../basic/edscreen.asm); the cursor is drawn by
[sub/cursor.asm](../../sub/cursor.asm).

The tenant never waits, because a sub-ROM tenant that blocks while mapped in
would starve the interrupt-driven features. The work-area cells involved are
the published ones: `CSRY`/`CSRX` (`$F3DC`/`$F3DD`), `LINLEN` (`$F3B0`),
`CRTCNT` (`$F3B1`), `LINTTB` (`$FBB2`), `INSFLG` (`$FCA8`) and `SCRMOD`
(`$FCAF`).

Four fixes live in the C-BIOS patch set rather than in zerobas:
[ins-del-keys.patch](../../cbios-repack/ins-del-keys.patch),
[home-key.patch](../../cbios-repack/home-key.patch),
[ctrl-keys.patch](../../cbios-repack/ctrl-keys.patch) and
[linttb-scroll.patch](../../cbios-repack/linttb-scroll.patch). The design notes
are in [spec-basic-screditor.md](../spec-basic-screditor.md); where they
disagree with this page, this page is current.

## Related pages

- [`program-text.md`](program-text.md) — what happens to a numbered line after
  RETURN.
- [`INPUT`](../keywords/INPUT.md), [`AUTO`](../keywords/AUTO.md),
  [`KEY`](../keywords/KEY.md), [`WIDTH`](../keywords/WIDTH.md),
  [`CLS`](../keywords/CLS.md), [`LOCATE`](../keywords/LOCATE.md),
  [`CSRLIN`](../keywords/CSRLIN.md), [`LIST`](../keywords/LIST.md);
  [`screen-modes.md`](screen-modes.md), [`interrupts-and-traps.md`](interrupts-and-traps.md).

## Tests that cover it

- `make screditor-acceptance` — re-entry of a wrapped and of a `VPOKE`d row,
  a typo fixed with ←, the cursor after a re-entered line, the bottom-row
  wrap and the stale mark, `INPUT` answers that wrap or are edited with ↑,
  the return from `SCREEN 2`, TAB, CTRL+E / U / B / F, and F1 / SHIFT+F1; each
  row on the VG-8020, the CF-3300 and zerobas.
- `make ctrlkeys-acceptance` — the code every CTRL key gives, against the
  VG-8020.
- `make linemax-acceptance` — the 254-character limit.
- Insert mode, DEL, BS, HOME and the cursor have no `make` target; the probes
  that measured them are [`insmode_probe.py`](../../scratchpad/insmode_probe.py),
  [`insbottom_probe.py`](../../scratchpad/insbottom_probe.py),
  [`homekey_probe.py`](../../scratchpad/homekey_probe.py) and
  [`cursorblock_probe.py`](../../scratchpad/cursorblock_probe.py).
