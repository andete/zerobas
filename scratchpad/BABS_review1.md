# docs/bdos/WRABS.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBABS2 (rows D and C)

1.1 (CORE, NEW BEHAVIOUR candidate) a RAM cache RDABS serves -> PHYDIO ($0144, to the medium) reads the written bytes
    (XA2 2, 6, 10). On the medium: the stated rule.
1.2 (CORE, NEW BEHAVIOUR candidate) neighbours written too -> RDABS 19, 21, 23, 20, 1438 read the image's / case 1's
    bytes (XA2 3, 4, 7, 8, 11). Only those sectors: the stated rule.
1.3 (CORE, COMBINATION) 17 bytes per sector checked -> two order-sensitive 16-bit sums per 512-byte half, expected
    from the fill formula and our own image. (A plain sum and 8-bit Fletcher were useless on this fill: every
    256-byte run is a permutation, so both are case-independent -- caught before use.)
1.4 (CORE) F unstated -> F $42 in the WRABS / RDABS rules.
1.5 (EDGE) SETDTA's A / HL -> stated in R-BA-WORK.
2.1 (CORE, NEW BEHAVIOUR candidate) logical DE vs a shared mapping f(DE) -> PHYDIO with DE (logical) reads the same:
    the stated rule.
2.2, 2.3 (CORE / EDGE, COMBINATION) L other than 0, the DTA poked -> [A].
3.1 the past-end claim cited row D only -> "the VG-8020 + NMS 1200", "CF-3300 not run".
3.2 "+383 .. +1024" -> the 12 sampled offsets named.
3.3 zerobas's F / HL on the past-end case -> recorded.
3.4 RDABS H 0's citation -> scratchpad/XBBLK3_run0_rdabsh0.out.
3.5 run0 from the earlier probe source -> said so.
4.x -> Open (persistence is now a rule; neighbours too; page-1 DTA, buffer coherence, sector 0, DE >= $8000, H
    crossing the end).

STOP: the new-behaviour candidates measured as the rule already stated -> FINAL (small-call rule).
XBABS2 predictions, all held: PHYDIO reads the written bytes; the neighbours the empty image's; the sums as modelled.
