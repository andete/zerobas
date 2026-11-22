# docs/bdos/SYSTEM.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22): answered by XBSYS3, CLEAN under the small-call stop

1. (CORE) a refused SDATE writing the year / month before refusing -> XS3 2-7: month 13 of 1999, January 32, November
   31: GDATE keeps 2026-12-01. No field written.
2. (CORE) GDATE's A the weekday or (day - 1) mod 7 -> a Tuesday (2026-12-01): 2; 2026-01-01: 4 (Thursday). Weekday.
3. (CORE) DSKRST "drive A" or "drive E" -> E 1 after SELDSK 1: CURDRV 0. Drive A.
4. (CORE) ALLOC E 0 = the current drive or drive A -> not measurable without the phantom drive B's prompt: [A].
5. (EDGE) the acceptance edges -> 12-31, 01-01, 23:59:59 accepted; day vs the month's length -> November 31 refused.
6. Citations: R-BS-ALLOC's "with E 0" (E 0 or 1), the Summary's refusal claims, D-F37DSETDATE's row (the SDATE refusals
   too), R-BS-WORK's count (it reads the DTA cell as well) -> fixed.
No new behaviour: FINAL (spec-method §7, small-call stop).
