# docs/bdos/FILES.md DRAFT 3 -- review pass 3 (test writer, 2026-11-22): the page's own functions answered by XBFILE4; FINAL

On the directory functions (CORE): FOPEN of a multi-extent file -> a 16384-byte file opens at extent 0 (+15 $80) and
1 (+15 0): extent e opens when e x 16384 does not pass the size; +26 / +28 the first cluster (+28 the CURRENT one).
FCLOSE's $93 -> FCLOSE with +12 $FF and no write: $10 -- the $93 belongs to the failed write. FMAKE's index -> the
first free entry (a freed entry 0 is taken); re-making an existing entry: not separated ([A]).
Citations: D-FMAKERS (+14 / +15 only; the size is written), XB3's vacuous DTA checks (no SETDTA there) -> fixed.
WRSEQ's findings (where data lands, +30, +15, +13, +12 1 / 2, +24 masks, disk full) belong to the record functions'
page (spec-method §7) -> [A] here.
No new behaviour on the page's functions: FINAL (small-call stop).
