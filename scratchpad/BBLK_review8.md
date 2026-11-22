# docs/bdos/BLOCKS.md DRAFT 8 -- review pass 8 (test writer, 2026-11-22), ANSWERED by XBBLK10 (rows D and C)

1.1 (CORE, NEW BEHAVIOUR) WRZER's zero fill into new clusters over nonzero disk bytes -> R.TXT over a deleted
    Q.TXT's full clusters reads 0 (XKA 12 / 13). WRZER zero-fills new clusters; WRBLK's gap does not.
2.1 (CORE, NEW BEHAVIOUR) +28 / +30 after a growing WRZER: "holding RR" vs "RR - 1" -> RR 8 with a gap: index 0
    (XKA 15); RR 8 without a gap: index 1 (XKA 18). The cluster reached LAST: the fill runs after the record.
    The summary's "holding RR" corrected; XK9 10's $4A is the same rule (a gap), not a 64 KB effect.
1.2, 1.3, 4.4, 4.5 (EDGE) -> Open (past 64 KB reads / writes, FOPEN with nonzero fields, the buffer after a
    growing WRZER).
2.2 (EDGE) the CF-3300 FCLOSE candidate falsified by XK5 C11 -> said so; the two rules that fit named.
3.1 (CORE) the summary's "+28 / +30 holding RR" -> fixed (2.1).
3.2 (EDGE) zerobas at XK9 10: +30 and the DTA -> added to D-WRZER64K (page and TODO).
3.3 (EDGE) FCLOSE's F $93 "after FOPEN then writes" -> "with no read between".
3.4 (EDGE) "the file's 25th" -> index 25, the 26th.
3.5, 4.3 (EDGE) -> fixed (the FCLOSE item; D-WRZERHL's third trigger in Open).

XBBLK10 predictions: zero fill in new clusters held (60%); RR - 1 with a gap held; RR - 1 without a gap MISSED
(the record's own cluster). zerobas: only the gap case's +28 / +30 (added to D-WRZEREXT).
