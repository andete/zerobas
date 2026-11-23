<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `PROMPT` (sub-ROM $0181) — display the prompt

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xsubpmt.asm](../../../probes/bios/spec/xsubpmt.asm), [scratchpad/AE_xsubpmt_msx2.out](../../../scratchpad/AE_xsubpmt_msx2.out), decoded by `scratchpad/xsubpmt_decode.py`; run with `tools/agent_wt.py --fresh`).

## Summary

`PROMPT` displays BASIC's prompt. On an MSX2 the prompt can be changed with `SET PROMPT`, stored in
the clock chip's battery-backed memory. PROMPT prints that stored prompt when the clock chip's block 3
holds one (ID 2), else "Ok", then a new line. It prints through CHPUT, at the cursor. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

Case numbers `[M xsubpmt n]` are the probe's case table. All three references gave identical records in every case
[M xsubpmt 0-15].

**Interface.**
- In: none. Out: none. Registers: all [P App. 1, SUB-ROM PROMPT]. Measured: AF, BC, HL, IX changed in every case;
  DE changed on the "Ok" path and kept on the block-3 path [M xsubpmt 0-15]. A / F / BC on return are leftovers of
  the path (e.g. A $0A, F $43 after "Ok"; A $00, F $44 after a block-3 prompt) [M xsubpmt 0, 3].
- Interrupts on return: **on**, also when entered with DI [M xsubpmt 0, 1].

**Behaviour.**
- `SET PROMPT` stores up to 6 characters [P Ch. 2 §2.10] in clock-chip block 3 with ID 2, two 4-bit registers per
  character [P Ch. 5 §6.7, Figure 5.34]: register 2k−1 holds character k's low nibble, register 2k its high nibble —
  "ABCDEF" written that way is printed as "ABCDEF" [M xsubpmt 3].
- When block 3's ID (register 0) is 2: the stored characters, from the first, up to the first $00 or 6 characters,
  then CR LF. "ABC" $00 "QR" prints "ABC"; "ABCDEF" prints all six; six $00 print nothing but CR LF (not "Ok")
  [M xsubpmt 2-5].
- When the ID is anything else — 0 (a title, also an empty one), 1 (a password), 3 — "Ok" CR LF, whatever block 3
  holds [M xsubpmt 0, 6-8].
- Every character goes through CHPUT: H.CHPU ($FDA4) sees exactly the characters printed, in order, then $0D $0A
  [M xsubpmt 0-15]. So it prints at the cursor, in the current mode:
  - no leading new line: from the cursor at column 5 the prompt lands in columns 5- of the same row [M xsubpmt 9, 10];
  - afterwards CSRY = the next row, CSRX = 1 [M xsubpmt 0-12];
  - SCREEN 0 at width 40 and 80, SCREEN 1: written to the name table at the cursor [M xsubpmt 3, 11, 12];
  - SCREEN 5: CHPUT is still called for every character but nothing is written to VRAM and the cursor does not move
    (CSRY stays 6) — CHPUT's graphic-mode rule [M xsubpmt 13];
  - on the last line with the key line on (CNSDFG $FF, CRTCNT 24, cursor on row 23): the prompt is printed, the CR LF
    scrolls rows 1-23 up one, row 23 is blanked and the key row (24) is left; the cursor stays on row 23
    [M xsubpmt 14, 15].
- The clock chip is left as it was (block 3 read back unchanged) [M xsubpmt 0-15].
- After a `--fresh` boot block 3 reads all 0 (ID 0, an empty title) on all three, so the fresh prompt is "Ok"
  [M xsubpmt 0].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject): **PROMPT is a no-op** — nothing printed (no CHPUT call, cursor not
moved), registers returned as entered; their fresh clock-chip block 3 reads $F in every register
([scratchpad/AE_xsubpmt_msx2.out](../../../scratchpad/AE_xsubpmt_msx2.out)).

## Open (not measured)

Recorded per case: A F BC DE HL IX IY, IFF (read twice), CSRY CSRX CNSDFG SCRMOD LINLEN CRTCNT, every character
passed to H.CHPU (48 at most) and their count, the number of bytes sent to port $98, clock-chip block 3 through ports
$B4 / $B5, four name-table rows from the cursor's row − 2 (name table filled with '#' before the call).

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | — | DI and EI, the base case | interrupt state on return | on | on | on |
| PR-OK | — | block 3 ID 0 "XYZ"; ID 1; ID 3; fresh (ID 0, empty) | "Ok" vs block 3's text regardless of ID | "Ok" | "Ok" | "Ok" |
| PR-SET | — | ID 2: "ABC" 0 "QR", "ABCDEF", "ABC" + zeros, six $00 | prompt from the clock chip; length rule | up to the first 0, max 6 | same | same |
| PR-NL | — | cursor at column 5, at column 1 | a leading newline when not at column 1 | none | none | none |
| PR-MODE | — | SCREEN 0 (40, 80), 1, 5 | printed via CHPUT, or nothing in graphics | CHPUT; nothing drawn in 5 | same | same |
| PR-KEY | — | key line on, cursor on the last row | scroll behaviour | scrolls, key row kept | same | same |
| PR-HOOK | — | H.CHPU logged | goes through CHPUT vs writes VRAM directly | CHPUT | CHPUT | CHPUT |
| PR-REG | registers distinct | — | registers kept | DE kept on the ID-2 path only | same | same |
| PR-CTL | — | ID 2 with control characters ($07, $0C, $1B) | passed to CHPUT raw vs filtered | ? | ? | ? |
| PR-HI | — | ID 2 with characters ≥ $80 | the same | ? | ? | ? |
| PR-ESC | — | ESCCNT ≠ 0 at entry | the prompt eaten by a pending escape sequence | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md) (the clock chip's settings); [SETSCR](SETSCR.md);
[WRTCLK](WRTCLK.md); MSX1 [CHPUT](../../bios/CHPUT.md).

## Tests that cover it

none yet
