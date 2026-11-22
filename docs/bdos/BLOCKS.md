<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The BDOS's block functions through `$F37D`

> **Spec:** DRAFT 3 (2026-11-22), four measured rounds on two references, review passes 1 and 2 answered
> ([`scratchpad/BBLK_review1.md`](../../scratchpad/BBLK_review1.md),
> [`scratchpad/BBLK_review2.md`](../../scratchpad/BBLK_review2.md)).
> One page for WRBLK ($26), RDBLK ($27), WRZER ($28) and RDABS ($2F), sharing one probe.

## Summary

Through the disk ROM's BDOS entry at $F37D (C the function, DE the FCB, HL the record count):

- **WRBLK** / **RDBLK** write / read HL records of the FCB's record size (+14 / +15) at the random record
  (+33 ..), advance it, and answer the records transferred in HL; a read that runs into the end of the
  file answers A 1 with HL the records read; a PARTIAL last record counts as read (HL includes it, and A
  is 0 if that makes HL what was asked), and its tail past the file is ZEROS in the DTA, whatever older
  bytes the sector still holds. FOPEN leaves +14 0 and +15 the file's records of 128, and the block
  functions read +14 / +15 as one word: a block read straight after FOPEN uses records of +15 x 256 bytes.
- **WRBLK** sets the size to the larger of the old size and where it stopped; with HL 0 it sets the size
  to RR x the record size, shrinking or growing, and writes nothing.
- **FSIZE** ignores the record size: it answers records of 128 (rounded up) and clears +14, keeping
  +15; it reads the directory, so a size not yet closed is not counted.
- **WRZER** writes the DTA's 128-byte record at the random record whatever the record size and HL,
  zero-fills the records between the old end and it, never shrinks the file, and clears +14 (keeping
  +15); **RDABS** reads absolute sectors (512 bytes each) into the DTA.

zerobas transfers the same bytes and records; it answers A 1 for a partial last record even when HL is
what was asked (D-RDBLKPART), leaves +14 in FSIZE (D-FSIZERS), writes a different size and clusters for
WRZER with HL 2 and +15 nonzero (D-WRZERHL), and its flags and working HL differ (D-F37DREGS).

## The specification

References: the Philips VG-8020 with an NMS 1200 disk interface (row `D`) AND the National CF-3300
(row `C`). Ours: zerobas's disk build.

**Evidence.** **[XK rNN]**: case `NN` on row `r` of the XBBLK1 probe -- run 1 for row D
([`scratchpad/XBBLK1_run1.out`](../../scratchpad/XBBLK1_run1.out), `--row disk`), run 2 for row C
([`scratchpad/XBBLK1_run2.out`](../../scratchpad/XBBLK1_run2.out), `--row cf3300`).
`probes/bios/spec/xbblk1.asm` documents the cases (SETDTA, FMAKE B.TXT, WRBLK 200 x 1, FCLOSE, FOPEN, RDBLK
13 x 1, 20 x 1 from 190, 1 x 128, 1 x 128 from 1, FSIZE with record size 1, WRZER at 3, FSIZE with record
size 128, RDABS sector 0) and the 54-byte record (A, F, the FCB, the DTA's first 13 bytes, HL); the DTA's
128 bytes hold $40 + the case + the offset before each case. WRBLK writes 200 bytes from that 128-byte
fill, so bytes 128 .. 199 are each machine's own RAM (UNSTABLE below). Case 0's FCB is left out (start-up
RAM). The disk is the project's generated image, whose boot sector is our own tool's.

**[XK2 rNN]**: case `NN` on row `r` of the XBBLK2 probe (round 2, answering review pass 1) -- run 1
([`scratchpad/XBBLK2_run1.out`](../../scratchpad/XBBLK2_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK2_run2.out`](../../scratchpad/XBBLK2_run2.out), `--row cf3300`).
`probes/bios/spec/xbblk2.asm` documents the cases (WRBLK 200 x 1 again, FOPEN then RDBLK HL 1 with the
record size FOPEN left, RDBLK at the end, the partial record, WRBLK HL 0, WRZER with record size 1, RDBLK 4
x 128 across the zero-filled record, RDABS) and the 58-byte record: round 1's, plus the DTA at +72, +128,
+511 and +512. The DTA's 512 bytes hold `$40 + the case + the offset` (AND $FF) before each case, so every
byte WRBLK writes is the probe's own; +512 is past the fill, each machine's RAM, checked as UNCHANGED.

**[XK3 rNN]** (round 3: which rule FOPEN follows for +14 / +15) -- run 1
([`scratchpad/XBBLK3_run1.out`](../../scratchpad/XBBLK3_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK3_run2.out`](../../scratchpad/XBBLK3_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk3.asm`: a 512-byte and a 300-byte file, each read with RDBLK HL 1 straight after
FOPEN, and FSIZE of a missing file; a 1040-byte DTA fill and a 62-byte record (the DTA sampled at +383 ..
+1024). A first run with one more case -- RDABS with H 0 -- never came back on the VG-8020 + NMS 1200
([`scratchpad/XBBLK3_run0_rdabsh0.out`](../../scratchpad/XBBLK3_run0_rdabsh0.out)); that case was dropped.

**[XK4 rNN]** (round 4, answering review pass 2) -- run 1
([`scratchpad/XBBLK4_run1.out`](../../scratchpad/XBBLK4_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK4_run2.out`](../../scratchpad/XBBLK4_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk4.asm`: E.TXT written to 512 bytes, shrunk to 50 with WRBLK HL 0, overwritten,
extended, WRZER with HL 2 and below the end, a partial read asking for 3 records, and FSIZE before and after
FCLOSE through a SECOND FCB (record size $0180 going in), which is the FCB recorded for those cases; a
64-byte record (the DTA sampled at +49 .. +1024). In every round, case 0's FCB is left out (start-up RAM).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xbblk_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xbblk_rules.py --write` -->

**9 rules; 9 hold on the reference. Of the 6638 recorded outputs (each case's cursor, cells, A, table entries ...): 6568 read by a rule's check, 70 declared NOT evidence (below), 0 unread.**

#### 1. The block functions through $F37D

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-BK-WRBLK** WRBLK ($26) with record size 1 (+14) and RR 0 writes HL = 200 records of 1 byte from the DTA: A 0, HL 200 (the records written), the size 200, RR 200, +24's bit 6 cleared, the clusters 2; FCLOSE answers A 0 and leaves the FCB. FOPEN then shows +14 0 and +15 2 (records of 128, rounded up) -- the word the block functions read as the record size: $0200 (R-BK-ROUND2). | 8 | ✓ | ✓ |
| **R-BK-RDBLK** RDBLK ($27) reads HL records of the record size into the DTA from RR, advances RR, and answers HL = the records read: 13 x 1 byte from 0 (the bytes WRBLK wrote, in order; A 0, RR 13); 20 x 1 from 190 runs into the end at 200 -- A 1, HL 10, RR 200; with record size 128, record 0 (A 0, HL 1, RR 1), then the PARTIAL last record 1 (bytes 128 .. 199) counts as read: A 0, HL 1, RR 2. | 8 | ✓ | ✗ 2: XK D08, XK C08 |
| **R-BK-FSIZE** FSIZE ignores the record size: with +14 1 or 128 it answers the records of 128 (2 for 200 bytes, rounded up) and CLEARS +14 (+15 was 0 here; round 4 shows it kept). It reads the DIRECTORY: the 512 bytes WRZER wrote (no FCLOSE) are not counted yet. | 4 | ✓ | ✗ 4: XK D09, XK D11, XK C09, XK C11 |
| **R-BK-WRZER** WRZER ($28) with RR 3 on that FCB (not opened: FSIZE's) answers A 0 and writes record 3 (size 512, CR 3, RR 3, clusters 3), +14 then 0; HL 0. | 2 | ✓ | ✓ |
| **R-BK-RDABS** RDABS ($2F) with DE 0, H 1, L 0 reads sector 0 of drive A into the DTA (the generated image's boot sector) and answers A 0, HL 0. It takes no FCB (DE is the sector): the FCB in RAM keeps what FSIZE left there. | 2 | ✓ | ✗ 2: XK D12, XK C12 |
| **R-BK-ROUND2** Round 2 (the DTA filled for 512 bytes): FOPEN leaves +14 0 and +15 the records of 128 (2 for 200 bytes), so the record-size word is $0200 -- 512 -- and RDBLK HL 1 straight after it reads one 512-byte record: B.TXT's 200 bytes, then ZEROS to byte 511 (A 0, HL 1, RR 1). RDBLK at the end (RS 1, RR 200, HL 5) reads nothing: A 1, HL 0, RR and the DTA left. The partial record (RS 128, RR 1) puts bytes 128 .. 199 in the DTA and zeros after them (+72: byte 200). WRBLK with HL 0 sets the file's size to RR x the record size (128) and writes nothing. WRZER ignores the record size (RS 1 at RR 3 writes 128-byte record 3: the size 512), zero-fills the records it skips (record 1 reads 0) and leaves +14 / +15 0. RDABS reads all 512 bytes of the sector (+511: the boot signature's $AA) and not one more. Nothing writes past what it transfers (DTA+512 keeps its byte). | 30 | ✓ | ✗ 4: XK2 D05, XK2 D07, XK2 C05, XK2 C07 |
| **R-BK-FOPENRS** Round 3: FOPEN sets +14 0 and +15 the file's records of 128, rounded up (4 for 512 bytes, 3 for 300), and the block functions read +14 / +15 as ONE record-size word -- so RDBLK HL 1 straight after FOPEN reads a record of +15 x 256 bytes: 1024 from the 512-byte file (its bytes, then zeros to +1023), 768 from the 300-byte one (zeros to +767), nothing past it; A 0, HL 1, RR 1. Not "the record size is $0200" (round 2's file could not tell). WRZER (RS 128, RR 3) on a freshly made FCB writes record 3 and zero-fills records 0 .. 2 (size 512, CR 3, RR 3, +14 / +15 cleared); WRBLK 300 x 1 keeps RS 1; FSIZE of a missing file answers A $FF and leaves the FCB and the DTA. | 22 | ✓ | ✗ 4: XK3 D05, XK3 D10, XK3 C05, XK3 C10 |
| **R-BK-ROUND4** Round 4. WRBLK sets the size to the larger of the old size and where it stopped (10 x 1 at RR 0 over 50 bytes: 50). WRBLK HL 0 sets the size to RR x the record size whichever way that moves it (RS 1, RR 50: 512 -> 50; RS 128, RR 3: 50 -> 384) and writes nothing: the bytes it takes in are whatever the sectors held (case 2's, read back at +50 .. +383). WRZER writes the DTA's record at RR, zero-fills the records between the old end and RR (+384 .. +639 read 0), ignores HL (HL 2: one record, size 768) and never shrinks the file (RR 1 under 768: the size stays). FSIZE and WRZER clear +14 and KEEP +15 (RS $0180 in: $0100 out). FSIZE reads the directory: 0 records before the first FCLOSE, then 1 for 50 bytes and 6 for exactly 768 (rounded up, not + 1). RDBLK 3 x 128 over the 50-byte file reads its one partial record: A 1, HL 1, RR 1, the 50 bytes then zeros -- not the older bytes still in the sector. RDBLK 8 x 128 over 768 bytes: A 1, HL 6, RR 6, nothing past +767. | 34 | ✓ | ✗ 18: XK4 D03, XK4 D05, XK4 D07, XK4 D12, XK4 D13, XK4 D14 … (+12) |
| **R-BK-WORK** A, F and HL are the same on both references in every case but the FCLOSEs declared UNSTABLE below (HL is a working value after the non-block functions); SETDTA answers A $08 and leaves the DTA. | 118 | ✓ | ✗ 86: XK D00, XK D01, XK D02, XK D03, XK D04, XK D05 … (+80) |

Declared UNSTABLE on the reference itself (4 cases: XK D06, XK D08, XK C06, XK C08): dta — bytes 128 .. 199 of B.TXT: WRBLK took them from RAM past the probe's 128-byte fill, so XBBLK1 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) read different bytes

Declared UNSTABLE on the reference itself (2 cases: XK2 D09, XK2 C09): a, f, hl — FCLOSE after WRBLK HL 0: XBBLK2 run 1 (VG-8020 + NMS 1200) answers A 0, run 2 (CF-3300) A $FF -- an error answer, though FOPEN then finds the size written on both

Declared UNSTABLE on the reference itself (4 cases: XK4 D06, XK4 D14, XK4 C06, XK4 C14): a, f, hl — FCLOSE: XBBLK4 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) return different F and HL (case 6) and A 0 vs $FF (case 14), while FSIZE / FOPEN after it find the same size on both

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-RDBLKPART** (RDBLK of a partial last record answers A 1; the references count it as read, A 0) | R-BK-RDBLK, R-BK-ROUND2, R-BK-FOPENRS, R-BK-WORK |
| **D-WRZERHL** (WRZER with HL 2 and record size $0180: another size, clusters and DTA) | R-BK-ROUND4, R-BK-WORK |
| **D-FSIZERS** (FSIZE leaves +14; the references clear it) | R-BK-FSIZE, R-BK-RDABS, R-BK-ROUND4 |
| **D-F37DREGS** (other working F and HL) | R-BK-WORK |

## Open (not measured)

- **[A]** Why the CF-3300's FCLOSE answers A $FF after a WRBLK HL 0 (XK2 C09) and after WRZER (XK4 C14)
  while the size it closes is found on both references (UNSTABLE above); whether FSIZE between them sees it.
- **[A]** Record sizes other than 1, 128, 512 and the +15 x 256 words; WRBLK past the first extent and
  growing across clusters; RDBLK with HL 0 or RR past the end; RDABS of several sectors, other drives,
  other sectors; RDABS with H 0 (the VG-8020 + NMS 1200 did not come back); WRABS ($30); a write-protected
  disk; a full disk.
- **[A]** WRZER: which of HL 2 and +15 nonzero moves zerobas (D-WRZERHL); a skipped record in another
  sector or cluster; the FAT after it (+28 3 in XK2 r11; round 1's cluster 3 for an FCB never opened).
- **[A]** FCLOSE after WRZER on an FCB that was never opened (the directory entry, the FAT, cluster 2).
- **[A]** +24's bit 6 going in set with other bits (only $40 was measured); +36 written by FSIZE.
- **[A]** The same functions under MSX-DOS ($0005).

## Related pages

[The record functions](RECORDS.md); [the FCB directory functions](FILES.md); [the system
functions](SYSTEM.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).
