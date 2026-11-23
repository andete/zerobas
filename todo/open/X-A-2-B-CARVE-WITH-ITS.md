- [ ] 💰 **A 2 B CARVE WITH ITS EVIDENCE ALREADY ATTACHED: `ems_typecheck`'s
      two `pop de` ARE PROVABLY UNNECESSARY.** Filed 2026-08-26 by D-MIDOP
      ([`docs/spec-basic-midop.md`](docs/spec-basic-midop.md) §4). They were
      written to be correct under a DISAGREEMENT between two records about
      whether `raise_error` resets SP — and **knife K-MD2 deleted both and moved
      0 rows of 9**, so it does: the trap arm at `basic/interp.asm`:1022, the
      abort arm through `fre_abort_low` (`:1731`, citing `4d35b6d`).
      🎯 **NOT TAKEN AT THE TIME ON PURPOSE**: popping is correct under both
      readings, and removing it makes the code DEPEND on the SAVSTK behaviour
      rather than merely survive it. `els_tc_common`'s header says *"every path
      out of here errors"*, so the dependency is sound — but that is a decision
      to take deliberately, not at the end of a slice.
      ⚠️ **AND THE SAME 2 B SIT IN `ems_err_pop2`/`ems_err_pop1` NEXT DOOR**, and
      in every other hand-rolled pop-then-raise tail in the tree. **The class is
      worth more than the bytes**: `scratchpad/` has no sweep for "a pop that
      only exists to satisfy a raise that unwinds anyway". ~~Unpriced.~~
      ✅ **SWEPT AND PRICED 2026-08-28 (D-POPRAISE,
      [`docs/spec-popraise.md`](docs/spec-popraise.md),
      `scratchpad/popraise_sweep.py --selftest`)**, and the class splits into
      THREE questions the filing above runs together. **16 tails**, never-return
      set derived as a fixed point from `raise_error` (120 routines), not
      declared. **Q1 delete the pops: 21 B — still 🙋 and still for the reason
      given above.** Q2 merge identical bodies: 21 B. 🎯 **Q3, the one neither
      the filing nor Q2 could see: 34 B.** Tails that share a RAISE TARGET but
      differ in POP COUNT are not identical bodies, yet **one chain serves them
      all** — the deeper entry falls through into the shallower one, the shape
      `ems_err_pop2 -> ems_err_pop1` has had all along.
      ✅ **THE `fp_runtime_error` GROUP SHIPPED 2026-08-28: −13 B; page 1 read
      106 → 119 B free on 2026-08-28** (a READING, not a standing figure — run
      `make basic-reloc`). Four routines (`cee_abort_fp`/`cepb_abort_fp`/
      `ela_abort_fp`/`elas_abort_fp`), all page 1, **18 B of code measured
      2026-08-28**, were one sequence in four register names; the register was free because the word is DISCARDED and
      `fp_runtime_error` writes A/DE/HL before reading anything.
      🔴 **THE KNIFE ON THE POPS CANNOT FALSIFY THIS** (K-MD2 already moved 0 of
      9), so the four ENTRIES are witnessed one knife each — 7 rows, DISJOINT,
      0 controls moved. 🔴 **AND THE FIRST CUT OF THAT KNIFE WAS A DESIGNED
      NO-OP**: retargeting to `stmt_error` re-raises the identical code, because
      `stmt_error` opens with `call check_expr_errors` (D-STMTPEND); three tails
      read "UNWITNESSED" for a reason that was not about the tails.
      ✅ **AND THE `stmt_error` GROUP'S ONE FREE MEMBER SHIPPED: `ela_err equ
      ems_err_pop2`, −5 B; page 1 read 119 → 124 B free on 2026-08-28.**
      🔴 **I FILED THAT GROUP AT "13 B nominal, ~10 B net" AND THE MEASUREMENT
      REFUTES IT — it is worth 5 B.** What decides is not the ADDRESS but the
      **CALL SITE'S JUMP FORM**: a `jr` caller PINS its target beside itself, so
      moving the body costs +1 B per site and eats most of a 3–4 B body.
      `ee_synerr_pop` (2 `jr`) nets **+2 B**, `ex_let_err` (2 `jr`) nets **+1 B**,
      `ems_err_pop2` (2 `jr`) is the canonical; only `ela_err` is reached solely
      by `jp` (arrays.asm:849) and only it could move. Witnessed alone by K-EL1
      ([`scratchpad/elaerr_knife.py`](scratchpad/elaerr_knife.py), row `s.ary`).
      ➡️ **STILL OPEN, measured, not shipped:**
      `gosub_stk_over` (**4 B, measured 2026-08-28**, adjacent, page 1, but
      **UNWITNESSED** — no probe row fills a control stack or over-nests a
      trap); `els_tc_common` (**4 B, measured 2026-08-28**, but it is a LOW →
      page 1 region trade, not a carve).
      🎚️ BUDGET — 2 B carve
      ~~🙋 NEEDS-JOOST — Q1 only (page-1 budget was the WRONG reason on the filing:~~ (re-marked 2026-09-10, see below)
      a carve frees bytes. The real call is whether to depend on `raise_error`
      resetting SP).
      🎯 **RULED (Joost, 2026-09-10): carve freely under the standing ≤20 B rule.** BUDGET;
      picked when a keyword tier needs the bytes.
      🤖 AUTONOMOUS — a carve under the standing rule (ruled 2026-09-10).
