# D-MSX1ON2 triage -- graphics, sound, tape, input, line input, disk-entry probes

Probes: xgfx1 xgfx2 xgfx3 xgfx4 xgfx5 xgfx5b xgfx6 b5sound xsnd1 xsnd1b xtap1-5 xinp1 xoutdlp xchg2 b4input b7tape
b8save xlin xlin2a xlin2b xlin2c xdent5 xdent6. Source: the per-probe file in scratchpad/AE_m1on2/ against the newest committed
VG-8020 reading (as `scratchpad/m1on2_cmp.py` picks it), decoded per case and field from each probe's header and its
`*_model.py` / `*_cases.py` / `xlin2_gen.py` / `xdent_common.py` / `xtap1_model.py`. Clean room: captures, probe sources
and spec pages only; nothing was run in the emulator.

Columns: **VG** = VG-8020, **F900** = Sony HB-F900 (MSX2, JP), **8250** = Philips NMS 8250 (MSX2, EU), **WSX** = Panasonic
FS-A1WSX (MSX2+, JP), **C-BIOS** = C-BIOS's MSX2 / MSX2+ build of each machine (JP / EU / 2+ where they differ).
Case numbers are the probe's own table index. For xsnd1b, page number = 107 + index.

## Summary

### GEN findings (the call behaves differently on the newer generation)

| # | Call (page) | Rule | What the MSX2 does | MSX2 | MSX2+ |
|---|---|---|---|---|---|
| G1 | MAPXYC ([MAPXYC.md](../docs/bios/MAPXYC.md)) | R-MX-MLT / R-MX-GRP / R-MX-AF / R-MX-REGS | The test is no longer "SCRMOD = 2". SCREEN 0, 1 and 4 use the SCREEN 2 mapping (CLOC $2662, CMASK $08, A $62, D := X for X 100 / Y 50). SCREEN 3 still uses the multicolour mapping. SCRMOD 6, $0A, $42, $82 and $FF (≥ 5) are bitmap: CLOC := X (HL $0064), CMASK := Y ($32), A := Y, and F differs. | yes | yes |
| G2 | MAPXYC, RIGHTC, LEFTC, UPC, TUPC, DOWNC, TDOWNC ([MAPXYC.md](../docs/bios/MAPXYC.md), [TUPC.md](../docs/bios/TUPC.md) …) | R-MX-REGS, R-xx-KEEP ("interrupt state kept") | In SCREEN 3, a call entered with interrupts OFF returns with them ON. MAPXYC shows this in 14 cases and the six cursor-move calls in 91 (every SCREEN 3 case entered with DI). SCREEN 2 and the other modes keep the interrupt state. | yes | yes |
| G3 | TUPC ([TUPC.md](../docs/bios/TUPC.md)) | R-TU-EDGE (+ R-TU-AF) | The SCREEN 3 top-edge test is relative to MLTCGP instead of the absolute "CLOC AND $FF07 = 0". CLOC $1000 / $10F8 / $1020 with MLTCGP $1000, and $0820 with $0800, now STOP (F $45, CLOC kept). On the MSX1 they moved on to $0Fxx / $07xx. | yes | yes |
| G4 | TDOWNC ([TDOWNC.md](../docs/bios/TDOWNC.md)) | R-TD-EDGE (+ R-TD-AF) | The SCREEN 3 bottom-edge test is relative to MLTCGP instead of "high byte ≥ 5". CLOC $1007 / $1027 / $1127 / $1427 (MLTCGP $1000) and $0827 / $0927 / $0C27 (MLTCGP $0800) now MOVE ON (F $54). | yes | yes |
| G4' | GRPPRT ([GRPPRT.md](../docs/bios/GRPPRT.md)) | R-GP-POS, R-GP-VRAM | This is G4 seen through GRPPRT. In SCREEN 3 with MLTCGP $1000 (xgfx5 case 22), the glyph is no longer cut at the block row: CLOC is $1264 (MSX1: $1167) and the VRAM block 4 sum changes. | yes | yes |
| G5 | GRPPRT ([GRPPRT.md](../docs/bios/GRPPRT.md)) | R-GP-KEEP (F kept) | F := $93 on return, whatever F was on entry (all 73 cases in xgfx5 + xgfx5b, including control codes). A and the other registers are still kept. | yes | yes |
| G6 | SCALXY ([SCALXY.md](../docs/bios/SCALXY.md)) | R-SX-CLIP | SCREEN 0 and 1 are no longer divided by 4: X 100 / Y 50 stay $64 / $32, and clipped values stay $FF / $BF. On the MSX1 they became $19 / $0C and $3F / $2F. | yes | yes |
| G7 | SCALXY | R-SX-AF | F is no longer "Z set" in SCREEN 2 ($41 / $40): it is $81 / $80, and the same in SCREEN 0 / 1. The carry and A still follow the rule. | yes | yes |
| G8 | WRTPSG ([WRTPSG.md](../docs/bios/WRTPSG.md)) | R-WP-REG ("R7 written whole") | R7 is not written whole: $3E reads back $BE (b5sound), and $3F reads back $BF (xsnd1 case 104). Bit 7 (port B direction) is forced to 1. Bit 6 is untested at 1. | yes | yes |
| G9 | BEEP ([BEEP.md](../docs/bios/BEEP.md)) | R-BP-REGS | A $0B, F $18, BC $0ED0 replace A 0, F $44, BC 0. E is $04 on both JP machines and $07 on the 8250. The PSG end state (R-BP-PSG) is the same as on the MSX1. | yes | yes |
| G10 | BEEP | R-BP-EI ("interrupts on after") | On the WSX, interrupts stay as they were: OFF after a call entered with DI (xsnd1 73, xsnd1b 118-121). | no | **yes (MSX2+ only)** |
| G11 | SETATR ([SETATR.md](../docs/bios/SETATR.md)), PNTINI non-SCREEN-2 ([PNTINI.md](../docs/bios/PNTINI.md)) | R-SA-F, R-PI-AF ("bits 5 / 3 from A") | F bit 5 is clear even when A has bit 5 set: A $FF gives F $89 (MSX1 $A9), and A $20 gives $01 (MSX1 $21). | no | **yes (MSX2+ only)** |
| G12 | MAPXYC, SCREEN 2, X > 255 (group XGX) | none (CMASK already excluded) | CMASK $FB / $4B on all three machines vs the VG-8020's $D5 / $C5. Deterministic, and independent of the CMASK preset. | yes | yes |
| G13 | GTSTCK, BREAKX ([GTSTCK.md](../docs/bios/GTSTCK.md), [BREAKX.md](../docs/bios/BREAKX.md)) | none (working values, groups XIW / XIA) | GTSTCK leaves L $0A lower (a table pointer into the ROM). BREAKX with CTRL+STOP leaves A $14 (MSX1 $0D). No compared rule changes. | yes | yes |

Calls with NO generation difference in these probes: FETCHC, STOREC, GTASPC, READC, SETC, NSETCX, SCANR, SCANL,
RDPSG, CHGSND, LFTQ, PUTQ, GETVCP, GETVC2, GICINI, STRTMS, STMOTR, TAPOON, TAPOUT, TAPOOF, TAPION, TAPIN, TAPIOF,
SNSMAT, KILBUF, CHGCAP, GTTRIG, ISCNTC, CKCNTC, GTPAD, GTPDL, CHGET, CHSNS, and the b4input / b7tape rungs (0 bytes).
They also include PINLIN, INLIN and QINLIN, on the only MSX2 with a full reading (F900: 0 bytes).

### C-BIOS MSX2 findings

- **MSX1 behaviour kept where the MSX2 changed it.** C-BIOS matches the VG-8020, not its own reference, here:
  - G2: interrupts stay OFF in SCREEN 3.
  - G5: GRPPRT keeps F.
  - G9: BEEP gives A 0, F $44, BC 0, E 7.
  - G10: the MSX2+ build turns interrupts on after BEEP.
  - G11: the MSX2+ build keeps F bit 5 from A.
- **The MSX2 behaviour is followed** for G1, G3, G4 / G4', G6, G7 and G8.
- **G12:** C-BIOS gives CMASK $80 / $01 ($80 >> (X AND 7)), which matches neither generation.
- **Different from every reference (MSX1 and MSX2 alike), so not a generation finding:**
  - SETC F has bits 5 / 3 set ($A8 / $AC / $88 / $24 vs $80 / $84 / $80 / $04). This breaks R-SC-AF (xgfx3 cases 31 48 49 50 66 74 78 85).
  - PINLIN / INLIN / QINLIN return F $44 where every reference returns $18. This is R-L-F, which zerobas already fails too.
  - The working registers of NSETCX, SCANR, SCANL, GTSTCK, GTTRIG, GTPAD, GTPDL, BREAKX, TAPOON, TAPOUT, TAPION and TAPIN differ. These fields are not compared on the pages.
- **The JP builds lack the Japanese OUTDLP conversion:** $85 / $FF go out unchanged on a non-MSX printer (see C1).
- **No reading:**
  - b8save never sets DONE on any C-BIOS MSX2 build (U2).
  - xdent5 / xdent6 read all zeros: these builds have no disk ROM, so the records are skipped.

### CONFIG (machine, not call)

- C1, OUTDLP: on a non-MSX printer (NTMSXP $FF), the JP machines (F900, WSX) send $85 and $FF as a space (A $20, F $30). The VG-8020 and the 8250 send them as they are. This follows the character set. Confirming it needs a Japanese MSX1 reference.
- C2, BDRCLR: the probes never preset it. After boot it is $07 on the JP machines and $04 on the EU ones (xgfx3 / 5 / 5b / 6, every case).
- C3, VDP R#1 bit 7: the probes preset R#1 $80 and every MSX2 reads back $00 after the call, including C-BIOS. The V9938 / V9958 has no 4/16K bit.
- C4, PSG R14 bit 6: $FF on the WSX and $BF elsewhere, C-BIOS 2+ included. This is a port-A input, so it shows in every RDPSG / snapshot and in GTPAD's H.
- C5, b8save and xdent5 / xdent6: the MSX2 machines have a built-in disk interface. Against the VG-8020's DISK row:
  - b8save matches byte for byte.
  - xdent's DPB matches. A, F, L and the interrupt state after GETDPB / a failed DSKCHG differ per interface ROM (the NMS 1200 is not the 8250's FDC).

### TIMING

- PPI port C's low nibble (the keyboard row the timer interrupt left: $0 vs $A, $7) varies across all seven runs. This shows in xsnd1 / xsnd1b, xtap1-5 and xoutdlp-like snapshots.
- WRTPSG R15 after the call (cases 4, 104-106) is irregular. The page does not compare it.
- xchg2: NEWKEY row 10 ($FBEF, "before") and the second changed work-area cell ($FCA3) appear or not per run, the VG-8020 included.

### APPARATUS (fix the probe or the comparison)

- A1, xlin / xlin2a / xlin2b / xlin2c: `@type-at 4` types before the 8250, the WSX and C-BIOS MSX2 EU reach the program. Leading keys are lost, so the rest shifts into the wrong calls and the runs end early (+LEN). xlin2c has no reading at all on the 8250 / WSX.
  - Fix: a KEYREADY handshake as b4input uses (the program sets a cell, the harness then types), or a per-machine `@type-at` well after boot.
  - The F900, the one complete MSX2 reading, matches the VG-8020 exactly.
- A2, m1on2_cmp.py for b8save, xdent5, xdent6: it compares against the VG-8020's NODISK row, which has no disk ROM (records skipped, 0 / $C9). For a disk probe it should take the DISK row.
- A3 (optional), xgfx3 / 5 / 5b / 6: preset R#1 without bit 7, or mask bit 7 on V99x8, so C3 drops out.

### UNKNOWN

- U1, G8: is it the call or the chip? Write R7 := $3F (and $7F) through ports $A0 / $A1 directly on an MSX2 and read it back with $A2:
  - $3F means WRTPSG forces bit 7.
  - $7F would also tell whether bit 6 is forced.
- U2, b8save on C-BIOS MSX2 (NOREAD): either H.STKE is never called after the ROM scan, or INIT is never run. A canary written in INIT and another in the H.STKE handler would tell which.
- U3, G9's E: JP $04 vs EU $07. Same machines, different locale: running BEEP on a 2nd EU MSX2 would tell model from locale.
- U4, G12: how the MSX2 CMASK for X > 255 is derived. Sweep X $0100-$0107 with two CMASK presets.

---

## Per probe

### xgfx1 (FETCHC / STOREC / SETATR / GTASPC / MAPXYC, 28-byte record; gen 77/77/79, cbios 18/18/20)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +291.. iff, cases 23 24 27 28 32 33 36 37 40 41 51 53 70 78 (MAPXYC SCR 3, DI) | 00 | 01 | 01 | 01 | 00 | GEN G2 | R-MX-REGS; C-BIOS keeps MSX1 |
| +349..358, +365..374, +621..630, cases 30 31 56 (SCR 1, 0, 4): A F D H L CLOC CMASK | 06 04 00 1692 F0 | 62 20 64 2662 08 | = | = | = MSX2 | GEN G1 | SCREEN 2 mapping |
| +63D..6A0, +835..860, cases 57 59 60 75 76 (SCR $FF 6 $82 $0A $42): A F H L CLOC CMASK | 06 04 1692 F0 | 32 82/02/16/12 0064 32 | = | = | = MSX2 | GEN G1 | bitmap: CLOC=X, CMASK=Y |
| +240 +278 +8B4 +8D0, cases 20 22 79 80 CMASK (SCR 2, X $0100 / $FFFF) | D5/C5 | FB/4B | FB/4B | FB/4B | 80/01 | GEN G12 | field excluded (XGX) |
| +0FE case 9, +4EE case 45, SETATR F | A9 / 21 | A9 / 21 | A9 / 21 | 89 / 01 | A9 / 21 | GEN G11 (MSX2+) | R-SA-F bit 5 |

### xgfx2 (RIGHTC … TDOWNC, 28-byte record; gen 145, cbios 91)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| iff, 91 cases (+15D … +2441): every SCR 3 case with DI, all six ops | 00 | 01 | 01 | 01 | 00 | GEN G2 | C-BIOS keeps MSX1 |
| TUPC cases 74-78 162 171 180: F, CLOC | 54, $0F07 / $0F27 / $0727 | 45, kept | = | = | = MSX2 | GEN G3 | R-TU-EDGE |
| TDOWNC cases 121 227 229 230 236 238 239 245 247 248: F, CLOC | 45, kept | 54, next block row | = | = | = MSX2 | GEN G4 | R-TD-EDGE |

### xgfx3 (READC / SETC / NSETCX, 128-byte record; gen 89/178/178, cbios 180)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +19 BDRCLR, all 89 cases | 04 | 07 | 04 | 07 | 07/04/07 | CONFIG C2 | not preset, not compared |
| +1B R#1, all 89 cases | 80 | 00 | 00 | 00 | 00 | CONFIG C3 | V99x8 |
| SETC F, cases 31 48 49 50 66 74 78 85 | 80/84/80/04 | = | = | = | A8/AC/88/24 | C-BIOS only | R-SC-AF bits 5/3 |
| NSETCX A F BC DE HL, 25 cases | ref values | = | = | = | differ | C-BIOS only | group XN, not compared |

### xgfx4 (SCALXY; gen 38, cbios 0)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| F, SCR 2 cases 0-13 65 66 | 41/40 | 81/80 | = | = | = MSX2 | GEN G7 | R-SX-AF |
| C, E, F, cases 28-31 59-64 (SCR 0 / 1) | 19 0C / 3F 2F; F 05 00 44 45 01 | 64 32 / FF BF; F 81/80 | = | = | = MSX2 | GEN G6 (+G7) | R-SX-CLIP |

### xgfx5 / xgfx5b (GRPPRT; gen 130/193/193 and 20/30/30, cbios 63 / 10)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| F, every case (63 + 10) | as entry (00/FF) | 93 | 93 | 93 | as entry | GEN G5 | R-GP-KEEP; C-BIOS keeps MSX1 |
| xgfx5 case 22 (SCR 3, MLTCGP $1000): sum4 / CLOC | $22AA / $1167 | $29B7 / $1264 | = | = | = MSX2 | GEN G4' | TDOWNC edge |
| BDRCLR / R#1, every case | 04 / 80 | 07 / 00 | 04 / 00 | 07 / 00 | per machine / 00 | CONFIG C2 / C3 | |

### xgfx6 (PNTINI / SCANR / SCANL; gen 89/178/179, cbios 350/350/351)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +302 case 6 F (PNTINI SCR 3, A $FF) | A9 | A9 | A9 | 89 | A9 | GEN G11 (MSX2+) | R-PI-AF |
| BDRCLR / R#1, all 89 cases | 04 / 80 | 07 / 00 | 04 / 00 | 07 / 00 | per machine / 00 | CONFIG C2 / C3 | |
| SCANR A F BC; SCANL A F BC DE (~260 bytes) | ref | = | = | = | differ | C-BIOS only | groups XR / XL, not compared |

### b5sound (gen 1/1/2, cbios 0/0/1)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +27 R7 after WRTPSG R7 := $3E | 3E | BE | BE | BE | BE | GEN G8 | R-WP-REG (U1) |
| +0E R14 at start | BF | BF | BF | FF | BF | CONFIG C4 | |

### xsnd1 / xsnd1b (sound region; gen 27/24/133 and 23/24/58, cbios 18/14/135 and 18/20/62)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| BEEP xsnd1 73 74, xsnd1b 118-121: A B C E F | 00 00 00 07 44 | 0B 0E D0 04 18 | 0B 0E D0 07 18 | 0B 0E D0 04 18 | = VG | GEN G9 | C-BIOS keeps MSX1 |
| BEEP iff, xsnd1 73, xsnd1b 118-121 (DI on entry) | 01 | 01 | 01 | 00 | 01 | GEN G10 (MSX2+) | R-BP-EI |
| xsnd1 case 104 R7 (WRTPSG 7, $3F) | 3F | BF | BF | BF | BF | GEN G8 | |
| R15, cases 4 104 105 106 | 8F/FF/80/C0 | mixed | mixed | mixed | mixed | TIMING | not compared |
| R14, every case | BF | BF | BF | FF | BF | CONFIG C4 | RDPSG 14 (case 13) too |
| PPI C low nibble, ~25 cases | 0 or A | irregular | | | | TIMING | |

### xtap1-xtap5 (cassette; gen 1-3, cbios 1-40)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| PPI C low nibble after STMOTR / TAPOOF / TAPIOF (xtap1 8 11 12 22 32; xtap2 8 15-18; xtap3 10 12; xtap4 6 8; xtap5 8 14) | 0/7/A | irregular | | | | TIMING | |
| TAPOON / TAPOUT / TAPION / TAPIN A, F, BC, DE, HL (working values) | ref | = | = | = | differ | C-BIOS only | groups XTW / XTO, not compared |

### xinp1 (input region; gen 26/26/124, cbios 193/193/288)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| GTSTCK L, cases 20-36 77-83 | e.g. 52 | 48 | 48 | 48 | 68 | GEN G13 | working value (XIW), ROM pointer |
| BREAKX A, cases 46 49 (CTRL+STOP) | 0D | 14 | 14 | 14 | 00 | GEN G13 | XIA, not compared |
| R14 every case; GTPAD H cases 54 58 64 | BF | BF | BF | FF | BF | CONFIG C4 | |
| GTSTCK / GTTRIG / GTPAD / GTPDL / BREAKX F and working registers | ref | = | = | = | differ | C-BIOS only | not compared |

### xoutdlp (gen 0/4/4, cbios 0/4/4)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +A6 +A7 / +AA +AB: pass 1 (NTMSXP $FF) calls 18, 19 ($85, $FF): A, F | 85 90 / FF BC | 20 30 / DF 98 | = VG | 20 30 / DF 98 | = VG | CONFIG C1 | JP charset; C-BIOS JP lacks it |

### xchg2 (CHGET / CHSNS; gen 23/9/20, cbios 9/27/26)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| "before" ($FBEF, NEWKEY row 10) and nchg / chg1 ($FCA3), all 14 cases | A5/FF, 1/2 | irregular | | | | TIMING | timer interrupt in the window |

### b4input, b7tape: 0 bytes on every machine and on C-BIOS.

### b8save (gen 7+LEN, cbios NOREAD)

| offset / case / field | VG (nodisk) | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| +00 H.PHYD, +01 $F37D, +04 +08 +0D +0F +12 | C9 00 … | F7 C3 … 40 40 40 01 01 | = | = | no reading | CONFIG C5 / APPARATUS A2 | equals the VG-8020's DISK row byte for byte; C-BIOS U2 |

### xlin, xlin2a, xlin2b, xlin2c (PINLIN / INLIN / QINLIN)

| offset / case / field | VG | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| STAGE / BUF / row cells, every call after the first lost key; length | full | = VG | 88 / 34 / 90 / 32 B, keys lost | 146 / 136 / 120 / 32 B, shifted | EU: shifted, short | APPARATUS A1 | `@type-at 4` too early |
| F after every call | 18 | 18 | 18 | 18 | 44 | C-BIOS only | R-L-F |

### xdent5 / xdent6 (GETDPB / DSKCHG, drive A empty; 30-byte record)

| offset / case / field | VG (disk row) | F900 | 8250 | WSX | C-BIOS | class | note |
|---|---|---|---|---|---|---|---|
| (tool's diff is vs the NODISK zeros) | | | | | all 0 | APPARATUS A2 | compare the DISK row |
| xdent5 rec 0 GETDPB: A F L iff | 02 20 29 00 | 01 00 EE 00 | 01 80 FA 00 | 01 00 29 01 | no disk ROM | CONFIG C5 | DPB itself identical |
| DSKCHG fail (xdent5 rec 1, xdent6 both): F L iff | 91 97 00 | 81 96 01 | 91 97 01 | 45 85 01 | no disk ROM | CONFIG C5 | A 02 and carry identical |
