<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `REDCLK` (sub-ROM $01F5) — read a clock-IC register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xclk.asm](../../../probes/bios/spec/xclk.asm), [scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out), decoded by [xclk_decode.py](../../../scratchpad/xclk_decode.py)). `[R1]` = that run's first sweep (64 reads, MODE's bank set to the block after the case's, TE = 1, AE = 0, blocks as found); `[R2]` = its second (52 reads, blocks 2 / 3 preset so every address's named register differs from the preselected block's, MODE's bank = the case's block XOR 2, TE / AE = each of the four pairs, A $5C on entry). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 4 measured, 0 moved to open.

## Summary

`REDCLK` reads one four-bit register of the clock IC: the time, the alarm, or the battery-backed
settings BASIC keeps there. The caller names the block and the register in one byte, so it never
touches the clock IC's MODE register itself. The clock IC, its blocks and what BASIC stores in them
are on the [concept page](../concepts/clock-and-misc.md).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01F5 [P A1]: through EXTROM, $01F5 returned the named register on every
  read [M R1, R2]. Chapter 5 heads the call with $015F, EXTROM's own address [P 5§6.8].
- In: C = `00MMAAAA` — MM the block (0-3), AAAA the register (0-15) [P A1, 5§6.8].
- Out: A = the register's value, bits 7-4 = 0 (entry A $5C: the 5 is not kept) [M R1, R2].
- F = the flags of `AND $0F` on the value: S 0, Z set for 0, H 1, P/V set for even parity, N 0, C 0, bit 3 a copy
  of the value's bit 3 — $54 for 0, $10 / $14 / $18 / $1C otherwise [M R1, R2: 116/116 reads].
- Registers changed: F [P A1]. B, C, DE, HL, IX, IY and the alternate set were not recorded [A].

**Behaviour.**
- The call selects the block itself; the caller need not write MODE first [P 5§6.8] [M R2: 52/52 reads return the
  named block's register with MODE on another block, every named register preset to differ from the preselected
  one; R1 agrees on 64/64 but some of its blocks hold equal values, so it does not separate on its own].
- **MODE afterwards = (MODE before AND $0C) OR MM:** the bank is left at the block read, TE (bit 3) and AE (bit 2)
  are kept [M R2: all four TE / AE pairs on every block, 52/52; R1 with TE = 1, AE = 0, 64/64].
- Register 13 reads back as MODE after that selection: $08 OR MM in R1 (entry TE = 1, AE = 0) [M R1].
- Registers 14 and 15 (write-only [P 5§6.2]) read $F [M R1] — openMSX's model of a write-only register, recorded
  as such.
- What C's bits 7-6 do when not 0 [A].
- The interrupt state after the call (the probe entered with DI and did not record it) [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) **OR** MM into MODE's bank bits instead of replacing them, so they read
block (preselected bank OR MM) and leave MODE there: R2 reads the wrong block on 26 of 52 cases (every block 0 / 1
read, entered on bank 2 / 3) and R1 on 25 of 64 (entered with bank 1 for a block-0 read MODE stays 1; with bank 2
for a block-1 read it ends at 3). Some of R1's 39 agreements are that rule meeting equal values: its block-2 reads
enter on bank 3 and read block 3, and the subject's blocks 2 and 3 both hold $F
([scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out), `--side ours`).

## Open (not measured)

The measurement matrix. Fixtures — apparatus, the per-address RTC preset, the register frame, both
call paths, all three references — as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices).
Every case records A (all 8 bits), F, B, **C**, DE, HL, IX, IY, the alternates, SP, the interrupt
state, MODE and all four blocks (debugger and ports), and the emulated cycles the call took.
RC-0 (the entry), RC-1 / RC-2 (the named block vs the selected one; A's bits 7-4) and RC-6 (TE / AE) are measured
above (R1, R2); RC-1's remaining part, a block-0 read with the clock stopped, is RC-9's question.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| RC-3 | C = $0D, $1D, $2D, $3D | MODE = each of the 16 values | reading MODE: its value as set, or with the bank bits rewritten to MM |
| RC-4 | C = $0E, $0F (and $1E-$3F) | TEST / RESET last written with distinct values | what a write-only register reads as (openMSX's model; noted) |
| RC-5 | C = $40-$4C, $80-$8C, $C0-$CC | MODE selects a block ≠ C's bits 5-4 | bits 7-6 ignored, folded into the block, or another register |
| RC-7 | C = each block × registers 0-12 | register frame | the registers actually kept, C included (only F is listed as changed) and F's value |
| RC-8 | C = each block × registers 0-12 | entered with DI, then with EI | the interrupt state on return |
| RC-9 | block 0, registers 0-12, clock running (TE = 1), the call placed so a seconds carry falls inside it | — | whether a read during a carry returns the old or the new digit (no rule is published; recorded only) |
| RC-10 | C = each block × registers 0-12, through SUBROM ($015C) | — | equal to EXTROM's results |
| RC-11 | C = each block × registers 0-12 | — | the time it takes, in emulated cycles, per block |

## Related pages

[WRTCLK](WRTCLK.md); [the clock concept page](../concepts/clock-and-misc.md);
[EXTROM](../main/EXTROM.md), [SUBROM](../main/SUBROM.md); [the inventory](../index.md).

## Tests that cover it

none yet
