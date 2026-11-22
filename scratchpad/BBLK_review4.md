# docs/bdos/BLOCKS.md DRAFT 4 -- review pass 4 (test writer, 2026-11-22), ANSWERED by XBBLK6 (rows D and C)

1.1 (CORE) the byte WRBLK wrote past the end never read -> XK6 15 samples file byte 1800 (+776): the written byte.
1.2 (CORE) past-end into an ALLOCATED sector -> XK6 10, but the buffer held that same sector (case 8's last
    transfer): the two rules still coincide -> [A] in Open, said so.
1.3 (CORE) WRBLK / WRBLK HL 0 with RS >= 256 -> XK6 8 / 9: RS $0180 writes 384 bytes, HL 0 sets 384. One word.
1.4 (EDGE) inner zero-filled records unsampled -> not re-asked (end points on both sides, every round).
2.1 (CORE) periodic fill -> the fill now differs in every sector (i >> 8 x 16); "older bytes" held (XK6 14).
2.2 (CORE) blank-image zeros vs DOS zero-fill -> over a deleted file's cluster: its bytes (XK6 15). The disk's.
2.3 (CORE) last transferred vs always sector 0 -> sector 1 last: the gap sector is G's sector 1 (XK6 15).
2.4 (EDGE) zeros past the end in the gap sector -> [A] (RDABS of it).
2.5 (EDGE) WRZER on a mid-record end -> [A].
3.1 (CORE) R-BK-FOPENRS's "+14 / +15 cleared" for WRZER -> "+14 cleared; +15 was 0 going in".
3.2 (EDGE) the CF-3300 FCLOSE item's WRBLK HL 0 half had no case -> reworded (only XK2 C09).
4.1-4.3 -> Open extended.

XBBLK6 predictions: one word for WRBLK held; HL 0 at 384 held; older bytes kept held; the disk's bytes in the
skipped new sector held (60%); the buffer = the last sector transferred held (55%). zerobas: only the gap sector
(XK6 15) differs -- it keeps the disk's bytes there; D-WRBLKGAP corrected (it is not "zeros").
