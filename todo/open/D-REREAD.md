- [ ] 💰 **D-REREAD — REREAD EACH ROUTINE AGAINST ITS CONTRACT: 82 B FROM THE FIRST TEN
      (2026-10-30).**
      🎚️ BUDGET — ROM space toward the reference; the space every later tier spends.
      🤖 **AUTONOMOUS** — Joost noticed that the zerobas fixes he ported into C-BIOS
      nearly all came out a few bytes smaller on a second look. The carve routes
      tried so far (`jp`→`jr`, dup spans, promotion, instruction pairs) are
      mechanical; this one reads a whole routine, writes its contract (registers
      and flags at every exit, callers, fall-through, internal labels reached from
      elsewhere) and rewrites it.
      ✅ **SAMPLE, 10 routines** ([`reread_sample.md`](scratchpad/reread_sample.md)):
      measured 2026-10-30: +23 B low region, +59 B main page 1; every premise checked in the source,
      layout facts pinned by assembly-time guards; no common path slower.
      ➡️ **THE ROUTE:** batches of ~10, largest first
      ([`reread_spans.out`](scratchpad/reread_spans.out) ranks them -- re-derive it,
      the ranking rots with every carve); `gates-fast`, then the full battery, one
      commit per routine; record the yield per batch and STOP when it falls below
      ~2 B a routine. A rewrite that changes behaviour is filed and measured, never
      applied (D-PRSTRFN below came out of the first batch -- and its fix was the
      held-back rewrite: another 52 B, measured 2026-10-30).
      🧬 **SINCE 2026-10-31, WITH z80flow** (tools/z80flow/README.md): each reviewer brief
      carries `make contract NAME=<routine>` for every routine in the batch (the register
      premises are then the tool's; memory / layout / timing are still checked by hand), and
      the batch closes with `make contract-diff BASE=<batch start>` at `broken: 0`, its counts
      in the commit message. It does NOT see timing: batch 6's withdrawn fp_trunc diffs as
      `fewer_clob: fp_trunc DE`, 0 broken (measured 2026-10-31) -- the tapes still run. If
      batch 7 is not faster than batch 6 with it, the step becomes optional.
      ✅ **BATCH 2 (2026-10-31), measured 2026-10-31: low region free 10 -> 83 B plus
      6 B of its pin pad, main page-1 pin pads +65 B -- ~144 B from nine
      routines** (widen_uint_to 42: digits ride the stack, no WIDIG; fp_cmp 19:
      operands swapped for a negative sign instead of the answer; apsub_close 8:
      ldi, not IX; ex_let_arr 4; dig15_shr 6 into the $3297 pad; ex_print 35: the
      class from fch_mode_class's CF, the sink computed by `adc a,-5`;
      parse_coord 17: the STEP flag on the stack, 16-bit adds; trap_return_check
      15). HELD BACK: the dl_cmd / is_cmd fold (~39 B; it routes the prompt's RUN
      test through rst $10, i.e. the H.CHRG hook -- decide that first), dig15_shr
      taking the shift in A (an interface change), ev_ff_ckdone's 3 B (they only
      grow the $4EF8 pad). tests/test_fpdiv_fast.py counts WIDIG as dead scratch
      now; the `ela_abort_fp` alias went with ex_let_arr's change. Write-up:
      [`reread_sample.md`](scratchpad/reread_sample.md).
      ✅ **BATCH 3 (2026-10-31), measured 2026-10-31: low region free 83 -> 158 B plus
      3 B of its pad, main page-1 pads +24 B and its tail 345 -> 356 B -- ~113 B
      from ten routines** (cmul_int 26: the sign in C, one borrow for the bound;
      fp_add's opposite-sign span 34: one subtract for both orders; ex_sound 16,
      the latch/latch/data port order kept; LINE 18 into the $6CF3 pad; gosub_push
      7; run_prog_at 4 -- clear_vars already runs trap_init; raise_error_hl 2;
      ev_ff_cv 3; str_func_ff 2; ems_close 1). HELD BACK: SOUND's single latch
      (changes the port sequence), RUN's DATA-cursor stores (PEEK($F6A5) would
      read 3 after RUN), CVI/CVS/CVD's hook arithmetic (CVI slower),
      ems_close's pops before raise_error (a filed item). tests/test_intfast.py
      compares A / F / DE now (BC and HL are combine_*'s documented clobbers);
      its register knife moved from C to E.
      ✅ **BATCH 4 (2026-10-31), measured 2026-10-31: low region free 158 -> 214 B and
      its pad 53 -> 98 B, page-1 pads +11 B -- ~112 B** (domain_convert_core 44:
      dcc_bound5 folded in, one tail; mul16x16_32 40 + its caller 6: the product in
      DE:HL, ~3x faster a bit, MULCAND / MULTPLR / MUL32 no longer written;
      fre_abort_low 3; ex_mid_stmt 5; field_item 5; ev_usr 9). NOT YET APPLIED (the
      reviews gave them only partly verbatim; next batch): ex_paint (~19 B),
      flo_emit_fixed (~55 B), evmc_csng / evmc_cdbl (4 B), try_text_slot (12 B,
      touches its island-1 caller). HELD BACK: fre_abort_low's reuse of
      psg_silence's undocumented A = 0, ex_mid_stmt's STRPTR re-read, a table for
      ev_ff_mathconv (ABS 17 T -> ~100 T), PAINT's mode-mask arithmetic and
      domain_convert_core's zero-test drop (behaviour changes), D-POPRAISE Q1's
      pops (Joost). tests/test_intfast.py and test_fpdiv_fast.py compare DE only
      now -- every value identical, the dead A / F / BC / HL not; their flag
      knife moved to register D. Tapes: Boulder Dash NEAR -> SAME, Boulder Dash
      II NEAR 24 -> 120 cells -- a snapshot taken at a fixed time moves with
      BASIC's speed.
      ✅ **BATCH 4b (2026-10-31), measured 2026-10-31: the $3297 pad 98 -> 152 B, page-1
      pads 2106 -> 2131 B -- ~79 B** (flo_emit_fixed 55: dec_exp read once, its
      -1..14 bound from flo_is_fixed, the only way in; ex_paint 19: CHRGTR's Z for
      both dangling commas, the ep_missing trampoline gone, one GFX_B store;
      evmc_csng / evmc_cdbl 6 via evmc_prologue). dig15_shr's `jr` to
      dshr_allzero became `jp` (the grown pad). STILL OPEN: try_text_slot (12 B;
      changes its island-1 caller -- its own small slice), PAINT's mode-mask
      arithmetic (behaviour change if a USR pokes SCRMOD mid-statement). The
      scratchpad knives in paintmiss_knives.py anchor on the old PAINT text.
      ✅ **BATCH 5 (2026-10-31), measured 2026-10-31: low region free 214 -> 320 B, its
      pad 152 -> 191 B, page-1 pads +27 B -- ~172 B** (fp_mul ~105: state in
      registers, digit_mul inlined, its carry folded into the next cell -- a Python
      model matched the true product on 200,000 random 14x14 pairs; flo_is_fixed
      27: `inc a / cp 16`; ex_print_using 24: the trailing-separator flag is the Z
      on arrival at pu_endlist; read_into_strscr + input_common 12; inpc's ?Extra
      / trampoline 9; str_arg_open 3). 📏 TIER 5 reading only (test_fpdiv_fast,
      against its fixed pre-D-DIVPACK baseline, every value identical): SQR 2.5x
      faster, EXP / LOG / SIN / COS / TAN / ATN / `^` 1.5x. HELD BACK: inpc_vloop's
      merged arms (16 B; reshuffles INPUT's stack), ev_ff_arg_in's shared bound in L
      (11 B; came as a line range), de_win (7-10 B; moves the reduced-build
      absent-sub-ROM path), FP_LHSVAL = LHS_FAC (4 B; a RAM-map change), the
      sidr_done fold (6 B). test_fpdiv_fast counts MUL_ADIG / MUL_CARRY / MUL_I /
      MUL_PP as dead scratch now. Tapes: the two Boulder Dash snapshots moved again
      (SAME -> NEAR 24, NEAR 30 -> 114): timing, as noted at batch 4.
      ✅ **BATCH 6 (2026-10-31), measured 2026-10-31: low region free 320 -> 368 B, its
      pad 191 -> 260 B, page-1 pads +7 B -- ~124 B** (ev_f_arr joins var_load_fac's
      value read at a new vlf_value, 27+6; STRING$ 22: eval_byte_arg, the count
      carried in H by `ex (sp),hl`, str_arg_err; INSTR 15: ev_f_empty RAISES since
      D-DEFERRSTUDY family 3, so the reject tails' pops were dead, and the guard
      words go [aT][p]; zkey_hook 18: the KEY band and TRAPPEND share ZTRAP's page,
      so only L is computed and BC / DE are untouched; ev_rel_str 9; ctl_alloc 8:
      the one-page margin folded into the floor with `inc b`; HEX$/OCT$/BIN$ 7:
      eval_addr; ERASE 6: var_name_key's VARTYPE already says DEFTBL_STR for a `$`
      or DEFSTR name; pop_lhs_and_probe 4: our caller's return address carried
      down the frame, PLF_RA2 no longer written; LEN/ASC/VAL 1). Each layout fact is
      pinned by an assembly-time guard. 🔴 **fp_trunc (24 B) WAS APPLIED AND TAKEN
      OUT AGAIN**: Boulder Dash II then hung at line 10 (PC looping in $FCE0-$FD69,
      the reference on line 3341 by T180); a file bisect named float-arith.asm, and
      800 INT / FIX cases were identical in value AND RAM old-vs-new
      (test_fpdiv_fast's Pair, HEAD as the old tree) -- layout or timing, not a
      wrong answer. D-BD2FRAGILE. Knife pins unchanged; tapes: the tally as batch 5,
      Boulder Dash NEAR 117, Boulder Dash II NEAR 27. Held back: ERASE+DIM's shared
      name head (reviewer's count on 2026-10-31: ~45 B low for 22 B on page 1), esa_release_int taking the
      success tail, cl_str's DIM-style VALTYP question (H1), CVI / LEN sharing a
      close helper, the dead `inc sp` pair in ixsp_unwind.
      ✅ **BATCH 7 (2026-10-31), the first with z80flow, measured 2026-10-31: low region free
      368 -> 422 B and its $3297 pad 259 -> 287 B; main page 1 free 356 -> 362 B and its pads
      +17 B -- ~105 B from ten spans** (candidates ranked against z80flow's routine list, briefs
      carrying `make contract` output; hot paths exec / ex_next left out). INPUT's console path
      tests the read mode once, not three times (17), and keeps textcur under the key (4);
      fp_div / fp_mul / fp_cmp / `/` / `^` share an `argb_dig_iszero` fall-in (12),
      check_preexp_bounds stores FP_TMP_B itself (9), xor_sign stores the sign (6), fp_div's
      zero divisor calls check_preexp_bounds' abort (`cpb_err`, a `; z80flow:
      call-never-returns` marker), combine_pow's classification (19); STR$'s two arms (8);
      stk_guard moved above ev_f_defer and unary `+` falls into ev_f (8); EXP / the math
      tenants share one overflow raise (6); VARPTR's `(` test (3); ON ERROR GOTO trusts rst
      $10's Z (6). `make contract-diff BASE=27d01d05`: 0 broken, xor_sign changes HL instead
      of B ([`b7_contract.out`](scratchpad/b7_contract.out)). Knife pins unchanged; tapes:
      every title's class as on HEAD, Boulder Dash II on line 3341. HELD BACK: the
      ON GOTO/GOSUB list scan as one loop (41-50 B page 1, reviewer's count 2026-10-31 -- it drops `rst $10` on trailing
      entries, so a hooked H.CHRG sees fewer calls: the dl_cmd fold's question); SQR/LOG's
      shared sign test with a block reorder (8 B page 1, reviewer's count 2026-10-31); the full stk_guard inline (3 B more,
      two test rows move). QUEUED as batch 7b: the shx_finish / str_lr_count spans' reviewer
      (~76 B low, reviewer's count 2026-10-31: str_lr_count / MID$ / str_min_bc, shx_finish as an alias of sst_op's tail,
      INKEY$ through the FILL op). Measured the same day: `STRING$(3, "A")` with a space
      after the comma WAS a divergence, with four relatives -- D-ARGSPACE, fixed.
      ✅ **BATCH 7b (2026-10-31), measured 2026-10-31: low region pin pad 289 -> 338 B --
      49 B, as predicted, from four of the queued reviewer's items**: str_lr_count clamps with
      `cp e` and keeps BC / HL (LEFT$ / RIGHT$ drop their reloads; 11), MID$'s tail with an
      8-bit count and E = $FF for the 2-argument form (15), str_min_bc deleted (7),
      shx_finish an `equ` of sst_op's identical tail (16). `make contract-diff BASE=HEAD`:
      0 broken; str_lr_count changes fewer registers (BC, HL) and no longer reads D
      ([`b7b_contract.out`](scratchpad/b7b_contract.out)). Knife pins unchanged; tapes:
      every class as on HEAD, Boulder Dash II on line 3341. STILL QUEUED (reviewer's counts,
      2026-10-31): INKEY$ through the FILL op with a shared shx_fill entry (~23 B; it moves
      the stk_room depth for INKEY$ -- run the deepexpr rows), STRING$'s first byte via
      pu_deref_body (2 B), ems_print's `ex (sp),hl` (1 B), INSTR's `ld de,1` hoist (1 B),
      an inc_eval_byte fall-in (4 B low for 1 B page 1, counted 2026-10-31).
      ✅ **BATCH 8 (2026-10-31 -> 11-01), measured 2026-11-01: low region free 422 -> 494 B and
      its $3297 pad 338 -> 344 B (+78 B); main page 1 free 362 -> 351 B, its pads 2183 -> 2246 B
      (+52 B net) -- ~130 B**. The array element store (ary_store_write, 48 B low, measured 2026-11-01) is
      var_store_at's own coercion, entered below D-FORFAST at a new vsa_dwiden, so an element is
      still widened + repacked (+11 B page 1, 2026-11-01); CLEAR keeps the NEW pool size on the stack and
      writes POOLSIZE only when it accepts -- nothing to restore on a reject (42 B page 1, 2026-11-01); one
      zero-result tail for rsp_zero_ok / raf_zero_ok (9), fp_add's alignment + sign test (11),
      fxt_int (1); `ixsp_open` folds `call ixsp_paren_req / call ixsp` at five sites (9);
      fre_abort_low's ENDFLAG via `inc a` and e21_no_resume falling into it (3); pl_exit compares
      through `ex (sp),hl` (5); mkf_back / INPUT$ declines (3); PLAY(n)'s 0..3 check through
      gfx_chk_dom (6); pl_typeerr an `equ` of type_mismatch_error (4). `make contract-diff
      BASE=HEAD`: 0 broken, ONE `wider_in` -- ex_clear now reads B on entry: on a REJECTED CLEAR
      the dispatcher's B reaches raise_error where the old POOLSIZE load sat; only a user H.ERRO
      hook can see it (the reviewers' "registers unspecified at a raise" class), accepted
      ([`b8_contract.out`](scratchpad/b8_contract.out)). 🧰 z80flow lists the DATA label
      `err_syntax` (`db "Syntax error",0`) as a routine and decodes its text -- a tool finding.
      Knife pins unchanged; tapes: every class as before, Boulder Dash II on line 3341.
      🔍 **TWO REVIEWER FINDINGS TO MEASURE (2026-11-01; (a) measured and FIXED the same day,
      D-CLEARWRAP):** (a) CLEAR's fit check
      adds PRGEND + size + 680 in 16 bits with no carry test, so `CLEAR 32100` .. `CLEAR 32767`
      may be ACCEPTED where both references say Out of memory (D-CLEARFIT's hang class);
      (b) chan_gate_bare's return has no `ei`, so FIELD / LSET / RSET / CALL FORMAT may come
      back with interrupts OFF. ❌ **(b) REFUTED 2026-11-01** ([`fieldei_probe.py`](scratchpad/fieldei_probe.py)
      -> [`fieldei_run.out`](scratchpad/fieldei_run.out)): TIME advances across a fixed loop right
      after FIELD / LSET / RSET exactly as after a plain assignment, on the CF-3300 (58-59) and
      zerobas (68-70) alike -- interrupts are ON (something on the way back re-enables them; the
      reviewer read one return path). The 58 vs 70 is speed (tier 5). A first control row used
      `REM`, which comments out the rest of the line and read 0 on both -- caught, replaced.
      ✅ **BATCH 9 (2026-11-01), measured 2026-11-01: low region free 494 -> 534 B (+40 B);
      main page 1 free 351 -> 361 B and its pads +18 B net of D-CLEARWRAP's 4 -- ~72 B**.
      widen_fac_to: sign by `xor c`, the exponent's high byte by `sbc a,a` off `sub 64`'s
      borrow, no HL guard, no WSRC reload, the pad count rides the stack (18 B low, 2026-11-01, every path
      faster); ary_parse_call: `inc_eval` per subscript and the malformed-list unwind dropped --
      ev_f_empty raises at once and raise_error re-bases SP (22 B low, 2026-11-01); READ keeps [cursor, key]
      in place across the item and exr_bad drops its pops (10 B); CIRCLE loads GFX_DPTR once and
      shares one store (7 B); DRAW loads GFX_DEXP once and jumps straight to gfx_absent (6 B);
      PSET / PRESET share one entry, the default colour from the token in A (3 B); one
      gfx_eval_colour for PSET / LINE / PAINT (3 B); OUT's trampoline moved into vdpio.asm
      (3 B). `make contract-diff BASE=HEAD`: 0 broken; ex_preset now reads A (the token the
      dispatcher supplies, asserted per token by test_stmt_dispatch) and no longer DE
      ([`b9_contract.out`](scratchpad/b9_contract.out)). Knife pins unchanged; tapes: every
      class as before. 🧰 The ranking is now [`reread_rank.py`](scratchpad/reread_rank.py) with
      the reviewed names in [`reread_reviewed.md`](scratchpad/reread_reviewed.md).
      HELD BACK (reviewers' counts, 2026-11-01): the merged DIM / ERASE loop (27 B low -- a
      one-item ERASE gets 20 T slower: needs a ruling against "no common path slower"), DIM
      alone reading VARTYPE (6 B low, counted 2026-11-01, faster), ary_parse_call keeping the cursor on the stack
      and releasing through ARY_IDXP (14 B low, counted 2026-11-01, retires ARY_CUR -- a new `ld-sp` marker),
      READ's R3 and LSET / RSET's shared FIELD head (pin-adjacent), PSET's P2 / P3 (knife
      anchors, stack depth under the colour eval), SPRITE's P5, DRAW's D2 (a malformed
      DRAW string changes from a likely hang to a clean resume).
      ✅ **BATCH 10 (2026-11-01), measured 2026-11-01: low region free 534 -> 537 B and its
      $3297 pad 344 -> 414 B (+73 B); main page 1 free 361 -> 383 B and its pads 2264 -> 2273 B
      (+31 B) -- ~104 B**. The float-to-text formatter (flt_fmt, 70 B low, 2026-11-01): the E-form emitter
      inlined into flt_fmt with an 8-bit exponent (`neg`, an `inc b / sub 10` digit loop),
      flo_is_fixed inlined, s carried in B from the strip, flo_write_digits_range takes DE, the
      sign pre-written; every path faster and FOUTBUF / FOSIGCOUNT unchanged (unit tests and the
      string / float suites). an `ary_op0_vt` entry for the two VARTYPE callers (3 B low,
      2026-11-01). 🔴 **ary_op0_resolve FALLING INTO ary_parse_call (5 B) WAS APPLIED AND TAKEN
      OUT**: the first scoped battery was 199/200 -- dimedge-acceptance's eval-p5-133 read FITTED
      where the VG-8020 says REFUSED: one call frame less under every array reference moved the
      out-of-memory edge by 2 B (`PRINT A(X)` at the DIM edge). contract-diff could not see it
      (a stack-DEPTH change, not a register one); the gate did. A comment at the routine says why
      it must CALL. LOCATE applies before the 4th-argument test, loc_next's
      carry flipped, loc_more gone (20 B); INPUT #'s mode test keeps the cursor pushed and uses
      `dec a` (3 B); the VPOKE and RUN trampolines moved beside their bodies (6 B); SWAP's
      operand type from VARTYPE (2 B); ON's counter is `dec e` (4 B). `make contract-diff
      BASE=HEAD`: 0 broken; the wider_in rows are the formatter's new inputs (flo_emit_fixed A B,
      flo_write_digits B, flo_write_digits_range DE), every caller rewritten in the same batch
      ([`b10_contract.out`](scratchpad/b10_contract.out)). 🧰 z80flow's data-label noise has a
      third case: cl_leaf (a `dw` table) shows `exits` changes when its addresses move; iv_seq
      (a `db` string) too. Knife pins unchanged; tapes: every class as before.
      HELD BACK (reviewers' counts, 2026-11-01): ON's one list walker (20 B; removes K-OL3 / K-OL4's
      anchors), the trap stubs' `ld c,N` at the dispatch (10 B; C into eval unverified), one
      GOTO / GOSUB tail (5 B; GOTO +21 T), SWAP keeping operand 1 on the stack (14 B; PEEKable
      SWPTMP cells, a 4 B deeper array resolve) and its 6 B ARGA-held cursor, POKE's trampoline
      (moves 1 B into the low region), INPUT's `db $FE` skip (a first overlapping-opcode idiom).
      ✅ **BATCH 11 (2026-11-01), measured 2026-11-01: low region free 537 -> 539 B (+2 B); main
      page 1 +18 B -- ~20 B, ~2 B a routine: THE STOP RULE IS REACHED, D-REREAD PAUSES HERE.**
      TAKEN BACK OUT: DIM reading string-ness from VARTYPE == DEFTBL_STR, as ERASE and SWAP do (6 B low, 2026-11-01) --
      lvfix's f.ary2d (`DIM A$(2,2)` then `INPUT#1,A$(1,1)`) went UNREADABLE with it and green without it
      (bisected 2026-11-01, reproduced twice); contract-diff showed nothing, cause NOT understood.
      NARROWED 2026-11-01: NOT an address shift (D1 + 6 B of pad in front of ex_dim, every later
      address as HEAD: still red); the type D1 computes is HEAD's (vnk_dollar writes DEFTBL_STR).
      With D1 it breaks ONLY as `DIM A$(2,2)` / next LINE `INPUT#1,A$(1,1)` after an OPEN -- DIM
      before the OPEN, any statement between (even `:` on one line) and a 1-D A$(2) all read [HI];
      what D1 changes is the stack below SP and the flags. HEAD after ten different predecessor
      statements: no crash. 🔴 DO NOT RETRY D1 until the crash is explained -- a correct-looking
      edit that crashes the NEXT line suggests something reads state it never wrote. POKE's
      check_fperr_only was dead (eval_byte_checked raises first; 3 B low, 2026-11-01) and its trampoline
      moved into poke.asm (+1 B low, -4 B page 1, 2026-11-01); LIST's skip path shares the loop tail and
      detok_emit enters through de_fromstart (5 B); VDP / BASE assignment trusts rst $10's Z and
      skips a GFX_OP reload (8 B); CONT clears GOTOFLAG + ENDFLAG with one word store, guarded
      (1 B). `make contract-diff BASE=HEAD`: no rows at all
      ([`b11_contract.out`](scratchpad/b11_contract.out)). Knife pins unchanged; tapes: every
      class as before. NOT TAKEN: 25 B in OPEN's LEN= parse and the channel close -- all of it
      would only grow the $72D4 pin pad (520 B already), a hole, not usable space.
      ➡️ **WHAT IS LEFT FOR D-REREAD** is the held-back lists of batches 7-11 (rulings, tool
      checks, stack-depth reviews) and spans under ~50 B. Total over eleven batches: ~1,360 B.
      ⏩ **NEXT PHASE: D-REREAD-EDGES (Joost 2026-11-01)** -- reread a routine TOGETHER WITH
      ITS EDGES (its callers' call sites, its callees' contracts): a prelude or postlude
      every caller repeats (fold into the callee / a second entry), a check done on both
      sides of the call (POKE's dead check_fperr_only was one), a result convention every
      caller converts, a one-caller wrapper. Tool first: rank clusters from
      build/contracts.json + the call graph by bytes x sites, EXCLUDING the ABI edges (sub
      tenants' callees, published BASIC entries, the low-region forced set). 🔴 z80flow is
      blind to stack depth and an edge change is where it bites (batch 10's dimedge, batch
      11's DIM crash): a cluster change runs the FULL battery. Feeds D-SUB2RETIRE.
      🧰 **THE RANKING TOOL EXISTS (2026-11-01):** [`edges_rank.py`](scratchpad/edges_rank.py)
      -> [`edges_rank.out`](scratchpad/edges_rank.out) -- every ROM context through z80flow's
      loader; per call target the PRELUDE / POSTLUDE that k of its n call sites share (a
      prelude folds behind a new entry label at 0 B cost; a postlude needs the callee's exits
      read). 📏 UPPER BOUNDS, overlapping, before ABI exclusions: main 674 B, sub 205 B
      (p0 131 + p1 74), sub2 152 B, disk 139 B -- ~1.2 KB in all; top real-looking rows are
      12-14 B each (skip_eq's prelude 3/8 sites, fch_mode_class 4/6, fch_check 4/7). ⚠️ The
      biggest sub / sub2 rows land MID-label (`fo_dev_cas+34`, `tk_copy_up+3`): a missing
      label, read them before believing them. ➡️ **So EDGES is worth a few hundred bytes,
      NOT the ~3 KB D-SUB2RETIRE needs** -- that needs the structural routes too (tenant
      merges, main / sub duplicates). Next: hand-exclude the ABI edges, take the rows top
      down, each a FULL battery.
      🔴 **THE FIRST TOP ROW WAS NOT FOLDABLE (same day):** skip_eq's shared prelude ended in
      `ex (sp),hl`, which swaps with the CALLER's pushed cursor -- inside a called routine
      (sp) is the return address. The tool now refuses any shared run that touches the stack
      (push / pop / ex (sp) / sp loads); upper bound after: ~910 B (main 501, sub 162,
      sub2 131, disk 116). First concrete candidate it leaves: `call var_alloc_or_find` /
      `jp nc,fp_runtime_error` at ~6 sites (deffn, fat, missing, interp x2, program) -> a
      `vaof_oom` helper (`call var_alloc_or_find / ret c / jp fp_runtime_error`, 7 B), ~11 B
      net, unmeasured; then the rows top down, the mid-label sub / sub2 ones read first.
      ✅ **`vaof_oom` SHIPPED (2026-11-01):** basic/vars.asm `vaof_oom` (call var_alloc_or_find
      / ret c / jp fp_runtime_error, 7 B) replaces the pair at all six sites (deffn, fat,
      missing, interp x2, program). 📏 Page 1 380 -> 383 B free and its pin pads 2176 ->
      2181 B -- ~8 B ([`vaof_reloc.out`](scratchpad/vaof_reloc.out)); the low region
      unchanged. 🔮 ~11 B: MISS by ~3. `make contract-diff BASE=HEAD`: no rows
      ([`vaof_contract.out`](scratchpad/vaof_contract.out)); knife pins unchanged; tapes: all
      42 classes as before.
      ✅ **BATCH 2 SHIPPED (2026-11-01): seven folds, 52 B** -- designed and applied by a
      read-only-then-scoped agent, every anchor unique, reviewed: `close_paren` (a label in
      g8_open_paren; graphics + print), and fall-through ENTRIES placed only after an
      unconditional exit: `rl_vst` (req_letter -> var_str_type), `widen_and_finalize`
      (arga_widen -> round_and_finalize), `print_dbwin` (HL := DB_WIN -> print_string),
      `seterr_rec` (set_errflg -> record_errline), `fch_select_e` (A := E -> fch_select); and
      the helper `vnk_paren` (var_name_key / skip_spaces / cp '('). 📏 Low 539 -> 543, page 1
      383 -> 395 free, its pin pads 2181 -> 2217 B -- +52 B
      ([`edges_b2_reloc.out`](scratchpad/edges_b2_reloc.out)); 🔮 the agent's -52 B: HIT.
      Contract-diff: no breaks; its only row is `ary_errmap`, a db table decoded as code that
      vnk_paren now follows ([`edges_b2_contract.out`](scratchpad/edges_b2_contract.out)).
      redundant-load-check clean; knife pins unchanged; tapes: all 42 classes as before.
      REJECTED (and why) in the agent's report: evsp_close (its error path drops its own return
      address), every `ret c / ret z` run (a conditional ret returns to the SITE), vars_reset
      (ctl_reset shares the machine stack), the ev_f_err family, and everything under 4 B.
      ➡️ Batching is the way: ~50 B per FULL battery instead of ~8.
      🏁 **CONCLUDED 2026-11-03 at 60 B (vaof_oom 8 + batch 2 52).** Re-ranked after batch 2:
      the main ROM is mined out (what is left is <= ~6 B a row, most of it on the rejected list);
      the big sub / sub2 rows (`call $0544 / xor a` x17, mid-label) are DATA decoded as code --
      no source names $0544 anywhere; the tool takes every label outside main as code. The space
      for D-SUB2RETIRE comes from moving tenants, not from folds.
      HELD BACK (reviewers' counts, 2026-11-01): fn_call F1-F3
      (13 B; IX / CF across sub-ROM calls), DEFINT's verdict in A (7 B main; a tenant
      interface change), PLAY's P2-P4 / P6, mkf_back S2 / S3 / S6 / S7, ex_get (6 B, only into
      the $72D4 pad), E2 / E3 / HB-a..f.
