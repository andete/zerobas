<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETSCR` (sub-ROM $0189) — start-up screen from the clock chip (interface unpublished)

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubset.asm](../../../probes/bios/spec/xsubset.asm), [scratchpad/AE_xsubset_msx2.out](../../../scratchpad/AE_xsubset_msx2.out), decoded by `scratchpad/xsubscr_decode.py --cases xsubset`; run with `tools/agent_wt.py --fresh`).
>
> Goldfish pass 1 (test writer) 2026-11-23: 4 findings, 3 measured (cases 14, 15 and the log's key-label positions
> added), 1 corrected, 0 moved to open.

## Summary

An entry at sub-ROM $0189 named SETSCR by other open implementations. It is
[SDFSCR](SDFSCR.md) followed by the start-up text: the clock chip's screen settings are applied,
the BASIC banner ("MSX BASIC version 2.0" / "2.1" / "3.0") is printed on the top line, and the
function-key line is shown when the stored key switch is on. The `SET TITLE` title, the password
and the prompt are NOT handled here. The MSX2 Technical Handbook does not list it. Shared facts:
[the screen-modes page](../concepts/screen-modes.md#the-clock-chips-screen-settings).

## The specification

Case numbers `[M xsubset n]` are the probe's case table.

**Interface.**
- Not published [P App. 1, SUB-ROM: not listed].
- In: none [A] (A = 0 and F = 0 in every case; the flags are not inputs of [SDFSCR](SDFSCR.md#the-specification)).
- Out: none. AF, BC, DE, HL, IX changed — A $0A, F $43, BC $7EF1, DE $00E3, HL $F67D, IX $6678 on all three
  references in every case [M xsubset 0-5, 7-13].
- Interrupts on return: **on**, also when entered with DI in SCREEN 1 or 40-column SCREEN 0 (where SDFSCR keeps
  them off) [M xsubset 0, 1, 4].

**Behaviour** (the same on all three references unless a machine is named).
- First the clock chip's block 2 settings exactly as [SDFSCR](SDFSCR.md) applies them: mode, width, colours,
  interlace, key click (SCREEN 0 / 1, width 30 / 37 / 80 / 100, from SCREEN 0, 1 and 5) [M xsubset 0-5]. A $F380-$FFFF
  diff of SETSCR against SDFSCR on the same settings shows only CSRY, CNSDFG and the key-line work area
  $FC18-$FC3E, plus the interrupt counters [M xsubset 6 / 7]. The screen is cleared, as SDFSCR clears it
  ([SDFSCR](SDFSCR.md#the-specification)): with the name table filled with 'Z' before the call, row 0 holds only the
  banner and spaces and row 23 reads as spaces [M xsubset 15].
- The banner, from the first column of the text window on the top row (name-table row 0): **"MSX BASIC version 2.0" on the HB-F900,
  "MSX BASIC version 2.1" on the NMS 8250, "MSX BASIC version 3.0" on the FS-A1WSX**, followed by a new line: CSRY = 2,
  CSRX = 1 after [M xsubset 0-5, 7-13, 15]. In a SCREEN 1 width 30 and a SCREEN 0 width 37 window the banner starts in the
  window's first column (VRAM column 1 / 2) [M xsubset 1, 4].
- A banner longer than the window wraps as CHPUT wraps: in SCREEN 1 width 18 (window = VRAM columns 7-24) row 0 holds
  "MSX BASIC version " and row 1 "2.0" / "2.1" / "3.0" from the window's first column; then the new line, CSRY = 3,
  CSRX = 1 [M xsubset 14].
- At width 100 (TEXT 2, not clamped by SDFSCR) the banner is written to VRAM (it is in the port-$98 log) but not on
  row 0; where it lands is not read [M xsubset 5].
- When block 2 register 9 bit 0 (key line) is 1: CNSDFG := $FF and the first five function keys' labels on
  the bottom row (name-table row 23), as [DSPFNK](DSPFNK.md) draws them (6 characters at width 37, 15 at width 80, 5 at
  SCREEN 1 width 29, 2 at width 18); the key-line work area $FC18-$FC3E holds the labels. When the bit is 0:
  CNSDFG := $00, no key line [M xsubset 0-5, 7, 14].
- Order: the key line is written BEFORE the banner, and more than once. In the log of every byte sent to port $98,
  key 1's label ("AAA" starting a run of 'A') first appears early (offset 896 / 960) and last just before the banner:
  last label at 3773 and "MSX" at 3802 on the HB-F900 / FS-A1WSX (SCREEN 1 width 29), 4037 and 4074 on the NMS 8250
  (width 37) [M xsubset 0]; 2 label runs at 40 columns, 3 at 80 (last at 6997, "MSX" at 9157) [M xsubset 0, 2, 8].
  The final screen is the same either way (key line on row 23, banner on row 0); an order that matters (a banner
  that scrolls the screen) was not constructed.
- Block 3 is not used: a title (ID 0) of 3 or 6 characters, a password (ID 1) and a prompt (ID 2) are never written
  to VRAM (not in the log of every byte sent to port $98 during the call), and the call takes no key — a key queued
  in KEYBUF before the call is still there after it (GETPNT unchanged), also with a 6-character title
  [M xsubset 8-12]. The title colour (block 2 register 11) changes nothing read (palette, cells, banner) [M xsubset 9].
- The ID (block 2 register 0) is not checked: ID 5 gives the same result [M xsubset 13].
- The keyboard buffer is not cleared [M xsubset 0-13]; the clock chip is left as it was [M xsubset 0-13].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject): **SETSCR is a no-op** — no settings applied, no banner, no key line;
registers returned as entered, interrupts on ([scratchpad/AE_xsubset_msx2.out](../../../scratchpad/AE_xsubset_msx2.out)).

## Open (not measured)

Recorded per case: as [SDFSCR](SDFSCR.md#open-not-measured), plus every byte written to port $98 during the call
(`@portlog`; searched for "SXA" and "MSX", and the first / last run of "AAA" with the run count), keys taken from KEYBUF (H.TIMI queues one 'K' whenever the buffer is
empty, at most 4), and a $F380-$FFFF diff for case 7.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | DI and EI, SCREEN 1 / width 37 / width 80 | interrupt state on return | on | on | on |
| SS-EX | — | all three machines | an entry at all | yes | yes | yes |
| SS-EQ | — | the SDFSCR settings | = SDFSCR + something | + banner, key line | same | same |
| SS-TITLE | — | block 3 ID 0: "SXA", "SXASXA"; title colour 0 / 3 | title shown; colour; a key wait at 6 characters | not shown, no wait | same | same |
| SS-PW | — | block 3 ID 1 (password "SXA") | asks for the password vs ignores it | ignored | ignored | ignored |
| SS-PROMPT | — | block 3 ID 2 (prompt "SXA") | block 3 printed vs not | not printed | same | same |
| SS-MODE | — | block 2 mode 0 / 1, width 30 / 37 / 80 / 100 | final mode and width | as SDFSCR | same | same |
| SS-W100 | — | width 100 | where the banner lands | ? | ? | ? |
| SS-WRAP | — | SCREEN 1 width 18 (banner 21 characters) | banner wraps vs truncated | wraps, CSRY 3 | same | same |
| SS-ORDER | — | the port-$98 log's label / banner positions | banner then key line vs key line then banner | key line (2-3 times) then banner | same | same |
| SS-CLR | — | name table := 'Z' before the call | cleared vs left | cleared | same | same |
| SS-GR | — | the state the boot leaves (the title and password are shown at start-up [P Ch. 2 §2.10]) | which start-up code shows the title / asks the password | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [SDFSCR](SDFSCR.md); [PROMPT](PROMPT.md);
[DSPFNK](DSPFNK.md).

## Tests that cover it

none yet
