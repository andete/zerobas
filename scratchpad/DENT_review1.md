# GETDPB.md / DSKCHG.md DRAFT 1 -- review pass 1 (one test writer for both, 2026-11-22), ANSWERED by XDENT3

The reviewer read only the two pages, XDENT1_run1 / XDENT2_run1 and xdent1-2.asm. Answered by measuring
(XDENT3_run1.out, row D):

1. Unpinned (CORE): DSKCHG's B 0 path READS the disk? (C always equalled the disk's $F9) -> XE3 0, C $F8:
   it reads -- A $F9, the $F9 block -- and answers B $FF, CHANGED. NEW BEHAVIOUR (zerobas: B 0, D-DSKCHGFF).
   Does a B 1 answer restart the clock? -> XE3 2-5 (DSKCHG every 48 interrupts): no; the count runs from the last
   READ, and 96 interrupts already read (the page's "~3 s" was wrong: < 2 s). zerobas: ~3 s (D-DSKCHGTIME).
   GETDPB not an access -> XE3 6-7: after 176 idle, GETDPB, DSKCHG reads. (EDGE) interrupts-on / carry-set entry,
   other HL, the buffer past HL + 20, A 1 -> open lists.
2. Rival rules: seconds or timer interrupts -> XE3 10 (3.5 s with interrupts OFF: B 1): interrupts. A disk-change
   timer or the motor -> XE3 8-9 (MTOFF, then DSKCHG: B 1): the timer. GETDPB from B or from a valid C -> XE3 1 (B
   $F9, C $F8: the $F9 block): B. (EDGE) A / HL exact -> A = 2 x (B - $F8), HL $7405 + 18 x (B - $F7): now checked.
   (EDGE) DSKCHG's F / HL by media -> F $50 (B 0) / $38 (B $FF), HL $7429 -- only the $F9 disk measured; open.
3. Citations: "each standard format ($F8 to $FF)" ($FB unmeasured), "$FA is 1 x 8 x 80" (no field shows the
   geometry) -> reworded.
4. Open-list gaps -> added (another disk format, the count's exact limit, what else restarts it, ...).
