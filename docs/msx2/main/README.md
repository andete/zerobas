<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The MSX2 / MSX2+ main-ROM entries — shared facts

> **Spec:** DRAFT 1 (2026-11-23): MEASURED on the HB-F900, NMS 8250 and FS-A1WSX -- the shared VRAM address matrix
> ("Measured" below) and the sub-ROM call's register / interrupt / slot rules ([EXTROM](EXTROM.md)); the rest of this
> page is the published interface.

The concept page for the twelve entries the MSX2 and MSX2+ add to the main ROM's jump table. It
holds what several of them share: the sub-ROM and its slot, the 128 KB VRAM addressing, the
active / display page cells, and the starting states and rival rules the call pages' measurement
matrices refer to. Each call's own state, differences and open items live on its page
([spec method](../../spec-method.md) §1), never here.

| entry | addr | page | generation |
|---|---|---|---|
| SUBROM | $015C | [SUBROM](SUBROM.md) | MSX2 |
| EXTROM | $015F | [EXTROM](EXTROM.md) | MSX2 |
| CHKSLZ | $0162 | [CHKSLZ](CHKSLZ.md) | MSX2 |
| CHKNEW | $0165 | [CHKNEW](CHKNEW.md) | MSX2 |
| EOL | $0168 | [EOL](EOL.md) | MSX2 |
| BIGFIL | $016B | [BIGFIL](BIGFIL.md) | MSX2 |
| NSETRD | $016E | [NSETRD](NSETRD.md) | MSX2 |
| NSETWR | $0171 | [NSETWR](NSETWR.md) | MSX2 |
| NRDVRM | $0174 | [NRDVRM](NRDVRM.md) | MSX2 |
| NWRVRM | $0177 | [NWRVRM](NWRVRM.md) | MSX2 |
| RDRES | $017A | [RDRES](RDRES.md) | MSX2+ |
| WRRES | $017D | [WRRES](WRRES.md) | MSX2+ |

## References and subject

- **References** (to be measured): Sony HB-F900 (openMSX `msx2`, a Japanese MSX2), Philips NMS
  8250 (`msx2_eu`, a European MSX2), Panasonic FS-A1WSX (`msx2plus`, an MSX2+). RDRES / WRRES are
  MSX2+ entries: only the FS-A1WSX is a reference for them.
- **Subject:** C-BIOS's MSX2 and MSX2+ builds (`main_msx2*.asm`, `main_msx2+*.asm`).

## Citation tags

The published source is the MSX2 Technical Handbook, Konamiman's English translation
([github.com/Konamiman/MSX2-Technical-Handbook](https://github.com/Konamiman/MSX2-Technical-Handbook)),
rated in [allowed-sources.md](../../allowed-sources.md). Pages cite it as:
- **[P A1]** Appendix 1, BIOS listing, MAIN-ROM, "entries appended for MSX2";
- **[P 1]** Chapter 1, the system overview (ROM sizes, memory map, VRAM size);
- **[P 2]** Chapter 2, MSX-BASIC version 2.0 (SET PAGE, VPEEK / VPOKE); **[P 2§5]** its §5, notes on
  software development (work area, VRAM capacity, BASIC version); **[P 2 T2.3]** / **[P 2 T2.9]** its
  tables of SET PAGE values / VDP() numbering;
- **[P 4§2.2]** Chapter 4 §2.2, VRAM access; **[P 4 F4.72]** the bitmap modes' page layout;
  **[P 4]** elsewhere in Chapter 4 (the register save area);
- **[P 5§7]** Chapter 5 §7, slots and inter-slot calls, with its subsections as **[P 5§7.1.2]**
  (selecting slots), **[P 5§7.2.2]** (the inter-slot routines), **[P 5§7.2.3]** (slot work areas),
  **[P 5§7.3.1]** (the cartridge header);
- **[P A6]** Appendix 6, the I/O map.

The handbook covers the MSX2 only. It lists neither CHKSLZ, CHKNEW (both MSX2 entries) nor the
MSX2+ entries RDRES / WRRES. Their interfaces are [A]; their pages cite [P] only for neighbouring
facts (the sub-ROM's header ID, the MSX2's I/O map).

**No generation's behaviour carries over to another** (Joost, 2026-11-23). Every case runs on all
three references, and each machine's reading is its own: the matrices have one column per machine
(**F900**, **8250**, **WSX**; `?` = to measure, `—` = not run, with the reason). A rule that holds
on one generation only names it. Where the MSX2+ could differ (the V9958, SCREEN 10-12, its sub-ROM),
a row's expected value is open per machine.

## The sub-ROM

- The MSX2 has a 16 KB sub-ROM beside the 32 KB main ROM, holding the extended features' routines,
  in page 0 of its own slot [P 1] (Chapter 1's memory map). It has its own jump table [P 2§5].
- Its slot is recorded in **EXBRSA ($FAF8)**, in the slot-ID format of EXPTBL [P 5§7.1.2]
  [P 5§7.2.3]; under BASIC 2.0 or later EXBRSA = $00 means there is no sub-ROM [P 2§5]. The slot-ID
  format (bit 7 expanded, bits 3-2 secondary, bits 1-0 primary) is on [slots](../../concepts/slots.md).
- SUBROM and EXTROM call a sub-ROM routine; they differ in whether IX is on the stack [P 5§7.2.2].
  They are not for use under MSX-DOS [P 5§7.2.2].
- On the MSX2 an inter-slot call restores the interrupt state it found; on the MSX1 interrupts stay
  off [P 5§7.2]. CALSLT and CALLF destroy IX, IY and the alternate registers [P 5§7.2]. (The MSX1
  pages' measured CALSLT is on [CALSLT](../../bios/CALSLT.md).)
- **Measured for EXTROM / SUBROM** [M] (the same on all three references; the rules and evidence are on
  [EXTROM](EXTROM.md)): the routine runs with interrupts off and only page 0 switched; IY and the alternate set are
  the caller's again on return (preserved, not destroyed); on return interrupts are on if they were on at the call,
  else the routine's state; EXBRSA is read at every call.

## 128 KB VRAM

- The MSX2 has at least 64 KB of VRAM, many machines 128 KB [P 1]. MODE ($FAFC) bits 2-1 give the
  size: 00 16 KB (MSX1), 01 64 KB, 10 128 KB [P 2§5].
- A VRAM address has 17 bits. VDP register **R#14** holds A16-A14 (one of eight 16 KB banks); the
  low 14 bits go through port $99 in two bytes with the read / write flag, and port $98 then reads or
  writes, the address counting up after each access [P 4§2.2]. How a carry out of A13 reaches R#14
  is the VDP's (V9938 / V9958 data book), not the BIOS's [A].
- The save cells of R#8-R#23 lie at $FFE7-$FFF6 [P 4] (Chapter 4's VDP() note); VDP(9)-VDP(24)
  read them [P 2 T2.9]. R#14's save cell is therefore $FFED, R#17's $FFF0 [A] (derived from that
  layout).
- Bitmap pages: SCREEN 5 / 6 have four pages at $00000, $08000, $10000, $18000; SCREEN 7 / 8 two, at
  $00000 and $10000 [P 4 F4.72]. With 64 KB of VRAM SCREEN 5 / 6 have two pages and SCREEN 7 / 8 none
  [P 2 T2.3].
- SET PAGE sets a **display page** and an **active page**, in SCREEN 5-8 only [P 2 T2.3]; BASIC's
  VPEEK / VPOKE address 0-65535 from the start of the active page there [P 2]. The work-area cells
  are **DPPAGE ($FAF5)** and **ACPAGE ($FAF6)** [A] (C-BIOS's names; the handbook's tables do not
  list them).
- On the MSX2, FILVRM treats VRAM as 16 KB in SCREEN 0-3 and not otherwise [P A1, under BIGFIL].

## The shared VRAM address matrix

The 16-bit HL of NSETRD, NSETWR, NRDVRM, NWRVRM and BIGFIL cannot carry A16, and the handbook does
not say where it comes from. These five calls' pages run the **VA cases** below, each followed by
the call's own read-back. This is a measurement design, not a call's state.

**Rival rules** [A]. In SCREEN 5-8 (and 10-12 on the WSX):

| id | the 17-bit address |
|---|---|
| **AR-64** | HL, A16 := 0 |
| **AR-PG+** | page base + HL, 17-bit wrap (page base = ACPAGE x $8000 in SCREEN 5 / 6, x $10000 in 7 / 8) |
| **AR-PG&** | page base + (HL AND (page size - 1)) |
| **AR-PG\|** | page base OR HL |
| **AR-DP** | any AR-PG rule with DPPAGE in place of ACPAGE |
| **AR-R14** | A16 from R#14 as the VDP holds it, A15-A0 from HL |
| **AR-R14\*** | R#14 not written at all: A16-A14 as the VDP holds them, A13-A0 from HL |
| **AR-SV / AR-SV\*** | the same two, from the save cell $FFED instead of the VDP |

In SCREEN 0-4 the AR-PG rules have no page size; there the rivals are AR-64, AR-R14 / AR-SV (with
and without \*), and **AR-16K** (HL AND $3FFF, bank := 0) or **AR-16K\*** (HL AND $3FFF, R#14 kept),
plus **AR-PG32** (ACPAGE x $8000 + HL in every mode). For each rule, open too: whether R#14 and $FFED
are WRITTEN (the port log shows the writes), and whether R#14 is put back afterwards.

**Starting states** [A]:
- **S-BASE** — SCRMOD 5 (set by CHGMOD, never by the call under test), ACPAGE 0, DPPAGE 0, VDP R#14
  $06, $FFED $A1 (R#14 and its save cell disagree in A16 and in bits 2-0), MODE as booted (128 KB),
  interrupts off, display on. A case lists only what it changes: `AC` ACPAGE, `DP` DPPAGE, `R14`
  the VDP's R#14, `SV` $FFED.
- **S-FILL** — the background: every VRAM byte := (A7-A0) XOR (A15-A8) XOR (A16 ? $C3 : 0) XOR $5A.
  It is address-DEPENDENT, not unique: it repeats, and holds $00 and $FF (at $0005A, $000A5).
- **S-MARK** — after S-FILL, every address a case's rivals predict (for BIGFIL every predicted span
  and one byte beyond each end) := its own marker, $E1, $E2, ... in the order the case lists the
  addresses. So the byte read names the rule, by construction; a write call's byte ($C7, $C8)
  differs from every marker.
- **S-REGS** — every register, IX / IY and the alternate set loaded with garbage unlike the inputs;
  entry A and F loaded separately (`push` / `pop af`), F $00 and $FF.

**Read-back** (every VA case): every register; the interrupt state, read twice
([spec method](../../spec-method.md) §3a); all VDP registers and the VRAM address counter, from the
emulator's debugger; the **log of port $99 writes** during the call (which registers it writes, in
what order); $FFE7-$FFF6, ACPAGE, DPPAGE, MODE, SCRMOD; the sixteen 8 KB-block sums of VRAM (read
by hand, R#14 set explicitly), and the bytes at the case's marked addresses.

| case | HL | state (from S-BASE) | predictions / separates | F900 | 8250 | WSX |
|---|---|---|---|---|---|---|
| VA-1 | $1234 | — | AR-64 / AR-PG / AR-SV $01234; AR-R14 $11234; AR-R14\* $19234; AR-SV\* $05234 — R#14 written or kept, VDP vs save cell | $01234 [M] | $01234 [M] | $01234 [M] |
| VA-2 | $C123 | — | AR-64 / AR-PG / AR-SV $0C123; AR-16K in SCREEN 5 $00123; AR-R14 $1C123; AR-R14\* $18123; AR-SV\* $04123 | $0C123 [M] | $0C123 [M] | $0C123 [M] |
| VA-3 | $C123 | AC 2, R14 $02, SV $05 | AR-64 $0C123; AR-PG+ / AR-PG\| $1C123; AR-PG& $14123; AR-R14 $0C123; AR-R14\* $08123; AR-SV $1C123; AR-SV\* $14123 | $1C123 [M] | $1C123 [M] | $1C123 [M] |
| VA-4 | $C123 | AC 2, R14 $05, SV $02 | AR-64 $0C123; AR-PG+ / \| $1C123; AR-PG& $14123; AR-R14 $1C123; AR-R14\* $14123; AR-SV $0C123; AR-SV\* $08123. VA-3 + VA-4 give each of the seven groups (AR-64, AR-PG+ with \|, AR-PG&, AR-R14, AR-R14\*, AR-SV, AR-SV\*) a different PAIR | $1C123 [M] | $1C123 [M] | $1C123 [M] |
| VA-5 | $C123 | AC 3, R14 $00, SV $00 | AR-PG+ wraps to $04123; AR-PG\| / AR-PG& $1C123 (VA-3 parts \| from &); AR-64 $0C123 | **$14123** [M] | **$14123** [M] | **$14123** [M] |
| VA-6 | $C123 | AC 0, DP 2, R14 $02, SV $01 | ACPAGE rules $0C123; AR-DP + / \| $1C123; AR-DP& $14123; AR-R14\* $08123; AR-SV\* $04123 | $0C123 [M] | $0C123 [M] | $0C123 [M] |
| VA-7 | $1234 | SCREEN 8 (and 7), AC 1, R14 $03, SV $01 | page size 64 KB $11234 vs 32 KB $09234; AR-64 $01234; AR-R14\* $0D234; AR-SV\* $05234 | $11234 (S8 and S7) [M] | $11234 (S8 and S7) [M] | $11234 (S8 and S7) [M] |
| VA-8 | $C123 | SCREEN 1, R14 $00, SV $00 | masked (AR-16K / \*) $00123 vs not (AR-64, AR-R14) $0C123 | $0C123 [M] | $0C123 [M] | $0C123 [M] |
| VA-9 | $C123 | SCREEN 1, R14 $05, SV $02 | AR-16K $00123; AR-16K\* $14123; mask keeping the save cell's bank $08123; AR-64 / AR-SV $0C123; AR-R14 $1C123 | $0C123 [M] | $0C123 [M] | $0C123 [M] |
| VA-10 | $C123 | as VA-9 in SCREEN 0 (width 40), 0 (width 80), 2, 3, 4 | which modes mask: the 16 KB boundary at 3 / 4, and TEXT2 | $0C123 in all five [M] | $0C123 in all five [M] | $0C123 in all five [M] |
| VA-11 | $C123 | SCREEN 1, AC 1, R14 $00, SV $00 | ACPAGE ignored ($00123 / $0C123) vs AR-PG32 $14123 | **$0015A** [M] | **$0015A** [M] | **$0015A** [M] |
| VA-12 | $1234 | AC 2, R14 $00, SV $00, MODE bits 2-1 := 01 (64 KB) | only where AR-PG holds (VA-3/4): MODE masks A16 ($01234) vs not ($11234) | $11234 [M] | $11234 [M] | $11234 [M] |
| VA-13 | $C123 | AC 1, R14 $00, SV $00, on a reference CONFIGURED with 64 KB of VRAM (a different machine, said so) | what the bank becomes where the VRAM has no A16; MODE 01 at boot | ? | ? | ? |
| VA-14 | $1234 | SCREEN 12, 11, 10; AC 1, R14 $03, SV $01 | as VA-7 in the MSX2+ modes: page size, bank rule, open on the WSX | — (no SCREEN 10-12 on an MSX2) | — (same) | ? |
| VA-15 | $C123 | AC 2 (entry R14 $06: a bank only AR-R14\* yields, and it writes nothing) | after the call R#14 = $06 with a write of R#14 in the log: put back; = the call's bank: left; no write: never written | $1C123; R#14 left $07 [M] | $1C123; R#14 left $07 [M] | $1C123; R#14 left $07 [M] |
| VA-16 | $1234 | VA-1, interrupts ON, a VDP interrupt made to arrive during the call (below) | the address is still right; whether the call disables interrupts across its port $99 writes | ? | ? | ? |

**Measured (2026-11-23)** [M] -- the three references give the same address and the same port $99 writes in
every case ([xva.asm](../../../probes/bios/spec/xva.asm); [scratchpad/AE_xva_msx2.out](../../../scratchpad/AE_xva_msx2.out),
decoded by `scratchpad/xva_decode.py`): the address read back from the VDP after the call (R#14 x $4000 + the
pointer's 14 bits), not from marked VRAM.
- Every one of the four calls writes **R#14 := the bank, then the 14-bit address**: four port $99 writes, nothing
  else. **$FFED is never written** (it keeps each case's preset), and R#14 is **left** at the call's bank (VA-15).
  So AR-R14 / AR-R14\* / AR-SV / AR-SV\* are out: the bank is computed.
- **SCREEN 5 / 6:** address = ((ACPAGE AND 1) x $8000 + HL) AND $FFFF, + (ACPAGE AND 2) x $8000 -- the 16-bit sum
  loses its carry. VA-3 ($1C123) and VA-5 separate it from every rival above: ACPAGE 3 + $C123 gives **$14123**,
  where AR-PG+ wraps to $04123 and AR-PG\| / AR-PG& give $1C123. **DPPAGE is not used** (VA-6).
- **SCREEN 7 / 8:** address = ACPAGE x $10000 + HL (VA-7: $11234). **MODE's VRAM-size bits are ignored** (VA-12).
- **SCREEN 0-4, ACPAGE 0:** address = HL, **no 16 KB mask** in any of SCREEN 0 (40 and 80), 1, 2, 3, 4 (VA-8 - VA-10):
  AR-16K / AR-16K\* are out.
- **SCREEN 0-4, ACPAGE not 0: HL is not used.** The address is **ACPAGE x $100 + E** -- VA-11 and its follow-ups
  (xva cases 18-24: ACPAGE 1 / 2 / 3, HL $C123 / $1234 / $0000, SCREEN 0 / 1 / 2 / 4) all land at $n5A with the
  probe's E $5A, and at $n34 with E $34 (a diagnostic run, DE $1234: [scratchpad/AE_xva_de1234.out](../../../scratchpad/AE_xva_de1234.out)). The same on all three references.
- **C-BIOS's MSX2 / MSX2+ builds** give every address above except the last: with ACPAGE not 0 in SCREEN 0-4 they
  address HL ($00123 for VA-11, five port writes) -- the one difference.

**VDP-model rows (not BIOS rules).** Where the counter goes after HL $FFFF (SCREEN 5) or $3FFF
(SCREEN 1) is decided by the VDP's auto-increment, which carries into R#14 as the BIOS would; the
two cannot be told apart from outside. These rows (VC-1 HL $FFFF, S-BASE; VC-2 HL $3FFF, SCREEN 1,
R14 $00) check the emulator's VDP and that the call leaves the counter at its address + 1, nothing
more.

**Methods for the open items.**
- *An interrupt during the call:* with R#1's interrupt bit set and an H.TIMI handler that reads S#0
  and counts, the probe repeats the case at delays stepped by 8 T-states after the previous VDP
  interrupt, so one repetition's call spans the next interrupt (the handler's count shows which);
  that repetition's address read-back is compared with the others.
- *The time it takes:* the emulator's machine time, read by debugger breakpoints at the call and at
  the return, per machine.
- *The stack it uses:* the 128 bytes below SP set to marker words before the call; the lowest one
  overwritten after it gives the depth.

## Related pages

[slots](../../concepts/slots.md), [screen modes](../../concepts/screen-modes.md), the MSX1 VRAM calls
([SETRD](../../bios/SETRD.md), [SETWRT](../../bios/SETWRT.md), [RDVRM](../../bios/RDVRM.md),
[WRTVRM](../../bios/WRTVRM.md), [FILVRM](../../bios/FILVRM.md)), [CALSLT](../../bios/CALSLT.md),
[shared state](../../bios/shared-state.md).
