# docs/disk/CHOICE.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XCHOICE2 (rows D and C)

2.1 (CORE, NEW BEHAVIOUR) CHOICE "A 0, F 0" vs "AF kept" -> AF $5AD7 in, $5AD7 out (XH2 0): KEPT. The page was wrong.
2.2 (CORE, COMBINATION) B = C in every case -> B $F8 / C $00 and B $00 / C $F9: kept, the same HL (XH2 0, 1).
2.3 / 2.4 / 2.5 (CORE / EDGE) DE / HL / A always one value -> DE $1234 / $5678, HL $C000, AF $5AD7: CHOICE keeps all
    but HL; MTOFF keeps DE everywhere, BC and HL on the CF-3300 (XH2 0, 2).
1.1 (CORE, COMBINATION) MTOFF's registers UNSTABLE though each reference is steady -> the CF-3300 pinned (R-CH-MTOFFCF);
    the NMS 1200's values stay declared by interface (and repeat with other inputs and after a read).
1.2 (CORE, NEW BEHAVIOUR) "writes nothing" on 21 bytes -> all 32 in round 2; outside the buffer -> [A].
1.3 (CORE, NEW BEHAVIOUR) the pointer only range-checked -> its target is the ROM's own bytes: not readable in the
    clean room (a FORMAT screen comparison is BASIC-level, out of this focus) -> [A], said so.
1.4, 1.5 (EDGE) interrupts on / not via CALSLT; after disk activity -> after a read measured (XH2 4, 5); the rest [A].
3.1 (EDGE) the NODISK hang's evidence -> the first run was overwritten; said so.
3.2 (EDGE) set-up details (HL $A400, di) -> stated.
4.x -> Open.

XCHOICE2 predictions: none stated before the run beyond "CHOICE AF as round 1" -- MISSED (kept, not 0).
Not FINAL: pass 1 found new behaviour (CHOICE keeps AF) -> review pass 2.
