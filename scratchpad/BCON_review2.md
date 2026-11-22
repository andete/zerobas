# docs/bdos/CONIN.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22), ANSWERED by XBCON3 (rows D and C)

2.1 (CORE, NEW BEHAVIOUR candidate) BUFIN ends at column 1 vs where input began -> started at column 2: ends at
    column 1 (XN3 11). The page's rule held: no new behaviour.
1.1 / 2.2 (CORE, COMBINATION) CONST with a key held, none waiting -> $FF (XN3 1): it counts the hold.
1.2 (CORE, COMBINATION) $08 with a key held -> the held 'X', 'D' stays (XN3 2).
1.3 (CORE, COMBINATION) DIRIO with a key held and one waiting -> the held 'X', 'B' stays (XN3 4).
1.4 / 2.4 (CORE, COMBINATION) output with the hold full -> 'K' stays (XN3 6 .. 8).
1.5, 1.6, 4.3, 4.4 (EDGE) -> Open.
2.3 (EDGE) zerobas passing XN2 02 for the wrong reason -> noted: it fails XN2 01, the take that makes 02 evidence.
3.1 (CORE) TAB "column 1 -> 9" -> "column 2 -> 9". Fixed.
3.2 (CORE) R-BC-CONST's "GETPNT moves up to PUTPNT" falsified by XN2 10 -> "moves by one". Fixed.
3.3 (CORE) "$08 with a key held" in round 2 -> it ran with the hold empty; said so (page and probe header).
3.4 (EDGE) bytes outside the records -> the page says "every byte of every record".

STOP: the one new-behaviour candidate measured as the stated rule; the rest combinations (now measured) or text
-> FINAL under the small-call rule (docs/spec-method.md §7).
XBCON3 predictions, all held: CONST $FF with a key held (70%), $08 / DIRIO the held key, CONOUT leaves 'K' (60%),
DIRIO 'X' then 0, BUFIN ends at column 1 (60%).
