# D-DEFERRSTUDY: classifying each deferred-error writer site

Read-only study of tree `fa0b793b` (2026-10-24). No build and no emulator was run.
Every verdict below comes from reading the source, so none of it is measured.

## Verdict key

The question for each site: would an immediate raise at this point behave the same
as the deferral does now?

Two effects apply to every site, so they are left out of the per-site verdict and
treated separately in the cross-cutting section:

* **(R) run-on.** With an immediate raise, the rest of the statement no longer runs
  after the fault: later USR calls, a FOR store, a DEFUSR store, a CIRCLE draw, a
  disk or sub2 tenant acting on the hard 0. Step 1a measured that for div0 and the
  function-domain faults, removing run-on moves zerobas **toward** the VG-8020. For
  type mismatch it may move **away** from it.
* **(P) precedence flip.** A later direct raiser that does not test FPERR first now
  wins, because `record_errline` consumes the pending code. Once the earlier fault
  raises at once, it wins instead.

The verdicts:

* **SAME**: the same ERR and ERL, and the same retained machine state, for every
  input, apart from (R) and (P).
* **DIFFERENT**: for some input the reported error or the kept state changes beyond
  (R) and (P). This covers a site-specific precedence rule, or a caller that consumes
  the value or the decline.
* **UNSAFE**: an in-place `raise_error` here is wrong as a mechanism. The reasons are:
  (a) the site runs inside a sub-ROM or disk-ROM tenant, or is shared with one;
  (b) a restore would be skipped;
  (c) a tenant reads FPERR to bail out.
* **UNSURE**: not decidable from the source without a measurement.
* **N/A**: the site is not an error writer (a reset, a primitive, or a shared tail).

Regions: **low** means the main ROM below $4000 (str-engine, input, float, float-arith,
subromcall, arrays, poke, sound, and the tail of main.asm). **p1** means main page 1
(interp.asm onwards: expr, strvar, clear, usr, print, deffn and the rest). **sub**
means a zerobas-sub page-1 tenant. **disk** means disk.rom.

## The table

| file:line | routine/label | error (FPERR code → ERR, fault) | region | how it is reached | immediate raise | why |
|---|---|---|---|---|---|---|
| basic/clear.asm:231 | clr_h_set | 3→5 range, 6→7 below floor, 4→2 junk after the 3rd arg | p1 | `CLEAR n,top[,…]` | UNSAFE | (b) The old POOLSIZE is still on the stack and goes back only at `clr_h_store` (236-238), before the raise. A bare raise here leaves the new pool size stored. The code that follows already shows the fix: restore, then raise. |
| basic/expr.asm:759 | ev_f_defer (`call penderr_set`) | E = any code | p1 | shared tail of every ev_f_* refusal | N/A (per caller) | Making this tail raise would convert the syntax, missing-operand, TM, IFC, stack-OOM and VAL families **all at once**. Convert at the callers instead. |
| basic/float-arith.asm:869 | check_preexp_bounds | 1→6 Overflow | low | fp_add/sub/mul/div and round_and_finalize, from **every** arithmetic op | UNSAFE | (a) The same code runs inside the sub math tenants (fp_sqrt, fp_log, fp_atan, fp_exp, fp_pow, fp_sin, circleparse import fp_*), and disk.rom imports round_and_finalize. (c) fp_pow reads FPERR after fp_mul to bail out. |
| basic/float-arith.asm:1090 | fp_div | 2→11 Division by zero | low | `/` (combine_div_float); also SQR/LOG/ATN/TAN/CIRCLE inside tenants | UNSAFE | (a) It is shared with the tenants: TAN at an exact cos 0 is documented as reaching this path. The safe point is the main-only `combine_div_float` (float-arith:2041). |
| basic/float-arith.asm:1459 | fac_to_int_go | 1→6 Overflow (coercion) | low | fac_to_int_addr (POKE, VPOKE, OUT, WAIT, TIME=, PEEK, HEX$, CLEAR top) and fac_to_int_strict (\, MOD, AND/OR/XOR/NOT, subscripts, int stores) | UNSAFE | (b) It is reached through `eval_addr` from CLEAR's memory-top argument, **after** the new POOLSIZE is stored. Elsewhere it is SAME: vsf_int and asw_int drop the store either way. |
| basic/float-arith.asm:2102 | combine_pow (x=0, y<0) | 2→11 | low | `0^-1` | SAME | Main-only (cl_leaf table). Nothing between the fault and the boundary decides anything. |
| basic/float-arith.asm:2198 | penderr_de0 (also the fall-in from cpow_frac:2186) | code from caller (3, 2 or 1); 2186: 3→5 for negative base with a fractional exponent | low | SQR/LOG, `\`/MOD by 0, EXP overflow, `(-2)^.5` | SAME | Every caller is main-side, before any tenant call. Converting the tail also converts EXP overflow (2404). |
| basic/input.asm:506 | ary_engine_call | ary_errmap → 5→9, 8→5, 7→10, 6→7, 14 | low | array reads, DIM, ERASE, VARPTR(A(i)), element string copy, **scalar allocation** (var_alloc_or_find: LET, INPUT, READ, FOR, …) | UNSURE | It runs after the tenant returns, so the mechanism is fine. But about 9 callers continue on NZ/CF-clear (vaof_fail, vptr_none, apc_release), and not all of them were audited for state half-built across the call. |
| basic/main.asm:262 | stk_room | 6→7 Out of memory (stack floor) | low | sh_go_g / sef_fn / fch_ctx_g: deep string expressions | UNSURE | The raise would happen AT the stack floor. raise_error's FN-unwind CALSLT needs stack (parennest's "dead machine" history at raise_error). The deferral lets the levels unwind first. |
| basic/strvar.asm:390 | mkf_back | 3→5 | p1 | MKI$/MKS$/MKD$ with no disk ROM claiming the hook | DIFFERENT | It defers and then **declines** (str_eval_no). A caller that raises straight on NC (pl_typeerr: PLAY, SPRITE$=) currently reports 13, which consumes the 5. Immediate gives 5. Probably the reference's answer; unmeasured. |
| basic/str-engine.asm:354 | str_heap_oom_error | 11→14 / 6→7 | low | string OOM callers | SAME | Already immediate: penderr_set, then `jp fp_runtime_error`. That is the template an immediate helper should copy (see H2). |
| basic/str-engine.asm:653 | str_temp_alloc | STROOM→14/7 | low | every string-producing op | SAME | It runs after sh_go returns (main context). The neutralised slot is never used once the statement has raised. |
| basic/str-engine.asm:660 | sta_overflow | 9→16 too complex | low | temp-descriptor stack full | SAME | As above. |
| basic/str-engine.asm:733 | sst_op (OOM arm) | STROOM | low | snapshot ops | SAME | As above. |
| basic/str-engine.asm:747 | sst_overflow | 9→16 | low | snapshot ops | SAME | As above. |
| basic/str-engine.asm:863 | sct_err2 / se2_arm | 10→13 after evaluating the operand, or MISSOP→24 at the end of the slot | low | `"AB"+5`, `A$+` | UNSURE | The 24 half is SAME. The TM half belongs to the TM family: step 1a shows the reference evaluates past a mismatch, so whether TM should raise at detection is unmeasured. |
| basic/str-engine.asm:898 | sct_ae_set | STROOM / 9→16 / STRLONG→15 | low | concatenation OOM or too long | SAME | "Rejoin the fold" exists only so the remaining terms are consumed under first-error-wins. Immediate makes that moot and changes only (R). |
| basic/str-engine.asm:1357 | str_arg_empty (+16 jumps: str_fn_chr, str_fn_str, str_fn_left, str_fn_right, str_fn_mid, str_fn_radix, str_fn_space, str_fn_string, sfg_reject1/2) | 4→2 | low | `CHR$()`, `LEFT$(,1)`, `STRING$(3` … | DIFFERENT | It defers and then **declines**. Through pl_typeerr, `SPRITE$(0)=CHR$()` and `PLAY CHR$()` currently report 13, which consumes the 2. Immediate gives 2. Inside a type probe (cl_rel_rhs, exp_maybe_strfn) the same fault recurs on the re-drive, so those cases are SAME. |
| basic/str-engine.asm:1920 | shx_finish | STROOM | low | HEX$/OCT$/BIN$/SPACE$/STRING$ results | SAME | It runs after sh_go returns. |
| sub/fp_pow.asm:247 | fpw_recip_zero | 1→6 | sub | `.5^-2000` | UNSAFE | (a) Inside a page-1 tenant under math_wrap. (b) math_wrap's MW_HOST restore (DEF FN formals, PRINT USING scratch) would be skipped. Convert in main after `cpow_tail`'s subrom_call returns. |
| sub/fp_pow.asm:329 | fpwf_overflow | 1→6 | sub | `10^1000` | UNSAFE | As above. |
| sub/fp_exp.asm:494 | fexp_overflow | 1→6 | sub | EXP inside the tenant, and fp_pow's frac path | UNSAFE | As above. |
| basic/interp.asm:94 | cold-boot hook | FPERR := 0 | p1 | power-on | N/A | A reset, not a writer. |
| basic/interp.asm:1576 | record_errline | FPERR := 0 (consume) | p1 | every raise | N/A | This is the consume behind (P). An immediate helper must realise the pending code BEFORE reaching here (H2). |
| basic/str-engine.asm:344 | penderr_set | the primitive store | low | all penderr_set callers | N/A | First-error-wins lives here. It is still needed for every family that stays deferred. |
| basic/str-engine.asm:2399 | type_mismatch_set | 10 (the TM primitive store) | low | the TM callers below | N/A (per caller) | The `ret nz` guard (D-TMFP) and the hard DE=0 / A=1 contract serve the callers. |
| sub/bload.asm:253 | sq_devifc (seqio_tenant) | 3→5 | sub | `EOF(n)` on a non-tape device channel | UNSAFE | (a) Inside a page-1 tenant. Convertible in main after the SEQIO subrom_call returns. |
| sub/strheap.asm:567 | ssn_err (callers 481, 486, 549) | 9→16, STROOM | sub | LEFT$/RIGHT$/MID$ slice of a kept scalar or array source (CLEARPOOL) | UNSAFE | (a) Inside the strheap tenant. Convertible at the main slice glue after the return. |
| basic/expr.asm:371 | cl_rel_mm | 10→13 | p1 | `5<A$` | UNSURE | TM family. Today zerobas runs on past a relational mismatch (the value is 0 and evaluation continues). Step 1a suggests the reference does too, so an immediate raise could create a USR-count divergence. Unmeasured. |
| basic/expr.asm:485 | ev_f `)` gate | 4→2 | p1 | `SQR()`, `(5+)` | SAME | Nothing downstream consumes the 0, and the backstop raises the same code. |
| basic/expr.asm:487 | ev_f `,` gate | 4→2 | p1 | `(,)` | SAME | As above. |
| basic/expr.asm:630 | ev_f_tmm tail | 10→13 | p1 | callers at 725, deffn:178, str-engine:1054, expr:1758 | UNSURE | TM family. |
| basic/expr.asm:640 | ev_f_ifc tail | 3→5 | p1 | callers at 1426, 1688, 1723, str-engine:1066, (2611 uses `ld e,3` directly) | SAME | The function-domain family's own tail. All callers are main-side. |
| basic/expr.asm:742 | ev_f_missop (end of line) | MISSOP→24 | p1 | `X=` | SAME | The rule (an empty slot) is decided before the deferral. |
| basic/expr.asm:744 | ev_f_missop (`:`) | MISSOP→24 | p1 | `X=:` | SAME | As above. |
| basic/expr.asm:748 | ev_f_missop (a token there) | 4→2 | p1 | `X=*5`, `X=THEN` | SAME | As above. |
| basic/expr.asm:924 | stk_guard | 6→7 | p1 | every ev_f at the stack floor | UNSURE | The same stack-headroom concern as stk_room. |
| basic/expr.asm:1051 | ev_f_paren | 4→2 | p1 | `A=(1+2` | SAME | Nothing reads the 0. |
| basic/expr.asm:1426 | ev_ff_field (LOF/LOC) | 3→5 | p1 | `LOF(n)` on a device or cassette channel | SAME | FCH_ACTIVE is not written yet at this point. |
| basic/expr.asm:1688 | CVI/CVS/CVD length check | 3→5 | p1 | `CVI("A")` | SAME | Main-side, before the hook. |
| basic/expr.asm:1723 | ev_cv_back | 3→5 | p1 | CVI with no disk ROM | SAME | It runs after the hook returned. The slot is restored and IX/BC are popped. |
| basic/expr.asm:2273 | evmc_sqr_err (= evmc_log_err) | 3→5 | p1 | `SQR(-1)`, `LOG(0)` | SAME | It runs before the tenant dispatch. Measured by step 1a (`sqr`). |
| basic/expr.asm:2404 | evmc_exp_overflow | 1→6 | p1 | `EXP(1000)` | SAME | It runs before the dispatch. |
| basic/expr.asm:2461 | ev_f_varptr | 4→2 | p1 | `VARPTR(5)` | SAME | |
| basic/expr.asm:2611 | vptr_unset | 3→5 | p1 | `VARPTR(Q)` with Q unset | SAME | The `)` precedence (D-EVFERR) is already resolved by `evsp_close` before the deferral. |
| basic/float-arith.asm:2269 | sdivmod_zerocheck | 2→11 | low | `\` or MOD by 0 | SAME | Main-only (cl_leaf). |
| basic/str-engine.asm:48 | ixsp_paren_req / ixsp_unwind | 4→2 | low | a function with a missing `(` or `)` | SAME | The frame discard before the raise is irrelevant: SP is reset. |
| basic/str-engine.asm:995 | ev_ff_strnum | 10→13 after evaluating the argument | low | `PRINT LEFT$(5,2)` | UNSURE | TM family. The "evaluate first" order (D-LEFTTM) would carry over unchanged. |
| basic/str-engine.asm:1012 | ev_str_arg `)` | 4→2 | low | `LEN()` | SAME | |
| basic/str-engine.asm:1014 | ev_str_arg `,` | 4→2 | low | `LEN(,` | SAME | |
| basic/str-engine.asm:1066 | ev_ff_asc | 3→5 | low | `ASC("")` | SAME | Measured by step 1a (`asc`). |
| basic/str-engine.asm:1105 | evnl_bovf | 1→6 | low | `&B` with 17 or more digits | SAME | |
| basic/str-engine.asm:1143 | evv_refuse | 4→2 / 1→6 | low | `VAL("&")`, `VAL("&H1FFFF")` | SAME | Only if the helper realises a pending code first. A sh_go_g skip lands here with A=6 → E=4 and must lose to the 7 already pending (H2). |
| basic/str-engine.asm:2112 | efi_reject_p | 4→2 | low | INSTR, 3-arg form, missing `,` | SAME | |
| basic/str-engine.asm:2136 | efi_tm_p / efi_tm_pa | 10→13 after eval | low | `INSTR("A",5)` | UNSURE | TM family. |
| basic/str-engine.asm:2201 | efi_reject_pa | 4→2 | low | `INSTR("AB")` | SAME | |
| basic/str-engine.asm:2208 | efi_reject_pab | 4→2 | low | INSTR missing `)` | SAME | |
| basic/str-engine.asm:2493 | ers_mismatch / ers_rhs_mismatch | 10→13 | low | `A$<5`, or a bare string LHS in numeric context | UNSURE | TM family (as for expr:371). |
| basic/usr.asm:164 | ev_usr_err | 4→2 | p1 | `A=USR`, `USR+1` | SAME | |
| basic/print.asm:297 | exps_notrel | 10→13 | p1 | `PRINT "A" AND 1` | SAME | Already immediate: `check_expr_errors` follows directly. |
| **not in the raw inventory:** | | | | | | |
| basic/arrays.asm:497 | ary_parse_call (malformed list) | 4→2 | low | `A(1;2)` | SAME | `call ev_f_empty`, which the grep missed. The partial frame is irrelevant after the SP reset. |
| basic/expr.asm:146 | cl_not_oom | 6→7 | p1 | a deep NOT chain at the floor | UNSURE | `call ev_f_defer`. The same stack concern as stk_guard. |
| basic/expr.asm:725 | ev_f_missop `"` | 10→13 | p1 | `5+"AB"` | UNSURE | TM family. Step 1a row `tm` (`1+"X"+USR(0)`): the reference counts 1, zerobas counts 0, and an immediate raise also gives 0. Converting changes nothing there, but the family's rule is unmeasured. |
| basic/expr.asm:1758 | cvi_tmm → esa_tmm | 10→13 | p1 | `CVI(5)` | UNSURE | TM family. |
| basic/str-engine.asm:1054 | esa_tmm | 10→13 after eval | low | `LEN(5)` | UNSURE | TM family. |
| basic/deffn.asm:178 | ev_fn | 10→13 | p1 | a `$` FN in a numeric factor | UNSURE | TM family. ⚠️ Its sibling `check_vartype_num` (arrays.asm:1204, `B=1+A$` under DEFSTR) **already raises TM immediately** through `type_mismatch_error`, so the TM family is mixed today. |
| disk/kernel.asm:1419 | hk_mki (hkmi_ovf) | 1→6 | disk | `MKI$(32768)` with disk.rom (H_MKI hook, CALSLT) | UNSAFE | (a) Inside disk.rom. Convertible at strvar `mkf_back` after the hook returns. |

**Counts (67 rows): SAME 36, DIFFERENT 2, UNSAFE 10, UNSURE 14, N/A 5.**

## Families and whether converting them looks feasible

| family | writer sites | feasible? |
|---|---|---|
| **F1 Division by zero (ERR 11)** | fp_div 1090 (via `/`), combine_pow 2102, sdivmod_zerocheck 2269, fp_div called inside tenants (TAN) | **Yes, at main-only points.** Pre-test the divisor in `combine_div_float` and raise; raise in `sdivmod_zerocheck` and in the x=0/y<0 arm of `combine_pow`. Keep fp_div's own test deferred for the tenants, and realise a tenant-internal div0 after the subrom_call returns (optional; "not known to occur"). Blocker: **H1** (CLEAR). |
| **F2 Function domain (ERR 5)** | SQR/LOG 2273, negative^fractional 2186→2198, ASC("") 1066, LOF/LOC device 1426, CVI short 1688, CVI no-disk 1723, MKI$ no-disk strvar 390, VARPTR unset 2611, EOF device sub/bload 253, CLEAR range clear 231 (statement-level) | **Yes, for the expression sites.** Most go through two tails (`ev_f_ifc`, `penderr_de0`), so converting a tail converts the family. Note that `penderr_de0` also carries EXP overflow and `\`/MOD div0. MKI$ no-disk is DIFFERENT (the decline flip, likely toward the reference). EOF device needs a post-tenant check. CLEAR 231 stays deferred unless CLEAR is reordered. Blocker: **H1**. |
| **F3 Missing operand / empty parenthesis / syntax inside an expression (ERR 2, 24)** | expr 485, 487, 742, 744, 748, 1051, 2461; str-engine 48, 1012, 1014, 1357 (+16 jumps), 2112, 2201, 2208; usr 164; arrays 497; VAL 1143 (syntax half) | **Likely.** Every site is SAME except `str_arg_empty`, whose decline flips `PLAY CHR$()` and `SPRITE$(0)=CHR$()` from 13 to 2. Precedence rules that are decided after realisation (missing.asm's ERRMARK test, D-MISSOPBOUND) are unaffected. Not measured by step 1a. |
| **F4 Type mismatch (ERR 13)** | expr 371, 630, 725, 1758; str-engine 863 (TM half), 995, 1054, 2136, 2493; deffn 178; print 297 (already immediate); primitive 2399 | **Not without a measurement.** Step 1a: the reference evaluates **past** `1+"X"`, so "raise at detection" is not its rule for TM. The family is already mixed: `check_vartype_num` raises at once, while `5+"AB"` defers. Step 3.2 of the study (pin where in `a+b+c` the reference raises) has to come first. |
| **F5 String heap OOM / too complex / too long (ERR 14/7, 16, 15)** | str-engine 354 (already immediate), 653, 660, 733, 747, 898, 1920; sub/strheap 567 | **Yes, at the main glue** after sh_go returns (every main site is SAME). The tenant-internal `ssn_err` needs a post-return check in the slice glue. The (P) flip applies, for example `TIME=A$+B$` on OOM is 13 today (tm_err13). |
| **F6 Stack-floor OOM (ERR 7)** | stk_guard 924, cl_not 146, stk_room main 262 | **Keep deferred for now.** Raising at the floor runs raise_error, including its FN-unwind CALSLT, in the least stack there is. The deferral unwinds first. UNSURE until it is measured near the floor (parennest and deepexpr rows). |
| **F7 Overflow in arithmetic (ERR 6)** | check_preexp_bounds 869, EXP 2404, &B 1105, VAL 1143 (overflow half), sub fp_pow 247/329, fp_exp 494 | **Only at main-side entry points.** In place it is UNSAFE: the code is shared with the tenants and disk.rom, and fp_pow uses FPERR as its own bail-out. Raise after each `combine_*` and after each math subrom_call. NEXT's "store, then check" (program.asm:2171) is a precedence detail to measure: is the loop variable updated on an overflowing NEXT? |
| **F8 Overflow in coercion (ERR 6)** | fac_to_int_go 1459; disk hk_mki 1419 | **Yes, after H1 is fixed.** hk_mki needs a post-hook check in `mkf_back`. Every other caller drops its store either way. |
| **F9 Array / variable engine (ERR 9, 5, 10, 7, 14)** | input.asm 506 | **UNSURE.** The mechanism is fine (post-tenant), but the many callers include scalar allocation paths that continue on failure. Audit them first. |
| **F10 CLEAR statement checks** | clear 231 | Deferred on purpose so the POOLSIZE restore runs. Feasible as "restore, then raise", which is what `clr_h_store` already does. |

## Cross-cutting hazards (read before converting F1/F2)

* **H1: CLEAR's memory-top argument. This is an actual blocker for F1/F2.**
  `clear.asm` stores the new POOLSIZE (around line 67) *before* it evaluates the second
  argument with `eval_addr` (around line 191). It puts the old value back only on the
  deferred path, at `clr_h_store`:236-238. Any immediate raise inside that `eval_addr`
  skips the restore: `CLEAR 200,1/0`, `CLEAR 200,SQR(-1)`, `CLEAR 200,ASC("")`, a
  coercion overflow, or a syntax fault. CLEAR is then rejected, but the pool floor has
  moved (strheap_floor is *derived* from POOLSIZE). The fix is to evaluate and validate
  the second argument before storing POOLSIZE, or to store it last.
  Sweep result: COLOR (sub2/scrstmt.asm) uses shadow cells and is safe. No other
  "store, eval, restore" site was found in basic/. The sub2 and disk tenants that call
  `eval` back through p0cb/calbak were **not** audited for held state.
* **H2: the immediate helper must realise the pending code first.** `record_errline`
  consumes FPERR, so a bare `ld a,N / jp raise_error` discards an earlier fault that is
  still deferred. That matters as long as other families stay deferred, for example
  `POKE 99999,1/0`, which must stay ERR 6, and VAL's skip arm, which must stay ERR 7.
  Use the `str_heap_oom_error` shape: `ld a,code / call penderr_set / jp fp_runtime_error`.
  It needs no `pop`, because raise_error resets SP.
* **H3: precedence flips (P), which no gate has rows for.** These direct raisers do not
  test FPERR first: `type_mismatch_error`, `pl_typeerr` (PLAY, SPRITE$=), `tm_err13`
  (TIME=), `gb_illegal` sites. `stmt_error` *does* test it (D-STMTPEND).
  Examples that would change and are unmeasured: `TIME=STR$(1/0)`, likely 13 today and
  11 after F1; `SPRITE$(0)=CHR$()`, 13 today and 2 after F3.
* **H4: run-on (R) state that changes.**
  - `FOR I=1/0 TO 3`: `for_set_at` stores 0 into I before the boundary raise
    (program.asm:1912-1914).
  - `DEFUSR=1/0`: `usr_setslot` stores 0 (usr.asm:84-87).
  - `USR(1/0)`: the routine is CALLED with 0.
  - CIRCLE: the circle is drawn with a 0 angle or aspect (graphics.asm:642 DREQ=3).
  - The disk and sub2 tenants act on the hard 0. The FILES/DSKF hooks already
    short-circuit on FPERR (`hk_dskf`).
  All of these disappear with an immediate raise, which step 1a says is the
  reference's direction for F1/F2.
* **H5: immediate raises are already shipped from deep inside the evaluator,** and
  they are gated. The `*_checked` / `eval_byte_arg` leaves raise from inside string
  functions, including inside str_eval type probes. `check_vartype_num` raises TM.
  raise_error is the designed exit from p0cb and calbak callbacks ("a callee that
  RAISES never returns"). The FN-frame unwind exists (o.errfend18/13). So F1/F2 add no
  new *kind* of raise.
* **H6: comments that would become false.**
  - raise_error's D-DEFFN note says `X/0` is deferred, so an FN body returns normally.
  - The D-TMFP, D-LEFTTM, D-STRTM and D-INSTRTM headers use div0 rows as their examples.
  - eval_chan's skip.
  - The PDL guard's `PDL(1/0)` justification.
  math_wrap's "a page-1 tenant cannot raise" stays true only if the conversion stays
  main-side.

## Realisation points if F1 (div0) and F2 (function domain) raise immediately

**No realisation point becomes dead.** Each one is still reached by at least one family
that stays deferred: overflow (F7/F8), TM, syntax/missop, string OOM, array or stack.

| point | still reached by | div0/domain-specific part that becomes moot |
|---|---|---|
| interp.asm:612 (exec_stmt backstop) | every deferred family | the `SCREEN 0*(1/0)` / `DEFUSR=0*(1/0)` justification |
| interp.asm:1212 (stmt_error's check, D-STMTPEND) | TM, overflow, OOM | the `FOR I=0*(1/0) STEP 2` row |
| interp.asm:2244 (eval_int16_checked, D-EVALCHK) | TM (hard 0), syntax, F7 overflow | the `WIDTH 70000+0*(1/0)` / `…SQR(-1)` rows |
| float-arith.asm:1496 (eval_chan fperr_test skip) | TM | **already redundant** by its own comment (penderr_set refuses the overwrite). F1/F2 remove its other motivation. |
| float-arith.asm:1520, files.asm:1393 (channel checks) | TM, overflow | the `PRINT#1+0*(1/0)` gap-2 row, p.lof.dz |
| expr.asm:1163 (PDL guard; not a listed realisation point, a FPERR reader) | TM (`PDL(A$)`) | the `PDL(1/0)` half |
| str-engine.asm:2389 (type_mismatch_set `ret nz`) | overflow-before-TM, syntax-before-TM | the `WIDTH 0*(1/0)+(A$<5)` / `0*SQR(-1)+(A$<5)` rows |
| clear.asm:193, 236, 240 | coercion overflow, the 3rd-arg syntax, ERR 5/7 range | none, but see H1 |
| arrays.asm:531 (skip the engine on a failed subscript) | subscript overflow, syntax | the subscript-div0 case |
| program.asm:2642 (READ syntax: a pending fault outranks it) | overflow | the div0 case |
| poke.asm:42, vdpio.asm:49/94/127, time.asm:66, expr.asm:1178, arrays.asm:912/832, str-engine.asm:2234, program.asm:2171 | overflow (eval_addr and fac_to_int coercion, NEXT, HEX$) | a div0 or domain fault in the operand |
| input.asm:154/224, play.asm:115, printusing.asm:227, strvar.asm:548, graphics.asm:984/1141, files.asm:943, program.asm:2604, arrays.asm:1059 | string/scalar OOM (F5/F9) | none (div0 does not reach them as a primary case) |
| print.asm:243/298, interp.asm:964/2009, arrays.asm:894, missing.asm:620 | every family (driver checks right after eval) | none |
| disk/kernel.asm:4930 (hk_dskf FPERR skip) | syntax, TM (`DSKF()`, `DSKF("A")`) | none |
| str-engine.asm:340 (inside penderr_set) | the primitive | none |

What F1/F2 make redundant is **justification text and test rows**, not code: the
div0/SQR rows of D-EVALCHK, D-TMFP, D-STMTPEND, D-LEFTTM, D-STRTM, D-INSTRTM, D-CVITM
and eval_chan. Code could only be deleted if F7/F8 (overflow) and the syntax and TM
families were converted as well.
