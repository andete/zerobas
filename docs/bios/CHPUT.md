<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `CHPUT` ($00A2) — write one character to the screen

> **Spec:** FINAL (2026-11-17) on its core — five measurement rounds, four fresh-review passes; the
> last two found nothing contradicting the data. Joost: "Fix, round 5, FINAL" without a fifth pass.
> The behaviour is stated as EXECUTABLE RULES, checked against every measured case. Coverage is
> field-level: every recorded output (cursor, cells, A, LINTTB entries) is read by a rule's check.
> The items in "Open" stay assumed. Measured on the Philips
> VG-8020 (the main-BIOS reference) by calling CHPUT directly, in SCREEN 0 at width 40; the cursor
> results agree with an earlier reading on the Panasonic CF-3300 through its BDOS.

## Summary

`CHPUT` writes the character in A to the text screen at the cursor and moves the cursor on. For a
control code or an escape sequence it moves the cursor or edits the screen instead. `PRINT` and
the MSX-DOS console both end up here.

zerobas behaves the same in every measured case.

## The specification

Reference: the Philips VG-8020's main BIOS. Second: the Panasonic CF-3300's. Ours: the C-BIOS
repack's CHPUT (the `cbios-repack` patches). The region's shared facts (the screen, the cursor
cells) are on [the screen editor page](../concepts/screen-editor.md).

**How to read the rules below.** Every rule is a sentence AND a check
(`probes/bios/spec/chput_rules.py`, run by `tools/spec_rules.py`; [docs/spec-method.md](../spec-method.md)
§3a) over the measured cases it names.
- **reference:** ✓ means the check holds on EVERY case it selects of the VG-8020's run.
- **zerobas:** the cases where zerobas fails it, which are its differences.

The tables are generated from the checks, so a sentence here cannot say more than the data does.

**Re-runs (2026-11-18).** The rules read zerobas's side of each probe below re-run, unchanged, on the 2026-11-18 build: [`XCH_fix4.out`](../../scratchpad/XCH_fix4.out), [`XCH2_fix4.out`](../../scratchpad/XCH2_fix4.out), [`XCH3_fix4.out`](../../scratchpad/XCH3_fix4.out), [`XCH4_fix4.out`](../../scratchpad/XCH4_fix4.out), [`XCH5_fix4.out`](../../scratchpad/XCH5_fix4.out). The runs cited below are the ones the rules were written from; the reference's side is the same machine and setup.

**Evidence.**
- **[XCH n]**: case `n` of the XCHPUT matrix, [`scratchpad/XCH_table.out`](../../scratchpad/XCH_table.out)
  (program `probes/bios/spec/xchput.asm`; raw run [`scratchpad/XCH_run1.out`](../../scratchpad/XCH_run1.out)).
  The byte is sent alone (cases 0–255), after ESC (256–511), or after the graphic prefix
  (512–767). Each case starts on a `Q` between `P` and `R`, at row 11, column 21.
- **[X2 Gn.i]**: case `i` of group `n` of the round-2 rung XCHPUT2,
  [`scratchpad/XCH2_table.out`](../../scratchpad/XCH2_table.out) (each group's setup is in
  `probes/bios/spec/xchput2.asm`'s header; raw run [`scratchpad/XCH2_run1.out`](../../scratchpad/XCH2_run1.out)).
  The groups:
  - G1: TAB from every column;
  - G2: the screen's corners, key line off and on;
  - G3: ESC or the prefix, then a control code, then `A`;
  - G4: the line and screen edits on a full screen;
  - G5: every byte as `ESC Y`'s parameters;
  - G6: every byte after `ESC x` / `ESC y`.
- **[X3 Gn.i]**: case `i` of group `n` of round 3, XCHPUT3 (`probes/bios/spec/xchput3.asm`'s header;
  raw run [`scratchpad/XCH3_run2.out`](../../scratchpad/XCH3_run2.out)). The groups:
  - G1: byte 1 inside `ESC Y`, the cursor after every byte;
  - G2: every `ESC x` / `ESC y` from both cursor cells set / clear;
  - G3: DEL / BS / 29 wrapping onto a row's end;
  - G4: `ESC A`–`D` at the corners, key line off and on;
  - G5: the line edits with the key line on;
  - G6: the A after an ESC / prefix call.

  Run 1 ([`scratchpad/XCH3_run1.out`](../../scratchpad/XCH3_run1.out)) is NOT used: it left the cursor
  display on, so the cell under the cursor read 255.
- **[X4 Gn.i]**: case `i` of group `n` of round 4, XCHPUT4 (`probes/bios/spec/xchput4.asm`'s header;
  raw run [`scratchpad/XCH4_run1.out`](../../scratchpad/XCH4_run1.out)). It has a NEUTRAL setup: the
  markers are written to VRAM directly, the cursor cells set directly, and no CHPUT or `ESC Y` is used
  to place anything. The groups:
  - G1: 14 sequences from 10 starts, key line off and on, including starts ON the key row;
  - G2: the edits, key line off and on;
  - G3: the separating cases.

  Round 4 RETIRES round 2's G2 / G4 and round 3's G4 / G5 from the rules. Their setup placed the
  cursor with `ESC Y`, so with the key line on the two machines started in different places, and the
  differences were the setup's. Those runs stay on file as evidence.
- **[X5 Gn.i]**: round 5, XCHPUT5. Its case list is GENERATED from `probes/bios/spec/xchput5_cases.py`,
  which documents the setup flags, the record kinds and every group, and also decodes the run, so the
  probe's layout and the rules' reading of it cannot drift. Raw run:
  [`scratchpad/XCH5_run1.out`](../../scratchpad/XCH5_run1.out). The groups:
  - G1: ESC then every byte, then `A`;
  - G2: every control code, then `A`;
  - G3: `ESC y` from both cursor cells set, `ESC x` from both clear;
  - G4: pending state across the prefix;
  - G5: the key row marked with the probe's own bytes;
  - G6: the edits from other positions and on continued rows;
  - G7: TAB from columns 33–39 on the last row.
- **[XM n]**: the CF-3300 reading through its BDOS, [`scratchpad/XM_table.out`](../../scratchpad/XM_table.out).
- **[A]**: assumed, NOT measured.

Units: CSRX / CSRY are the BIOS's 1-based cursor cells. "The last text row" is row 24, or row 23
when the function-key line is shown.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/chput_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/chput_rules.py --write` -->

**67 rules; 67 hold on the reference. Of the 24279 recorded outputs (each case's cursor, cells, A, table entries ...): 24276 read by a rule's check, 3 declared NOT evidence (below), 0 unread.**

#### 0. The interface

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-A** CHPUT returns A unchanged (the rung passes v in A and records the A returned). | 768 | ✓ | ✓ |

#### 1. One byte, from mid-screen (row 11, column 21, on a Q between P and R)

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-PRINT** A byte 32–126 or 128–255 is written at the cursor, which moves right. | 223 | ✓ | ✓ |
| **R-NOP** Bytes 0–7 and 14–27 (incl. 1, the prefix, and 27, ESC, left pending) do nothing visible. | 22 | ✓ | ✓ |
| **R-RIGHT** 28 moves the cursor right one; nothing is written. | 1 | ✓ | ✓ |
| **R-LEFT** 8 (BS) and 29 move the cursor left one; nothing is written. | 2 | ✓ | ✓ |
| **R-DEL** 127 (DEL) moves left one and blanks the cell it moves onto (nothing shifts). | 1 | ✓ | ✓ |
| **R-DOWN** 10 (LF) and 31 move the cursor down one; nothing is written. | 2 | ✓ | ✓ |
| **R-UP** 30 moves the cursor up one. | 1 | ✓ | ✓ |
| **R-HOME** 11 homes the cursor (row 1, column 1); nothing is written. | 1 | ✓ | ✓ |
| **R-CLEAR** 12 homes the cursor and clears the text rows (with the key line on, the key line is redrawn: R5-KEYROW). | 1 | ✓ | ✓ |
| **R-CR** 13 (CR) moves to column 1 of the same row. | 1 | ✓ | ✓ |
| **R-TAB** 9 (TAB) writes spaces up to the next stop of 8 (columns 9, 17, 25, 33). | 1 | ✓ | ✓ |
| **R-TAB-ALL** From column c (0–31, 0-based) a TAB writes spaces to column 8·(c//8 + 1); from 32 on, to the row's end, and the cursor goes to the next row's column 1. | 40 | ✓ | ✓ |

#### 3. ESC v

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-ESC-ABCD** ESC A / B / C / D move the cursor up / down / right / left one, writing nothing. | 4 | ✓ | ✓ |
| **R-ESC-H** ESC H homes the cursor; nothing is written. | 1 | ✓ | ✓ |
| **R-ESC-EJ** ESC E and ESC j home the cursor and clear the screen. | 2 | ✓ | ✓ |
| **R-ESC-KJ** ESC K and ESC J erase from the cursor on (the cursor stays). | 2 | ✓ | ✓ |
| **R-ESC-l** ESC l erases the whole line; the cursor stays where it is. | 1 | ✓ | ✓ |
| **R-ESC-LM** ESC L and ESC M move the cursor to column 1 (the line edits: R4-EDIT, R5-EDIT). | 2 | ✓ | ✓ |
| **R-ESC-OTHER** ESC then any other byte (a control code, or a non-command printable) does nothing visible (that it also ENDS the escape: R5-ESC-ENDS; ESC Y / x / y: R5-ESC-CMD). | 244 | ✓ | ✓ |
| **R-ESC-CTRL** After ESC, a control code (but 1) is swallowed and ends the escape: a following A is printed. | 31 | ✓ | ✓ |
| **R-ESC-1** After ESC, byte 1 still acts as the graphic prefix: ESC, 1, A writes $01. | 1 | ✓ | ✓ |
| **R-ESC-L-CELLS** ESC L leaves the cursor's row blank (an inserted line). | 1 | ✓ | ✓ |

#### 5. ESC Y's parameters

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-Y-ROW** Key line off: ESC Y's row byte r = 32..55 puts the cursor on row r − 31 (1-based) (key line on: R4-Y-KEYCLAMP). | 24 | ✓ | ✓ |
| **R-Y-ROWCLAMP** Key line off: any other row byte but 1 clamps to the last row (24). | 231 | ✓ | ✓ |
| **R-Y-COL** ESC Y's column byte c = 32..71 puts the cursor in column c − 31 (1-based). | 40 | ✓ | ✓ |
| **R-Y-COLCLAMP** Any other column byte but 1 clamps to column 40. | 215 | ✓ | ✓ |

#### 6. The graphic prefix, and pending state

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-PFX-GRAPH** The prefix, then a byte 64–95, writes byte − 64 (graphic $00–$1F) and moves right. | 32 | ✓ | ✓ |
| **R-PFX-PLAIN** The prefix, then a byte 32–63 or 96–255 but 127, writes the byte itself. | 191 | ✓ | ✓ |
| **R-PFX-ESC** The prefix, then ESC, arms the escape: a following A is ESC A (cursor up, nothing written). | 1 | ✓ | ✓ |
| **R-PFX-ALONE** The prefix, then a control code (0–31) or DEL, does what the REFERENCE does with that byte alone (cursor and cells as the VG-8020's mode-0 case); no graphic is written (but 1: R-PFX-1). | 33 | ✓ | ✓ |
| **R-PFX-CTRL** The prefix, then a control code (not 1 or 27), then A: the code acts and the prefix is cancelled -- A is written plainly where the code left the cursor. | 25 | ✓ | ✓ |
| **R-PFX-CTRL-MOVE** … and for codes that move the cursor off row 11 (10, 11, 12, 30, 31), A is not written on row 11. | 5 | ✓ | ✓ |
| **R-PFX-1** The prefix, then 1, then A writes a plain A (the second 1 cancels, it does not re-arm). | 1 | ✓ | ✓ |

#### 8. ESC x / ESC y

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-XY-CURSOR** ESC x v and ESC y v never move the cursor. | 512 | ✓ | ✓ |
| **R-Y-4** ESC y '4' sets $FCAA to 1. | 1 | ✓ | ✓ |
| **R-Y-5** ESC y '5' sets CSRSW ($FCA9) to 1. | 1 | ✓ | ✓ |
| **R-G6-STATE** ESC x / ESC y with any other byte than '4' / '5' leave $FCA9 and $FCAA as they were (round 2's carried state, from 0 / 0). | 512 | ✓ | ✓ |

#### 9. Round 3: byte 1 inside ESC Y, the cursor cells, DEL wrapping, the edges, the key line

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-XY-CELLS** From both cells set, ESC x '4' clears $FCAA and ESC x '5' clears CSRSW; from both clear, ESC y '4' / '5' set them; every other byte after ESC x / y changes neither. | 512 | ✓ | ✓ |
| **R-Y1-SEQ** Byte 1 inside ESC Y (the general rule: R5-Y1): the cursor after each byte of five measured sequences (row byte '%' = 37 = row 6), as the reference gives them: `ESC Y 1 '%' A B` [(1, 1), (1, 1), (1, 1), (1, 6), (34, 6), (35, 6)]; `ESC Y '%' 1 A B` [(1, 6), (1, 6), (1, 6), (1, 6), (2, 6), (35, 6)]; `ESC Y 1 1 '%' '%'` [(1, 6), (1, 6), (1, 6), (1, 24), (6, 24), (7, 24)]; `1 ESC Y '%' '%' A` [(1, 24), (1, 24), (1, 24), (1, 6), (6, 6), (7, 6)]; `ESC Y 1 A '%' B` [(1, 6), (1, 6), (1, 6), (2, 6), (2, 6), (35, 6)]. | 5 | ✓ | ✓ |
| **R-Y1-PARAM** Byte 1 as ESC Y's row or column byte (the other '%' = 37): a SNAPSHOT mid-sequence -- the 1 is not a parameter and the escape is still waiting (R5-Y1); the cursor reads column 1, row 6. | 2 | ✓ | ✓ |
| **R-DEL-WRAPCELL** A DEL that wraps from column 1 to the row above blanks that row's column 40; BS and 29 leave it; none of them changes the rows' LINTTB entries. | 6 | ✓ | ✓ |
| **R-A-PENDING** CHPUT returns A unchanged after an ESC or a graphic prefix too. | 2 | ✓ | ✓ |
| **R-DEL-WRAP-ROWS** … and the row DEL / BS / 29 left (row 11) keeps its blank cells at columns 1 and 2, the row above its column 39. | 6 | ✓ | ✓ |

#### 10. Round 4: the edges, the key row and the edits, from a NEUTRAL setup

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R4-CURSOR** From every corner, key line off and on (and ON the key row): BS / 29 / DEL move left, at column 1 to the row above's column 40, not past the top-left; 28 moves right, at column 40 to the next row unless on the last text row (it stays), from the key row into the last text row; 30 / ESC A up, not past row 1; 31 / ESC B / LF down, not past the last text row, from the key row INTO the last text row; CR to column 1; TAB to the next stop of 8, from column 33 on wrapping like a printable; a printable writes and moves right, at column 40 wrapping; ESC C / D right / left, not past the edges. | 140 | ✓ | ✓ |
| **R4-CELLS** The cells: DEL blanks the cell it moves onto (a row's column 40 included, continued or not); a printable writes its cell; TAB writes spaces; LF from the last text row, and a printable or TAB wrapping from it (or from the key row, from which they first move onto the last text row) scroll rows 1..last up one and blank the last. The key row changes only where the cursor itself writes on it (the key-row cells here compare with each machine's OWN labels -- DSPFNK's text differs; R5-KEYROW pins them against the probe's own markers). | 140 | ✓ | ✓ |
| **R4-LT** LINTTB: after a clear 24, 23, …, 1 down the rows; a wrap from a row sets its entry to 0 (continued) -- the key row's too, when the wrap starts there; a scroll shifts the text rows' entries up one and gives the last text row $AF. | 140 | ✓ | ✓ |
| **R4-A** A comes back as the last byte sent. | 140 | ✓ | ✓ |
| **R4-EDIT** The edits from (row 11, column 21), on rows 1..last text row only: ESC L inserts a blank line (the last text row's content drops off), ESC M deletes the line (a blank last text row), ESC K erases to the line's end, ESC J to the last text row's end, ESC l the whole line, 12 / ESC E / ESC j clear the text rows and home; the key row is never touched. | 16 | ✓ | ✓ |
| **R4-EDIT-LT** LINTTB after an edit from (row 11, column 21), from a fresh table: ESC K / ESC l give the cursor's row $AF; ESC J gives it and every text row below $AF; ESC M shifts the entries below up and gives the last text row $AF; ESC L shifts them down, gives the inserted row $AF and the last text row $FB; 12 / ESC E / ESC j restore 24 … 1 (all positions, continued rows: R5-EDIT). | 16 | ✓ | ✓ |
| **R4-ESC-ENDS** ESC then a non-command byte (Z, ~, DEL) does nothing and ends the escape: the next A is printed. | 3 | ✓ | ✓ |
| **R4-ESCXY-1** ESC x / ESC y, then 1: the 1 is NOT taken as the parameter -- it arms the graphic prefix, and the next A writes $01. | 2 | ✓ | ✓ |
| **R4-ESCXY-ESC** ESC x / ESC y, then ESC: the ESC IS taken as the parameter; the A's after it print. | 2 | ✓ | ✓ |
| **R4-PFX-DEL** The prefix, then DEL, then A: DEL acts (left, blanking P), then A is written there. | 1 | ✓ | ✓ |
| **R4-DEL-NOCONT** DEL at column 1 onto a row that does NOT continue still blanks its column 40. | 1 | ✓ | ✓ |
| **R4-Y-KEYCLAMP** ESC Y's row, with the key line on, clamps to the last TEXT row (23); key line off, row byte 54 is row 23. | 3 | ✓ | ✓ |
| **R4-G3-REST** In these cases A comes back as the last byte sent, and the row above's column 40 ('z') is untouched but by the DEL case; the cells of row 11 are as stated above (Y cases: untouched). | 12 | ✓ | ✓ |

#### 11. Round 5: every escape, pending state, ESC x / y both ways, the key row, the edits anywhere

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R5-ESC-ENDS** ESC then any byte that is not a command (A B C D E H J K L M Y j l x y) or 1 does nothing and ENDS the escape: a following A is printed (240 bytes). | 240 | ✓ | ✓ |
| **R5-ESC-CMD** ESC then a command, then A: the command acts (A B C D move; E j clear; H homes; J K erase; L M edit; l erases the line) and A prints; after ESC x / y / Y the A is their PARAMETER (nothing printed; ESC Y A puts the cursor on the clamped row 24); ESC 1 A writes $01. | 16 | ✓ | ✓ |
| **R5-NOPEND** A control code alone leaves nothing pending but 1 (the prefix: the next A is $01) and 27 (ESC: the next A is ESC A): each acts, then A prints where it left the cursor. | 32 | ✓ | ✓ |
| **R5-XY** From both cursor cells SET, ESC y v changes neither for every v; from both CLEAR, ESC x v changes neither for every v (with R-XY-CELLS: only x / y '4' / '5' clear / set them). | 512 | ✓ | ✓ |
| **R5-PENDING** ESC, ESC x and ESC y STAY PENDING across the prefix + a graphic: ESC 1 A B is a graphic then ESC B (down); ESC 1 A K a graphic then ESC K; ESC x / y 1 A 5: the 5 is their parameter. | 4 | ✓ | ✓ |
| **R5-Y1** Inside ESC Y, byte 1 is the graphic prefix, NOT a parameter: if the next byte is 64–95 it is written as a graphic and ESC Y keeps waiting; any other next byte IS the parameter (so row bytes 0, 13, 31, 96, 128, 255 clamp to row 24). | 9 | ✓ | ✓ |
| **R5-UNTOUCHED** In these pending-state sequences no other row changes: (row 6, columns 1–3) and the last row's (columns 1–3) keep their markers. | 13 | ✓ | ✓ |
| **R5-KEYROW** With the key line on and the KEY ROW marked: a printable / TAB / DEL on the key row write there as anywhere; ESC J, LF and a wrap from the last text row leave it; 12 / ESC E / ESC j REDRAW it (the probe's markers are replaced by the key line's labels: 'c', 'o' at columns 1, 2 on the VG-8020). | 9 | ✓ | ✓ |
| **R5-EDIT** Every edit works from any row and column the same way (key line off): ESC L / M at the last text row only blank it ($AF); LINTTB entries MOVE with their rows (a continued row's 0 shifts down under ESC L, up under ESC M -- not a renumbering); ESC J / K / l mark the rows they blank $AF. | 20 | ✓ | ✓ |
| **R5-TAB-LAST** TAB from columns 33–39 on the last text row wraps and scrolls: the cursor at (1, 24), row 23's entry 0 (continued), row 24's $AF, the rows moved up. | 7 | ✓ | ✓ |

Declared NOT evidence (1 cases: XCH 333): cells — ESC M pulls up the NEXT row, whose content the case before left there (the matrix does not set it); X4 G2 measures ESC M on a known screen

<!-- RULES END -->

## Differences from the reference

None measured: every rule holds on zerobas.

## Open (not measured)

- **[A]** CSRX / CSRY out of range ON ENTRY (0, past LINLEN, past row 24): a program can poke them;
  unmeasured.
- **[A]** The edits with the key line on from positions other than row 11, and `ESC J` / `ESC K` with
  a continued row below the cursor's.
- **[A]** The other registers and the flags.
- **[A]** What the VG-8020's LINTTB values MEAN (24 … 1 after a clear, $AF on a blanked or inserted row,
  $FB on the last text row after `ESC L`, 0 on a continued row): the rules state the values, not why.
- **[A]** Other widths (32, 37, 80) and the graphic modes.
- **[A]** Whether CHPUT goes through the hook H.CHPU ($FDA4), and with interrupts in which state;
  the cursor block's drawing; whether BEL sounds.

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also `biosl-acceptance` rung b1text (L3 in tools/bios_levels.py) and the suites `tools/entry_table.py --bios` lists. Which of those older rows the matrix makes redundant is the audit's next step: a row is retired only with mutation evidence.

