# docs/bdos/BLOCKS.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22), ANSWERED by XBBLK3 + XBBLK4 (rows D and C)

1.1 (CORE) FSIZE "rounded up" vs "+1" -> 768 bytes: 6 (XK4 15). Rounded up.
1.2 (CORE) "clears +14 / +15" -> $0180 in, $0100 out for FSIZE (XK4 3/5/7/15) and WRZER (XK4 12): +14 ONLY.
    The page and D-FSIZERS were wrong; fixed.
1.3 (CORE) WRBLK's size: RR_end or max -> 10 x 1 at RR 0 over 50 bytes: 50 (XK4 10). The larger.
1.4 (CORE) WRBLK HL 0: RR x RS -> RS 1, RR 50: 50 (shrink, XK4 4); RS 128, RR 3: 384 (grow, XK4 11).
1.5 (CORE) WRZER and HL -> HL 2: one record, size 768 (XK4 12). Ignores HL. Below the end (RR 1): no shrink (XK4 13).
1.6 (EDGE) byte 199 never sampled -> [A]: not re-asked; XK4 9 samples the 50-byte file's last byte (+49).
1.7 (EDGE) RDBLK RR past the end, +36 from FSIZE -> [A] in Open.
2.1 (CORE) A for a partial record -> RDBLK 3 x 128 over 50 bytes: A 1, HL 1 (XK4 9). A is 1 when HL is short.
2.2 (CORE) zero tail vs stale disk bytes -> after a 512-byte write shrunk to 50: +50 .. +127 read 0 (XK4 9).
    The DOS zero-fills; but WRBLK HL 0 GROWING the file takes in the old sector bytes (XK4 17, +50 .. +383).
2.3 (CORE) FSIZE directory lag vs unopened FCB -> FSIZE through a second FCB before the first FCLOSE: 0 (XK4 3).
2.4 (CORE) where WRBLK HL 0 puts the size -> FSIZE before FCLOSE: 0 (XK4 5); after: 1 (XK4 7). FCLOSE writes it.
2.5-2.7 (EDGE) skipped records in another sector, +24 bits, the FAT after WRZER -> [A] in Open.
3.1 (CORE) WORK's "$0300 after FCLOSE" -> text rewritten: no value list.
3.2 (CORE) the XK2 9 UNSTABLE reason -> names the CF-3300's A $FF; XK4 14 shows it again (also UNSTABLE).
3.3 (EDGE) RDABS "the FCB is not touched" -> reworded: RDABS takes no FCB; the RAM keeps FSIZE's.
3.4 (EDGE) case 0's FCB in every round -> said once for all rounds.
4.1 (CORE) the first [A] item -> answered by XBBLK3: the word, +15 x 256 (R-BK-FOPENRS).
4.2-4.3 -> the Open list rewritten.

Round 3 also: RDABS with H 0 never came back on the VG-8020 + NMS 1200 (dropped; scratchpad/XBBLK3_run0_rdabsh0.out).
zerobas: A at XK3 5 / 10 (D-RDBLKPART); FSIZE's +14 (D-FSIZERS); WRZER HL 2 + $0180 (NEW: D-WRZERHL).
Predictions for XBBLK4: 7 of 7 held; NOT predicted: +15 kept by FSIZE / WRZER, zerobas's WRZER split.
