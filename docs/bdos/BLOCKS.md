<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The BDOS's block functions through `$F37D`

> **Spec:** FINAL (2026-11-22), eleven measured rounds on two references, review passes 1 .. 9 answered;
> pass 9's one new-behaviour item measured as a split between the references (UNSTABLE), so the review
> stops under the small-call rule (docs/spec-method.md §7)
> ([`scratchpad/BBLK_review1.md`](../../scratchpad/BBLK_review1.md),
> [`scratchpad/BBLK_review2.md`](../../scratchpad/BBLK_review2.md),
> [`scratchpad/BBLK_review3.md`](../../scratchpad/BBLK_review3.md),
> [`scratchpad/BBLK_review4.md`](../../scratchpad/BBLK_review4.md),
> [`scratchpad/BBLK_review5.md`](../../scratchpad/BBLK_review5.md),
> [`scratchpad/BBLK_review6.md`](../../scratchpad/BBLK_review6.md),
> [`scratchpad/BBLK_review7.md`](../../scratchpad/BBLK_review7.md),
> [`scratchpad/BBLK_review8.md`](../../scratchpad/BBLK_review8.md),
> [`scratchpad/BBLK_review9.md`](../../scratchpad/BBLK_review9.md)).
> One page for WRBLK ($26), RDBLK ($27), WRZER ($28) and RDABS ($2F), sharing one probe.

## Summary

Through the disk ROM's BDOS entry at $F37D (C the function, DE the FCB, HL the record count):

- **WRBLK** / **RDBLK** write / read HL records of the FCB's record size (+14 / +15) at the random record
  (+33 ..), advance it, and answer the records transferred in HL; a read that runs into the end of the
  file answers A 1 with HL the records read; a PARTIAL last record counts as read (HL includes it, and A
  is 0 if that makes HL what was asked), and its tail past the file is ZEROS in the DTA, whatever older
  bytes the sector still holds. FOPEN leaves +14 0 and +15 the records of 128 in extent 0 (the file's up to 16 KB, $80 past
  it: CP/M's record count), and the block
  functions read +14 / +15 as one word: a block read straight after FOPEN uses records of +15 x 256 bytes.
- **WRBLK** writes at RR x the record size and sets the size to the larger of the old size and where it
  stopped; with HL 0 it sets the size to RR x the record size, shrinking or growing, and writes nothing.
  The record size is one word here too ($0180: 384 bytes). Writing past the end leaves a gap that is NOT
  zeroed: an allocated sector keeps its older bytes, a new sector nobody writes keeps the disk's (a deleted
  file's bytes), and the sector in a new cluster that the new bytes go into is built from the DOS's sector
  buffer -- the LAST sector it transferred -- which a read then shows.
- **FSIZE** ignores the record size: it answers records of 128 (rounded up) and clears +14, keeping
  +15; it reads the directory, so a size not yet closed is not counted.
- **WRZER** writes the DTA's 128-byte record at the random record whatever the record size and HL,
  zero-fills the records between the old end and it (in newly allocated clusters too, over whatever the
  disk held), never shrinks the file, and clears +14 (keeping
  +15); **RDABS** reads absolute sectors (512 bytes each) into the DTA.
- **Past 16 KB, WRZER** keeps CP/M's split of the position in the FCB: +12 the extent (RR / 128) and +32
  the record inside it (RR mod 128); +33 .. +35 hold the whole RR. It rewrites them on every call, below
  the end too, and points +28 / +30 at the cluster it reached last: RR's own, except when it zero-fills a
  gap -- the fill runs after the record, so it ends in the cluster holding record RR - 1 (the same
  cluster unless RR starts one). WRBLK and RDBLK neither use +12 / +32
  (they position by RR alone) nor change them: they leave what they find.
- **Registers.** A is the answer (0, or 1 / $FF as above). F and HL are working values: the two references
  agree in every case (R-BK-WORK checks them case by case), but beyond these the page does not predict
  them -- e.g. H after a growing WRZER is RR's high byte, after FSIZE the record count's; FCLOSE answers F
  $93 / HL 0 after FOPEN then writes with no read between, F $42 / HL $0300 after the other sequences
  measured.
- **The FCB's other fields** (checked byte for byte by the rules, stated here): every write (WRBLK, WRBLK
  HL 0, WRZER) clears +24's bit 6, the reads keep it; only WRZER sets +32 (CR) -- to RR mod 128; +28 / +30 hold
  the cluster last reached and its index in the file (2 / 0 inside the first cluster, 3 / 1 in the
  second).

zerobas transfers the same bytes and records; it answers A 1 for a partial last record even when HL is
what was asked (D-RDBLKPART), leaves +14 in FSIZE (D-FSIZERS), writes a different size and clusters for
WRZER with HL 2 and +15 nonzero, and zeroes the DTA there (D-WRZERHL), keeps the disk's bytes in the new-cluster sector WRBLK
writes into past the end (D-WRBLKGAP), leaves +12 0 and the low byte of RR in +32 past 16 KB
(D-WRZEREXT), and past 64 KB writes WRZER's size one record short with $0FFF in +28, +30 one higher and the DTA
zeroed (D-WRZER64K), and its flags and working HL differ (D-F37DREGS).

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
64-byte record (the DTA sampled at +49 .. +1024).

**[XK5 rNN]** (round 5, answering review pass 3) -- run 1
([`scratchpad/XBBLK5_run1.out`](../../scratchpad/XBBLK5_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK5_run2.out`](../../scratchpad/XBBLK5_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk5.asm`: F.TXT written to 1024 bytes, FOPEN with +14 / +15 $80 / $FF going in,
RDBLK with record size $0180, a shrink to 384, a 1024-byte record read over it, WRZER at RR 6 over the
older sector bytes, WRBLK 2 x 128 at RR 2, WRBLK at RR 2000 (past the end), FSIZE with +15 $FF going in,
and the whole file read back; a 66-byte record (the DTA sampled at +127 .. +1024).

**[XK6 rNN]** (round 6, answering review pass 4) -- run 1
([`scratchpad/XBBLK6_run1.out`](../../scratchpad/XBBLK6_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK6_run2.out`](../../scratchpad/XBBLK6_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk6.asm`: H.TXT written to 2048 bytes and deleted (its clusters free, their bytes
left), then G.TXT: 1024 bytes, WRBLK and WRBLK HL 0 with record size $0180, WRBLK at RR 5 past the end,
WRBLK at RR 1800 into a new cluster, and the file read back. The DTA fill differs in every sector: byte i
is `($40 + the case + (i AND $FF) + (i >> 8) x 16) AND $FF`; a 66-byte record (+383 .. +1024).

**[XK7 rNN]** (round 7, answering review pass 5) -- run 1
([`scratchpad/XBBLK7_run1.out`](../../scratchpad/XBBLK7_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK7_run2.out`](../../scratchpad/XBBLK7_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk7.asm`: J.TXT (20096 bytes) and K.TXT (38528) grown with WRZER, FOPEN and FSIZE of
each, and FCLOSE after WRZER below the end with HL 0 and HL 1; XBBLK6's record. The files are never read
back. A first try with a 60-second limit stopped mid-WRZER; the runs cited used 300.

**[XK8 rNN]** (round 8, answering review pass 6) -- run 1
([`scratchpad/XBBLK8_run1.out`](../../scratchpad/XBBLK8_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK8_run2.out`](../../scratchpad/XBBLK8_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk8.asm`: L.TXT in directory entry 2 grown to 301 records, then WRZER below the end,
WRBLK and RDBLK with +12 / +32 nonzero going in, the records read back after FOPEN, FOPEN with +12 1
going in, and FSIZE; XBBLK7's record.

**[XK9 rNN]** (round 9, answering review pass 7) -- run 1
([`scratchpad/XBBLK9_run1.out`](../../scratchpad/XBBLK9_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK9_run2.out`](../../scratchpad/XBBLK9_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk9.asm`: WRZER below the end in a later cluster, FOPEN / WRBLK / FCLOSE, and N.TXT
grown to 256 and to 601 records (76928 bytes, past 64 KB) with FSIZE after; XBBLK8's record.

**[XKA rNN]** (round 10, answering review pass 8) -- run 1
([`scratchpad/XBBLK10_run1.out`](../../scratchpad/XBBLK10_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK10_run2.out`](../../scratchpad/XBBLK10_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk10.asm`: Q.TXT written to 4096 bytes and deleted, R.TXT grown over its clusters
with WRZER and read back, and WRZER at a cluster boundary with and without a gap; XBBLK9's record.

**[XKB rNN]** (round 11, answering review pass 9) -- run 1
([`scratchpad/XBBLK11_run1.out`](../../scratchpad/XBBLK11_run1.out), `--row disk`), run 2
([`scratchpad/XBBLK11_run2.out`](../../scratchpad/XBBLK11_run2.out), `--row cf3300`);
`probes/bios/spec/xbblk11.asm`: U.TXT (two full clusters) deleted, V.TXT grown over them with WRZER RR 8,
then to 2048 bytes with WRBLK HL 0 and read back; FCLOSE after an RDBLK answering A 1; XBBLK10's record.
In every round, case 0's FCB is left out (start-up RAM).

<!-- RULES BEGIN -->
<!-- GENERATED by tools/spec_rules.py from probes/bios/spec/xbblk_rules.py -- do not edit; `python3 tools/spec_rules.py probes/bios/spec/xbblk_rules.py --write` -->

**16 rules; 16 hold on the reference. Of the 20680 recorded outputs (each case's cursor, cells, A, table entries ...): 20232 read by a rule's check, 448 declared NOT evidence (below), 0 unread.**

#### 1. The block functions through $F37D

| rule | cases | reference | zerobas |
|---|---|---|---|
| **R-BK-WRBLK** WRBLK ($26) with record size 1 (+14) and RR 0 writes HL = 200 records of 1 byte from the DTA: A 0, HL 200 (the records written), the size 200, RR 200, +24's bit 6 cleared, the clusters 2; FCLOSE answers A 0 and leaves the FCB. FOPEN then shows +14 0 and +15 2 (records of 128, rounded up) -- the word the block functions read as the record size: $0200 (R-BK-ROUND2). | 8 | ✓ | ✓ |
| **R-BK-RDBLK** RDBLK ($27) reads HL records of the record size into the DTA from RR, advances RR, and answers HL = the records read: 13 x 1 byte from 0 (the bytes WRBLK wrote, in order; A 0, RR 13); 20 x 1 from 190 runs into the end at 200 -- A 1, HL 10, RR 200; with record size 128, record 0 (A 0, HL 1, RR 1), then the PARTIAL last record 1 (bytes 128 .. 199) counts as read: A 0, HL 1, RR 2. | 8 | ✓ | ✗ 2: XK D08, XK C08 |
| **R-BK-FSIZE** FSIZE ignores the record size: with +14 1 or 128 it answers the records of 128 (2 for 200 bytes, rounded up) and CLEARS +14 (+15 was 0 here; round 4 shows it kept). It reads the DIRECTORY: the 512 bytes WRZER wrote (no FCLOSE) are not counted yet. | 4 | ✓ | ✗ 4: XK D09, XK D11, XK C09, XK C11 |
| **R-BK-WRZER** WRZER ($28) with RR 3 on that FCB (not opened: FSIZE's) answers A 0 and writes record 3 (size 512, CR 3, RR 3, clusters 3), +14 then 0; HL 0 (round 8: H 1 when it grows a file to 301 records -- a working value). | 2 | ✓ | ✓ |
| **R-BK-RDABS** RDABS ($2F) with DE 0, H 1, L 0 reads sector 0 of drive A into the DTA (the generated image's boot sector) and answers A 0, HL 0. DE is the sector, so it takes no FCB: the FCB in RAM is checked as FSIZE left it (+14 0), which is why this case also fails on D-FSIZERS. | 2 | ✓ | ✗ 2: XK D12, XK C12 |
| **R-BK-ROUND2** Round 2 (the DTA filled for 512 bytes): FOPEN leaves +14 0 and +15 the records of 128 (2 for 200 bytes), so the record-size word is $0200 -- 512 -- and RDBLK HL 1 straight after it reads one 512-byte record: B.TXT's 200 bytes, then ZEROS (+511 0; A 0, HL 1, RR 1). RDBLK at the end (RS 1, RR 200, HL 5) reads nothing: A 1, HL 0, RR and the DTA left. The partial record (RS 128, RR 1) puts bytes 128 .. 199 in the DTA and zeros after them (+72: byte 200). WRBLK with HL 0 sets the file's size to RR x the record size (128) and writes nothing. WRZER ignores the record size (RS 1 at RR 3 writes 128-byte record 3: the size 512), zero-fills the records it skips (record 1 reads 0) and clears +14 (+15 was 0). RDABS reads all 512 bytes of the sector (+511: the boot signature's $AA) and not one more. Nothing writes past what it transfers (DTA+512 keeps its byte). | 30 | ✓ | ✗ 4: XK2 D05, XK2 D07, XK2 C05, XK2 C07 |
| **R-BK-FOPENRS** Round 3: FOPEN sets +14 0 and +15 the file's records of 128, rounded up (4 for 512 bytes, 3 for 300), and the block functions read +14 / +15 as ONE record-size word -- so RDBLK HL 1 straight after FOPEN reads a record of +15 x 256 bytes: 1024 from the 512-byte file (its bytes, then zeros to +1023), 768 from the 300-byte one (zeros to +767), nothing past it; A 0, HL 1, RR 1. Not "the record size is $0200" (round 2's file could not tell). WRZER (RS 128, RR 3) on a freshly made FCB writes record 3 and zero-fills records 0 .. 2 (size 512, CR 3, RR 3, +14 cleared; +15 was 0 going in); WRBLK 300 x 1 keeps RS 1; FSIZE of a missing file answers A $FF and leaves the FCB and the DTA. | 22 | ✓ | ✗ 4: XK3 D05, XK3 D10, XK3 C05, XK3 C10 |
| **R-BK-ROUND4** Round 4. WRBLK sets the size to the larger of the old size and where it stopped (10 x 1 at RR 0 over 50 bytes: 50). WRBLK HL 0 sets the size to RR x the record size whichever way that moves it (RS 1, RR 50: 512 -> 50; RS 128, RR 3: 50 -> 384) and writes nothing: the bytes it takes in are whatever the sectors held (case 2's, read back at +50 .. +383). WRZER writes the DTA's record at RR, zero-fills the records between the old end and RR (+511 reads 0), ignores HL (HL 2: one record, size 768) and never shrinks the file (RR 1 under 768: the size stays). FSIZE and WRZER clear +14 and KEEP +15 (RS $0180 in: $0100 out). FSIZE reads the directory: 0 records before the first FCLOSE, then 1 for 50 bytes and 6 for exactly 768 (rounded up, not + 1). RDBLK 3 x 128 over the 50-byte file reads its one partial record: A 1, HL 1, RR 1, the 50 bytes then zeros -- not the older bytes still in the sector. RDBLK 8 x 128 over 768 bytes: A 1, HL 6, RR 6, nothing past +767. | 34 | ✓ | ✗ 18: XK4 D03, XK4 D05, XK4 D07, XK4 D12, XK4 D13, XK4 D14 … (+12) |
| **R-BK-ROUND5** Round 5. FOPEN overwrites +14 / +15 ($80 / $FF going in: 0 / 8 for 1024 bytes). The record size is ONE word: RS $0180 reads 384 bytes (+383 the file's, +384 left), not +14's 128. WRBLK writes at RR x RS (2 x 128 at RR 2: bytes 256 .. 511; RR 4, HL 2, the size kept). WRZER at RR 6 over a file shrunk from 1024 to 384 zero-fills 512 .. 767 although the sector still held the older bytes, and clears +14. A read of a 1024-byte record over the 384-byte file: the 384 bytes, then zeros to +1023 -- not the older sector bytes; A 0, HL 1. WRBLK 1 x 1 at RR 2000 sets the size 2001 and links a second cluster (+28 3, +30 1); what the gap reads: 896 .. 1023 the OLDER bytes still in that sector, the new cluster's first sector the blank image's zeros, and the sector the byte went into the DOS's sector buffer -- the file's sector 0 as it last transferred it -- with byte 2000 in it (read back only in round 6), then zeros past the end. FSIZE keeps +15 $FF (+14 cleared). RDBLK 8 x 128 twice: A 0, HL 8, RR 8 then 16 (the second ends in the partial record 15, which counts). | 30 | ✓ | ✗ 6: XK5 D07, XK5 D12, XK5 D15, XK5 C07, XK5 C12, XK5 C15 |
| **R-BK-ROUND6** Round 6 (the fill differs in every sector). WRBLK and WRBLK HL 0 read +14 / +15 as one word too: 1 x $0180 at RR 1 writes bytes 384 .. 767 (RR 2, HL 1), and HL 0 at RR 1 sets the size 384. Past the end, nothing is zeroed: after the shrink to 384, bytes 384 .. 639 keep what case 8 wrote and 768 .. 1023 what case 7 did; WRBLK 1 x 1 at RR 1800 links a new cluster whose first sector keeps the deleted H.TXT's bytes (the DISK's, not zeros) and builds the sector it writes into from the DOS's buffer -- the LAST sector transferred (G's sector 1, as case 10 left it), not the file's first -- with byte 1800 in it. RDBLK 8 x 128 from RR 8 over 1801 bytes: A 1, HL 7, RR 15 (record 14, partial, counts; record 15 is past the end). FDEL leaves the FCB; G takes H's directory entry 0 and cluster 2 again. | 30 | ✓ | ✗ 2: XK6 D15, XK6 C15 |
| **R-BK-ROUND7** Round 7 (past one 16 KB extent). WRZER at RR 156 (157 records, 20096 bytes) and RR 300 (301 records, 38528 bytes) keeps CP/M's split of the position: +12 the extent (RR / 128: 1, 2) and +32 CR the record inside it (RR mod 128: 28, 44), +33 the whole RR; the clusters run 2 .. $15 for J.TXT (+28 $15, +30 $13) and $16 .. $3B for K.TXT (+30 $25). FOPEN then leaves +15 $80 -- the records in extent 0, at most 128 -- NOT the file's records (157, 301); a block read straight after it would take $8000 as the record size (inferred, not run: it would overrun RAM). FSIZE answers 157 and 301 (+14 cleared, +15 kept). FCLOSE after WRZER below the end with HL 0 and with HL 1 answers A 0 on both references (F $93, HL 0): HL 0 is not what makes the CF-3300 answer $FF elsewhere. Nothing reads the DTA. | 32 | ✓ | ✗ 12: XK7 D02, XK7 D03, XK7 D05, XK7 D07, XK7 D08, XK7 D10 … (+6) |
| **R-BK-ROUND8** Round 8 (L.TXT, directory entry 2, grown past 16 KB). The block functions IGNORE +12 / +32 going in: straight after WRZER RR 300 (+12 2, +32 44) WRBLK 1 x 128 at RR 5 writes record 5 (read back after FOPEN: its DTA) and RDBLK at RR 200 reads record 200 (WRZER's zeros); both LEAVE +12 2 / +32 44. WRZER rewrites them every time: RR 3 (below the end) sets +12 0, +32 3 and +28 / +30 to the cluster holding record 3 (2 / 0: the first); RR 300 again sets 2 / 44 and the last cluster. FOPEN with +12 1 going in keeps +12 1 (+15 $80: extent 1 is full too, so this does not tell extent 0 from extent +12). HL after WRZER is $0100 when it grows the file to 301 records (case 4) and 0 when it does not (5, 6), whatever the directory entry (2 here, 1 for K.TXT): RR's high byte when growing (round 9). FSIZE answers 301, HL $0100. | 28 | ✓ | ✗ 12: XK8 D04, XK8 D05, XK8 D06, XK8 D07, XK8 D08, XK8 D09 … (+6) |
| **R-BK-ROUND9** Round 9. WRZER below the end at RR 200 (M.TXT, 301 records) points +28 / +30 at the cluster HOLDING the record ($1B, +30 $19: index 25, the 26th) -- not the first -- and splits RR as always (+12 1, +32 72). Growing, WRZER answers H = RR's high byte: RR 255 (256 records, exactly 32768 bytes) H 0, RR 600 (601 records, 76928 bytes -- past 64 KB, +16 .. +19 three bytes) H 2; not growing, H 0. FSIZE answers H = the record count's high byte (601: 2). FCLOSE after FOPEN and WRBLK with no read between answers F $93, HL 0, as after FOPEN and WRZER (the $42 / $0300 pair follows the other sequences). | 24 | ✓ | ✗ 16: XK9 D02, XK9 D03, XK9 D04, XK9 D07, XK9 D09, XK9 D10 … (+10) |
| **R-BK-ROUND10** Round 10. WRZER ZERO-FILLS the records it skips in NEWLY allocated clusters too: R.TXT grown to 32 records (RR 31) over the clusters a deleted 4096-byte Q.TXT left full of bytes reads 0 at records 0 .. 7 and 16 .. 23 -- unlike a WRBLK gap, which keeps the disk's. +28 / +30 after a growing WRZER are the cluster it reached LAST: with a gap, the zero fill runs after the record and ends in the cluster holding record RR - 1 (RR 8 on an empty S.TXT: +28 6, +30 0, though record 8 is in index 1; RR 31 on R.TXT: index 3, which holds record 30 too); with no gap, the record's own cluster (T.TXT at 8 records, WRZER RR 8: +28 9, +30 1). FDEL frees Q.TXT's entry and clusters: R.TXT takes entry 0 and clusters 2 .. 5 again. | 36 | ✓ | ✗ 2: XKA D15, XKA C15 |
| **R-BK-ROUND11** Round 11. Over a deleted file's two full clusters, WRZER RR 8 on an empty V.TXT zero-fills records 0 .. 7 and writes record 8 into the second cluster (size 1152; +28 / +30 2 / 0: the cluster holding record 7). What the rest of that new cluster holds is NOT one behaviour: grown to 2048 with WRBLK HL 0 and read back, the VG-8020 + NMS 1200 shows record 8, then $FF to the sector's end, then the deleted file's bytes; the CF-3300 answers the FCLOSE after it A $FF, links cluster 0 as the file's second (+28 0) and reads zeros (UNSTABLE below). RDBLK 2 x 128 from RR 15 answers A 1, HL 1 on both; FCLOSE after FOPEN and that read answers A 0 on both -- an RDBLK answering A 1 is not what makes the CF-3300 answer $FF. | 30 | ✓ | ✗ 6: XKB D07, XKB D08, XKB D09, XKB C07, XKB C08, XKB C09 |
| **R-BK-WORK** A, F and HL are the same on both references in every case but the FCLOSEs declared UNSTABLE below (HL is a working value after the non-block functions); SETDTA answers A $08 and leaves the DTA. | 342 | ✓ | ✗ 272: XK D00, XK D01, XK D02, XK D03, XK D04, XK D05 … (+266) |

Declared UNSTABLE on the reference itself (4 cases: XK D06, XK D08, XK C06, XK C08): dta — bytes 128 .. 199 of B.TXT: WRBLK took them from RAM past the probe's 128-byte fill, so XBBLK1 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) read different bytes

Declared UNSTABLE on the reference itself (2 cases: XK2 D09, XK2 C09): a, f, hl — FCLOSE after WRBLK HL 0: XBBLK2 run 1 (VG-8020 + NMS 1200) answers A 0, run 2 (CF-3300) A $FF -- an error answer, though FOPEN then finds the size written on both

Declared UNSTABLE on the reference itself (4 cases: XK4 D06, XK4 D14, XK4 C06, XK4 C14): a, f, hl — FCLOSE: XBBLK4 run 1 (VG-8020 + NMS 1200) and run 2 (CF-3300) return different F and HL (case 6) and A 0 vs $FF (case 14), while FSIZE / FOPEN after it find the same size on both

Declared UNSTABLE on the reference itself (2 cases: XKB D09, XKB C09): a, f, hl — XBBLK11 run 1 (VG-8020 + NMS 1200) reads the rest of WRZER's record sector as $FF and the deleted file's bytes after it; run 2 (CF-3300) answers FCLOSE A $FF, links cluster 0 as the file's second (+28 0) and reads zeros

Declared UNSTABLE on the reference itself (2 cases: XKB D11, XKB C11): fcb, dta, spots — XBBLK11 run 1 (VG-8020 + NMS 1200) reads the rest of WRZER's record sector as $FF and the deleted file's bytes after it; run 2 (CF-3300) answers FCLOSE A $FF, links cluster 0 as the file's second (+28 0) and reads zeros

Declared UNSTABLE on the reference itself (4 cases: XKB D12, XKB D15, XKB C12, XKB C15): fcb — XBBLK11 run 1 (VG-8020 + NMS 1200) reads the rest of WRZER's record sector as $FF and the deleted file's bytes after it; run 2 (CF-3300) answers FCLOSE A $FF, links cluster 0 as the file's second (+28 0) and reads zeros

Declared UNSTABLE on the reference itself (2 cases: XKB D14, XKB C14): fcb, dta — XBBLK11 run 1 (VG-8020 + NMS 1200) reads the rest of WRZER's record sector as $FF and the deleted file's bytes after it; run 2 (CF-3300) answers FCLOSE A $FF, links cluster 0 as the file's second (+28 0) and reads zeros

<!-- RULES END -->

## Differences from the reference

| TODO item | rules zerobas fails |
|---|---|
| **D-RDBLKPART** (RDBLK of a partial last record answers A 1; the references count it as read, A 0) | R-BK-RDBLK, R-BK-ROUND2, R-BK-FOPENRS, R-BK-ROUND5, R-BK-WORK |
| **D-WRZERHL** (WRZER with HL 2 and record size $0180: another size, clusters and DTA) | R-BK-ROUND4, R-BK-WORK |
| **D-WRZEREXT** (WRZER past 16 KB leaves +12 0 and puts RR's low byte in +32; the references split RR into extent and record; below the end it keeps +28 / +30) | R-BK-ROUND7, R-BK-ROUND8, R-BK-ROUND9, R-BK-ROUND10, R-BK-ROUND11 |
| **D-WRZER64K** (WRZER growing a file past 64 KB: the size one record short, $0FFF in +28) | R-BK-ROUND9 |
| **D-WRBLKGAP** (the new-cluster sector WRBLK writes into past the end keeps the disk's bytes; the references build it from the DOS's sector buffer) | R-BK-ROUND5, R-BK-ROUND6 |
| **D-FSIZERS** (FSIZE leaves +14; the references clear it) | R-BK-FSIZE, R-BK-RDABS, R-BK-ROUND4, R-BK-ROUND5, R-BK-ROUND7 |
| **D-F37DREGS** (other working F and HL) | R-BK-WORK |

## Open (not measured)

- **[A]** What WRZER leaves past its record in a NEWLY allocated cluster: the references split (XKB 11:
  $FF to the sector's end on the VG-8020 + NMS 1200; the CF-3300's FCLOSE fails first). Not specified.
- **[A]** Why the CF-3300's FCLOSE answers A $FF at XK2 C09 and XK4 C14 while the size it closes is
  found on both references (UNSTABLE above). WRZER before it is not the cause (FCLOSE after WRZER answers
  A 0 there at XK2 C12, XK3 C03), nor is HL 0 (WRZER HL 0 below the end, then FCLOSE: A 0 at XK7 C13);
  nor is WRBLK HL 0 (FCLOSE after it answers A 0 there at XK4 C06 -- A only: that case's F / HL are
  UNSTABLE; case 5 between them is an FSIZE through the second FCB). "An RDBLK between FOPEN and a
  size-changing write" fits XK2 C09 and XK4 C14 but is FALSIFIED by XK5 C11 (FOPEN, RDBLK, WRBLK HL 0:
  A 0); "an RDBLK that answered A 1 after FOPEN" is refuted too (XKB C15: A 0). At XKB C09 the failing FCLOSE
  leaves the file's chain BROKEN (+28 0 for its second cluster, the read-back all zeros): the $FF is the
  CF-3300's own failure, after WRZER then WRBLK HL 0 there.
- **[A]** Record sizes other than those run: 1 and 128 for every function, $0180 for RDBLK / WRBLK /
  WRBLK HL 0 / WRZER, $0200 / $0300 / $0400 for RDBLK only ($8000 -- +15 $80 -- was NOT run); WRBLK past
  the first extent; a single transfer crossing a cluster boundary; RDBLK / WRBLK on an FCB never opened; RDBLK with HL 0 or RR past the end; RDABS of several sectors, other drives,
  other sectors; RDABS with H 0 (the VG-8020 + NMS 1200 did not come back); WRABS ($30); a write-protected
  disk; a full disk.
- **[A]** WRZER: which of HL 2, +15 nonzero and growing past 64 KB (XK9 10: HL 1, +15 0) makes zerobas
  zero the DTA (D-WRZERHL, D-WRZER64K); the FAT after it (+28 3 for the FCB never opened, XK r10).
- **[A]** FCLOSE after WRZER on an FCB that was never opened (the directory entry, the FAT, cluster 2).
- **[A]** +24's bit 6 going in set with other bits (only $40 was measured); +36 written by FSIZE.
- **[A]** WRBLK past the end into an ALLOCATED sector when the DOS's buffer holds ANOTHER sector (XK6 10's
  buffer held that same sector, so "the buffer" and "the sector's own bytes" coincide); WRZER on a file
  whose end is mid-record (zero from the end byte, or from the next record?); RR past 16 bits (+35 / +36);
  the gap sector's bytes past the written byte, read raw with RDABS.
- **[A]** FOPEN with +12 nonzero going in on a file whose extent +12 is NOT full (XK8 13's was): +15 of
  extent 0 or of extent +12?
- **[A]** RDBLK / WRBLK at a byte offset past 64 KB (N.TXT was never read back); FOPEN with RR / CR /
  +28 / +30 nonzero going in; which sector the DOS's buffer holds after a growing WRZER.
- **[A]** FOPEN with +12 past the file's last extent (A $FF as in CP/M?); RR of 4096 and more (+12 past $1F); a DTA below $8000 or across a page boundary; a transfer
  wrapping past $FFFF; a drive byte other than 0; +28 / +30 after WRBLK HL 0 across clusters; FSIZE (found
  and missing) with +12 / +24 / +28 .. +35 nonzero going in; FSIZE before FCLOSE after a write linked a
  cluster; multi-record transfers with a record size over 128; WRBLK / RDBLK with +12 / +32 matching RR.
- **[A]** FOPEN of an empty file (+15 0: a record-size word of 0); which sector the DOS's buffer holds when
  the last transfer was a READ, or of another file; a write into a new cluster's FIRST sector, and a
  multi-record one.
- **[A]** WRBLK HL 0 shrinking across a cluster boundary or to 0 (are clusters freed?), growing with HL 0
  into unallocated clusters, and a WRBLK gap spanning whole clusters.
- **[A]** The same functions under MSX-DOS ($0005).

## Related pages

[The record functions](RECORDS.md); [the FCB directory functions](FILES.md); [the system
functions](SYSTEM.md).

## Tests that cover it

**`spec-live`** ([tools/spec_live.py](../../tools/spec_live.py), in every gate): every rule above, run live on zerobas against these cases' measured reference values. It fails if a rule fails that *Differences from the reference* does not name, or a named one holds ([docs/spec-method.md](../spec-method.md) §8).
