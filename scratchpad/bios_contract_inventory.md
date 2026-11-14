# MSX1 main-BIOS per-row CONTRACT inventory (2026-11-14)

For each of the 108 entries: what a caller can observe afterwards (the answer kind), which
gate actually DIFFS that answer against a reference, and what no gate compares (the gap). A
read-only agent read the gate sources; rows marked (inf) are where the contract was inferred
rather than read in the repo. docs/tier-status.md's "exercised by" column only shows that a
gate NAMES an entry; this file shows what is COMPARED.

## Comparing gates

| code | gate | what it compares |
|---|---|---|
| BR | biosregs | HL / DE / BC / A against the VG-8020 -- except on `:END` rows, which diff only their `[C...]` cell line; F only in TUPC / TDOWNC |
| BF | biosflags | masked F, sometimes A |
| BM / BT | biosmode / biostext | the work-area bytes the call changed |
| BV | biosvram | VRAM and RAM windows |
| SR | slotregs | registers and port $A8, against the CF-3300 |
| P1 / BE | p1vec / bootenv | RAM answers, against the CF-3300 |
| BL-bN | biosl rung N | that cartridge's capture block, plus `@vram` spans, against the VG-8020 |

The rest: IO initio, PB paintbios, ST strtms, TB tapebios, SY synchr, IC iscntc, OD outdlp,
BP beep, GI gicini, PH phydio (run by diskbasic-acceptance), ID input-devices.

Not comparing: subrom-acceptance (boots stock C-BIOS, no reference); lstout-acceptance
(zerobas only).

## Gaps, ranked

1. **FORMAT ($0147):** nothing compared; its only witness is the word "FORMAT".
2. **LPTOUT ($00A5):** no direct comparing call. The byte stream and Cy could be compared
   with outdlp's apparatus (openMSX printer logger, A / Cy in RAM).
3. **STMOTR ($00F3), CHGSND ($0135):** the whole answer is a port $AA bit (4 motor, 7
   sound), and only the registers are diffed. The fix is chgcap's pattern.
4. **OUTDO ($0018):** the character it outputs is dropped from the readout; nothing checks
   the PRTFLG -> printer path.
5. **The actual VDP registers** after DISSCR, ENASCR, WRTVDP, CHGMOD, INI* / SET*, TOTEXT,
   CHGCLR: only the RAM shadows are diffed. They can be read through the debugger.
6. **SETRD / SETWRT:** the VDP address pointer is never observed (an IN / OUT $98 by our own
   code would show it).
7. **Flags BF does not cover:** CNVCHR (Z/C, the graphic header), ISFLIO (Z), GSPSIZ (Cy),
   SETATR (Cy, inf), PINLIN / INLIN / QINLIN's Cy on STOP, BREAKX with Ctrl-STOP held.
8. **Only the idle / empty state is compared:** LPTSTT with a ready printer; LFTQ / GETVCP
   with a non-empty queue or other voices; PUTQ when full; joysticks / GTPAD with a device.
9. **GICINI called directly:** QUETAB / PLYCNT not compared. **INITIO:** its exit registers
   are printed but not diffed (both references agree: F $54, A $FF, E $0B). Its printer
   init is inferred.
10. **The SCREEN 3 variants** of RIGHTC / LEFTC / UPC / DOWNC, MAPXYC, READC, SETC, NSETCX.

Everything except CHKRAM (a reset, whose contract is the boot state every gate inherits) can
be probed black-box: registers, work area, VRAM, PSG / VDP registers, ports $AA / $A8, or the
printer logger.

## Mechanical faults in tools/entry_table.py (not contract gaps)

- It never credits biosl's rung .asm files (biosl_run.py globs them). They witness SNSMAT,
  GTSTCK, GTTRIG, CHSNS, the VDP set, the slot entries, the tape entries, the text entries
  and KEYINT.
- Spurious witnesses: CHKRAM (0x0000 constants), LEFTC (an 0x00FF mask), FORMAT (the word in
  "CALL FORMAT").
- subrom-acceptance compares against nothing, yet it backs CALSLT's "vs reference: yes".
- biosregs's `:END` rows (INITXT and the other mode setters, ERAFNK, DSPFNK, INIFNK, FNKSB,
  POSIT, CHGCLR, CLRSPR, NSETCX, INLIN) do not diff registers, by design.

## Per entry (the agent's table, condensed)

| addr | name | answer | compared by | gap |
|---|---|---|---|---|
| 0000 | CHKRAM | cold start | boot / BL-b1 | low value |
| 0008 | SYNCHR | HL, A, F / error | SY | - |
| 000C | RDSLT | A, BC / D / E | SR, P1, BL-b6 | - |
| 0010 | CHRGTR | HL, A, Z / C | BR, BF, SY | - |
| 0014 | WRSLT | memory | SR, P1, BL-b6 | - |
| 0018 | OUTDO | char out; PRTFLG -> printer | BR (registers) | the output; the printer path |
| 001C | CALSLT | the callee's result | P1 | IX / IY / AF' (inf) |
| 0020 | DCOMPR | Z / C, A | BR, BF | - |
| 0024 | ENASLT | slot map, DI | SR, P1, BL-b6 | - |
| 0028 | GETYPR | flags | BF, SY | - |
| 0030 | CALLF | the callee's result | P1, BE | as CALSLT |
| 0038 | KEYINT | JIFFY, hooks, STATFL | ruled indirect; BL-b3 | click, REPCNT, TRPTBL (inf) |
| 003B | INITIO | PSG, $AA | IO | exit registers not diffed |
| 003E | INIFNK | FNKSTR | BR | - |
| 0041-0047 | DISSCR / ENASCR / WRTVDP | VDP reg + shadow | BR (shadow), BL-b2 | the VDP register |
| 004A-005C | RDVRM / WRTVRM / FILVRM / LDIRMV / LDIRVM | A / VRAM / RAM | BV, BR, BL-b2 | - |
| 0050 / 0053 | SETRD / SETWRT | the VDP address | BR (registers) | the address |
| 005F / 0062 | CHGMOD / CHGCLR | VDP, work area, VRAM | BM, BV, BL-b2 | the VDP registers |
| 0066 | NMI | - | ruled | - |
| 0069 | CLRSPR | sprite VRAM | BV, BR, BL-b2 | - |
| 006C-0081 | INITXT .. SETMLT | work area, VDP, VRAM | BM, BR | the VDP registers, cleared VRAM |
| 0084 / 0087 | CALPAT / CALATR | HL | BR, BL-b2 | - |
| 008A | GSPSIZ | A, Cy | BR, BL-b2 | Cy |
| 008D | GRPPRT | glyph, GRPACX / Y | BR | the glyph (font) |
| 0090 | GICINI | PSG, MUSICF, queues | IO, BL-b5, GI | QUETAB / PLYCNT |
| 0093 / 0096 | WRTPSG / RDPSG | PSG / A | BL-b5, BR, IO | - |
| 0099 | STRTMS | queues, PSG | ST | - |
| 009C / 009F | CHSNS / CHGET | Z / A, KEYBUF | BF, BR, BL-b4 | CHSNS Z with a key (inf) |
| 00A2 | CHPUT | VRAM, cursor | BT, BR, BL-b1 | - |
| 00A5 | LPTOUT | printer byte, Cy | none directly | all of it |
| 00A8 | LPTSTT | A, Z | BF, BR (no printer) | printer ready |
| 00AB | CNVCHR | A, Z, C | BR (A) | flags, the header path |
| 00AE-00B4 | PINLIN / INLIN / QINLIN | BUF, HL, Cy | BR | Cy; QINLIN's prompt |
| 00B7 | BREAKX | Cy | BF, BR (no key) | Cy held |
| 00BA / 00BD | ISCNTC / CKCNTC | INTFLG, break | IC, BR | - |
| 00C0 | BEEP | PSG over time | BP, BL-b5 | - |
| 00C3 | CLS | VRAM, cursor | BT, BL-b1 | graphics modes |
| 00C6-00CF | POSIT / FNKSB / ERAFNK / DSPFNK | cells, key line | BT, BR, BL-b1 | - |
| 00D2 | TOTEXT | mode | BR | the VDP registers |
| 00D5-00DE | GTSTCK / GTTRIG / GTPAD / GTPDL | A | BR, BL-b4, ID | with a device |
| 00E1-00F0 | TAPION .. TAPOOF | Cy, signal, motor | TB, BL-b7 | the motor bit (inf) |
| 00F3 | STMOTR | $AA bit 4 | BR (registers) | **the motor bit** |
| 00F6 / 00F9 | LFTQ / PUTQ | HL; queue, Z | BR, ST | non-empty / full |
| 00FC-0111, 011D-0123 | cursor / MAPXYC / READC / SETC / NSETCX | cells, VRAM | BR | SCREEN 3 |
| 010E / 0114 / 0117 | SCALXY / FETCHC / STOREC | registers, cells | BR, BF | - |
| 011A | SETATR | ATRBYT, Cy | BR | Cy (inf) |
| 0126 | GTASPC | DE / HL | BR | - |
| 0129-012F | PNTINI / SCANR / SCANL | BDRATR, HL / DE, VRAM | PB | - |
| 0132 | CHGCAP | $AA bit 6 | BR | - |
| 0135 | CHGSND | $AA bit 7 | BR (registers) | **the sound bit** |
| 0138 / 013B | RSLREG / WSLREG | A / $A8 | BR, P1, SR | - |
| 013E | RDVDP | A | BR, BL-b3 | - |
| 0141 | SNSMAT | A | BL-b4, BE, TB | - |
| 0144 | PHYDIO | sectors, Cy | PH, BL-b8 | - |
| 0147 | FORMAT | disk format | none | all of it |
| 014A | ISFLIO | A, Z | BR | F |
| 014D | OUTDLP | printer, LPTPOS | OD | - |
| 0150 / 0153 | GETVCP / GETVC2 | HL | BR | voices 1 / 2 |
| 0156 | KILBUF | pointers | BT, BR, BL-b4 | - |
| 0159 | CALBAS | the callee's result | BR | - |
