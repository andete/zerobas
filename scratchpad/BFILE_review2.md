# docs/bdos/FILES.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22), ANSWERED by XBFILE3 (rows D and C)

1. (CORE) round 2's failures: the extent (+12) or the current record (+32 $FF)? -> each alone: the EXTENT makes WRSEQ fail
   (A 1); with only CR $FF WRSEQ WRITES record 127 (16384 bytes, extent -> 1, CR 0). NEW behaviour: WRSEQ writes at
   CR AND $7F. zerobas writes record 0 every time (D-FCBEXTENT widened).
2. (CORE) WRSEQ writes or clears +24 / +32 -> +24 $41 -> $01 (bit 6 cleared); CR $85 -> record 5 written, CR 6.
3. (CORE) FOPEN of a file with data -> 6 records: +15 6, size 768, clusters 18 / 18. FOPEN of an extent the file
   lacks (+12 $FF, +12 1) -> A $FF, carry clear.
4. (CORE) FSIZE writes or leaves +33 .. +36 -> over $FF: +33 .. +35 = 6, +36 left.
5. (CORE, NEW) not-found of FDEL / FREN / FSIZE -> A $FF, carry SET (zerobas: FDEL's carry clear -> D-BDOSCARRY).
6. Citations: the Summary's carry sentence, R-BF-MAKE's "+12 0", FOPEN's +14, R-BF-WORK's prose, "round 1's every A",
   "the empty disk" -> fixed.
7. Pre-filled FCBs for FOPEN / FSIZE / FREN / FDEL / SFIRST, FMAKE over a file with data, STIME, re-stamping -> [A].
