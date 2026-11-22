# docs/bdos/SYSTEM.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XBSYS2 (rows D and C)

1. (CORE, NEW) what ALLOC's IX / IY point AT -> the DPB (drive 0, $F9, 512) and the FAT ($F9 $FF $FF $00): R-BS-ALLOC2.
2. (CORE, NEW) a refused SDATE's effect on the date -> kept (GDATE after month 13: 2026-11-23).
3. (CORE, NEW) DSKRST and the current drive -> SELDSK 1, CURDRV 1, DSKRST, CURDRV 0: drive A again. NEW behaviour.
4. (CORE) GDATE's A day of week vs always 0; SDATE's A accepted vs day -> a Monday: SDATE A 0, GDATE A 1.
5. (EDGE) SDATE / STIME edges -> month 0, day 0, day 32, hour 24, minute 60, second 60: all refused.
6. (EDGE) ALLOC E 1 -> as E 0.
7. (EDGE) Disk BASIC frame, another slot, IX $56D3 -> [A].
8. Citations: D-F37DREGS's wording (A, DE too), the probe's run line (--row disk), the year-range wording -> fixed.
