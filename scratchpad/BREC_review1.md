# docs/bdos/RECORDS.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBREC2 (rows D and C)

1. (CORE) SETRND's rule -> after a write (CR 2), FOPEN (CR 0), a good read (CR 1): RR 1 every time. Not the position.
2. (CORE) RDSEQ's end of file: +15 or the size -> CR 3 inside the size, past +15: it reads (A 0). The size.
3. (CORE) FOPEN's +15 -> the 6-record file: 6 (the records in the extent).
4. (CORE, NEW) RDRND past the end -> RR 6 / 20: A 1, CR := RR, the DTA left.
5. (CORE) overwriting -> WRRND RR 1: the size stays 768, RDRND 1 reads the new bytes.
6. (CORE) all 128 bytes -> the DTA's bytes now differ by offset; the read-backs keep the order (13 recorded).
7. (EDGE) FSIZE's +36 -> left. +14 / +24 / WRSEQ-overwrite / cluster boundaries -> [A].
8. Citations: SETRND's "from the position", "only flags differ", the case-0 FCB exclusion, WRRND and the cluster
   words -> fixed.
