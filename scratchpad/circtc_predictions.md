# D-CIRCTC predictions (write BEFORE each run, score incl. misses)

## Hypothesis (the interesting claim)
CIRCLE's trailing comma after a COMPLETE arg list is NOT a restructure. `cp_done`
(basic/graphics.asm:611-621) ALREADY does `ld hl,(GFX_DPTR) / jp exec_stmt` after
the GFX_OP=4 draw. GFX_DPTR (a RAM sysvar) is preserved across GFX_OP=4
(gfx_circle_op :1307 does not touch it). So if the tenant, at `cpt_asp_done`,
reports SUCCESS (GFX_RES=0) and leaves the cursor on the trailing comma instead of
raising ERR 2, the draw happens and the existing `jp exec_stmt` -> es_noentry ->
stmt_error raises ERR 2 (trappable) AFTER the draw. => CLEAN DELETE, like
SWAP/PAINT/SPRITE, refuting the filed "RESTRUCTURE, confirmed".

The edit: delete `cp ',' / jp z,cpt_err2` at cpt_asp_done (sub/circleparse.asm
:242-243). -5 B of sub page 1. Moves sub.rom ONLY (basic-reloc.rom + merged
UNCHANGED) -- same signature as D-CIRCMISS.

## BASELINE (circtc_before.out) -- reproduces D-CIRCMISS shipped state
- c.colour/c.start/c.end/c.aspect: `24 4` all three -> agree
- k.colour/k.start/k.end/k.aspect: `24 4` all three -> agree
- o.none `0 15`; o.colour `0 15`; o.start `0 5`; o.end `0 5` -> agree (drawn)
- x.extra `2 4` all three -> agree
- x.extra2: refs `2 5`, zb `2 4` -> **1 DIFF** (the target)
- r.miss `24 4`; r.nocomma `2 4`; c.ok `0 5` -> agree
PREDICT: 17 printed, ~16 scored, **1 DIFF (x.extra2)**.

## AFTER (circtc_after.out) -- with the delete
PREDICT: x.extra2 refs `2 5`, zb `2 5` (drawn then ERR 2) -> **0 DIFF**.
ALL other rows UNCHANGED from baseline (only cpt_asp_done's comma path moves):
  - x.extra STAYS `2 4` (cpt_at_aspect, aspect slot empty, untouched)
  - c.ok STAYS `0 5`, o.* STay drawn, c.*/k.* STay `24 4`.
PREDICT: 17 printed, ~16 scored, **0 DIFF**.

## SCORING
- BASELINE: EXACT. 17 scored, 1 DIFF (x.extra2 refs `2 5` / zb `2 4`). (minor
  miss: predicted "~16 scored"; all 17 scored, none NOT MEASURED.)
- ROM signature: EXACT. sub.rom dd8f417b->1922eaa0 MOVED; basic-reloc.rom
  41b8c4ed and merged 53124034 UNCHANGED.
- AFTER: EXACT. x.extra2 -> `2 5` all three, 0 DIFF, all else unchanged
  (x.extra STAYS `2 4`, c.ok `0 5`, o.* drawn, c.*/k.* `24 4`).

## KNIVES (predict, then score)
Only THREE rows reach cpt_asp_done (aspect present): c.ok, x.extra2, o.end.
The tenant no longer distinguishes trailing-comma from clean completion, so a
circleparse knife CANNOT uniquely target x.extra2 -- the split now lives in the
resident's exec_stmt. That is itself the refutation of "restructure".
- K-CT1: cpt_asp_done `jp cpt_finish` -> `jp cpt_err2` (re-impose raise-first).
  PREDICT moves {x.extra2:'2 4', c.ok:'2 4', o.end:'2 4'} -- all aspect-present
  rows revert together (proves the exit carries draw-then-delegate + unification).
- K-CT2: cpt_at_aspect `jp z,cpt_err2` -> `jp z,cpt_finish` (send EMPTY aspect
  slot to the delegate path). PREDICT moves {x.extra:'2 5'} ONLY -- proves the
  empty-slot case must raise-BEFORE-draw and my fix correctly left it alone.

## WALL
PREDICT sub page 1 free +5 B (from D-CIRCMISS's 1617). Main page 1 UNCHANGED
(107 B free at 14fd9a5). basic-reloc.rom + merged byte-IDENTICAL.
