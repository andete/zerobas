# docs/bdos/BLOCKS.md DRAFT 9 -- review pass 9 (test writer, 2026-11-22), ANSWERED by XBBLK11 (rows D and C)

3.1 (CORE, the rule as written false) "+28 / +30 the cluster before RR's" after a gap-filling WRZER -> "the
    cluster holding record RR - 1" (the rules checked bytes and held; the TEXT was wrong). Fixed.
2.1 (CORE, NEW BEHAVIOUR) what WRZER leaves past its record in a new cluster -> XKB 11: the references SPLIT
    ($FF to the sector's end on the VG-8020 + NMS 1200; the CF-3300's FCLOSE answers $FF and breaks the chain).
    Declared UNSTABLE, both runs cited; not specified.
1.1 (CORE, COMBINATION) records 24 .. 31 of R.TXT -> the same question as 2.1; not re-asked.
1.2-1.4, 2.2 (EDGE) -> Open.
3.2 (EDGE) the FCLOSE item's two candidate rows falsified on row C -> rewritten.
4.1 (EDGE) candidate "an RDBLK that answered A 1" -> XKB C15: A 0. Refuted. The CF-3300's $FF at XKB C09 comes
    with a broken chain: its own failure.
4.2 stale Open items (skipped records in other sectors / clusters; WRZER exactly at the end) -> removed.
4.3, 4.4 -> Open.

STOP: pass 9's one new-behaviour finding measured as a reference split, its factual error was text only, the rest
are edges / combinations -> FINAL under the small-call rule (docs/spec-method.md §7).
XBBLK11 predictions: zeros in the rest of the sector MISSED ($FF on D; C failed); the other sector the disk's held
on D; the CF-3300 $FF after an A-1 read MISSED (A 0). zerobas: only the gap case's +28 / +30 (D-WRZEREXT).
