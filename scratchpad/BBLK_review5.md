# docs/bdos/BLOCKS.md DRAFT 5 -- review pass 5 (test writer, 2026-11-22), ANSWERED by XBBLK7 (rows D and C)

2.1 (CORE) FOPEN's +15: the file's records vs CP/M's record count in extent 0 (max $80) -> 20096 / 38528-byte
    files: +15 $80 (XK7 4 / 9). CP/M's. WRZER past 16 KB also splits RR into +12 extent / +32 record.
    The page's "over 32640 bytes" boundary was the wrong one (16384 comes first) -- dropped.
2.2 (EDGE) FSIZE's +14 for big files -> 157 / 301 records, +14 cleared, +15 kept (XK7 5 / 10).
4.1 (EDGE) the CF-3300 FCLOSE $FF: "the last block call had HL 0" -> WRZER HL 0 below the end, FCLOSE: A 0 (XK7
    13). Not HL 0 either; still open.
1.1, 1.2, 2.3, 2.4, 3.1-3.4, 4.2-4.4 (EDGE) -> text fixes (RDABS's FCB check explained, ROUND2's WRZER +14, the
    "byte 2000" read back only in round 6, the summary's D-WRZERHL DTA, the FCB side fields stated) and Open.
Only ONE core finding this pass, and it is answered; the rest are edges / combinations.

XBBLK7 predictions: +15 $80 held (55%); FSIZE 157 / 301 held; FCLOSE $FF after HL 0 MISSED (A 0).
NOT predicted: zerobas's WRZER leaves +12 0 / CR = RR AND $FF (NEW: D-WRZEREXT). The first runs stopped at the
60-second limit (not a hang; 300 used).
