<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRTCLK` (sub-ROM $01F9) — write a clock-IC register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xclk.asm](../../../probes/bios/spec/xclk.asm), [scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out), decoded by `scratchpad/xclk_decode.py`).

## Summary

`WRTCLK` writes one four-bit register of the clock IC — to set the time or the alarm, or to change a
setting BASIC keeps in its battery-backed blocks (the screen, colours, beep, title, prompt,
password). It takes the same one-byte address as [REDCLK](REDCLK.md). The clock IC and its blocks are
on the [concept page](../concepts/clock-and-misc.md).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01F9 [P A1, 5§6.8].
- In: C = `00MMAAAA` as for REDCLK; A = the value, bits 3-0 [P A1, 5§6.8].
- Out: nothing [P A1, 5§6.8].
- Registers changed: F [P A1]. That A, BC, DE, HL, IX, IY and the alternate set are kept follows from
  that list and is [A].

**Behaviour.**
- The call selects the block itself, as REDCLK does [P 5§6.8].
- The handbook's example writes six characters to block 3 by calling it with C counting up from $30,
  one nibble per call [P 5§6.8, List 5.10].
- Bits a register does not have read back as 0 whatever is written [P 5§6.6].
- What A's bits 7-4 do [A]; what MODE holds afterwards and whether TE / AE survive [A]; what a write
  to 13, 14 or 15 does when MM differs from MODE's bank [A]; what C's bits 7-6 do [A]; the interrupt
  state after the call [A].

**Measured** [M] (the same on all three references, $01F9 through EXTROM; block 2 registers 1 / 5, block 3
registers 1 / 12): the value lands in the register (read back through the ports); A kept (the value), F $14 / $1C;
MODE left at the block written. (The probe writes the original back after each case: the blocks are battery-backed.)

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds write and leave MODE the same ([scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out)).

## Open (not measured)

The measurement matrix. Fixtures as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices). The
result of every case is read back through the debugger and ports $B4 / $B5 (all four blocks and
MODE), never through REDCLK, so a fault both calls share cannot hide. Every case also records A, F, B,
**C**, DE, HL, IX, IY, the alternates, SP, the interrupt state and the emulated cycles.

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| WC-1 | C = each block × registers 0-12; A = $A5, $5A, $0F, $F0 | MODE selects another block (per-address preset); TE = 0 | writes the named block vs the selected one; whether A's bits 7-4 are masked |
| WC-2 | the WC-1 set | the written register's neighbours and the same address in the other three blocks preset distinct | the write touches one register only |
| WC-3 | C = $0D-$3D, A = each value 0-$F | per row, MODE preset so A's bits 1-0, MM and the preset bank are three different blocks where possible | a MODE write: A's bank, MM, or the call's restore wins — counted only on rows where the three differ |
| WC-4a | C = $0F (RESET), A = each bit alone; TE = 0 | alarm registers and the sub-second stage preset non-zero | RESET bit 0 clears the alarm; bit 1 the sub-second stage |
| WC-4b | C = $0E (TEST), A = each bit alone, then A = 0; TE = 0, then 1 for one second of emulated time | TEST cleared (A = 0) before the next row | TEST reaches the chip. If openMSX does not model TEST, this row pins nothing (noted on the result) |
| WC-5 | C = $40-$4C, $80-$8C, $C0-$CC | MODE selects a block ≠ C's bits 5-4 | bits 7-6 ignored, folded, or another register |
| WC-6 | the WC-1 set | MODE preset to each of the 4 TE / AE combinations × 4 banks | MODE restored, left on MM, TE / AE changed |
| WC-7 | the WC-1 set | register frame | the registers actually kept, C included (only F is listed as changed; the handbook's example saves BC and HL, so it shows nothing) |
| WC-8 | block 0, TE = 0: seconds / minutes / hours / day / month / year units = $A-$F; month = 00; day = 00; hours tens = 3 (24-hour) | 12- / 24-hour bit both ways | values within the field width but invalid as BCD / as a date: does the call refuse, correct, or store them as written (then what the chip keeps) |
| WC-9 | — | — | moved: what BASIC's SET statements store and what the boot code makes of it are CK-1 / CK-2 on the [concept page](../concepts/clock-and-misc.md#open-not-measured--this-pages-own-as) — they pin the boot code, not WRTCLK |
| WC-10 | the WC-1 set | entered with DI, then with EI | the interrupt state on return |
| WC-11 | the WC-1 set through SUBROM ($015C) | — | equal to EXTROM's results |
| WC-12 | the WC-1 set | — | the time it takes, in emulated cycles |

## Related pages
## Related pages

[REDCLK](REDCLK.md); [the clock concept page](../concepts/clock-and-misc.md); [BEEP](BEEP.md) (reads
its sound from block 2); [EXTROM](../main/EXTROM.md); [the inventory](../index.md).

## Tests that cover it

none yet
