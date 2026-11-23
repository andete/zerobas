# D-MSX1ON2 triage — disk / BDOS group (47 probes)

The three MSX2 references are set against the VG-8020 + NMS 1200 (`disk` row). msx2jp = Sony HB-F900, msx2eu = Philips NMS 8250, msx2p = Panasonic FS-A1WSX. C-BIOS NOREAD is ignored throughout.
Sources: `scratchpad/AE_m1on2/*.out`, the committed `scratchpad/X*_run*.out`, and the probe headers and `*_rules.py` in `probes/bios/spec/`. Clean room: only captures and probe sources were read.
How to read the offsets: `+N` is the byte offset in the capture, and the record is `N div RECLEN`. For the xb* probes the FCB starts at +2, so FCB+14h/15h is the date word and FCB+16h/17h the time word.

## Summary

**BEHAV findings (real kernel / disk-ROM differences):**
1. **Interrupts are left ON on all three MSX2.** This happens after every BDOS call through `$F37D` (xbsys1-3, every case), after PHYDIO (xdsk*, xdskio2p, every case), after DSKCHG (xdent*), after DSKFMT on the 8250 and WSX, and after DSKIO's success path. The VG-8020 + NMS 1200 always returns with interrupts off. `R-BS-DI` fails on all three. (The 8250 part was already noted as UNSTABLE in `xchoice_rules.py` "XH2 N03".)
2. **HB-F900, DSKCHG:** it never answers B=1 "unchanged". Every call re-reads the disk and answers B=0 (or B=$FF when C differs from the disk). This holds at once, at about 1 s and at about 2 s, where the VG, 8250 and WSX answer B=1 (xdent1 #7, xdent2 #1-2, xdent3 #2,4,9,10, xdent4 #1).
3. **HB-F900, GETDPB for media $FF / $FE / $FC / $FD:** it fills the 19-byte DPB buffer with bytes that are not a DPB (there is no media byte at +1). The VG and WSX return a proper DPB. The 8250 refuses and leaves the buffer untouched (already pinned) (xdent1 #3, xdent2 #5-7).
4. **HB-F900, DSKFMT:** choice 0 is ACCEPTED and formats a 1DD `$F8` disk, where VG, 8250 and WSX refuse with A=$0C and carry set. Its successful formats return A=7 instead of A=0 (xdfmt1 #0, #2, #3).
5. **HB-F900, CHOICE:** it returns A=1 and F=$10/$11. The other three keep the A/F they were given (xchoice1 #0-2, xchoice2 #0,1,5).
6. **FS-A1WSX, PHYDIO/DSKIO past the end of a 720 KB disk:** it answers error **$0C** with F=$55, where VG, 8250 and F900 answer $02 (read) or $08 (write). On a refused straddling write it leaves B at the full count (3, not 2). On "read 2 from $FFFF" it answers **success** with 1 KB of zeros, where the VG answers error 2 with B=2 (xdsk1 #3,4,10; xdsk2 #14,15,17; xdsk4 #51,53; xdsk5 #64,68; xdsk6 #71,73; xdskio1/2/2p; xdsk3 #21-23,26,27,29,31).
7. **F900 and WSX, PHYDIO media $FF sector 700:** both READ the sector, A=0. The VG answers error 2 and the 8250 error $0C (xdsk4 #49).
8. **NMS 8250, WRABS:** the FIRST absolute write, to sector 20, is lost. WRABS answers A=0, but RDABS and PHYDIO then read the sector as zeros (xbabs1 #2; xbabs2 #2,#8). Later WRABS calls (sectors 21-22, 1439) do land. The F900 and WSX behave like the VG. **This is new for the 8250:** it was never run on the 8250 before.
9. **All three MSX2 (candidate):** after `SDATE 2025-06-15`, FMAKE stamps **2025-04-15** (xbfile2 #3-6). `SDATE 2026-11-22` stamps correctly (#7, #14).
- The DOS kernels agree everywhere else. FCB, record and block arithmetic, FSIZE, FOPEN extents and the VG/CF-3300 FCLOSE splits all match the VG on all three machines (xbblk1-11, xbrec1-3, xbfile1-4, xrrnd1). xbcon1-3 are byte-identical.

**RTC / date effects (TIMING):**
- Every FMAKE/FCLOSE stamp is the host date and time from the RTC: FCB+14h `0x5D77` (2026-11-23) instead of `0x0821` (1984-01-01), and FCB+16h 07:35-07:38 instead of 0.
- GDATE with no SDATE before it returns today's date and the real weekday (A=1, Monday); the VG returns 1984-01-01, A=0.
- GTIME returns the real time. After `STIME 12:34:56`, GTIME returns 12:34:56 on the MSX2; the VG returns 0:00:00 (it keeps no clock).
- GDATE leaves the RTC's hour and minute in BC and F=$44 (VG: BC=0, F=$40). STIME leaves E=6.
- A rule that pins `0x0821`, a time of 0, or GDATE/GTIME contents breaks. Such rules should compare against GDATE/GTIME, or only assert "the same stamp as GDATE".

**ADDR / DRIVE:**
- **ADDR**, a different number under the same rule:
  - ALLOC IX/IY: VG $F197/$E597, F900 $F196/$E596, WSX $F185/$E585. The 8250 is the same as the VG.
  - DSKRST DE=IX: $F1AC, $F1AB, $F19A.
  - The rules are self-relative (`ix-iy==$0C00`, `>= $E000`, `DE==IX`), so they survive.
- **ROM pointers:** CHOICE's HL ($799B / $79BA / $79AA / $7852) and GETDPB/DSKCHG's HL ($7429 / $74EE / $74FA / $7429) are each ROM's own addresses.
- **DRIVE:**
  - DRVSLT $81 becomes $8B (F900, WSX) or $8F (8250); H.PHYD's slot byte follows. 2 drives everywhere.
  - IY after BDOS is $0314 on all three MSX2 (VG $0110): its high byte is the primary slot.
  - The working registers are the interface's own: MTOFF A=3 (WSX 4); C after a read is VG $32, F900 $01, 8250/WSX $3C; the 8250 also leaves D/E (`$400A`) after a read.

**APPARATUS fixes:**
- **(a) The summary is computed against the wrong reference.** `m1on2_cmp.py` `vg8020()` prefers the `nodisk` row ("nodisk before disk"). So **18 of these probes are compared against the DISKLESS VG-8020**: xchoice1-2, xdent1-4, xdent7, xdfmt1, xdrvtbl, xdsk1-6, xdskio1, xdskio2, xdskio2p. Their `gen=` counts are meaningless.
  - Fix: for a probe with `@disk`, prefer the `disk` row.
  - This triage used the `disk` row.
- (b) **xdfmt2 and xdfmt3 have no MSX2 reading.** Their `AE_m1on2` files (07:14) predate the biosl_run patch that prints the finished side's `CAP`. Delete them and re-run `m1on2_run.py xdfmt2 xdfmt3`. They also have NO committed VG reference, only CF-3300 rows, so a `--row disk` run is needed too.
- (c) **R-BS-SLOT** hard-codes IY per row. Derive it from DRVSLT's primary slot.
- (d) **xdsk3 on msx2eu / msx2jp:** see the xdsk3 section.

**UNKNOWN:**
- **8250 WRABS** (finding 8). Swap the order (WRABS 21 first, then 20), write 20 twice, and add an RDABS before the first write. That shows whether "first write after boot" or "sector 20" is the cause.
- **SDATE month 6 → 4** (finding 9). Run `SDATE y-m-15` then GDATE for m = 1..12, with no FMAKE in between, on each MSX2. That separates the kernel's SDATE from the RTC model.

**Verdict:** the disk spec rules are robust in substance: FCB, record, block, DPB and BPB arithmetic hold on all three MSX2 disk ROMs. They are not robust in the margins:
- the interrupt state (`R-BS-DI`, R-CH-READ);
- date and time pins;
- per-row constants (IY, error codes, interface working registers);
- three F900 entry-point quirks (DSKCHG, GETDPB, DSKFMT) and the WSX's past-end error code, which need per-interface allowances.

---

## Per probe

Columns: off / case / field | VG+NMS1200 | F900 | 8250 | WSX | class | note. A cell of "=" means the same as the VG.
- **RAM** = power-on RAM pattern in a field that is not written. It is not compared (the case-0 FCB of every xb* probe), or it lies past the last record. The pattern is F900 all-$FF, and 8250/WSX `00 FF 00 FF`- or `00 00 FF FF`-like.
- **TIME** = an RTC stamp.

### xbabs1 (66-byte records; WRABS/RDABS)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| +2..+38 of every record | FCB (untouched) | RAM | RAM | RAM | RAM | RAM | not set by the probe |
| +171..+183, +186..+189 | #2 RDABS 20: DTA 0-12, spots +383.. | $41.. | = | **00** | = | BEHAV/UNKNOWN | the 8250 reads sector 20 as zeros after a WRABS that answered A=0 |

### xbabs2 (74-byte records; + PHYDIO read-back, sums)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| FCB of every record | FCB | RAM | | | | RAM | |
| #2 (+187..), #8 (+631..) | DTA, spots, sum1/sum3 | case-1 bytes, sum $C4FF | = | **00 / 0** | = | BEHAV | PHYDIO (#2) and RDABS (#8) both see an unwritten sector 20 on the 8250. Sectors 21-22 (#5,#6) and 1439 (#9) are fine |

### xbblk1 (54-byte records)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| +2..+38 | #0 FCB (not output) | FF/00 | FF | 00/FF | 00/FF | RAM | |
| n·54+22..+25, n=1..10 | FCB date/time | 0821 / 0000 | 5D77 / 3C6E.. | 5D77 / 3C6F.. | 5D77 / 3C70.. | TIME | |
| #6 / #8 DTA | bytes 128..199 of B.TXT | RAM | | | | RAM | already UNSTABLE (WRBLK took RAM past the fill) |
| +702,+703 | past the 13 records | | | | | RAM | |

### xbblk2 (58) · xbblk3 (62) · xbblk4 (64) · xbblk5-10 (66) · xrrnd1 (66)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| #0 FCB | not output | RAM | | | | RAM | |
| every case with an FCB: +22..+25 of the record | FCB date / time | 0821 / 0 | today / 07:35-07:38 | " | " | TIME | 7-9 and xrrnd1 show only the time (the dates were already tagged) |
| xbblk2 spot +512 (n·58+57) | DTA+512, past the 512-byte fill | FF | FF | 00 | 00 | RAM | the rules already check it "against the residue" |
| xbblk2 +929..+941 | past the records | | | | 00 | RAM | |
- No A, F, HL, size, cluster or DTA difference in any of these probes.
- The VG/CF-3300 FCLOSE splits (XBBLK2 #9, XBBLK4 #6/#14) side with the VG on all three machines.

### xbblk11 (66)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| dates/times | | | | | | TIME | |
| +780, +783 | #11 RDBLKV8 spots 0, 3 | FF | FF | FF | 00 | RAM (residue) | already UNSTABLE `XKB 11`: the record sector's leftover bytes |
- The FCLOSE #9 split (VG A=0 / CF-3300 A=$FF) sides with the VG on all three.

### xbcon1 · xbcon2 · xbcon3
Byte-identical on all three (`+LEN` = padding past the capture end: zeros and one RAM byte).

### xbfile1-4 (52-byte records)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| #0 FCB | | RAM | | | | RAM | |
| n·52+22..+25 | FCB date/time | 0821/0 | today | today | today | TIME | |
| xbfile2 +178/+179 (#3-#6) | date after `SDATE 2025-06-15` | **5ACF (2025-06-15)** | **5A8F (2025-04-15)** | 5A8F | 5A8F | BEHAV? / UNKNOWN | the month is stored as 4. #7/#14 (`SDATE 2026-11-22`) are correct |
| tails (xbfile2 +781, xbfile3 +833.., xbfile4 +677..) | past the records | | | | | RAM | |

### xbrec1-3 (52)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| dates/times | | | | | | TIME | |
| xbrec1 +715..+727 | #13 RDRND of a never-written record: DTA | residue | = | = | FF/00 differ | RAM | already UNSTABLE `XR 13` |
| xbrec2 +611..+623 | #11 RDSEQ, never-written record: DTA | residue | = | = | differ | RAM | already UNSTABLE `XR2 11` |
| tails | | | | | | RAM | |

### xbsys1 · xbsys2 · xbsys3 (15 / 23-byte records: A F B C D E H L iff IX IY DTA)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| every +8 | iff after | 0 | **1** | **1** | **1** | BEHAV | BDOS returns with interrupts ON. `R-BS-DI` fails |
| every +11/+12 | IY | $0110 | $0314 | $0314 | $0314 | DRIVE | slot leftover. `R-BS-SLOT` must derive it |
| xbsys1 #5, xbsys2 #10/#11 | ALLOC IX / IY | F197/E597 | F196/E596 | = | F185/E585 | ADDR | `ix-iy=$0C00` holds. atix/atiy (DPB, FAT bytes) are identical |
| xbsys1 #12, xbsys2 #14, xbsys3 #13 | DSKRST DE, IX | F1AC | F1AB | = | F19A | ADDR | `DE==IX` holds |
| xbsys1 #6 | GDATE, no SDATE yet | 1984-01-01, A=0 | 2026-11-23, A=1 | " | " | TIME | RTC |
| GDATE after SDATE (xbsys1 #8; xbsys2 #1,#3; xbsys3 #1,3,5,7,10) | F, BC | F=$40, BC=0 | F=$44, BC=$0724 | " | " | TIME | BC = the RTC's hour:minute (07:36). The date itself is the same |
| xbsys1 #9 | GTIME | 0:00:00 | 07:36:20.. | " | " | TIME | |
| xbsys1 #11 | GTIME after `STIME 12:34:56` | **0:00:00** | 12:34:56 | " | " | TIME | the VG keeps no clock |
| STIME (xbsys1 #10, xbsys3 #11) | E | 0 | 6 | 6 | 6 | BEHAV (open register) | |
- The SDATE / STIME refusals (month 13, day 0/32, hour 24/25, minute 60, second 60) are byte-identical, apart from iff/IY.

### xchoice1 (30) · xchoice2 (41)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| CHOICE A, F (x1 #0-2, x2 #0,1,5) | kept | 00/00, 5A/D7 | **01/10, 01/11** | kept | kept | BEHAV | |
| CHOICE HL | ROM pointer | $799B | $79BA | $79AA | $7852 | DRIVE (ROM address) | the rule only needs "HL in the disk ROM" |
| MTOFF A F BC HL (x1 #3-5, x2 #2,#4) | | 03 28 0022 F1C1 | 03, F/BC/HL kept | = F900 | **04**, kept | DRIVE (interface regs) | the 8250 values were already pinned |
| x2 #3 DSKIO read: C / DE / iff | | $32 / 0 / 0 | $01 / 0 / **1** | $3C / $400A / 1 | $3C / 0 / 1 | DRIVE + BEHAV(iff) | the boot-sector bytes are identical |

### xdent1-4, xdent7 (30-byte records: A F B C D E H L iff buf21)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| GETDPB F9/F8/FA: A, F, L | working regs, ROM pointer | A=2/0/4, HL=$7429 | A=1/0/2, HL=$74EE | A=1/0/2, HL=$74FA | A=1/0/2, HL=$7429 | DRIVE | the DPBs are byte-identical |
| GETDPB $FF/$FE/$FC/$FD (x1 #3, x2 #5-7): buffer | DPB | proper DPB | **19 bytes that are not a DPB**, A=7/6/4/5 | refused, buffer untouched | proper DPB | BEHAV (F900) | the 8250 was already pinned |
| DSKCHG repeat within the window (x1 #7, x2 #1,#2, x3 #2,#4,#9,#10, x4 #1) | B | 1 | **0** (re-read; x4 #1 → $FF) | 1 | 1 | BEHAV (F900) | |
| DSKCHG F | | $22 / $02 | | $2A / $0A | $2A / $0A | noise | flag bits 3 and 5 |
| DSKCHG and GETDPB (WSX) iff | | 0 | 1 | 1 | 1 | BEHAV | |
| MTOFF (x1 #0, x3 #8, x4 #3) | | 03 28 0022 F1C1 | 03, kept | 03, kept | 04, kept | DRIVE | |
| xdent7 | DSKCHG C=$FA | B=$FF | = | = | = | — | only HL and iff differ |

### xdfmt1 (38-byte records)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| #0 choice 0 | A, F, BPB | 0C, carry, disk F9 | **07, no carry, disk now F8** | 0C | 0C | BEHAV (F900) | the F900 formats choice 0 as 1DD |
| #1 choice 5 | | 0C, refused | 0C | 0C | 0C | — | F, B and E are interface values |
| #2 / #3 choice 1 / 2 | A after a format, BPB | 00, F8 / F9 | **07**, F8 / F9 | 00 | 00 | BEHAV (A) | the BPB fields and FAT bytes are identical |
| #4, #5 choice 3 / 4 | | VG record empty | 0C | 0C | 0C | APPARATUS | the committed VG capture ends inside #3 |
| iff | | 0 | 1 on #0/#2/#3 | 1 | 1 on success | BEHAV | |

### xdfmt2 · xdfmt3
No MSX2 reading was saved (APPARATUS (b)), and there is no VG reference: re-run both.

### xdrvtbl
| off | field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| +1 | DRVTBL slot | $81 | $8B | $8F | $8B | DRIVE | 2 drives everywhere |
| +13 | H.PHYD slot byte | $81 | $8B | $8F | $8B | DRIVE | follows DRVSLT, so the rule is self-relative if written so |

### xdsk1 · xdsk2 · xdsk4 · xdsk5 · xdsk6 (PHYDIO, 14-byte records: A F B C D E H L iff sum +0 +512 pad)
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| every +8 | iff | 0 | 1 | 1 | 1 | BEHAV | |
| every success: C (D E) | working regs | $32 | $01 | $3C ($40xx/$0A) | $3C | DRIVE | already UNSTABLE on VG/CF |
| past-end / straddle (x1 #3,4,10; x2 #14,15,17; x4 #51,53; x5 #64,68; x6 #71) | A, F (B) | 02/41 (08/11 write) | = | = | **0C/55**, B=3 on #64 | BEHAV (WSX) | |
| x6 #73 read 2 from $FFFF | | A=02, B=2 | = | = | **A=0, 1 KB of zeros** | BEHAV (WSX) | |
| x4 #49 read 700, media $FF | | A=02 | **A=0, zero sector** | 0C | **A=0** | BEHAV | |
| x2 #12, x4 #41, x5 #63, x6 #70 (media $FF reads) | | read OK | = | refused 0C | = | DRIVE (8250) | already pinned in `XDSK*_nms8250.out` |
| x2 #19, x4 #44, x6 #72 | E on the error path | entry F | = | interface values | = | DRIVE (8250) | pinned |
- The 8250 readings are byte-identical to the committed `XDSK{1,2,4,5,6}_nms8250.out`, so they reproduce.

### xdsk3 — no reading on msx2eu / msx2jp
- The WSX read; its differences are xdsk1's classes (#21-23, #26-27, #29, #31: error $0C, B=2 on #23; iff=1).
- On the 8250, DONE stayed at its power-on value (0, and F900 255).
- **The source has nothing machine-specific.** The frame and cases are the same as xdsk1, 2, 4, 5 and 6, which all completed on these machines. The header itself records that one PHYDIO case did not return on the VG (a B=0 write), so this is how the probe can hang.
- **The 8250 completed this exact probe on 2026-11-22.** The probe file has not changed since, apart from the licence comment. That run, `XDSK3_nms8250.out` and `_b`, has 17 records and JIFFY about $017E at the dump.
- So this is a **run-to-run hang inside one PHYDIO error case.** The candidates are #26/#29 (write beyond with ei / F=$FF) and #30/#31 (sector $FFFE / $F000: the 8250 wraps 1440 to 0, see xdskio2 #0). It is **not** a probe that does not suit the machine.
- **APPARATUS fix:** biosl_run should print the CAP and a per-case progress cell even when DONE is never set. Re-run `xdsk3 --row msx2eu` twice and `--row msx2jp`. One hypothesis to test: persistent openMSX RTC/SRAM state written by earlier m1on2 probes.

### xdskio1 · xdskio2 · xdskio2p
| off | case / field | VG | F900 | 8250 | WSX | class | note |
|---|---|---|---|---|---|---|---|
| iff | | 0 | 1, but **0 on DSKIO's error paths** (x1 #3,4,10; x2 #0,4) | 1 | 1 | BEHAV | |
| C (D E) | | $32 | $01 | $3C ($400A) | $3C | DRIVE | |
| past end (x1 #3,4,10; x2/x2p #0,#4) | A/F | 02/41 | = | = (x2 #0: **reads 0+1 OK**, already pinned) | **0C/55** | BEHAV (WSX) | |
| HL after multi-sector | | buffer + $200 per sector | = | = | = | — | `R-` holds |
