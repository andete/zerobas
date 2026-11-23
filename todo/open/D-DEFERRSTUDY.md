- [ ] 🔴 **STUDY: DEFERRED ERRORS VS RAISING AT THE POINT OF DETECTION — HOW MUCH OF
      THE PER-COMMAND "WHICH ERROR WINS" CODE EXISTS ONLY BECAUSE ZEROBAS DEFERS?
      (D-DEFERRSTUDY, filed 2026-10-24 at Joost's request.)**
      🎚️ TIER 1 — ruled by Joost 2026-10-24: *"it doesn't really fit the tiers I
      guess, so just file as tier 1"*. It is an architecture question, not a keyword.
      🤖 **AUTONOMOUS** — the study (inventory, one prototype family, the
      numbers). The decision to convert beyond that family goes back to Joost
      with the numbers, at step 3 below: it changes the error architecture.
      📏 **Why it was raised.** Joost, on D-CLEAR3ARG: *"every fix like that makes
      me worry we're introducing a ton of command specific error handling, while
      reference probably has generic mechanisms mostly?"* Black-box, the VG-8020
      behaves as if each fault is raised the moment it is detected, so precedence
      falls out of parse order: D-CLEAR3ARG (overflow, then statement end, then the
      range checks) and D-ERRORARG (expression fault, then byte range, then end,
      then 0) both measured exactly that. zerobas instead records many faults as
      PENDING (`penderr_set`, first-error-wins) and raises them at
      `check_expr_errors`, so each site has to rebuild the reference's order by hand
      (D-CLEAR3ARG needed an `fperr_test` arm plus an end check routed through the
      pending path to keep the POOLSIZE restore). At filing: 19 `penderr_set` call
      sites, 17 `check_expr_errors` sites, 9 `stmt_bare_end` callers.
      🎯 **The deferral looks historical.** D-F2-1's deferred discipline predates
      `raise_error`, and [`spec-basic-error-handling.md`](docs/spec-basic-error-handling.md)
      itself says the `SAVSTK` reset lets an error from ANY depth unwind cleanly,
      "strictly more robust", anticipating "a future non-deferred site". So an
      immediate raise from inside an expression is mechanically possible TODAY.
      ⚠️ **What is NOT known, and must be measured, not assumed:** which deferred
      sites protect state an immediate raise would leave half-written — D-CLEARFIT's
      POOLSIZE restore is one; DEF FN shadow frames, string temporaries, a
      half-assigned variable (`var_store_fac`'s contract), FIELD / file state are
      candidates.
      ➡️ **Plan.**
      1. Inventory every deferred-error writer and every realisation point; for
         each, classify "an immediate raise is equivalent" vs "it protects state
         (name the state)". A table in a spec, with file:line.
      2. Prototype ONE family on a branch — the argument range checks are the
         likeliest (the `get_int16_checked` / `eval_byte_checked` callers) — as an
         immediate raise; run the FULL battery, the TIER 6 error rows, the tape
         collection; price the bytes (expected to go DOWN: ordering code deleted).
      3. Report to Joost: bytes, rows moved, what state-protecting sites remain,
         and whether new "which error wins" items would become deletions rather than
         additions. He decides whether to convert further.
      🔴 **Until then, every TIER 6 fix prefers an existing generic path** (as
      D-USRBARE, D-CONTPROG and D-ERRORARG did) and says so in its ✅ note when it
      had to add a site-specific check instead.
      📏 **STEP 1a DONE 2026-10-24** ([`spec-basic-deferr-study.md`](docs/spec-basic-deferr-study.md) §2,
      [`deferr_side_run.out`](scratchpad/deferr_side_run.out)): a USR call counter after a faulting
      operand reads **0 on the VG-8020 and 1 here** for `1/0`, `(1/0)*`, `SQR(-1)` and
      `ASC("")` -- four observable divergences caused by deferral alone, so the
      prototype family is the expression-level DOMAIN faults (Division by zero,
      function domain), not the argument range checks (those already raise at once:
      `LEFT$("A",-1)` reads 0 on both). 🔴 Type mismatch goes the OTHER way: the
      reference evaluates `USR(0)` after `1+"X"`, zerobas does not -- an evaluation-
      order question for its own measurement. PRINT agrees (items realised one by one).
      📏 **STEP 1b DONE 2026-10-24** (spec §2b, [`tmorder_run.out`](scratchpad/tmorder_run.out)): the
      type-mismatch order is its own divergence, filed as D-TMORDER (TIER 6) below.
      📏 **PROTOTYPE MEASURED 2026-10-24, branch `deferr-proto` (local, unpushed;
      spec §4 there):** step 1a 11/12 as the VG-8020, every emulator suite green,
      tapes 42/42; `unit-test` RED (4 files assert the deferred contract; 1 differs
      in VALTYP at the error). 🎯 **That one field is EXPLAINED 2026-10-27**: it is
      VALTYP ($F663) at the moment of the error, which the reference makes visible
      to machine code through H.ERRO -- implemented on main as D-HERRO -- and the
      reference's values are measured per fault ([`herro_run2.out`](scratchpad/herro_run2.out):
      `/` 8, SQR / LOG 8, `\` 2, `0^-1` 2, `(-2)^.5` 8, ASC("") 3). The prototype's
      `/` raise left 2 where the reference has 8 -- so a converted site must set
      VALTYP as the reference has it; main itself already differs on five of these
      (D-ERRVALTYP). Converting further is Joost's call.
      🏗️ **RULED BY JOOST 2026-10-27: *"Convert, family by family"*.** Ship the prototype
      family (expression DOMAIN faults, each leaving VALTYP as measured in herro_run2.out),
      then the other SAME-classified writers one family at a time, each gated and knifed;
      the UNSAFE / UNSURE rows of the classification stay deferred until each is settled.
      ✅ **FAMILY 1 SHIPPED 2026-10-27** (spec §2c): the prototype's sites on main -- `/`, `\` /
      MOD, `0^-1`, SQR / LOG, `(-x)^frac`, `ASC("")` raise AT ONCE through raise_now; CLEAR's
      pool store moved after the memory-top argument; each site leaves VALTYP as measured
      (raise_now8 / raise_now_t) -- 🔮 10/10 VALTYP rows HIT after the fix
      ([`deferr1_herro.out`](scratchpad/deferr1_herro.out); before it, single `/` left 4, not
      the predicted 2). Side effects 11/12 as the VG-8020 ([`deferr1_side.out`](scratchpad/deferr1_side.out); the 12th
      is D-TMORDER). +13 B low (pin pad 16 -> 3). Gate: missing-acceptance row `dz-side`
      ([`deferr1_gate.out`](scratchpad/deferr1_gate.out), 40/40); 🔪 K-DF1 ([`deferr1_knife.py`](scratchpad/deferr1_knife.py)): the four
      ROM files back to HEAD -> `dz-side` alone FAILs (zb `11 5 2`), all five restored
      ([`deferr1_knife.out`](scratchpad/deferr1_knife.out)). Unit tests: msxtest's OPT-IN trap_raise_now() (keeps the
      code, abandons the call; opt-in -- automatic, it stopped test_forint's ON ERROR
      handlers, test_deepexpr_guard and test_statements); test_float's `1\0 DE` and test_expr's `5/0 result=0` rows (the
      deferred tail's zero) removed with a note; test_fpdiv_fast ignores FACTYP / DE when
      both images raise the same fault. ➡️ Next family: the SAME-classified writers in
      [`deferr_sites_table.md`](scratchpad/deferr_sites_table.md), one family per commit.
      📏 **FAMILY 2 (OVERFLOW) MEASURED 2026-10-28** (spec §2d, [`deferr2_run.out`](scratchpad/deferr2_run.out),
      [`herro3_run.out`](scratchpad/herro3_run.out)): the VG-8020 raises EXP(1000), VAL("&H1FFFF"), a 17-digit `&B`,
      1E38*1E38 and CINT(40000) at once (USR counter 0); a store-time overflow runs on (1) on
      both. zerobas defers four (`&B` already immediate). VALTYP differs for CINT (4 there, 2
      here) and `&B` (8 / 2). ⚠️ CINT's writer (fac_to_int_go) and the float overflow
      (round_and_finalize) are SHARED -- measure their other callers first (spec §2d list);
      EXP and VAL are single-site and go first.
      ✅ **FAMILY 2, PART SHIPPED 2026-10-28** (spec §2d cont.): EXP, VAL's overflow arm and `&B`
      raise at once (`&B` with VALTYP 8); penderr_de0 deleted (-6 B). Other callers measured
      ([`deferr2b_run.out`](scratchpad/deferr2b_run.out)): AND / NOT / `\` / float `/` raise at once there; POKE's address runs
      the USR first on both. After ([`deferr2_after.out`](scratchpad/deferr2_after.out), [`herro3_after.out`](scratchpad/herro3_after.out)): all as the VG-8020
      except fmul and CINT. Gate `ov-side` ([`deferr2_gate.out`](scratchpad/deferr2_gate.out)); 🔪 K-DF2 ([`deferr2_knife.py`](scratchpad/deferr2_knife.py)): `ov-side`
      alone FAILs (zb `6 6 2`) ([`deferr2_knife.out`](scratchpad/deferr2_knife.out)). 🔴 fac_to_int_go and check_preexp_bounds were
      converted and the BUILD REFUSED them (check_tenant_closure: the sub-ROM's math
      tenants call both, with main page 1 switched out) -- reverted; they need a
      tenant-safe shape (spec §2d cont.). Docs: concepts/errors.md.
      ✅ **FAMILY 2 COMPLETE 2026-10-28** (spec §2d cont. 2): fac_to_int_go was NOT in the tenant
      closure after all (alone it builds clean; check_preexp_bounds was the failure) -- it now
      raises at once (CINT's VALTYP 4 as there); the float writer keeps deferring for the tenants
      and main's combine_mul / combine_div_float go through page-1 wrappers fp_mul_raise /
      fp_div_raise (17 B of page 1 on 2026-10-28, raise only code 1). 🔮 22/22 rows as the VG-8020
      ([`deferr2c_after.out`](scratchpad/deferr2c_after.out), [`deferr2bc_after.out`](scratchpad/deferr2bc_after.out), [`herro3c_after.out`](scratchpad/herro3c_after.out)). Gate `ov-side2`
      ([`deferr2c_gate.out`](scratchpad/deferr2c_gate.out), 42/42); 🔪 K-DF2C ([`deferr2c_knife.py`](scratchpad/deferr2c_knife.py)): float-arith.asm + expr.asm back to
      HEAD -> `ov-side2` alone FAILs (zb `6 6 6 6 4`) ([`deferr2c_knife.out`](scratchpad/deferr2c_knife.out)). ➡️ Next family: syntax
      (4 -> 2) in deferr_sites_table.md.
      ✅ **FAMILY 3 (SYNTAX) SHIPPED 2026-10-28** (spec §2e): the VG-8020 raises every measured
      syntax fault in an expression at once ([`deferr3_run.out`](scratchpad/deferr3_run.out), 9 forms; 🔮 HIT). zerobas ran on
      for `SQR()`, a bare `USR` and `VAL("&")`. ev_f_empty (the code-4 tail, 16 syntax callers)
      raises at once (+3 B page 1 on 2026-10-28); VAL's syntax arm uses it (-2 B low, same date); ev_f_defer itself
      is NOT converted (cl_not_oom, the stack-floor family, calls it). After: 10/10
      ([`deferr3_after.out`](scratchpad/deferr3_after.out); VALTYP rows unchanged, [`deferr3_herro.out`](scratchpad/deferr3_herro.out)). Gate `sx-side` ([`deferr3_gate.out`](scratchpad/deferr3_gate.out),
      43/43); 🔪 K-DF3 ([`deferr3_knife.py`](scratchpad/deferr3_knife.py)): expr.asm + str-engine.asm back to HEAD -> `sx-side` alone
      FAILs (zb `2 2 2 3`) ([`deferr3_knife.out`](scratchpad/deferr3_knife.out)). ➡️ Left: the TM family (D-TMORDER's, UNSURE rows),
      the stack-floor family (kept deferred by §1b), string OOM (mostly immediate already),
      and the tenant-side UNSAFE rows (convert after each tenant call returns).
      ✅ **FAMILY 4 (OVERFLOW INSIDE A MATH TENANT) SHIPPED 2026-10-28** (spec §2f): the VG-8020 raises
      `10^1000`, `.5^-2000`, `10^500.5` at once ([`deferr4_run.out`](scratchpad/deferr4_run.out); 🔮 3/3; `SIN(1E38)*...` was a
      bad case, it does not overflow). cpow_tail -- every math tenant's way back -- ends in a
      page-1 mt_back that raises code 1 in main (15 B of page 1 on 2026-10-28, 0 low). After:
      5/5 + family 2's rows unchanged ([`deferr4_after.out`](scratchpad/deferr4_after.out), [`deferr4_f2.out`](scratchpad/deferr4_f2.out), [`deferr4_h3.out`](scratchpad/deferr4_h3.out)). Gate
      `pw-side` ([`deferr4_gate.out`](scratchpad/deferr4_gate.out), 44/44); 🔪 K-DF4 ([`deferr4_knife.py`](scratchpad/deferr4_knife.py)): `pw-side` alone FAILs (zb
      `6 6 2`) ([`deferr4_knife.out`](scratchpad/deferr4_knife.out)). ➡️ Left: the TM family (UNSURE), the stack floor (kept), the
      remaining tenant rows (EOF on a device in seqio, the strheap slice OOM, hk_mki in
      disk.rom) -- each convertible after its own call returns, measure first.
      ✅ **FAMILY 5 (EOF ON A DEVICE) SHIPPED 2026-10-28** (spec §2g): `EOF(1)` on CRT: / LPT: is ERR 5 at
      once on the VG-8020 ([`deferr5_run.out`](scratchpad/deferr5_run.out); 🔮 hit); eof_dev raises the tenant's deferred FPERR 3 in
      main after the seqio call (8 B of page 1 on 2026-10-28). After 3/3 ([`deferr5_after.out`](scratchpad/deferr5_after.out)). Gate
      `ef-side` ([`deferr5_gate.out`](scratchpad/deferr5_gate.out), 45/45); 🔪 K-DF5 ([`deferr5_knife.py`](scratchpad/deferr5_knife.py)): `ef-side` alone FAILs (zb `5 1`)
      ([`deferr5_knife.out`](scratchpad/deferr5_knife.out)). ➡️ Left: the strheap slice OOM (needs a CLEARPOOL OOM construction),
      hk_mki (Joost: keep the copy), the TM family (D-TMORDER), the stack floor (kept).
      📏 **STEP 1 CLASSIFICATION DRAFTED 2026-10-24** (spec §1b, [`deferr_sites_table.md`](scratchpad/deferr_sites_table.md)):
      67 writers -- SAME 36, DIFFERENT 2, UNSAFE 10 (tenant context / CLEAR's restore),
      UNSURE 14. ➡️ Next: reorder CLEAR first (blocker), then prototype Division by zero
      + function domain at their main-only points with a pending-first raise helper.
