# docs/bdos/BLOCKS.md DRAFT 6 -- review pass 6 (test writer, 2026-11-22), ANSWERED by XBBLK8 (rows D and C)

1.1 (CORE, NEW BEHAVIOUR) +12 nonzero going in -> XK8 7 / 8: WRBLK and RDBLK position by RR alone and LEAVE
    +12 / +32; WRZER RR 3 rewrites +12 0 / +32 3 and +28 / +30 (XK8 5).
2.1 (CORE, NEW BEHAVIOUR) H after WRZER = the directory entry? -> L.TXT is entry 2 and answers $0100 too (XK8 4,
    14). Refuted: $0100 when WRZER grows the file to 301 records, 0 when it does not (XK8 5 / 6). A working value
    (R-BK-WORK checks it on both references); R-BK-WRZER's "HL 0" text scoped.
1.2 (CORE, COMBINATION) a transfer crossing a cluster boundary -> [A] in Open.
1.3 (CORE, COMBINATION) RDBLK past 16 KB -> XK8 8: record 200 read, +12 / +32 left.
1.4, 1.5 (EDGE) -> Open; FCLOSE's two F / HL values are checked across references by R-BK-WORK.
2.2 (EDGE) WRZER rewrites +12 always vs only when extending -> XK8 5: always.
2.3 (EDGE) FOPEN's +15 with +12 nonzero -> XK8 13: +12 1 kept, +15 $80 -- extent 1 is full, no separation; [A].
2.4-2.6 (EDGE) -> not re-asked (combinations of stated rules).
3.1 (CORE) "+32 -- to RR" -> "RR mod 128".
3.2 (CORE) the 16 KB split scoped to WRZER; WRBLK / RDBLK stated (round 8).
3.3 (EDGE) the FCLOSE $FF item -> XK4 C06 is FCLOSE after WRBLK HL 0 (A 0); reworded.
4.1 (EDGE) the record-size open item -> rewritten with what was run per function.

XBBLK8 predictions: H = entry MISSED; +12 ignored held (75%); WRZER rewrites held (70%); WRBLK / RDBLK leave +12
held (60%). NOT predicted: WRZER resets +28 / +30 below the end (zerobas keeps them: added to D-WRZEREXT).
