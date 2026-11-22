# docs/bdos/BLOCKS.md DRAFT 3 -- review pass 3 (test writer, 2026-11-22), ANSWERED by XBBLK5 (rows D and C)

1.1 (CORE) WRBLK with HL > 0 only ever at RR 0, RS 1 -> XK5 9: WRBLK 2 x 128 at RR 2; XK5 10: 1 x 1 at RR 2000.
1.2 (CORE) WRZER's zero fill only seen over zero sectors -> XK5 8: 1024 written, shrunk to 384, WRZER at RR 6;
    the read-back samples +384 .. +767 where the second sector still holds case 2's bytes.
1.3 (CORE) "FOPEN sets +14 0" never had +14 nonzero going in -> XK5 4: +14 $80 / +15 $FF going in.
1.4 (EDGE) FOPEN of an empty / > 32640-byte file -> [A].
1.5 (EDGE) +15 kept, one value only -> XK5 12: $FF going into FSIZE.
1.6 (EDGE) WRBLK past the end -> XK5 10 (the gap read back at XK5 15).
1.7 (EDGE) R-BK-RDABS's FCB clause cannot fail -> dropped from the rule text.
2.1 (CORE) one word vs "+14 if nonzero else +15 x 256" -> XK5 5: RDBLK HL 1 with RS $0180 (384 vs 128 bytes).
2.2 (CORE) WRBLK writes at RR x RS vs at 0 / CR -> XK5 9.
2.3 (CORE) WRZER zero-fills every skipped record vs only the old end's sector -> XK5 8 (see 1.2).
2.4 (EDGE) zero tail vs raw later sectors -> XK5 7: a 1024-byte record over the file shrunk from 1024 to 384.
3.1 (EDGE) "+28 3 in XK2 r11" -> wrong row: it is XK r10; fixed.
3.2 (CORE) "+384 .. +639 read 0" wider than the samples -> narrowed to the sampled bytes; XK5 widens them.
3.3 (EDGE) XK2 r05 "zeros to 511" one sample -> text says "+511 0".
4.1 (CORE) the CF-3300 FCLOSE item's triggers contradicted (A 0 at XK4 C06, XK2 C12, XK3 C03) -> reframed:
    the preceding function is not the cause; what separates C09 / C14 from them is open.
4.2-4.3 -> FOPEN of an empty / huge file and +15 at its ends added to Open.

XBBLK5 predictions: FOPEN 0 / 8 held; RS $0180 = 384 held; zeros past the end held; WRZER zero fill over older
bytes held; WRBLK at RR x RS held; +15 $FF kept held; RDBLK 8 x 128 A 0 / HL 8 held. The gap (50/50) went
neither way: older bytes in the allocated sector, the blank image's in the new one, and the DOS's sector buffer
in the one the byte went into -- identical on both references; zerobas zeros it (NEW: D-WRBLKGAP).
