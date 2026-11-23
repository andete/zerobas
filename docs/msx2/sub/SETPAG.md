<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `SETPAG` (sub-ROM $013D) — switch the display and active pages

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xmode.asm](../../probes/bios/spec/xmode.asm), [scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out), decoded by `scratchpad/xmode_decode.py`).

## Summary

`SETPAG` makes DPPAGE the displayed page and ACPAGE the page drawing goes to, in the bitmap modes
(SCREEN 5-8). The display page is the name-table base in R#2. Shared facts:
[the screen-modes page](../concepts/screen-modes.md).

## The specification

**Interface.**
- In: DPPAGE ($FAF5) the display page, ACPAGE ($FAF6) the active page [P App. 1, SUB-ROM SETPAG].
- Out: none. Registers: AF [P App. 1, SUB-ROM SETPAG].
- Interrupts on return: [A].

**Behaviour.**
- In GRAPHIC 4-7 the display page is switched by R#2, the name-table base [P Ch. 4 §4, "Switching
  the display page"]; the base steps by 32 KB in GRAPHIC 4 / 5 [P Ch. 4 §3.6.2], by 64 KB in GRAPHIC
  6 / 7 [A].
- R#2's low bits (set to 1 for an odd page in alternation [P Ch. 4 §4, "Automatic alternate screen
  display"]) are kept / forced [A]; RG2SAV updated [A].
- ACPAGE: only stored for the drawing calls, or also applied (R#45, NAMBAS?) [A].
- In SCREEN 0-4: [A].

**Measured** [M] (the same on all three references, SCREEN 5): DPPAGE 0 / 1 / 3 set **R#2 := $1F / $3F / $7F and R#6
:= $0F / $1F / $3F** -- the sprite pattern base follows the display page; ACPAGE writes no VDP register. The call
also rewrites R#1, R#3 and R#7 from their copies (the probe's $A5 showed up in the VDP). Out: A = SCRMOD, F $40,
interrupts ON.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds set R#2 the same but leave R#6 at $0F and do not rewrite R#1 / R#3 / R#7 from the
copies; other A / F ([scratchpad/AE_xmode_msx2.out](../../scratchpad/AE_xmode_msx2.out)).

## Open (not measured)

Recorded per case: A, F, BC, DE, HL, IX, IY and the alternate set (the handbook says only AF changes), interrupt state, R#2,
RG2SAV, R#13, R#45, DPPAGE, ACPAGE, NAMBAS..ATRBAS, VRAM block sums.

| case | inputs | state | what it separates | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|---|---|---|
| IE | the page's base case (its first row) | entered once with DI, once with EI | interrupt state on return: forced on, forced off, or kept (read twice, §3a) | ? | ? | ? |
| SP-5 | DPPAGE 0..3, ACPAGE ≠ DPPAGE | SCREEN 5, 6 | R#2 = page · 32 KB bits; low bits $1F set | ? | ? | ? |
| SP-7 | DPPAGE 0, 1, 2, 3 | SCREEN 7, 8, and 10-12 | 64 KB step; page 2 / 3 masked, wrapped or refused | ? | ? | ? |
| SP-OOR | DPPAGE 4, $FF | SCREEN 5 | masked to 2 bits vs written raw | ? | ? | ? |
| SP-LOW | DPPAGE 1 | SCREEN 0, 1, 2, 4 | nothing vs R#2 rewritten | ? | ? | ? |
| SP-R2 | — | RG2SAV ≠ R#2; RG2SAV low bits 0 (alternation odd-page form) | R#2 from DPPAGE + fixed bits vs from RG2SAV's bits | ? | ? | ? |
| SP-AC | ACPAGE 0..3 | SCREEN 5 | ACPAGE stored only vs written to NAMBAS / R#45 / R#14 | ? | ? | ? |
| SP-REG | BC, DE, HL distinct | SCREEN 5 | "registers: AF" holds | ? | ? | ? |
| SP-R13 | — | R#13 garbage | alternation rate untouched | ? | ? | ? |

## Related pages

[The screen-modes page](../concepts/screen-modes.md); [CLS](CLS.md); [CHGMOD](CHGMOD.md).

## Tests that cover it

none yet
