- [x] 💰 **A DATA-ONLY SPAN STILL CONFERS FALLTHROUGH ON WHATEVER FOLLOWS IT**
      (filed 2026-08-22 by D-PROLOGUE, §12.5). `err_io: db "load",…` falls into
      `do_cload` in this model, and nothing ever runs off the end of a string
      table. **Measured**, cutting fallthrough only out of spans that EMIT DATA
      (never out of empty ones — that is §12.1's 1227-span error): main 43 edges
      → **1 finding, `ex_sep`, 4 B**; sub 77 edges → **4 findings, 97 B**.
      🔴 **NOT SHIPPED, AND THE SUB COLUMN IS WHY: `sub_p1_table` (72 B) IS THE
      PAGE-1 ENTRY TABLE** — unmistakably live, reached by the main ROM through
      **address arithmetic** (`SUBROM_ENTRY_BASE_P1 + 3*index`), which no
      name-following model can see. So this change does not merely find dead
      code, it surfaces a whole CLASS of labels reached by arithmetic rather than
      by name (`em_ill_direct` looks like the same shape, indexed off a message
      table). Each needs a seed or an allowlist entry with a reason before the
      gate could be believed. That triage is the slice, not the edge rule.
      ✅ **TRIAGED AND SHIPPED 2026-08-28 (D-DATASPAN),**
      [`docs/spec-dataspan.md`](docs/spec-dataspan.md) — and the numbers above moved
      in BOTH directions.
      🔴 **THE TRACKED SCRIPT REPRODUCED §12.1'S CATASTROPHE, NOT THIS
      MEASUREMENT** — `main 1195 findings / 28820 B in a 22510 B ROM`. One line:
      `return seen or True`, which is `True`, so an EMPTY span counts as data-only
      — the exact thing this item says was excluded. The script implements §12.1's
      DEMONSTRATION (its own commit is titled *"the obvious fix reports 27 KB in a
      22 KB ROM"*); `--empty-too` now reproduces that deliberately, and with empty
      spans excluded the filed numbers come back exactly.
      🔴 **THEN BOTH `dw`-TABLE FINDINGS TURNED OUT TO BE THE RULE'S OWN ARTIFACT.**
      A fallthrough edge and a REFERENCE edge to the same label are ONE entry in
      the edge dict, so discarding one discards both: `stmt_table` contains
      `dw ex_sep` AND is followed by `ex_sep`. Main's only finding was manufactured
      by the rule; `em_table`/`em_ill_direct` is identical. **main 1 → 0,
      sub 4/97 B → 3/82 B.**
      ✅ **ALL THREE SURVIVORS WERE THE ARITHMETIC CLASS.** `sub_p1_table` (72 B)
      and `sub_p0_table` are now SEEDED, not allowlisted — an allowlist entry would
      claim "dead and kept on purpose", which is false. `tkf_ref65535`/`tkf_ref32768`
      were GENUINELY DEAD and are deleted: `flt_to_int16` lives in
      `basic/float-arith.asm`, not in sub's closure, and all three loads are BY NAME
      with no arithmetic over the table. ⚠️ `tkf_ref32767` stays — the file header's
      plural *"the tkf_ref* bound tables … used by tkf_cmp32767"* is true of ONE of
      three, and that is how two dead tables kept their place.
      📏 **Sub page 0 was 2434 B → 2444 B free on 2026-08-28**; main does not move.
      The bytes are not the point — the gate now cuts 26 main / 37 sub fallthrough
      edges that never existed. `--blind` still exits non-zero; both new predicates
      unit-checked (empty is NOT data-only; a named target keeps its edge); battery
      43/43 with 7 flakes recovered serially.
