# D-MSX1ON2 triage: slot probes, the control group and XSET

Probes: b6slots xcalslt xenaslt xrdslt xenaslt2 xrdslt2 xset. Control group: b3int xchg xchgw xchput xchput2-5 xchrgtr
xchrgtr2 xcnv xcnv2 xdcompr xfsw xgetypr xkey xlin3-6 xlpt xlpt2 xlpt3 xoutdo xrslreg xspr xsynchr xsynchr2.

Source: the per-probe file in scratchpad/AE_m1on2/, compared with the newest committed VG-8020 reading (`scratchpad/m1on2_cmp.py`
picks it). For the slot probes it is also compared with the committed CF-3300 row (`XCALSLT_run4c`, `XENASLT_run4c`,
`XRDSLT_run5c`, `XENASLT2_run5c`, `XRDSLT2_run1c`). Each byte is decoded by case and field from the probe's header and
its case table. Clean room: only captures, probe sources, spec pages and the open C-BIOS source; nothing was run.

Columns: **VG** = VG-8020, **CF** = CF-3300 (an MSX1 whose RAM is the expanded slot 3-0), **F900** = HB-F900 (MSX2,
JP), **8250** = NMS 8250 (MSX2, EU), **WSX** = FS-A1WSX (MSX2+, JP). **C-BIOS** = C-BIOS's MSX2 build of each machine,
given as F900-build / 8250-build / WSX-build when the three differ. Offsets are into the capture block, in hex.

## Slot maps (they explain most of the slot bytes)

| | VG | CF | F900 | 8250 | WSX | C-BIOS (all three builds) |
|---|---|---|---|---|---|---|
| RAM slot ID (page 3) | $03 | $83 (3-0) | $87 (3-1) | $8B (3-2) | $83 (3-0) | $8B (3-2) |
| Slot 0 expanded | no | no | no | no | **yes** | no |
| Slot 3 expanded | no | yes | yes | yes | yes | yes |
| Slot 3's secondary register at boot (complemented) | - | $00 | $50 | $A0 | $00 | $A0 |
| 3-0, page 1 | - | RAM | not ROM ($FF) | a ROM, header "CD" | RAM | nothing ($FF) |
| 3-1, page 1 | - | a ROM ("AB") | RAM, reads $FF | $FF | a ROM ("AB") | $FF / $FF / "AB" |

The cartridge sits in slot 1 everywhere, and the slot register at boot is $F4 on every machine.

## Summary

### GEN findings

| # | Call (page) | Rule | What the newer machine does | MSX2 | MSX2+ |
|---|---|---|---|---|---|
| G1 | SETTXT ([SETTXT.md](../docs/bios/SETTXT.md)) | R-TX-SHADOW | Only RG2SAV (name table) and RG4SAV (pattern table) are computed from the cells. RG3SAV, RG5SAV and RG6SAV keep what they held ($A5, or $5A). | yes | yes |
| G2 | SETMLT ([SETMLT.md](../docs/bios/SETMLT.md)) | R-MT-SHADOW | RG3SAV keeps what it held. It is not set to MLTCOL / $40. RG2SAV and RG4-6SAV are still computed. | yes | yes |
| G3 | SETTXT, SETT32, SETMLT | R-TX/T3/MT-R01 | RG0SAV := RG0SAV AND $F1: bits 7-4 and 0 are kept, and only M3-M5 (bits 3-1) are cleared. The MSX1 does AND $01, so $FF gives $F1 (MSX1 $01), $5A gives $50 and $FE gives $F0. RG1SAV still follows the rule. | yes | yes |
| G4 | SETGRP ([SETGRP.md](../docs/bios/SETGRP.md)) | R-GR-R01 | RG0SAV := (RG0SAV AND $F3) OR $02, so M4 and M5 are cleared. The MSX1 does a plain OR $02: $FF gives $F3 (MSX1 $FF), and $5A gives $52. | yes | yes |
| G5 | SETTXT, SETT32, SETGRP, SETMLT | R-xx-VDP ("R#7 is not written") | R#7 := RG7SAV in all 76 cases ($A5 / $00 / $FF / $5A). On the VG-8020, R#7 keeps the value the probe set by hand ($F4). | yes | yes |
| G6 | SETTXT, SETT32, SETGRP, SETMLT | R-xx-REGS | A is $00, not the new RG6SAV. F is $44 (Z, P/V), or $0C / $2C / $20 in SETTXT. SETTXT keeps DE (MSX1: $0000) and returns BC $0010 (MSX1: $0007). The other three calls return BC $0000. SETGRP returns DE $0000 (MSX1: $7F03). HL is not "just past the table": it is $0000, $0F00 or $3F00 in SETTXT, and $00xx / $01xx in the other three, with xx the new RG5SAV. IX, IY, the interrupts after the call (R-xx-EI), VRAM, SCRMOD and the cells (R-xx-KEEP) are unchanged. | yes | yes |

XSET is identical on the F900, the 8250 and the WSX. No other probe in this set shows a GEN difference.
**Candidate, not counted (see U1):** for a RAM target in page 1 of the expanded slot 3-1 / 3-2, CALSLT and CALLF have
interrupts ON in the target and after the call, even when entered with DI (R-CS-DI / R-CF-DI). This shows on the F900
and the 8250, but not on the WSX or the CF-3300 (both 3-0).

### C-BIOS MSX2 findings

- **C1, XSET: no reading on any build.** DONE is never set; the harness wrote "NO READING". The capture block is
  9216 bytes of other data, so the 8400+ "differences" mean nothing. The probe ran to completion on all three
  references. See U2.
- **C2, CALSLT / CALLF: stack depth.** The target runs 10 bytes below the caller's SP. The references use 6 for a slot
  that is not expanded and 14 for an expanded one. This is the known MSX1 divergence D-CALSLTSTACK, kept unchanged.
  C-BIOS does **not** match the VG-8020.
- **C3, CALSLT / CALLF: IY in the target.** C-BIOS passes the slot ID over the caller's low byte (CALSLT) or over $41 /
  $45 (CALLF: a stale F', not the entry F). The references give $0314 for an expanded target and slot-ID:entry-F for
  CALLF. This is the known D-CALSLTIY, kept. C-BIOS does not match the VG-8020 or the CF-3300.
- **C4, CHRGTR (xchrgtr, xchrgtr2): the numeric-constant tokens are not handled.** This covers tokens $0B-$0F, $11-$1D
  and $1F: no CONTXT / CONSAV / CONTYP / CONLO update, and a different HL / F. For $10 and $1E, A / F differ. All four
  references agree among themselves. C-BIOS ships no BASIC ROM, so this is not about the generation. C-BIOS does not
  match the VG-8020.
- **C5, PINLIN / INLIN / QINLIN (xlin3-6): F = $44 on a normal return; the references give $18** (R-L-F, the same
  class as zerobas's D-TEXTAF). The carry is clear on both, so the published contract holds. Unpublished bits only;
  C-BIOS does not match the VG-8020.
- Every other C-BIOS byte in b6slots, xcalslt, xenaslt, xrdslt, xenaslt2 and xrdslt2 is CONFIG. C-BIOS's machines put
  RAM in 3-2 and leave slot 0 not expanded, even for the WSX build. Where the slot map is the same (the 8250 build),
  C-BIOS gives the 8250's answers. This includes RDSLT / WRSLT's B = PSL and C = $C0 for an expanded slot, which match
  the CF-3300 too.
- The C-BIOS page-1 RAM cases in xcalslt (6, 7, 10, 11, 19) are not readable. See U1.

### APPARATUS fixes

- **A1, xcalslt: the copy of `tgt` into the RAM slot's page 1.** The copy sets `out ($A8)` to page 1 := slot 3 and
  takes whatever page 1's secondary field holds. That field is 3-0 on every MSX2 and on C-BIOS, and 3-0 is not the RAM
  on the F900, the 8250 or C-BIOS. (The header says "3-0 selected where expanded"; that assumption holds only for the
  CF-3300 and the WSX.) Fix: copy with WRSLT(ramid) or ENASLT(ramid, page 1). Then read the copy back with RDSLT
  (ramid, $4010...) into the header, so the record shows the target was really there.
- **A2, xcalslt: the secondary preset 3-1.** On the F900 the preset (cases 10, 11, 15-18) is the RAM's own sub-slot, so
  "the call must switch and put back" is not tested there. Fix: preset (RAM's secondary + 1) AND 3.
- **A3, xenaslt2 and xrdslt2** assume RAM in 3-0 (markers written there by hand) and an "AB" ROM in 3-1. That holds on
  the CF-3300 and the WSX, and the WSX is **byte-identical to the CF-3300** on both probes. It fails on the F900 (3-1
  is RAM, 3-0 is not) and the 8250 (3-0 holds a "CD" ROM). Fix: take the RAM sub-slot from SLTTBL. Find an "AB" sub-slot
  by the header bytes the ruling allows. Otherwise, skip the machine and state that it was skipped.
- **A4, xrdslt's witness:** its "bit 7 = slot 3, expanded" shortcut holds here (the only expanded slot named is RAM in
  slot 3), so no byte is wrong. It would break on a machine with an expanded cartridge slot.

### UNKNOWNs

- **U1, xcalslt page-1 RAM cases 6, 7, 10, 11, 19.** Given A1, it is unclear how `tgt` reached the RAM slot's page 1
  on the F900 and the 8250. The records match `tgt` exactly, but the copy went to 3-0. That casts doubt on the
  candidate GEN above: the F900 and the 8250 show interrupts on in the target and after the call, even when entered
  with DI.
  - On C-BIOS, `tgt` never ran in cases 6, 10 and 11: the registers came back exactly as passed. It ran in cases 7 and
    19, with interrupts on inside the target, although the C-BIOS CALSLT path has no EI before the call.
  - Measurement: apply A1, record the RDSLT read-back, and add a WRSLT-to-ramid:$4010 / read-$8010 alias test. Then
    re-run xcalslt on all six. If the interrupts-on result survives, run a target in 3-0 on the F900 / 8250 and one in
    3-1 / 3-2 on the WSX, to tell "MSX2" from "a non-zero sub-slot".
- **U2, XSET on C-BIOS MSX2.** The probe does not finish, so it is unclear whether a call hangs or crashes. Measurement:
  write the case index (`cidx`, $E91A) and a stage byte into the capture block before each call, then re-run. That
  shows the case and op where C-BIOS stops.

### Control group verdict: the agreement is real, not an artefact

All 28 probes have a complete capture on every machine: the finish marker, the same length as the VG-8020's (32 to
10242 bytes), and no `+LEN`. The captures are dense, with 4 to 8874 nonzero bytes and up to 256 distinct values. They
record register contracts, work-area cells, VRAM cells and editor state, so an identical capture is a real agreement.

Limits by design, which make them blind to things that do differ between these machines:
- b3int counts JIFFY and hook calls per HALT, so it cannot see 50 Hz against 60 Hz.
- xchput* and xkey read name-table codes and cursor cells, not glyph patterns, so the JP / EU character set is out of
  view.
- xlpt2 and xlpt3 have only 4 meaningful bytes each: the not-ready answer and the CTRL+STOP abort.

The probes with C-BIOS differences are C4 (xchrgtr, xchrgtr2) and C5 (xlin3-6). Every other control probe is identical
on C-BIOS too.

---

## b6slots

| off | case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|
| 09 | EXPTBL bit 7, slot 0 | 00 | 00 | 00 | 80 | 00 | CONFIG | the WSX's slot 0 is expanded; C-BIOS's WSX build is not (C-BIOS CONFIG) |
| 0A | EXPTBL bit 7, slot 3 | 00 | 80 | 80 | 80 | 80 | CONFIG | the probe itself says "excused if the hardware differs" |

RDSLT of the "AB" header, ENASLT of RAM into page 2, the read-back, WRSLT / RDSLT and RDSLT's register contract
(CAP+0..8) are identical everywhere.

## xcalslt (header 5 bytes, then 40 per case)

| off | case / field | VG | CF | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|---|
| 02 | EXPTBL+3 | 00 | 80 | 80 | 80 | 80 | 80 | CONFIG | |
| 03 | RAM slot ID | 03 | 83 | 87 | 8B | 83 | 8B | CONFIG | |
| +2 / +31 in every case | slot 3's secondary, in the target / after | 00 | 0x | 5x | Ax | 0x | Ax | CONFIG | page 3's field is the RAM's sub-slot. The page-1 / page-2 fields behave as on the CF-3300 (R-CS-SEC holds: switched in the target, put back after, a 3-1 preset left alone for a cartridge target) |
| +3 (SP), cartridge cases 0-5, 15, 16 | stack depth | 06 | 06 | 06 | 06 | 06 | 0A | ref: none. C-BIOS: C2 | |
| +3, RAM cases 6, 7, 10-13, 17-19 | stack depth | 06 | 0E | 0E | 0E | 0E | 0A (00 where it did not run) | CONFIG (refs: an expanded target, as on the CF-3300). C-BIOS: C2 | |
| +15/16 (IY in the target), CALLF cartridge cases 2, 3, 5, 16 | IY low | entry F (00/5A/FF) | = | = | = | = | 41 | C-BIOS: C3 | R-CF-IY |
| +15/16, RAM cases 6, 7, 10-13, 17-19 | IY | 03:case low | 0314 | 0314 | 0314 | 0314 | 8B:case low / 8B41 / 8B45 | CONFIG (refs, = CF-3300). C-BIOS: C3 | R-CS-IY / R-CF-IY |
| 0F6, 11E, 196, 1BE, 2FE (+1) and 113, 13B, 1B3, 1DB, 31B (+30) | IFF in the target / after, RAM **page 1** cases 6, 7, 10, 11, 19 | 0 | 0 | **1** | **1** | 0 | 1 (cases 7, 19) | UNKNOWN (U1) | GEN candidate against R-CS-DI / R-CF-DI. Page-2 RAM targets (12, 13, 17, 18) keep DI on all machines |
| 0F5-115, 195-1B5, 1BD-1DD | the whole record, cases 6, 10, 11 | (tgt's) | = | = | = | = | target not run, registers back as passed | UNKNOWN (U1) | C-BIOS, and apparatus A1 |
| 161, 189 | IY high after CALBAS, cases 8, 9 | 00 | 00 | 00 | 00 | 80 | 00 | CONFIG | the main-ROM slot ID: 0-0, expanded, on the WSX |

## xenaslt (header 13 bytes, then 16 per case)

| off | case / field | VG | CF | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|---|
| 02, 05, 06, 09, 0A, 0B | header: slot register, EXPTBL 0 / 3, SLTTBL 0 / 3, secondary, RAM ID | (MSX1 map) | | | | | | CONFIG | see "Slot maps" |
| +4 (secondary after), cases 0-8 | page 1 / 2 field := the RAM's sub-slot when RAM is named; the other fields kept | 00 | 00 | 54/50 | A8/A0 | 00 | A8/A0 | CONFIG | same rule everywhere; C-BIOS = 8250 (same map) |
| +5 (SLTTBL 0) | junk $1B left in slot 0, which is not expanded | 1B | 1B | 1B | 1B | F0 | 1B | CONFIG | the WSX's slot 0 is expanded, so the probe writes no junk there |
| +8 (SLTTBL 3) | junk $4E left (VG), or the live secondary | 4E | 00 | 54/50 | A8/A0 | 00 | A8/A0 | CONFIG | |

A, F, IFF, the slot register, B-E, `moved` and both witness bytes are identical on all machines in all 9 cases.
ENASLT behaves the same.

## xenaslt2 (no VG-8020 run; header 4 bytes, then 12 per case)

| off | case / field | CF | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|
| 02, 03, +3, +4 | secondary / SLTTBL+3 | 00 / 0x | 5x / 4x | Ax / 8x | = CF | Ax / 8x | CONFIG | page 3's field differs. Pages 0-2 follow the same rule (the register's fields, not SLTTBL's; cases 6, 7) |
| +5/+6, cases 0, 4, 6 (3-0) | $4000 / $4001 | 5A A5 | FF FF | 43 44 | = CF | FF FF | APPARATUS (A3) | the markers are not in 3-0 on the F900 / 8250 / C-BIOS |
| +5/+6, cases 1-3, 5, 7, 8 (3-1) | $4000 / $4001 | 41 42 | FF FF | FF FF | = CF | FF / FF / 41 42 | APPARATUS (A3) | 3-1 is RAM on the F900, empty on the 8250 |

**The WSX is byte-identical to the CF-3300.** The MSX2+ keeps the MSX1 secondary-slot behaviour of ENASLT.

## xrdslt (header 17 bytes, then 12 per case)

| off | case / field | VG | CF | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|---|
| 02-0B | header | (MSX1 map) | | | | | | CONFIG | |
| +4 (secondary after), every case | | 00 | 0x | 5x | Ax | 0x | Ax | CONFIG | presets 21-24, 27-30 are put back (R-*-SEC holds) |
| +7 / +8 (B, C after), RAM cases | B = PSL, C = $C0 | 3x / CF-style | F4 C0 (F0 under the slot-0 preset) | = | = | = | = | CONFIG | the expanded-slot contract, as on the CF-3300 |
| +B (pre-witness), cases 0, 2, 4, 6, 12, 14, 16, 18, 21, 23, 25, 31, 34 | the RAM byte before WRSLT | FF / 00 | FF / 00 | FF | 00 | 00 / FF / 55 | FF | CONFIG | power-on RAM content, not the call |
| 1C1 | A, control case 36 | 03 | 83 | 87 | 8B | 83 | 8B | CONFIG | A still holds the RAM ID |

The witness bytes, A, F, IFF, the slot register and `moved` are identical on all machines in all 37 cases. Neither
RDSLT nor WRSLT changes with the generation.

## xrdslt2 (no VG-8020 run; header 6 bytes, then 8 per case)

| off | case / field | CF | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|---|
| 03, 09, 11, 19, 21, 29, 31 | secondary | 0x | 5x | Ax | = CF | Ax | CONFIG | |
| 04/05, 0E, 16, 2E | 3-1's "AB", by hand and by RDSLT $87 | 41 42 | FF | FF | = CF | FF / FF / 41 42 | APPARATUS (A3) | |
| 1E, 26 | RDSLT $83 $4000 after WRSLT $18 | 18 | FF | 43 | = CF | FF | APPARATUS (A3) | 3-0 is not RAM there |

**The WSX is byte-identical to the CF-3300.**

## xset (header 1 byte, then 112 per case; 76 cases). The F900, 8250 and WSX are identical.

| case / field | VG | MSX2 / 2+ | C-BIOS | class | note |
|---|---|---|---|---|---|
| SETTXT RG3SAV, RG5SAV, RG6SAV (cases 0-11, 48-51, 64, 68, 72) | from the cells (e.g. 01 / 3F / 04) | the preset kept (A5, or 5A) | no reading | GEN G1 | |
| SETMLT RG3SAV (36-47, 60-63, 67, 71, 75) | MLTCOL / $40 (00 / 49 / 4F / FF) | A5 / 5A kept | no reading | GEN G2 | |
| RG0SAV after, the $FF / $5A / $FE presets (TXT, T32, MLT) | AND $01 | AND $F1 | no reading | GEN G3 | |
| RG0SAV after, SETGRP | OR $02 | AND $F3, OR $02 | no reading | GEN G4 | |
| R#7 (all 76) | F4 (not written) | = RG7SAV | no reading | GEN G5 | |
| A, F, BC, DE, HL (all 76) | RG6SAV, 00, 0007, 0000 / 7F03, F3xx | 00, 44 / 0C / 2C / 20, 0010 / 0000, DE kept (TXT) / 0000, see G6 | no reading | GEN G6 | |
| R#0, R#1, R#2, R#4, R#5, R#6 as the VDP holds them (same RGnSAV) | R#2 bits 3-0, R#4 / R#6 bits 2-0, R#5 bits 6-0, R#1 without bit 2 | wider (e.g. R#2 3F, R#4 1F, R#5 FF, R#6 1F / 25), R#1 without bit 7, R#0 without bits 7 and 0 | no reading | CONFIG | V9938 / V9958 register widths, not the BIOS |
| IX, IY, IFF, RG1SAV, RG2SAV, RG4SAV, RG7SAV, SCRMOD, the VRAM sums and the 20 cells | | identical | no reading | - | R-xx-EI and R-xx-KEEP hold |

## Control group: C-BIOS differences only (gen = 0 everywhere)

| probe | off / field | refs (= VG) | C-BIOS (all three) | class | note |
|---|---|---|---|---|---|
| xchrgtr | cases $0B-$0F, $11-$1D, $1F, both passes: F, HL, CONTXT, CONSAV / CONTYP / CONLO cells. Cases $10, $1E: A, F | constant-token handling | not handled | C-BIOS (C4) | no BASIC ROM behind CHRGTR |
| xchrgtr2 | every case (all numeric tokens, 3 calls) | as on the VG-8020 | differs | C-BIOS (C4) | |
| xlin3 | 242 = case 8 F | 18 | 44 | C-BIOS (C5) | the other cases end by STOP; their F agrees |
| xlin4, xlin5, xlin6 | +01 of every 72-byte record (F) | 18 | 44 | C-BIOS (C5) | R-L-F |
