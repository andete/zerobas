# docs/bdos/FILES.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBFILE2 (rows D and C)

1. (CORE) "writes 0" vs "leaves it" (the FCB cleared first) -> an FCB pre-filled with $FF: FMAKE writes +14 .. +31,
   leaves +12 / +13 and +32 .. +36 (R-BF-MAKE2). NEW: the pre-fill set the EXTENT byte to $FF too, which made WRSEQ
   fail (A 1) and FOPEN answer $FF (R-BF-EXTENT).
2. (CORE) FOPEN of a file with data -> not reached: the write failed on the extent; [A].
3. (CORE) the date -> SDATE 2025-06-15 then FMAKE: $5ACF; 2026-11-22: $5D76. Today's date.
4. (CORE) +25 constant or the entry index -> the second file: 1. Index.
5. (CORE) carry "on A $FF" vs "on not-found" -> FREN onto an existing name: A $FF, carry CLEAR. Not-found.
6. (CORE) case 10's "removed" -> SFIRST of all with two files: both found, in order.
7. (EDGE) SETDTA's A from DE -> $9300: A $08 too. Constant.
8. Citations: the frame's name, the DTA in every rule, FREN's set-up, D-F37DREGS's F -> fixed.
