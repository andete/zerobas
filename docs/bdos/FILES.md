<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: BSD-2-Clause
-->

# The BDOS's FCB directory functions through `$F37D`

> **Spec:** FINAL (2026-11-22) for the directory functions: review pass 3's findings on THEM were answered
> by round 4 with no new behaviour (FOPEN's extents and clusters, FCLOSE's flags, FMAKE's first free entry);
> its WRSEQ findings belong to the record functions' page (§7: another call's findings move), now [A]
> here. Four measured rounds on two references (scratchpad/BFILE_review1.md to BFILE_review3.md).
> One page for the directory side of the FCB functions sharing one probe: FMAKE ($16), FCLOSE ($10),
> FOPEN ($0F), SFIRST ($11), SNEXT ($12), FSIZE ($23), FREN ($17), FDEL ($13). The record functions
> (sequential, random, block reads and writes) are not on it.

## Summary

Through the disk ROM's BDOS entry at $F37D (C the function, DE the FCB), on the empty disk in drive A:

- **FMAKE** creates a file (or makes an existing one again) and writes the FCB's +14 .. +31: record
  size and file size 0, the current date's word at +20, time 0, $40 at +24, the new entry's index in
  the directory at +25; it leaves the extent (+12 / +13) and +32 .. +36 as they were. **FCLOSE** answers
  0 and leaves the FCB; **FOPEN** finds the file and fills the same FCB. A new file takes the FIRST free
  directory entry.
- The **extent** byte (+12) counts: at $FF WRSEQ answers 1 and writes nothing, and FOPEN answers $FF
  for an extent the file does not reach (e x 16384 past the size). **FOPEN** fills the records left in
  the extent (+15, at most 128), the size, and the first cluster in +26 and +28 (the current cluster);
  **FSIZE** puts the record count in +33 .. +35. (WRSEQ, used here only to give a file data, writes at
  the FCB's current record: the record functions' page.)
- **SFIRST** finds the first matching entry and puts it in the DTA (drive 1, name, attribute);
  **SNEXT** answers $FF when there is no more.
- **FSIZE** sets the random record to the file's size in records (0 here).
- **FREN** renames to the name at FCB +17; **FDEL** deletes.
- A function that finds nothing (FOPEN, SFIRST, SNEXT, FDEL, FREN, FSIZE of a missing file) answers A $FF
  with the carry SET, and A 0 comes with the carry clear -- except FREN refusing an existing name and
  FOPEN refusing an extent (A $FF, carry clear) and FCLOSE after a failed write (A 0, carry set).
  SETDTA answers $08.

zerobas writes round 1's every FCB and DTA byte the same (its SETDTA's A differs). It leaves the carry
clear on SNEXT's, SFIRST's and FDEL's "not found" and sets it on FREN's refusal (D-BDOSCARRY), leaves
FMAKE's record size (+14 / +15) as it was (D-FMAKERS), writes sequentially at its own
position, ignoring the extent and the current record (D-FCBEXTENT),
and its other flags differ (D-F37DREGS). It stamps the date SDATE set (since D-F37DSETDATE, 2026-11-22).

## The specification

References: the Philips VG-8020 with an NMS 1200 disk interface (row `D`) AND the National CF-3300
(row `C`); every rule holds on both. Ours: zerobas's disk build.

**Evidence.** **[XB rNN]**: case `NN` on row `r` of the XBFILE1 probe -- run 1 for row D
([`scratchpad/XBFILE1_run1.out`](../../scratchpad/XBFILE1_run1.out), `--row disk`), run 2 for row C
([`scratchpad/XBFILE1_run2.out`](../../scratchpad/XBFILE1_run2.out), `--row cf3300`).
**[XB2 rNN]**: XBFILE2 the same way, runs 1 (row D) and 2 (row C)
([`XBFILE2_run1.out`](../../scratchpad/XBFILE2_run1.out), [`XBFILE2_run2.out`](../../scratchpad/XBFILE2_run2.out),
`probes/bios/spec/xbfile2.asm`): SETDTA $9300 / $A800, SDATE 2025-06-15, FMAKE TEST.TXT over an FCB
pre-filled with $FF at +12 .. +36, WRSEQ, FCLOSE, SDATE 2026-11-22, FMAKE SECOND.TXT pre-filled, FOPEN
TEST.TXT pre-filled, FSIZE TEST.TXT, SFIRST ???????????, SNEXT twice, FREN SECOND.TXT onto TEST.TXT, FMAKE
TEST.TXT again. **[XB3 rNN]**: XBFILE3 the same way ([`XBFILE3_run1.out`](../../scratchpad/XBFILE3_run1.out),
[`XBFILE3_run2.out`](../../scratchpad/XBFILE3_run2.out), `probes/bios/spec/xbfile3.asm`): WRSEQ with only the
extent $FF, with only the current record $FF, with +24 $41 / +32 $85 (each on a fresh FMAKE, then
FCLOSE); FOPEN with +12 $FF and with +12 1; FOPEN and FSIZE (over $FF) of the 6-record file; FDEL, FREN
and FSIZE of a missing file (no SETDTA in that probe: its DTA checks read $A800, which is NOT the DTA
there, so they are vacuous for XB3). **[XB4 rNN]**: XBFILE4 the same way
([`XBFILE4_run1.out`](../../scratchpad/XBFILE4_run1.out), [`XBFILE4_run2.out`](../../scratchpad/XBFILE4_run2.out),
`probes/bios/spec/xbfile4.asm`): SETDTA, a 16384-byte file opened at extents 0 and 1, FCLOSE with +12 $FF
and no write, FMAKE after an entry is freed. **[XB5 rNN]**: XBFILE5 the same way
([`XBFILE5_run1.out`](../../scratchpad/XBFILE5_run1.out), [`XBFILE5_run2.out`](../../scratchpad/XBFILE5_run2.out),
`probes/bios/spec/xbfile5.asm`; D-COPYDATE, 2026-11-25): WHICH date FCLOSE writes -- a date and time poked into
the FCB after a write, one poked before it, and one poked before an FCLOSE with nothing written, each read back
by FOPEN. `probes/bios/spec/xbfile1.asm` documents the frame (XBSYS1's H.STKE cartridge; drive A
the generated empty 720 KB disk), the cases in order -- SETDTA $A800, FMAKE TEST.TXT, FCLOSE, SFIRST ????????.TXT,
SNEXT, FOPEN TEST.TXT, FSIZE TEST.TXT, FREN TEST.TXT -> NEW.TXT, FOPEN TEST.TXT, FDEL NEW.TXT, SFIRST
????????.??? -- the FCB set-up (a named case clears the FCB and writes drive 0 and the name; FREN also the new name
at +17, +16 0) and the 52-byte record: A, F, the FCB, the DTA's first 13 bytes (the DTA is refilled with $E5 before each case).
Case 0 (XBFILE2: cases 0-2) runs on the FCB as start-up left it, so its FCB is not read -- left out
of the record set, not declared. Every rule also checks the DTA: unless it says otherwise, a call leaves
it alone.

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xbfile_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xbfile_rules.py --write` -->

**19 rules; 19 hold on the reference. Of the 6140 recorded outputs (each case's cursor, cells, A, table entries ...): 5454 read by a rule's check, 0 declared NOT evidence (below), 686 unread.**

#### 1. The FCB directory functions through $F37D

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-BF-MAKE** FMAKE ($16) of TEST.TXT on the empty disk, over a CLEARED FCB, answers A 0 and leaves it: +12 .. +19 0 (+12 / +13 as entered, R-BF-MAKE2; record size and file size written 0), the DATE word at +20 ($0821: 1984-01-01, the date after start-up), the time 0, $40 at +24, the rest 0. FCLOSE ($10) answers A 0 and leaves the FCB; FOPEN ($0F) of the closed file answers A 0 with the same FCB. | 6 | ✓ | ✓ |
| **R-BF-SEARCH** SFIRST ($11) of ????????.TXT answers A 0 and puts the entry in the DTA: drive 1 (A:), the name, attribute 0; the FCB stays as set up. SNEXT ($12) then answers A $FF (no more) and leaves the DTA. After the file was renamed and deleted (a deleted entry left), SFIRST of ????????.??? answers A $FF and leaves the DTA. | 6 | ✓ | ✓ |
| **R-BF-SIZE** FSIZE ($23) of the empty TEST.TXT answers A 0 with the random record +33 .. +35 = 0 (the FCB otherwise as set up). | 2 | ✓ | ✓ |
| **R-BF-REN** FREN ($17) TEST.TXT -> NEW.TXT (the new name at +17) answers A 0 and leaves the FCB; FOPEN of TEST.TXT then answers A $FF; FDEL ($13) of NEW.TXT answers A 0. | 6 | ✓ | ✓ |
| **R-BF-CARRY** The carry is SET on a NOT-FOUND answer (A $FF from SNEXT with no more, FOPEN of a missing file, SFIRST finding nothing) and clear on A 0 -- but FREN refusing a name that exists answers A $FF with the carry CLEAR (XB2 13): it marks not-found, not every A $FF. (The extent-$FF cases are R-BF-EXTENT's.) | 36 | ✓ | ✗ 8: XB D04, XB D10, XB C04, XB C10, XB2 D12, XB2 D13 … (+2) |
| **R-BF-MAKE2** FMAKE writes the FCB's +14 .. +31 -- record size 0, file size 0, the DATE word of the current date ($5ACF after SDATE 2025-06-15, $5D76 after 2026-11-22), time 0, $40 at +24, the new entry's INDEX in the directory at +25 (0, then 1 for the second file), +26 .. +31 0 -- and leaves +12 / +13 and +32 .. +36 as they were ($FF here). FMAKE of a name that exists answers A 0 and makes it again (today's date). | 6 | ✓ | ✗ 4: XB2 D03, XB2 D07, XB2 C03, XB2 C07 |
| **R-BF-EXTENT** The FCB's EXTENT byte (+12) counts: left $FF by FMAKE, it makes WRSEQ ($15) answer A 1 and write nothing (+24 then 0, +32 $7F; FCLOSE answers A 0 with that FCB; FSIZE of the file then reads 0 records), and FOPEN with +12 $FF answers A $FF (no extent 255), writing +14 0 and leaving the rest. (Round 3 shows the extent ALONE does it: R-BF-SEQ3.) The flags there: WRSEQ F $44, FCLOSE F $93 (the carry SET with A 0), FOPEN F $82 (the carry CLEAR with A $FF); an SDATE between them leaves the FCB. | 10 | ✓ | ✗ 10: XB2 D04, XB2 D05, XB2 D06, XB2 D08, XB2 D09, XB2 C04 … (+4) |
| **R-BF-SEARCH2** With two files, SFIRST ??????????? finds TEST.TXT (the first entry), SNEXT SECOND.TXT, the next SNEXT A $FF. | 6 | ✓ | ✓ |
| **R-BF-RENEX** FREN onto a name that exists answers A $FF (carry clear, R-BF-CARRY) and leaves the FCB. | 2 | ✓ | ✓ |
| **R-BF-SETDTA2** SETDTA answers A $08 whatever DE is ($9300 and $A800), F 0; SDATE of a valid date answers A 0 (as on the system functions' page). | 6 | ✓ | ✗ 4: XB2 D00, XB2 D01, XB2 C00, XB2 C01 |
| **R-BF-SEQ3** Round 3 separates round 2's cause. With ONLY the extent +12 $FF, WRSEQ answers A 1 and writes nothing (+24's bit 6 cleared; FCLOSE then F $93). With only the current record +32 $FF it WRITES: at record (+32 AND $7F) = 127 of the extent -- the file becomes 16384 bytes, the clusters 2 .. 17 -- then the extent advances (+12 1) and +32 is 0; with +24 $41 and +32 $85 it writes record 5 (768 bytes, cluster 18), +32 becomes 6 and +24 $01: WRSEQ CLEARS bit 6 of +24, it does not write it. FCLOSE answers A 0 and leaves the FCB (F $42). | 18 | ✓ | ✗ 12: XB3 D01, XB3 D02, XB3 D04, XB3 D05, XB3 D07, XB3 D08 … (+6) |
| **R-BF-OPEN3** FOPEN asks for the extent in +12: with +12 $FF, or 1 on a file of one extent, it answers A $FF (F $82 / $42 -- the carry CLEAR) and leaves the FCB. FOPEN of THREE.TXT (6 records) fills +15 (the records in the extent) 6, the size 768, the date, $40, its index 2, the clusters 18 / 18, the rest 0. FSIZE over $FF at +33 .. +36 writes the record count 6 to +33 .. +35 and leaves +36. | 8 | ✓ | ✗ 8: XB3 D09, XB3 D10, XB3 D11, XB3 D12, XB3 C09, XB3 C10 … (+2) |
| **R-BF-MISS** FDEL, FREN (the source) and FSIZE of a MISSING file answer A $FF with the carry SET and leave the FCB. | 6 | ✓ | ✗ 2: XB3 D13, XB3 C13 |
| **R-BF-OPEN4** FOPEN opens extent e when e x 16384 does not pass the size (a 16384-byte file opens at extent 0 AND 1; a 0-byte file refuses 1, R-BF-OPEN3), and +15 is the records left in that extent, at most 128 ($80 at extent 0, 0 at extent 1); +26 and +28 both the file's FIRST cluster (2) -- +28 the current cluster, not the last -- +30 0. | 4 | ✓ | ✗ 4: XB4 D06, XB4 D07, XB4 C06, XB4 C07 |
| **R-BF-INDEX** FMAKE takes the FIRST free directory entry: after FDEL of entry 0 a new name gets index 0, the next new one 2; making the existing BBB.TXT again keeps its 1. FDEL answers A 0 and leaves the FCB. | 12 | ✓ | ✓ |
| **R-BF-CLOSE4** FCLOSE answers A 0 and leaves the FCB; its F is $10 after FMAKE with no write -- also with +12 poked to $FF (so round 2-3's $93 belongs to the FAILED write, not the extent) -- and $42 after a write. The WRSEQ between them (the setup that gives BBB.TXT its 16384 bytes) writes as R-BF-SEQ3 states. | 8 | ✓ | ✗ 8: XB4 D02, XB4 D04, XB4 D05, XB4 D12, XB4 C02, XB4 C04 … (+2) |
| **R-BF-CLOSEDATE** FCLOSE ($10) of a file WRITTEN since FMAKE / FOPEN writes the FCB's own date (+20) and time (+22) into the directory entry: poked after the write as 1990-05-05 12:34:56 ($14A5 / $645C), they are what FOPEN reads back. A write stamps the current date into the FCB first -- WRSEQ over that poked date leaves +20 $0821 (1984-01-01) and the time 0, and the entry gets those. FCLOSE with nothing written since FOPEN writes no date: 1999-12-31 23:59:58 ($279F / $BF7D) poked there stays in the FCB and the entry keeps its own. FMAKE stamps $0821 too (R-BF-MAKE); every call answers A 0. (So COMMAND.COM's COPY, which sets the source's date in the FCB after its last write, keeps it.) | 20 | ✓ | ✓ |
| **R-BF-SETDTA4** SETDTA $A800 again answers A $08, F 0 (XBFILE4 sets it, so its DTA checks are real). | 2 | ✓ | ✗ 2: XB4 D00, XB4 C00 |
| **R-BF-WORK** F, and SETDTA's A, are the same on both references in every case (mostly $44 on A 0, $45 on a not-found; but $10 / $42 / $93 after FCLOSE, $42 after FDEL, $44 on FREN's refusal, $82 / $42 on FOPEN's extent refusals; SETDTA A $08, F 0); SETDTA leaves the DTA alone. | 132 | ✓ | ✗ 52: XB D00, XB D02, XB D04, XB D09, XB D10, XB C00 … (+46) |

Measured but read by no rule's check: XB5 D00, XB5 C00 (2): dta[0], dta[10], dta[11], dta[12], dta[1], dta[2], dta[3], dta[4], dta[5], dta[6], dta[7], dta[8], dta[9]; XB5 D01, XB5 D02, XB5 D03 … (+17) (20): fcb[0], fcb[10], fcb[11], fcb[12], fcb[13], fcb[14], fcb[15], fcb[16], fcb[17], fcb[18], fcb[19], fcb[1], fcb[24], fcb[25], fcb[26], fcb[27], fcb[28], fcb[29], fcb[2], fcb[30], fcb[31], fcb[32], fcb[33], fcb[34], fcb[35], fcb[36], fcb[3], fcb[4], fcb[5], fcb[6], fcb[7], fcb[8], fcb[9]

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-BDOSCARRY** (SNEXT, SFIRST and FDEL answer "not found" -- A $FF -- with the carry clear; FREN's refusal sets it) | R-BF-CARRY, R-BF-MISS, R-BF-WORK |
| **D-FMAKERS** (FMAKE leaves +14 / +15 -- the record size -- as entered) | R-BF-MAKE2 |
| **D-FCBEXTENT** (WRSEQ writes at its own position, record 0, ignoring the extent and the current record; FOPEN opens any extent; sizes and clusters follow from that) | R-BF-EXTENT, R-BF-SEQ3, R-BF-OPEN3, R-BF-OPEN4, R-BF-CLOSE4 |
| **D-F37DREGS** (other working A / F: SETDTA's A and F, F after FCLOSE / FDEL) | R-BF-WORK, R-BF-SETDTA2, R-BF-SETDTA4 |

## On later generations (MSX2, MSX2+)

Measured 2026-11-23 on the HB-F900 and NMS 8250 (MSX2) and the FS-A1WSX (MSX2+), each with its own built-in drive and disk ROM: the page's probes through `probes/bios/biosl_run.py --row msx2all` ([scratchpad/AE_m1on2/xbfile1.out](../../scratchpad/AE_m1on2/xbfile1.out), [scratchpad/AE_m1on2/xbfile2.out](../../scratchpad/AE_m1on2/xbfile2.out), [scratchpad/AE_m1on2/xbfile3.out](../../scratchpad/AE_m1on2/xbfile3.out), [scratchpad/AE_m1on2/xbfile4.out](../../scratchpad/AE_m1on2/xbfile4.out)); triage [scratchpad/m1on2-triage-disk.md](../../scratchpad/m1on2-triage-disk.md). Each rule's check was run on each machine's capture in the reference's place.

| rule | HB-F900 | NMS 8250 | FS-A1WSX |
|---|---|---|---|
| R-BF-MAKE2, R-BF-EXTENT | after SDATE 2025-06-15 FMAKE stamps $5A8F, 2025-**04**-15 (XB2 03-06); after SDATE 2026-11-22 the date is right (XB2 07, 14) [M] | the same [M] | the same [M] |
| every other rule | holds [M] | holds [M] | holds [M] |

With a clock chip: every FCB's date and time words are the clock's (that day, $5D77, and the time of day; after SDATE the set date, with the clock's time), not $0821 (1984-01-01) and 0, on all three [M]; with the stamps set aside these rules hold, and as written they do not: R-BF-MAKE, R-BF-MAKE2 (its time words), R-BF-SEQ3, R-BF-OPEN3, R-BF-OPEN4, R-BF-INDEX, R-BF-CLOSE4.

**[A]** Whether the month is lost by SDATE or by the stamp: SDATE y-m-15, then GDATE, for m = 1 .. 12 with no FMAKE between, on each machine. (SYSTEM.md's SDATE / GDATE round trips -- 2026-11-22, 2026-12-01, 2026-01-01 -- hold on all three.)

**On the turbo R** (FS-A1GT / FS-A1ST, measured 2026-11-23, D-TRSPEC): every call result (A, F, HL, the FCB fields, the DTA bytes a call reads or writes) is the FS-A1WSX's, on both models: the FS-A1WSX column above holds, FMAKE's $5A8F after SDATE 2025-06-15 included. The bytes that differ are not the calls': each FCB's time word (the clock chip's time of day, which follows the host clock) and power-on RAM in fields no case writes [M] ([AE_trall/xbfile1.out](../../scratchpad/AE_trall/xbfile1.out), [AE_trall/xbfile2.out](../../scratchpad/AE_trall/xbfile2.out), [AE_trall/xbfile3.out](../../scratchpad/AE_trall/xbfile3.out), [AE_trall/xbfile4.out](../../scratchpad/AE_trall/xbfile4.out); overview: [turbor/remeasured.md](../turbor/remeasured.md)).

## Open (not measured)

- **[A]** FOPEN / FSIZE / FREN / FDEL / SFIRST over a PRE-FILLED FCB (only FMAKE and FSIZE's +33 .. +36
  were); FMAKE over a file holding data (truncation, its clusters); FSIZE's record-size dependence (+14);
  STIME and the time field (FCLOSE's copy of +22 is measured: R-BF-CLOSEDATE); a written FCLOSE after SDATE /
  STIME changed the clock between the write and the close; FDEL / FMAKE / FOPEN / FREN with
  wildcards, an explicit or invalid drive byte (+0), SNEXT without SFIRST or after the FCB changes,
  FCLOSE of a file never opened; a full directory; a write-protected disk; drive B;
  attributes; the DTA beyond its first 13 bytes; the directory and FAT on the disk after each call.
- **[A]** WRSEQ's own contract (the record functions' page, not this one): where the data lands (records
  0 .. 126 of a CR-$FF write), +30 / +31, +15 not updated, +13 alone, +12 1 / 2 (a position past the disk
  vs the extent rule), +24 beyond $40 / $41 (bit 6 cleared or a mask), a full data area.
- **[A]** FOPEN of a file of three extents or more (at a middle extent); FMAKE of an existing name when a
  free entry precedes it (reuse in place vs first free: round 4's BBB.TXT cannot tell); FSIZE of a size
  not a multiple of 128 (rounding); FREN's +16.
- **[A]** The record functions (SEQRD / SEQWR / RDRND / WRRND / RDBLK / WRBLK / WRZER / SETRND):
  compared under MSX-DOS by bdos-acceptance and through $F37D by bdosf37d-acceptance, not specified here.
- **[A]** The same functions under MSX-DOS ($0005); the registers other than A and F.

## Related pages

[The system functions](SYSTEM.md); [CONOUT](CONOUT.md), [DIRIO](DIRIO.md), [STROUT](STROUT.md); [the disk
concept page](../concepts/disk.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).
