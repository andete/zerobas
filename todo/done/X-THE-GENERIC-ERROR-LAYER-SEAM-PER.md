- [x] 💰 **THE GENERIC ERROR-LAYER SEAM: per-verb error checks that duplicate a
      layer that already exists — a carve AND a correctness seam.** Opened
      2026-08-24 by D-SWAP3, [`docs/spec-basic-swap3.md`](docs/spec-basic-swap3.md)
      §6, on the user's observation that SWAP is one instance of a class. **Two
      generic layers get reimplemented per-verb:**
      * **Trailing-token → ERR 2**: `exec_stmt`'s `es_noentry`
        (`basic/interp.asm`) already raises `Syntax error` for any leftover token
        after a statement returns via `jp exec_stmt`. Bespoke duplicates alias
        `pl_syntax` and are reached from a `cp ','`/`cp COLON`/`or a` peek PAST
        the last valid argument: `graphics.asm:748/798` (PAINT 3rd/4th arg),
        `1203`/`1210` (`PUT SPRITE 0`/`0,`), `1250` (5th sprite arg),
        `play.asm:73` (PLAY 4th voice). **DELETED so far: SWAP, PAINT `:798`,
        SPRITE `:1250`, CIRCLE `cpt_asp_done`** (D-SWAP3/D-PAINT4/D-SPRITE5/
        D-CIRCTC). ⚠️ The incomplete-arg siblings (PAINT `:748`, SPRITE
        `:1203`/`:1210`) are NOT deletable — they raise before the effect and
        agree on both refs — the per-site oracle split, measured. PLAY `:73` is
        KEEP (raises before playing). 🟢 **CIRCLE turned out DELETABLE too, not a
        restructure** (D-CIRCTC — the classifier's one wrong verdict, reasoned not
        measured): the resident's `cp_done` already `jp exec_stmt`s after the
        draw, so the trailing comma delegates like the other three. **ALL FOUR
        trailing-token members are now SHIPPED; this half of the seam is CLOSED.**
      * **Missing/empty operand → ERR 24 / ERR 2**: `ev_f`'s
        `ev_f_missop`/`ev_f_empty` machinery — the D-MISSOP arc already found
        this is *"one rule at 16 slots"* (docs/spec-basic-missop.md).
        🟢 **FIVE MEMBERS SHIPPED 2026-08-26, AND ONLY KEY'S ABSENT FORM IS
        LEFT** (and that one is BLOCKED on ~160 B of defaults data, not on
        knowledge). What each one COST: `ev_f_err`'s seven sites (D-EVFERR)
        spent **0 B**; `PLAY` (D-PLAYOP) spent **+2 B**; `PRINT USING`
        (D-PUSING) **freed 6 B** and turned 2 filed rows into 13; `MID$()=`
        (D-MIDOP) spent **+6 B**, and spent it in the low region, not page 1;
        `DRAW` (D-DRAWOP) spent **0 B**.
        🎯 **ONE RULE, THREE VERBS, THREE DIFFERENT PRICES.** The last three
        slices all split the SAME shared tail — `call str_eval / jp nc,<one
        error>`, where str_eval declines both for *"nothing is here"* and for
        *"this is not a string"* and the references answer **24** and **13**.
        The rule is shared; **the price is a property of each site's stack and
        neighbourhood**, and so is the fix's SHAPE — an EOL/`:` peek works at
        `PRINT USING` and is WRONG at both `MID$()=` and `DRAW`, where a stray
        operator must read 24. Ask *"can a FACTOR start here"*, which is `ev_f`'s
        question, by delegating to `els_tc_common`.
        📏 **D-PUSING is still the one to read before pricing anything else**:
        the filed item named TWO rows and the verb had **THIRTEEN**, and the
        rows that found that were the ones added to keep the fix NARROW. 🟢 **THE `ev_f_err` SEVEN-SITES MEMBER IS SHIPPED**
        (D-EVFERR 2026-08-26, [`docs/spec-basic-evferr.md`](docs/spec-basic-evferr.md)):
        five live sites split by MEANING onto `ev_f_empty` (2) and `ev_f_ifc`
        (5) at **ZERO bytes**, 11 DIFF → 1, and `ev_f_err` now has **no
        incoming jumps at all**. 🔴 Its lesson is the seam's own: **four of the
        five rows filed as AGREEING agreed through a DIFFERENT LAYER** —
        `es_noentry`, `fch_check`, `gfx_syntax` — which is the same shape as
        this seam's thesis read backwards, and it is why a per-site oracle is
        not optional here either.
      🎯 **The failure is not just wasted bytes — the bespoke check is usually
      subtly WRONG**: SWAP had wrong CODE (5 not 2) AND wrong ORDERING (raised
      before its exchange; the ref swaps then raises). The SAME ordering bug is
      FILED for two more verbs — **PAINT's 4th argument** (D-PAINT4, CLOSED
      2026-08-24, fill-then-raise) and **CIRCLE's trailing comma** ("draw before
      raising", still open, the cross-ABI tenant case) — so this class has three
      measured instances, **two fixed (SWAP, PAINT)**.
      ⚠️ **THE CARVE IS REAL BUT NOT UNIFORM, and the split is the whole job.**
      SWAP was a clean 23 B DELETE because its side effect (the exchange) is
      INLINE and guards the cursor, so falling to `jp exec_stmt` with the cursor
      on the leftover token Just Works. PAINT/SPRITE/CIRCLE issue their side
      effect through a sub-ROM TENANT (`ep_draw`/`GFX_OP`), so whether deleting
      the check is free (draw, `jp exec_stmt`, boundary rejects — matching the
      ref's draw-then-fail) or a restructure depends on whether the parse cursor
      SURVIVES the tenant round-trip. PAINT's DID — `ep_draw` already `push hl`s
      across the tenant and `pop hl`s before `jp exec_stmt`, so it was a clean
      delete like SWAP; CIRCLE's may not (parse in the tenant, result tested
      before the draw op — likely a second flag, not a delete). That is a
      per-verb MEASUREMENT (build +
      3-machine differential + a value read for the side effect), one verb at a
      time — never a mechanical sweep. Reuse `scratchpad/swap3_probe.py`'s shape.
      🎯 **BUT MEASURING PER-VERB DOES NOT MEAN THE VERBS ARE DIFFERENT — HEAVY
      SHARING IS THE EXPECTED RESULT.** The per-verb differential CONFIRMS a verb
      belongs to the shared rule; it does not presume uniqueness. Direct
      precedent: D-MISSOP measured the missing-operand case verb-by-verb and found
      **one rule at 16 slots** (docs/spec-basic-missop.md). So the likely finding
      is that most of these bespoke ERR-2 raisers ARE the one `es_noentry` rule
      wearing per-verb labels — which is why the consolidation is a real carve,
      not a marginal one. The per-verb measurement is the ADMISSION test; the
      shared handler is the payoff.
      📏 **ONE-PASS CLASSIFICATION 2026-08-24** (`scratchpad/seam_classify.py`,
      SPRITE/CIRCLE/PLAY in a single differential, each with an effect column):
      * **SPRITE `PUT SPRITE …,` (`:1250`, 5th arg) → DELETABLE — ✅ SHIPPED
        (D-SPRITE5, −8 B).** Refs PLACE then raise (`2 30`, sprite-0 Y attr), zb
        raised before placing (`2 209`); `pspr_go` guards the cursor like `ep_draw`
        (and has no overflow check, so even cleaner). 8 rows, 3 DIFF → 0, knives
        2/2 EXACT. [`docs/spec-basic-sprite5.md`](docs/spec-basic-sprite5.md).
        The `:1203`/`:1210` incomplete-arg sites KEEP their gfx_syntax (raise
        before place, agree — sp.incomp/sp.barep).
      * **CIRCLE trailing comma → classified RESTRUCTURE, but SHIPPED AS A CLEAN
        DELETE** (D-CIRCTC, −5 B). Refs DRAW then raise (`2 15`/`2 5`), zb raised
        before (`2 4`) — the filed `x.extra2`. The classifier's *"second flag, not
        a delete"* was REASONED, not measured, and wrong: `cp_done` already
        `jp exec_stmt`s after the draw, so deleting `cpt_asp_done`'s `cp ',' /
        jp z,cpt_err2` delegates the leftover comma to the statement boundary —
        draw-then-raise, like the other three. 🎯 The one wrong verdict in the
        one-pass classification, and it was wrong by reasoning where the others
        were right by measuring.
      * **PLAY 4th voice (`:73`) → KEEP.** Refs raise BEFORE any voice plays
        (`2 0`, `PLAY(0)`=0-not-playing) — the bespoke check's ordering is CORRECT.
        🎯 This is the concrete verb a blind batch delete would have REGRESSED
        (it would have made zb play 3 voices then error, where the reference plays
        none). The measurement is exactly what caught it.
      ✅ **RETIRED 2026-08-28 — BOTH HALVES ARE CLOSED.** Trailing-token: all four
      members shipped (SWAP −23 B, PAINT, SPRITE −8 B, CIRCLE −5 B).
      Missing-operand: five of six shipped (`ev_f_err` 0 B, PLAY +2 B, PRINT USING
      −6 B, `MID$()=` +6 B, DRAW 0 B); only `KEY`'s absent form remains, blocked on
      ~160 B of defaults DATA rather than on knowledge, and it lives on its own
      🔭 item rather than here.
      🎯 **WHAT THE SEAM TAUGHT, and why the doc stays: ONE RULE, SIX VERBS, SIX
      DIFFERENT PRICES.** The rule is shared; the price and the FIX'S SHAPE are
      properties of each site's stack and neighbourhood. An EOL/`:` peek is right
      at PRINT USING and WRONG at both `MID$()=` and DRAW. A blind batch delete
      would have REGRESSED PLAY — the per-verb measurement is exactly what caught
      it. Retired because nothing is left to DECIDE, not because the class stopped
      mattering: on Joost's 2026-08-28 steer toward aggregation/size work, the live
      remainder of this class is the ranked CLONE GROUPS, not this item.
