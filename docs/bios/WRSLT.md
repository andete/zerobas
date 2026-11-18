<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# `WRSLT` ($0014) — write a byte to a slot

> **Spec:** FINAL (2026-11-18), after the fifth reviews (two) and round 6, which reads 3-1's "AB" header (Joost's ruling) to pin the ID's secondary slot, with the CF-3300 row (Joost: "Add a CF-3300 row"). Measured on the
> VG-8020, alone and with a disk interface, and on the CF-3300: writes to the machine's RAM slot in
> all four pages, with interrupts on and off and three values of the slot register (two on each machine).

## Summary

`WRSLT` writes E to the address HL in the slot that A names. A is a slot ID: bits 0-1 the primary
slot, bits 2-3 the secondary, bit 7 set when the slot is expanded. It returns with the slot register
put back as it was and interrupts off. For the expanded slot 3-0 it reaches 3-0's RAM from a page whose
secondary selection is 3-1, and leaves that selection (a write to another sub-slot is not
measured).

A and D hold the slot register on return. Its F is a logical result's on the slot register as it was
while the page was switched; for the expanded RAM slot B and C hold the slot register and $C0. E, HL,
IX and IY are kept.

zerobas does all of the measured behaviour the same.

## The specification

References: the Philips VG-8020's main BIOS, alone (row `N`) and with an NMS 1200 disk interface
(row `D`), and the National CF-3300's (row `C`), a Japanese MSX1 whose RAM is the expanded slot 3-0,
the same kind as zerobas's. Ours: the C-BIOS repack, diskless on row `N`, the disk build on `D` and `C`.

**Evidence.** **[XR rNN]**: case `NN` of the XRDSLT probe, run 5, on row `r`:
[`scratchpad/XRDSLT_run5.out`](../../scratchpad/XRDSLT_run5.out) (`N`),
[`scratchpad/XRDSLT_run5d.out`](../../scratchpad/XRDSLT_run5d.out) (`D`),
[`scratchpad/XRDSLT_run5c.out`](../../scratchpad/XRDSLT_run5c.out) (`C`).
`probes/bios/spec/xrdslt.asm` documents the header, the cases and the 12-byte record:
- The probe runs from RAM in page 3. It works out two slot IDs from the slot register, EXPTBL and
  SLTTBL: the RAM's (page 3's slot) and the cartridge's (page 1's slot at boot). The RAM is slot 3
  on the VG-8020, and the expanded slot 3-0 on the CF-3300 and on zerobas's machine. The cartridge
  is slot 1, or 2 on row `D`'s reference; it is not expanded on any machine.
- Each case calls WRSLT or RDSLT. The WRSLT cases write RAM in pages 0-3, from $0000 to $EE40, with
  values including 00; the RDSLT cases read back what a WRSLT case wrote just before, and the
  cartridge's first bytes ("AB" and init's low byte). One case of each adds $70 to the slot ID.
- Where slot 3 is expanded (zerobas on every row, the CF-3300 on row `C`), eight cases first set
  its secondary selection for page 0 or page 1 to 3-1 by hand, then name 3-0: the call must reach
  3-0's RAM, and the selection after it shows whether 3-1 is still there. Each address is
  written and read twice, with two values. On the VG-8020 these cases run without the preset, so on
  rows `N` and `D` the two machines start them from different set-ups: there the secondary
  selection, B and C are not compared (A, F, the bytes, the slot register and the interrupts are).
- Five cases first set page 1's primary slot to 0 by hand: the slot register is $F0 for them on
  every machine, its second value. The probe puts it back after each case.
- A CONTROL record (case 36, on RDSLT's page) turns interrupts on and calls nothing, to show the
  interrupt readout reports 1.
- One RDSLT names the cartridge at $8002, where page 2 is RAM holding $C6 (a WRSLT case wrote it):
  replacing page 2's field reads the cartridge, ORing the cartridge's slot into it would read slot 3.
- Entry F is $00 or $FF, and interrupts are on or off per case. B, C, D, IX and IY carry markers.
- Before and after the call a WITNESS reads the same address by switching the slot register (and
  slot 3's secondary register, when expanded) by hand, with interrupts off.
- At boot pages 2 and 3 are already the RAM slot and page 1 the cartridge, so only pages 0 and 1 of
  the RAM cases switch to a slot other than the one mapped there.
- The slot register is $F4 at boot on rows `N` and `C`, $F8 on row `D`'s reference. Row `D`'s
  reference has slot 1 expanded (EXPTBL); no case names it. On the disk
  machines the probe's cartridge starts before the disk ROM does.

**[XR2 n]**: case `n` of the XRDSLT2 probe, run 1, on row `C` only,
[`scratchpad/XRDSLT2_run1c.out`](../../scratchpad/XRDSLT2_run1c.out)
(`probes/bios/spec/xrdslt2.asm`). Under Joost's ruling of 2026-11-18 it reads 3-1's two header bytes
at $4000 / $4001 ("AB", the ID the BIOS's slot scan reads), by hand and through RDSLT, and no other
byte of a ROM. It writes $18 into 3-0 at $4000, then reads $4000 / $4001 naming 3-1 and 3-0, plain
and from a page-1 selection of 3-1 or 3-2 set by hand.

On rows `N` and `D` the two machines' RAM slots differ in kind, so B, C and slot 3's secondary
selection after a RAM access come from different paths there and are not compared; row `C` compares
them, slot kind for slot kind.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xwrslt_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xwrslt_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 486 recorded outputs (each case's cursor, cells, A, table entries ...): 486 read by a rule's check, 0 declared NOT evidence (below), 0 unread.**

#### 1. WRSLT ($0014): write a byte to an address in a slot

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-WR-W** E lands at HL in the slot A names: a read by switching the slot register by hand finds another byte there before the call and E after -- in pages 0 and 1 a slot other than the one mapped there ($0000 to $7FFF), in pages 2 and 3 the slot already mapped ($8ABC to $EE40). | 48 | ✓ | ✓ |
| **R-WR-IGN** Bits 4-6 of the slot ID are ignored (a RAM ID with $70 added writes the same RAM). | 3 | ✓ | ✓ |
| **R-WR-SLOT** The slot register ($A8) is as before the call -- its boot value, or with page 1 set to slot 0 by hand ($F0): a second value on every machine. | 48 | ✓ | ✓ |
| **R-WR-SEC** Where slot 3 is expanded (the cf3300 row), a write naming 3-0 reaches 3-0's RAM from a page whose secondary selection is 3-1 (set by hand before the call), and leaves that selection 3-1 after it; the other pages keep 3-0. Only 3-0 holds RAM: whether 3-1 there differs from 3-0 is not read (clean room). | 16 | ✓ | ✓ |
| **R-WR-DI** Interrupts are off on return, whether they were on or off on entry. | 48 | ✓ | ✓ |
| **R-WR-A** A and D are the slot register as restored; E, HL, IX and IY are kept. | 48 | ✓ | ✓ |
| **R-WR-F** F is a logical result's on the slot register with the written page switched to the slot (S, Z, bits 5 / 3 from it, P/V its parity; H, N, C clear) -- whatever F was on entry ($00 / $FF). Page 1 carries it: $F4 with page 1 set to slot 3 is $FC, F $AC, where the restored $F4 would give $A0. | 48 | ✓ | ✓ |
| **R-WR-SUB** Round 6 (the cf3300 row): WRSLT naming 3-0 ($83) at $4000 -- where 3-1 holds its header -- returns with the slot register and the secondary selection as before, A the slot register, F a logical result's on the switched one ($AC); RDSLT then reads the $18 back from 3-0 (RDSLT's page). | 1 | ✓ | ✓ |
| **R-WR-BCX** For the expanded RAM slot 3-0 (the cf3300 row), B is the slot register's value as it was before the call ($F4, or $F0 with page 1 set to slot 0 -- not the switched value: page 0 gives $F0, not $F3) and C $C0, in every page. | 17 | ✓ | ✓ |

<!-- RULES END -->

## Differences from the reference

None measured: every rule holds on zerobas.

## Open (not measured)

- **[A]** Sub-slots 3-2 and 3-3 as the target; a target sub-slot in pages 0, 2 and 3 (round 6 reads
  page 1, where 3-1's header is). An expanded slot that is not page 3's own (the call must switch
  page 3 to reach its secondary register): the disk row's reference has one, slot 1.
- **[A]** Pages 2 and 3 with a secondary selection other than 3-0 before the call.
- **[A]** A slot ID with bit 7 set for a slot that is not expanded; bit 7 clear naming an expanded
  slot ($03 on the CF-3300 or zerobas), with or without bits 2-3 set.
- **[A]** Bits 4-6 of the slot ID other than all three at once ($70), and on the cartridge's ID.
- **[A]** Page 3 in a slot other than the one mapped there; page 0 or 1 holding a slot whose number
  is not a subset of the target's.
- **[A]** B and C for a slot that is not expanded, compared on both machines: the VG-8020 has them
  for its RAM, but zerobas's RAM is expanded, so they are not comparable.
- **[A]** A third slot-register value on zerobas ($F4 and $F0 measured): S, bit 5 and Z of F come
  out alike for those.
- **[A]** IX and IY with a second set of markers.
- **[A]** A secondary preset on a page other than the target's.
- **[A]** SLTTBL after the call (not recorded).
- **[A]** Writing to a slot that holds ROM, or to nothing.
- **[A]** That a write leaves other slots alone (3-1, or the slot mapped at HL before the call): no
  case reads them after a write.
- **[A]** The alternate registers and SP; other RAM; the time it takes.

## Related pages

[RDSLT](RDSLT.md), measured by the same probe; the other slot calls (CALSLT, ENASLT, CALLF, RSLREG, WSLREG,
CALBAS) in [the index](index.md); the slots ([docs/concepts/rom-layout.md](../concepts/rom-layout.md)).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).

Also the suites `tools/entry_table.py --bios` lists for $0014.
