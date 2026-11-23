- [x] ⚠️ **`DEF FN`: two formals of ONE call can alias, and no row separates
      it.** Filed 2026-08-22 by D-DEFFN,
      [`docs/deffn-impl-2026-08-22.md`](docs/deffn-impl-2026-08-22.md) §8. The
      draft binds in place: `FNA(P,Q)` called as `FNA(X, X*2)` from inside an FN
      whose own formal is `X` writes slot 0 before the second actual reads it.
      The reference's behaviour is UNMEASURED — the 82-row design set has no
      case where a caller's formal is read by a LATER actual of a callee that
      overwrites it. Needs a reference reading before the fix is priced; the
      alternative (evaluate every actual into a stack temp first) is ~30 B in a
      region that has none.
      ✅ **THE REFERENCE READING IS TAKEN (2026-08-27, D-FNALIAS),**
      [`docs/spec-deffn-alias.md`](docs/spec-deffn-alias.md). Premise re-run on the
      SHIPPED code, not the draft it was filed against. **Both references agree, so
      there is an oracle: every actual is evaluated in the CALLER's scope.**
      `DEF FNA(P,Q)=P*100+Q : P=3 : FNA(5,P)` → ref **503**, zb **505**;
      `DEF FNA(X,Q)=X*100+Q : DEF FNB(X)=FNA(9,X) : FNB(3)` → ref **903**, zb **909**;
      both controls green at 507/907. ⚠️ I predicted zb correctly and guessed the
      reference WRONG — it does not shadow.
      🔴 **TWO ROWS, TWO CAUSES, NOT ONE FIX.** Top-level is the *grow, never shrink*
      in `dfn_a_x` (deleting it fixes that row and FREES 8 B). Nested is `fn_enter`
      resetting `FN_SLOTP` to slot 0, which **physically overwrites** the caller's
      slot — the grow is not even involved.
      🎯 **This is why D-DEFFNKNIFE's K-GS1 reddened ZERO rows**: it cut exactly that
      block and no row separated the behaviours. `o.alias` is that row.
      🔴 **THE ITEM'S PRICE WAS WRONG AND ITS CONCLUSION SURVIVES ANYWAY.** The fix
      lands in `sub/` (**2464 B free on page 0**, measured), not "a region that has
      none" — but the cheap design (slots above the caller, relocate at `dfn_body`,
      ~+17 B) is **REFUTED BY A SECOND MEASUREMENT**: `FN_AREA` is exactly nine slots
      (`((LINEBUF - FN_PAREA)/11)*11`) and the reference gives **nine formals to a
      NESTED call too** (`o.p9nest` = 9/9/9) — which zerobas matches *precisely
      because it clobbers*. Two coexisting frames need ~198 B where 99 exist.
      ⚠️ The four `o.alias*` rows are deliberately NOT in the probe: `deffn-strict`
      has no XFAIL class and a knowingly-red row would redden a green battery.
      They reproduce from `scratchpad/deffn_alias_probe.py`; adding them is step 1
      of whichever fix is chosen.
      🔴 **"FIX TOP-LEVEL ONLY FOR −8 B" IS REFUTED — BUILT AND MEASURED
      2026-09-09 (Joost chose it: *"b first"*).** Deleting the *grow, never
      shrink* does free space — **sub page 0 1313 → 1320 B, so 7 B, not 8, and in
      the SUB ROM, not main page 1** — and it does not fix `o.alias`. It breaks
      `DEF FN` outright:

          row               vg8020   cf3300   zb BEFORE   zb WITH THE CUT
          o.alias              503      503         505   ERR 6 AT 60
          o.alias.ctl          507      507         507   ERR 6 AT 60
          o.aliasnest          903      903         909   -?.?????????????E+62
          o.aliasnest.ctl      907      907         907   -?.?????????????E+62

      **Both CONTROLS go red**, which is what says this is not a partial fix but a
      broken verb ([before](scratchpad/alias_before_2026-09-09.out),
      [after](scratchpad/alias_after_2026-09-09.out),
      [reverted](scratchpad/alias_revert_2026-09-09.out) — the baseline returns
      byte-for-byte). Reverted; nothing shipped.
      🎯 **AND THE TREE CONTRADICTED ITSELF IN WRITING, WITH THE COMMENT RIGHT.**
      `sub/deffn.asm`'s `fn_enter` says the slot walk *"grows FN_FEND without ever
      shrinking it"* and calls that **`o.nestsame`'s WHOLE POINT**; this item said
      deleting the same four instructions was a clean −8 B win. Both were filed as
      measured. The comment is the one that survived contact
      [[a-fix-falsifies-the-justification-beside-it]].
      📐 **WHY IT CANNOT BE THAT CHEAP.** `FN_FEND` is overloaded: it is the
      visibility window `[FN_PAREA, FN_FEND)` **and** the "an FN call is in
      progress" gate — `FN_FEND == low FN_PAREA` means *no call*, tested by
      `sub/arrays.asm`, `sub/strheap.asm` and `basic/usr.asm`. Freezing it during
      the walk therefore does not merely narrow scope, it tells the rest of the
      interpreter no call is running. A real fix has to separate those two
      meanings, which is bytes — so the honest option set is now **grow the shadow
      area (~+99 B RAM) or accept BOTH divergences**, not three options.
      ✅ **DECIDED 2026-09-09 (Joost, after the refutation): *"we need to match
      the reference"*.** So it is the shadow-area growth — **~+99 B of page-3 RAM
      below `LINEBUF`**, giving the caller's and the callee's frames room to
      coexist — and BOTH rows close: `o.alias` 505 → 503 and `o.aliasnest`
      909 → 903. Accepting the divergences is off the table.
      📐 **WHAT THE SLICE HAS TO DO.** `FN_AREA` is exactly nine slots
      (`((LINEBUF - FN_PAREA)/11)*11`) and the reference gives nine formals to a
      NESTED call too, which zerobas matches *precisely because it clobbers* — so
      two coexisting frames need ~198 B where 99 exist. `fn_enter` must stop
      resetting `FN_SLOTP` to slot 0 and allocate above the caller's frame
      instead, and `FN_FEND`'s two meanings (the visibility window AND the "a
      call is in progress" gate, `FN_FEND == low FN_PAREA`) have to be separated
      — that is what the −8 B attempt proved cannot be skipped.
      📋 **STEP 1 IS THE ROWS**: the four `o.alias*` rows are deliberately not in
      `deffn-strict` (no XFAIL class, and a knowingly-red row reddens a green
      battery). They go in as the fix lands, not before.
      🔴 **AND THE FIRST THING THE AUTHORISATION BOUGHT WAS A REFUTATION OF ITS
      OWN NUMBER (2026-09-09, D-FNNESTDEPTH,
      [`scratchpad/deffn_nestdepth_probe.py`](scratchpad/deffn_nestdepth_probe.py),
      [`.out`](scratchpad/deffn_nestdepth.out)).** *"Match the reference"* makes
      the reference's own ceiling the first question, and the ~198 B figure came
      from ONE row at depth 2. Nine formals at the innermost level, depth 1..4:

          row     vg8020  cf3300      zb   what it asks
          d.n1         9       9       9   nine formals at top level
          d.n2         9       9       9   ...called from inside ONE outer FN
          d.n3         9       9       9   ...from inside TWO
          d.n4         9       9   ERR 7   ...from inside THREE   🔴

      **Both references answer 9 at every depth probed.** A fixed 18-slot area
      closes these two rows and then invents a NEW ceiling of its own — *"a bigger
      number is a different wrong answer, not a fix"*, which is word for word the
      reasoning `spec-basic-trapsvc.md` §6 used and §10 had to **invert** when the
      references turned out to have no fixed array either. Building one here
      repeats that mistake in the same tree, three days later.
      🟢 **AND `d.n4` IS A NEW DIVERGENCE WITH A ROW.** zerobas's ERR 7 at depth
      4 is not the shadow area — it answers 9 at depth 3 *because it clobbers*, so
      nine slots always suffice however deep it goes. It is the `DEF FN` nesting
      cap of THREE that D-FNSTK measured and called *"not a constant, it is the
      Z80 stack's address"*. That item had no differential row until now.
      ➡️ **SO THE SHAPE IS A POOL FRAME, AND IT NEEDS NO NEW RAM AT ALL.**
      `ctl_alloc` is already a HIMEM-bounded allocator (`basic/str-engine.asm`;
      HL = size in, base out, CF=1 on collision) and D-CTLPOOL landed it exactly
      because the references allocate control frames from one pool. A call's
      shadow frame is the same object: allocate `formals × 11` per call, the
      caller's frame is never in the way, **both alias rows close**, depth becomes
      HIMEM/`CLEAR`-bounded as `d.n4` asks, and it **frees** the 99 B `FN_PAREA`
      array instead of spending 99 more. `FN_FEND`'s two meanings separate for
      free: the frame pointer is the window, "no frame" is the gate.
      ⚠️ **THE COST IS ADDRESSING.** Slots are reached today by LOW BYTE against a
      fixed page; a pool frame is at an arbitrary 16-bit address, so the walk goes
      16-bit through `sub/deffn.asm`, the lookup in `sub/arrays.asm`, the GC root
      walk `sg_walk_fnframe` in `sub/strheap.asm` and `basic/usr.asm`'s
      in-progress test. A slice, not an edit.
      🎯 **THE DECISION DID NOT CHANGE — THE SHAPE DID.** Joost authorised
      ~99 B of page-3 RAM for a fixed array; the measurement says that array is
      the wrong object, and the pool route is both MORE faithful to *"match the
      reference"* and RAM-NEGATIVE, at the price of a wider change. Spending an
      authorisation on a shape it was not given for is the thing to check first
      [[a-priced-decline-is-a-claim-about-a-design]].
      🎚️ TIER 6 — `DEF FN` formals aliasing
      🔁 **PARKED (Joost, 2026-09-10): every TIER 5 item waits until TIERS 1–4 are clean, and
      *"when we get to TIER 5, we'll have to do a prioritization together"* —
      the TIER 5 order is a joint pass, not the loop's pick.
      ~~🙋 NEEDS-JOOST~~ — the ~99 B array he authorised is refuted; the pool route
      needs no RAM but is a slice across four files, and that is a bigger yes.
      🏗️ **RULED BY JOOST 2026-09-27 (his "ask me in detail" pass): YES — THE POOL ROUTE.** Evaluate every actual into the control
      pool before binding (`docs/spec-deffn-alias.md`). ⚠️ The 503-vs-505 reading
      quoted to him is 2026-08-27's; re-run it on today's ROM before building.
      📏 **RE-RUN 2026-11-05 on today's ROM** ([`fnalias_today.out`](scratchpad/fnalias_today.out),
      scratchpad/deffn_alias_probe.py): `o.alias` VG-8020 503 / CF-3300 503 / zerobas 505,
      `o.aliasnest` 903 / 903 / 909, both controls equal (507, 907). 🔮 "unchanged since
      08-27" HIT. The divergence stands; the pool-route build is next.
      🤖 **AUTONOMOUS** — ruled above; price it from a clean tree, carve first.
      ✅ **SHIPPED 2026-11-07 (built by a subagent from the spec; reviewed, tested and gated
      here).** Two passes (docs/spec-deffn-alias.md §8): pass 1 (sub/deffn.asm dfn_actual +
      basic/deffn.asm fn_st) evaluates every actual in the CALLER's scope and parks it --
      a number coerced into an 11-B `[name][type][value]` entry, a string snapshotted onto
      the temp-descriptor stack (route (a), the reference's own 10-deep shape); pass 2
      (dfn_body) binds the formals from the entries, a repeated formal taking the LAST
      actual as both references do (o.dupformal 2, o.dupformal3 32, o.dupstr b --
      [`fnalias2_scout.out`](scratchpad/fnalias2_scout.out)); a call releases its parked temps at its end (q.tend 111 on both
      references, ERR 16 here before). 🔴 **ONE DEVIATION FROM THE RULED SHAPE, STATED:** the
      parked entries live on the main servicer's own Z80 stack, not in a ctl_alloc pool
      block. Measured both: the pool block slid the whole live stack per entry (D-SPMERGE)
      -- `DEF FNA(X)=FNA(X)` reached ERR 7 in 1010 jiffies against HEAD's 718 and b.recurse
      ran past its capture -- while the stack (the same merged free space under the frontier,
      under stk_guard, unwound by an error's SP reset) took 723
      ([`fnalias2_time_head.out`](scratchpad/fnalias2_time_head.out), [`fnalias2_time_pool.out`](scratchpad/fnalias2_time_pool.out), [`fnalias2_time_stack.out`](scratchpad/fnalias2_time_stack.out)). Since D-SPMERGE (ruled
      09-11) the Z80 stack and the control pool are one region, so this keeps "evaluate
      every actual into the control pool before binding"; flagged for Joost all the same.
      📏 After: o.alias 503 / o.aliasnest 903 on all three ([`fnalias2_aliasprobe_after.out`](scratchpad/fnalias2_aliasprobe_after.out)); 11
      new deffn-probe rows agree on all three sides ([`fnalias2_newrows.out`](scratchpad/fnalias2_newrows.out)); the whole probe
      0/91 divergent on zerobas ([`fnalias2_deffn_zb2.out`](scratchpad/fnalias2_deffn_zb2.out)). Knife: HEAD's two asm files -> the new
      rows red (505 / 909 / ERR 16 / ERR 16, [`fnalias2_knife_rows.out`](scratchpad/fnalias2_knife_rows.out)); K-PARK (the parked actual
      unrooted) turns o.gcpark / o.gcroot / o.str9 red ([`fnalias2_kpark_rows.out`](scratchpad/fnalias2_kpark_rows.out)). Bytes: main's
      $6CF3 pin pad +65, sub page 0 +39 (124 -> 85). tests/test_deffn_alias.py (9 rows; the
      host bridge gained an OPT-IN `bridge_keeps_tenant_sp` -- no FN call could run on the
      host before, and the default broke test_ramad). 🟢 **AND d.n4 CLOSED TOO:** the nesting
      cap of three (ERR 7 at depth 4, D-FNSTK) is gone -- depth 4 answers 9 on all three
      ([`fnalias_pin_nest.out`](scratchpad/fnalias_pin_nest.out), refcache off); both probes' pins left tools/filed-row-known.txt
      after a by-hand re-run with the refcache OFF ([`fnalias_pin_alias.out`](scratchpad/fnalias_pin_alias.out): all four rows
      agree). 🆕 q.frelit stays divergent: a literal
      string actual costs 4 B here and 0 on both references (the D-LITREF / D-TEMPD10 class).
