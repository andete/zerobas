- [ ] ⚠️ **`clone_scout` prices LABEL-BLOCKS, so a routine split by an interior
      label is priced at a fraction of its collapse.** Filed 2026-08-23 by
      D-DEFFNLAND, [`docs/spec-basic-deffnland.md`](docs/spec-basic-deffnland.md)
      §4.3. `arga_pack_fac`/`arga_pack_single` were ranked at **14 B** and
      measured at **27 B**: the tool compared only their 22-byte header spans,
      because `apf_lp`/`aps_lp` are separate symbols, so the two identical
      13-byte LOOPS were invisible to it. The remaining ranked groups are
      therefore FLOORS, not estimates — and 🔴 **three of them are now known to
      be worth ZERO** (§4.4: `ev_t_mul`/`ev_t_div`, `ev_e_add`/`ev_e_sub`,
      `dde_div`/`pn_div`/`pfi_div` all push PERSISTENT frames a helper's own
      return address cannot sit under). Unspent and unre-ranked:
      `raf_noround`/`rsp_noround` (12), `ev_usr_index`/`usr_index` (8),
      `detok`/`pu_emit_tail` (8), the `files.asm` four (8),
      `ev_ff_stick`/`ev_ff_strig` (6).
      ✅ **`clone_scout --extend` SHIPPED 2026-08-26 — AND THE RANKED GROUPS ARE
      NOT FLOORS TODAY.** After grouping, each group now grows forward across
      label boundaries while every member's next block still agrees, bounded by
      a real terminator.
      📏 **CALIBRATED EXACTLY ON THIS ITEM'S OWN EXAMPLE.** `head 22 B` alone
      gives `save = (n-1)·22 − 4n = **14**`; extended by the 13-byte loop it
      gives `save = (n-1)·35 − 4n = **27**` — the two numbers the item records
      as *ranked* and *measured*. The match test was verified against the
      pre-carve source (`dd0c84d~1`), where the two loop bodies compare EQUAL.
      🔴 **AND ON TODAY'S TREE IT FINDS NOTHING.** 8 groups extend
      (`dde_div` +11 B, `vsf_single` +42, `print_string` +57, …) and **not one
      of them reaches the ranked table**; every group that IS ranked extends by
      **zero**, so the ranked rows are byte-identical with and without the flag.
      The floors claim is now measured, and it is currently vacuous.
      🎯 **THREE SHAPES, AND ONLY THE CALIBRATION SEPARATED THEM.**
      **(1) merge-then-match** — pre-merging blocks into terminator-delimited
      runs made spans LONGER and so LESS likely to match: **10 groups / 55 B**
      against 27 / 180. Two routines sharing a prefix and diverging after it are
      a real clone at block granularity and vanish at run granularity. Wrong
      shape, discarded.
      **(2) strict extend** — required successors byte-identical, and **failed
      this item's own example**: `apf_lp`/`aps_lp` differ in exactly one
      position, `djnz apf_lp` vs `djnz aps_lp`, each block's jump into ITSELF.
      **(3) alpha-normalised extend, terminator-bounded** — normalise a block's
      own label to `<self>` before comparing, and stop where the routine does.
      🔴 Unbounded, (3) ran away: `gosub_stk_over` grew **+1307 B** and
      `tokenise` **+1107 B** — the rest of the file, not a clone. Those values
      never reached the output, which was LUCK, not design.
      ⚠️ **THE `arga_pack` PAIR IS ALREADY SPENT** — `basic/float-arith.asm` now
      carries *"Two ENTRY POINTS … is 27 B smaller"*, so the item's example is
      history, not a candidate. That is why the calibration had to be done
      against `dd0c84d~1` and by arithmetic rather than by re-ranking it.
      ➡️ The five unspent groups it lists are unchanged by this: they do not
      extend. Re-ranking them is still owed, but not for the label-block reason.
      🎚️ BUDGET — carve tool
      🤖 AUTONOMOUS — the reference or a gate settles it; finishable unattended (tool fixed + calibrated 2026-08-26; the ranked groups extend by zero).
