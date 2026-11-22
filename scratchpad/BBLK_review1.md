# docs/bdos/BLOCKS.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBBLK2 (rows D and C)

1. (CORE) RDBLK at / past the end (nothing to read) -> RR 200, HL 5: A 1, HL 0, RR and the DTA left.
2. (CORE) WRBLK with HL 0 -> sets the size to RR x the record size (128), writes nothing; HL 0.
3. (CORE) RDBLK straight after FOPEN, no record-size poke -> +14 0, +15 2: the word $0200, one 512-byte record:
   the 200 bytes, then zeros; A 0, HL 1. "+15 = the records of 128" and "RS $0200" COINCIDE here -> [A] in Open.
4. (CORE) WRZER with record size 1, on the OPENED file -> ignores RS: 128-byte record 3 (size 512), the skipped
   records zero-filled (RDBLK 4 x 128 reads 0 at record 1), +14 / +15 cleared.
5. (CORE) the DTA past a partial record / short read -> zeros to the record's end; nothing past the transfer
   (DTA+512 unchanged on every case).
6. (CORE) +36 for RS 1 and RS 128 -> 0 in every FCB the rules compare (both rounds).
7. (CORE) transfers longer than the 128-byte fill -> the fill is 512 bytes in round 2; RDABS's whole sector
   checked at +72 / +128 / +511 (the $AA signature byte).
8. (EDGE) FCLOSE after WRZER on an unopened FCB (the directory / FAT, cluster 2), FSIZE of a missing file,
   RDABS with H 0 -> [A] in Open.
9. Citations (D08 / C08, D09 / D11, the 18 WORK failures, the output counts) -> checked by the reviewer, held.

zerobas on round 2: only A at XK2 5 / 7 (both D-RDBLKPART; the bytes and the zero tail are right).
FCLOSE after WRBLK HL 0 (XK2 9): A / F / HL differ between the references -> UNSTABLE.
