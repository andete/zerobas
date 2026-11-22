# docs/bdos/BLOCKS.md DRAFT 7 -- review pass 7 (test writer, 2026-11-22), ANSWERED by XBBLK9 (rows D and C)

1.1 (CORE) FCLOSE's F / HL unpredicted -> candidate "F $93 after FOPEN then writes" tested: FOPEN, WRBLK, FCLOSE
    gives $93 / 0 (XK9 7). Stated in the page's Registers paragraph as measured, not as a full rule: F and HL are
    working values the references agree on case by case (R-BK-WORK), not predicted beyond the cases.
1.2 (CORE) FSIZE's H -> 601 records: H 2 (XK9 12). The record count's high byte (157: 0, 301: 1).
2.1 (CORE) H after WRZER: count >> 8 vs RR >> 8 -> RR 255 (256 records): H 0; RR 600: H 2 (XK9 9 / 10). RR's.
2.2 (CORE) +28 / +30 below the end: the first cluster vs the one holding RR -> RR 200: $1B / $19 (XK9 3). The one
    holding RR; the page and D-WRZEREXT's wording corrected.
2.3, 2.5, 4.2-4.6 (EDGE) -> Open.
2.4 (EDGE) XK8 8's zeros: WRZER's vs the blank image's -> not re-asked (Open names the case).
3.1 (EDGE) XK4 C06 cited for A only -> said so.
4.1 (CORE, COMBINATION) the CF-3300 FCLOSE candidate -> named in the Open item with its limit (XK5 C11).

XBBLK9 predictions: +28 / +30 = the cluster holding RR held (65%); H = the count's high byte MISSED (RR's); FSIZE H
2 held; FCLOSE $93 after FOPEN + WRBLK held (50%). NOT predicted: zerobas's WRZER past 64 KB -- the size one
record short, $0FFF in +28 (NEW: D-WRZER64K, tier 3).
