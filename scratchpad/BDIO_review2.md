# docs/disk/DSKIO.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22)

No new behaviour. 1.1, 1.2, 1.3, 4.2, 4.3, 4.4 (combinations: bytes outside the 1 KB sum, a mid-disk read failure,
multi-sector writes) -> [A]. 2.1, 2.2 (D = 0 vs the drive; DSKIO vs the shared inter-slot call for F / DE / IFF)
-> [A], the "D and E unmeasured" item corrected (4.1: they ARE checked, against PHYDIO's). 3.1 xdskio2p.asm's
header described the wrong call -> fixed. 3.2 the NODISK skip true for the reference only -> said so.
STOP -> FINAL (small-call rule, docs/spec-method.md §7).
