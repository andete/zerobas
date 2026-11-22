# docs/bdos/CONIN.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBCON2 (rows D and C)

1.1 (CORE) DIRIO A 0 with no key never measured (case 3 had a key held) -> XN2 0: A 0 with nothing held.
1.2 (CORE) the held key first, only for CONIN / DIRIO -> XN2 3 ($07: the held 'X'), XN2 7 (BUFIN: 'Z' + "HI").
1.3 (CORE) one place? -> XN2 2: CONST with the hold full leaves 'Y' in the buffer. One place.
1.4 (EDGE) DIRIO with a key held AND one waiting -> XN2 3 is the same with $07 ('C' stays).
2.1 (CORE, NEW BEHAVIOUR) the echo takes a key vs any output -> CONIN "EF" takes both (XN2 8, F then held), and
    CONOUT 'Q' takes 'K' (XN2 17 / 18). Any console output.
2.2 (CORE) CONST to PUTPNT vs by one -> "XY": GETPNT by ONE (XN2 10).
2.3 (CORE) "control characters raw" from $01 / $0D -> TAB expands to column 9 with spaces; BS, CTRL+B, LF raw
    (XN2 12 .. 15). The rule restated.
2.4, 2.5 (EDGE) -> Open.
3.1 (CORE) R-BC-RAW's XN 04 failure is inherited cursor state -> said so in Differences.
3.2 (CORE) the graphic-prefix effect sits in case 9, not R-BC-ECHO's set -> R-BC-BUFIN's text now states the $08.
3.3 (EDGE) the probe header's "20-byte record" -> 24.
3.4 (EDGE) 22 outputs per record: HL counts once, the buffer and the screen once each -- the count is per FIELD.
3.5 (EDGE) $A110 past the records is uncleared RAM -> "every byte of every record".
3.6 (EDGE) the cell-to-column mapping -> stated (the same margin on both).
4.x -> Open.

XBCON2 predictions, all held: DIRIO 0 (80%), one place (60%), $07 the held key, BUFIN "ZHI", the echo takes 'F'
(60%), CONST by one, TAB to spaces (50%), the raw BS / CTRL+B / LF, CONOUT takes 'K' (55%).
