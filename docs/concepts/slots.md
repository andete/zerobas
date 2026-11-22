<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# Slots — how an MSX reaches more than 64 KB

> **Status (2026-11-18):** the shared facts of the slots region's eight BIOS calls (RDSLT, WRSLT,
> CALSLT, ENASLT, CALLF, RSLREG, WSLREG, CALBAS). Each call's state, and the differences its page
> names, are in the generated [BIOS index](../bios/index.md), never repeated here. Speed is
> deliberately left out of these docs until on-par speed is established.

## Summary

The Z80 sees 64 KB, in four 16 KB **pages**. An MSX has more memory and ROM than that, in
**slots**: four primary slots, each of which can be **expanded** into four secondary slots
(sub-slots). Every page shows one slot at a time, chosen by the slot registers. The BIOS's slot
calls read, write and call code in a slot other than the one mapped, switch a page for good, and
read or write the primary slot register.

The calls behave alike: they switch a page, do their work, put the slot registers back (except
ENASLT, which leaves the page switched) and return with interrupts off. zerobas does all of the
measured behaviour the same, apart from two details of the inter-slot calls (below).

## How it works

Every statement below carries its source:
- **[P]** the published interface, the MSX2 Technical Handbook (rated in
  [allowed-sources.md](../allowed-sources.md));
- **[M]** measured by this project (the per-call pages);
- **[A]** not yet established.

### The slot ID

The calls name a slot with one byte, the **slot ID** [P]:

| bits | meaning |
|---|---|
| 0–1 | the primary slot, 0–3 |
| 2–3 | the secondary slot, 0–3 (only when bit 7 is set) |
| 7 | set when the primary slot is expanded |

So `$03` is slot 3, not expanded; `$83` is sub-slot 3-0 and `$87` is 3-1. Bits 4–6 do not count:
RDSLT and WRSLT with $70 added to the ID behave as without it [M]
([RDSLT](../bios/RDSLT.md), [WRSLT](../bios/WRSLT.md)).

### The slot registers

- **The primary slot register** is I/O port $A8: two bits per page, page 0 in bits 0–1 up to
  page 3 in bits 6–7 [P]. RSLREG reads it and WSLREG writes it, keeping every other register and
  the interrupt state [M] ([RSLREG](../bios/RSLREG.md), [WSLREG](../bios/WSLREG.md)).
- **The secondary slot register** of an expanded slot is at address $FFFF *of that slot*, with
  the same layout, and it reads back complemented [P]. It can only be reached while page 3 shows
  that primary slot.

### The work area

- **EXPTBL** ($FCC1–$FCC4) has one byte per primary slot, bit 7 set when it is expanded; EXPTBL+0 is
  also the main ROM's slot ID [P]. A program that needs the main ROM (the probes switch page 1 to
  it) reads it from there.
- **SLTTBL** ($FCC5–$FCC8) keeps a copy of each expanded slot's secondary register, since the
  register itself is not readable from elsewhere [P]. ENASLT, switching a sub-slot of slot 3, sets
  SLTTBL+3 to the register's new value; the entry of a slot that is not expanded is left alone [M]
  ([ENASLT](../bios/ENASLT.md)).
- **[A]** RAMAD0–RAMAD3 ($F341–$F344, the RAM's slot per page, kept by the disk ROM) are not
  measured.

### What the calls share

Measured on the calls' pages, on all three rows below [M]:
- **A page's field is replaced, not combined.** Switching a page writes the slot's number into
  that page's two bits; the other pages keep theirs. RDSLT naming the cartridge at $8002, where RAM
  is mapped, reads the cartridge's byte.
- **For an expanded slot**, the page's field of its secondary register takes the ID's secondary
  number, and the other fields keep the register's.
- **The slot registers come back** as they were (RDSLT, WRSLT, CALSLT, CALLF, CALBAS), and the
  secondary selection RDSLT and WRSLT found stays in place.
- **Interrupts are off on return**, whatever they were on entry, for every call except RSLREG and
  WSLREG.
- **The inter-slot calls** (CALSLT, CALLF, CALBAS) pass AF, BC, DE and HL to the target as set and
  return the target's AF, BC, DE, HL, IX and IY.

### The machines

| machine | main ROM | RAM | cartridge | expanded |
|---|---|---|---|---|
| Philips VG-8020 (row `N`) | 0 | 3 | 1 | none |
| VG-8020 + NMS 1200 (row `D`) | 0 | 3 | 2 | slot 1 |
| National CF-3300 (row `C`) | 0 | 3-0 | 1 | slot 3 |
| zerobas | 0 | 3-0 | 1 | slot 3 |

zerobas's own ROMs sit in slot 3 too (the sub-ROM in 3-2, the disk ROM in 3-1; see
[ROM layout](rom-layout.md)), so its RAM is the expanded 3-0. The VG-8020's is plain slot 3, so on
rows `N` and `D` the two machines are handed different IDs for the same RAM, and the values that
come from the expanded path (B and C, the secondary selection, the stack depth in a target) are
not compared there. The **CF-3300 row** exists for that: its RAM is the expanded 3-0, as zerobas's
is, so row `C` compares those values slot kind for slot kind (Joost's ruling of 2026-11-18, "Add a
CF-3300 row").

### What a probe may read

The clean-room rule ([docs/spec-method.md](../spec-method.md)) lets a probe read registers, RAM,
I/O ports and slot state, and never a ROM byte. One exception, Joost's ruling of 2026-11-18: the
two cartridge-header bytes at $4000 / $4001 of a ROM slot or sub-slot ("AB", the ID the BIOS's own
slot scan reads), and no other ROM byte. That is how RDSLT and ENASLT are shown to reach 3-1 and not
3-0.

## Differences from the reference

Each call's differences are on its own page, never repeated here; the
[BIOS index](../bios/index.md) lists them per call. Two items cover the inter-slot calls,
CALSLT and CALLF: **D-CALSLTSTACK**, the target's stack depth, and **D-CALSLTIY**, IY in a target.

## What we found, and how

Each call was measured by a probe that runs from RAM in page 3, sets the slot registers by hand
before each case, and reads the result back through a WITNESS that switches the registers itself,
never through the call under test. The rules are checked against every case on the three rows
([docs/spec-method.md](../spec-method.md)).

## How zerobas does it

The slot calls are C-BIOS's, in the main ROM, patched where a page found a difference
([cbios-repack-provenance.md](../cbios-repack-provenance.md)).

## Related pages

- [The BIOS](bios.md): what every BIOS call has in common.
- [ROM layout](rom-layout.md): which zerobas ROM is in which slot.
- [The memory map](memory-map.md): the work area.
- The calls: [RDSLT](../bios/RDSLT.md), [WRSLT](../bios/WRSLT.md), [CALSLT](../bios/CALSLT.md),
  [ENASLT](../bios/ENASLT.md), [CALLF](../bios/CALLF.md), [RSLREG](../bios/RSLREG.md),
  [WSLREG](../bios/WSLREG.md), [CALBAS](../bios/CALBAS.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate) re-runs every rule
of the eight call pages on zerobas, on each row the page measured.
