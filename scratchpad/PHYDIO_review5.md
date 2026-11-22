# PHYDIO.md DRAFT 5 -- review pass 5 (test writer, 2026-11-22): CLEAN under the small-call stop

A fresh reviewer read only the page, the six run files and xdsk1-6.asm, decoded all 73 row-D reference records and
confirmed every rule's case assignment and count (28 / 8 / 14 / 6 / 4 / 13). Its findings:

1. Unpinned -- all COMBINATIONS: the 16-bit refusal on a write; which sector a wrapped count other than 0 selects;
   the media check against the 16-bit refusal. -> [A] on the page.
2. Rival rules -- all COMBINATIONS / EDGE: the 16-bit refusal's scope (2 from $FFFE), B 0 in the up-front check,
   $F8's count width (8 bits or more), C / B / D against the entry A. -> [A].
3. Citations: "$FF only 0 in" (case 70 reads track 1), the wrap "measured with $F8" (only the non-wrap at 128),
   the Summary's "B 0 means 256" -> fixed.
4. Open-list gaps -> added.

No new behaviour and no unpinned core rule: the page's core rule is FINAL (docs/spec-method.md §7, small-call
stop, Joost 2026-11-18).
