<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# `WRTCLK` (sub-ROM $01F9) — write a clock-IC register

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX ([xclk.asm](../../../probes/bios/spec/xclk.asm), [scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out), decoded by [xclk_decode.py](../../../scratchpad/xclk_decode.py)). `[W1]` = that run's first WRTCLK set (block 2 registers 1 / 5, block 3 registers 1 / 12; A = 5, $A, 3, 9; MODE already on the block, TE = 1, AE = 0); `[W2]` = its second (the same registers, MODE on ANOTHER block with each TE / AE pair once -- $03, $04, $09, $0E --, A = $F5, $07, $3E, $C1: bits 7-4 set, odd and even parity). Each case's register and the preselected block's same register are read through the ports before and after; the probe restores them afterwards (the blocks are battery-backed). Every reading below is the same on all three references.
>
> Goldfish pass 1 (test writer) 2026-11-23: 7 findings, 7 measured, 0 moved to open.

## Summary

`WRTCLK` writes one four-bit register of the clock IC — to set the time or the alarm, or to change a
setting BASIC keeps in its battery-backed blocks (the screen, colours, beep, title, prompt,
password). It takes the same one-byte address as [REDCLK](REDCLK.md). The clock IC and its blocks are
on the [concept page](../concepts/clock-and-misc.md).

## The specification

Tags as on the [concept page](../concepts/clock-and-misc.md#references-subject-citation-tags).

**Interface.**
- Called through EXTROM / SUBROM with IX = $01F9 [P A1, 5§6.8]; measured through EXTROM [M W1, W2].
- In: C = `00MMAAAA` as for REDCLK; A = the value, bits 3-0 [P A1, 5§6.8]. Bits 7-4 of A are ignored: $F5, $3E,
  $C1 stored 5, $E, 1 [M W2] (the chip's registers hold four bits, so whether the call or the chip drops them is
  not visible).
- Out: nothing [P A1, 5§6.8]. **A is returned as the value AND $0F** ($F5 -> $05, $3E -> $0E, $C1 -> $01; values
  $0-$F come back unchanged) [M W1, W2] — A is changed although the handbook lists F only [P A1].
- F = the flags of `AND $0F` on the value, as REDCLK's: H 1, bit 3 a copy of the value's bit 3, P/V set for even
  parity — $14 / $1C for 5, 3 / $A, 9, $10 / $18 for the odd-parity 7, 1 / $E [M W1, W2].
- BC, DE, HL, IX, IY and the alternate set were not recorded [A].

**Behaviour.**
- The call selects the block itself [P 5§6.8] [M W2: with MODE on another block, the named register takes the value
  and the preselected block's same register keeps its own, 4/4].
- **MODE afterwards = (MODE before AND $0C) OR MM:** the bank is left at the block written, TE and AE kept [M W2:
  $3 -> $2, $4 -> $6, $9 -> $B, $E -> $F; W1 $A / $B with MODE already there].
- The handbook's example writes six characters to block 3 by calling it with C counting up from $30,
  one nibble per call [P 5§6.8, List 5.10].
- Bits a register does not have read back as 0 whatever is written [P 5§6.6].
- What a write to 13, 14 or 15 does when MM differs from MODE's bank [A]; what C's bits 7-6 do [A]; the interrupt
  state after the call [A].

## Differences from the reference

C-BIOS's MSX2 / MSX2+ builds (the subject) OR MM into MODE's bank bits, as their REDCLK does: entered with MODE on
block 3, C = $21 (block 2) wrote block 3's register 1 and left block 2's alone, MODE after 3 [W2]. W2's other three
cases (banks 0, 1, 2 OR'd with MM = 2, 3, 3) and all of W1 land on the named block. A and F agree with the
reference ([scratchpad/AE_xclk_msx2.out](../../../scratchpad/AE_xclk_msx2.out), `--side ours`).

## On the turbo R

Measured 2026-11-23 (D-TRSPEC) on the FS-A1GT / FS-A1ST: the MODE register, every block 1-3 register and WRTCLK's results are the FS-A1WSX's, on both models; REDCLK's block-0 time registers (seconds, minutes, hours), with the A and F that carry them, read the time of day of the run (the clock chip follows the host clock; the A1GT and A1ST ran seconds apart) [M] ([AE_trall/xclk.out](../../../scratchpad/AE_trall/xclk.out); overview: [turbor/remeasured.md](../../turbor/remeasured.md)).

## Open (not measured)

The measurement matrix. Fixtures as on the
[concept page](../concepts/clock-and-misc.md#shared-measurement-fixtures-for-the-call-pages-matrices). The
result of every case is read back through the debugger and ports $B4 / $B5 (all four blocks and
MODE), never through REDCLK, so a fault both calls share cannot hide. Every case also records A, F, B,
**C**, DE, HL, IX, IY, the alternates, SP, the interrupt state and the emulated cycles.
WC-6 (TE / AE kept) is measured above (W2: each pair once, each on a different bank).

| case | inputs | desynced state | what it separates |
|---|---|---|---|
| WC-1 | C = each block × registers 0-12; A = $A5, $5A, $0F, $F0, A recorded after | MODE selects another block (per-address preset); TE = 0 | writes the named block vs the selected one on blocks 0 / 1 and the other registers (W2 covers four registers of blocks 2 / 3) |
| WC-2 | the WC-1 set | the written register's neighbours and the same address in the other three blocks preset distinct | the write touches one register only |
| WC-3 | C = $0D-$3D, A = each value 0-$F | per row, MODE preset so A's bits 1-0, MM and the preset bank are three different blocks where possible | a MODE write: A's bank, MM, or the call's restore wins — counted only on rows where the three differ |
| WC-4a | C = $0F (RESET), A = each bit alone; TE = 0 | alarm registers and the sub-second stage preset non-zero | RESET bit 0 clears the alarm; bit 1 the sub-second stage |
| WC-4b | C = $0E (TEST), A = each bit alone, then A = 0; TE = 0, then 1 for one second of emulated time | TEST cleared (A = 0) before the next row | TEST reaches the chip. If openMSX does not model TEST, this row pins nothing (noted on the result) |
| WC-5 | C = $40-$4C, $80-$8C, $C0-$CC | MODE selects a block ≠ C's bits 5-4 | bits 7-6 ignored, folded, or another register |
| WC-7 | the WC-1 set | register frame | the registers actually kept, C included (A is changed, W2; the handbook's example saves BC and HL, so it shows nothing) |
| WC-8 | block 0, TE = 0: seconds / minutes / hours / day / month / year units = $A-$F; month = 00; day = 00; hours tens = 3 (24-hour) | 12- / 24-hour bit both ways | values within the field width but invalid as BCD / as a date: does the call refuse, correct, or store them as written (then what the chip keeps) |
| WC-9 | — | — | moved: what BASIC's SET statements store and what the boot code makes of it are CK-1 / CK-2 on the [concept page](../concepts/clock-and-misc.md#open-not-measured--this-pages-own-as) — they pin the boot code, not WRTCLK |
| WC-10 | the WC-1 set | entered with DI, then with EI | the interrupt state on return |
| WC-11 | the WC-1 set through SUBROM ($015C) | — | equal to EXTROM's results |
| WC-12 | the WC-1 set | — | the time it takes, in emulated cycles |

## Related pages

[REDCLK](REDCLK.md); [the clock concept page](../concepts/clock-and-misc.md); [BEEP](BEEP.md) (reads
its sound from block 2); [EXTROM](../main/EXTROM.md); [the inventory](../index.md).

## Tests that cover it

none yet
