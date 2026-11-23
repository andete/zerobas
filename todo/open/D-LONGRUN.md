- [ ] 💰 **THE CARVE INVENTORY, RE-RUN 2026-09-17 (D-LONGRUN) — THE MECHANICAL
      FAMILY IS NOT SHUT, IT IS JUST SMALL: ~20-40 B, NONE OF IT IN ONE PIECE.**
      🎚️ BUDGET — funding for TIER 1: this is what `PLAY`'s `X<var>;` is ~30 B
      short of. 🔴 **AND THIS LINE READ `🎚️ TIER 1 funding —` FOR ONE COMMIT,
      WHICH SILENTLY STOLE ANOTHER ITEM'S ROW** — `tools/tier_table.py`'s TAG
      regex wants `TIER n —`, so ` funding` made it parse as NOTHING; this item
      is the first top-level `- [ ]` in a ~1900-line stretch that has no other,
      so its block swallowed the `🎚️` line at docs/TODO-done.md:11056 (T-6443D1) and the sheet printed
      THAT text against THIS line number. The TIER 1 count read 3 before and 3
      after. [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]]
      Every route in [[carve-routes-measured-shut]] re-measured from a clean
      tree: `clone_scout --min 4 --extend` **0 groups** of 1278 spans;
      `scratchpad/jr_mapper.py` **2 sites / 2 B on 2026-09-17** (both page 1,
      `jp kill_status` at `basic/files.asm:1609` and `:1681`) — and Route D
      RENEWS on every insertion, so that figure was taken, not predicted; promotion still
      moves the page-1 ↔ low split 1:1 and **cannot raise their sum**;
      `scratchpad/pair_carve_scout.py` best row **net 5 B**. 🔴 **THE ONE
      UNASKED QUESTION WAS ITS SITE FLOOR** — that tool discards every run seen
      at fewer than 8 sites, and `net = n*(cost-3) - (cost+1)` is linear in
      **cost** as well as in n, so a 12 B run at 4 sites beats a 4 B run at 10
      five times over, and long runs are RARER by construction. Removing the
      floor (`scratchpad/longrun_scout.py`, `--selftest`, reuses the parent's
      normaliser and sizer so the two agree on every shared judgement) gives
      478 rows at 3+ sites. **Live candidates, overlap NOT deduped:**
      ~~`ld ix,SUBROM_ENTRY_BASE_P0+3*SUBROM_IDX_DEFFN`+`call subrom_call`~~
      **TAKEN 2026-09-17 (D-DEFFNSUB), +12 B not the 8 the scout priced**: the
      helper FALLS THROUGH into `subrom_call`, so it costs the `ld` alone (4 B,
      not 7). Page 1 was 22 → 38 B and low 36 → 32 B on 2026-09-17, predicted
      before building and measured exactly. 🎯 **THE SCOUT CANNOT SEE A
      FALL-THROUGH** — `net` assumes a helper that cannot have one, so a row
      whose second instruction is the START of a routine is UNDERPRICED, and
      that is the class to look for first. `call skip_comma`+`jp nz,stmt_error`+`inc hl` (4 sites, 7 B,
      net 8 — the D-SKIPCOMMA family, which has already paid four times);
      `ld hl,0`+`or a`+`sbc hl,de` (5 sites, 6 B, net 8); `ld
      hl,(CURLINE)`+`inc hl`+`inc hl`+`ld e,(hl)`+`inc hl`+`ld d,(hl)`+`ex
      de,hl` (3 sites, 9 B, net 8); `call subrom_call`+`pop ix`+`jp
      c,subrom_absent_error` (3 sites, 8 B, net 6). ⚠️ **`net` IS A CEILING**
      (it assumes a helper that cannot fall through), rows OVERLAP so the
      savings are NOT additive, and `sites` counts SOURCE lines — D-EVSPCLOSE
      lost one to `IF !G8_RESIDENT`. 🎯 **AND THE TOP ROW OF THE NEW SCAN IS
      PRE-REFUSED IN THE SOURCE**: `push de`+`call push_lhs_frame`+`call
      set_factyp_int_ret` (6 sites, net 14) is declined at
      [basic/float-arith.asm:1550](../../basic/float-arith.asm:1550) because the run
      is a FIXED-SIZE FRAME PROTOCOL and a helper's return address lands INSIDE
      the frame — a comment that ends *"the sweep will keep ranking it, and the
      answer will keep being no"*, and it was right. **Reading it also found
      its DE-stash bullet enumerating FIVE call sites when there are SIX**
      (`ev_pw_lp` unnamed); the sixth satisfies the argument (`push de`
      immediately before, `call ev_f` immediately after), so the code was right
      and only the count was stale — fixed here, 0 B. ⛔ **DO NOT re-open the
      `push_lhs_frame` run.** Routes B (page-0 verb eviction, 2563 B behind a
      structural refusal) and C (the sub page-1 eval-bounce co-routine, open
      and unpriced) were NOT re-measured today and are the only routes left
      that could pay in one piece.
