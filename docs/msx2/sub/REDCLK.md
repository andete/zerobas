<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `REDCLK` (sub-ROM $01F5) — read a clock-IC register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xclk.asm](../../probes/bios/spec/xclk.asm), [scratchpad/AE_xclk_msx2.out](../../scratchpad/AE_xclk_msx2.out), decoded by `scratchpad/xclk_decode.py`).

## Summary

`REDCLK` reads one four-bit register of the clock IC: the time, the alarm, or the battery-backed
settings BASIC keeps there. The caller names the block and the register in one byte, so it never
touches the clock IC's MODE register itself. The clock IC, its blocks and what BASIC stores in them
are on the [concept page](../concepts/clock-and-misc.md).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01F5 [P A1]. Chapter 5 heads the call with $015F,
  EXTROM's own address [P 5§6.8]; that $01F5 is the entry is [A] until RC-0.
- In: C = `00MMAAAA` — MM the block (0-3), AAAA the register (0-15) [P A1, 5§6.8].
- Out: A = the register's value; only bits 3-0 are valid [P A1, 5§6.8].
- Registers changed: F [P A1]. That B, C, DE, HL, IX, IY and the alternate set are kept follows from
  that list and is [A].

**Behaviour.**
- The call selects the block itself; the caller need not write MODE first [P 5§6.8].
- What A's bits 7-4 hold [A].
- What MODE holds after the call — the caller's block, the block in C, or something else — and whether
  MODE's TE (bit 3) and AE (bit 2) survive it [A].
- What C's bits 7-6 do when not 0 [A].
- What a read of registers 13 (MODE), 14 and 15 (write-only) returns [A].
- The interrupt state after the call [A].

**Measured** [M] (the same on all three references, $01F5 through EXTROM): for every block 0-3 and register 0-15,
with MODE's block bits set by hand to ANOTHER block first, A's low nibble equals the register read through the
clock IC's ports -- the call selects the block itself -- and A's high nibble is 0. **MODE is left at the case's
block** (its bits 3-2 kept), not put back.

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) do not select the block reliably: 25 of the 64 reads differ from the
port -- nearly all of blocks 0 and 1 (the time) -- and MODE after shows a wrong block (entered with block 1 for a
block-0 read it stays at 1; entered with 2 for a block-1 read it ends at 3) ([scratchpad/AE_xclk_msx2.out](../../scratchpad/AE_xclk_msx2.out)).

## Open (not measured)

The measurement matrix. Fixtures — apparatus, the per-address RTC preset, the register frame, both
call paths, all three references — as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices).
Every case records A (all 8 bits), F, B, **C**, DE, HL, IX, IY, the alternates, SP, the interrupt
state, MODE and all four blocks (debugger and ports), and the emulated cycles the call took.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| RC-0 | IX = $01F5 and IX = $015F (through SUBROM), C = $2B | block 2 reg 11 preset to a value no other register holds | which address is REDCLK: only the call that returns that value is |
| RC-1 | C = each block × registers 0-12 | MODE selects another block (per-address preset, concept page); TE = 0; A's high nibble preset to 5 (not 0, $F, nor C's) | reads the named block vs the selected one; A's bits 7-4: 0, $F, kept from entry, or other (an "open bus" value is openMSX's model, noted as such) |
| RC-2 | the RC-1 set | MODE selects the named block | the control for RC-1 |
| RC-3 | C = $0D, $1D, $2D, $3D | MODE = each of the 16 values | reading MODE: its value as set, or with the bank bits rewritten to MM |
| RC-4 | C = $0E, $0F (and $1E-$3F) | TEST / RESET last written with distinct values | what a write-only register reads as (openMSX's model; noted) |
| RC-5 | C = $40-$4C, $80-$8C, $C0-$CC | MODE selects a block ≠ C's bits 5-4 | bits 7-6 ignored, folded into the block, or another register |
| RC-6 | the RC-1 set | MODE preset to each of the 4 TE / AE combinations × 4 banks | MODE restored, left on MM, or TE / AE changed |
| RC-7 | the RC-1 set | register frame | the registers actually kept, C included (only F is listed as changed) and F's value |
| RC-8 | the RC-1 set | entered with DI, then with EI | the interrupt state on return |
| RC-9 | block 0, registers 0-12, clock running (TE = 1), the call placed so a seconds carry falls inside it | — | whether a read during a carry returns the old or the new digit (no rule is published; recorded only) |
| RC-10 | the RC-1 set through SUBROM ($015C) | — | equal to EXTROM's results |
| RC-11 | the RC-1 set | — | the time it takes, in emulated cycles, per block |

## Related pages
## Related pages

[WRTCLK](WRTCLK.md); [the clock concept page](../concepts/clock-and-misc.md);
[EXTROM](../main/EXTROM.md), [SUBROM](../main/SUBROM.md); [the inventory](../index.md).

## Tests that cover it

none yet
