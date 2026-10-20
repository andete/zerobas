<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Stack room inside an expression, per site (D-DEEPEXPR)

Status: **BUILT 2026-10-20 (D-DEEPEXPR): §10 steps 1 and 2 -- `stk_room`, R1-R3,
R5, `sh_go_g` with P1-P3, `sp_ceil` -- with `STK_EVAL_RESERVE` still 128. Host
unit tests green; the emulator rows (§8.1, `scratchpad/deepexpr_probe.py`) NOT yet
run. §11 records what was built where it differs from the design below.** Steps 3-4
(re-measure, lower R, the climber and FN-margin items) remain open.
Drafted 2026-10-19 as the design pass that TODO.md's D-DIMRESERVE item asked for
("the per-op audit the item priced, with a spec"), by reading the source at
`b7de9904`, plus `make basic-reloc` for the addresses and the walls. Everything
below marked **by reading** is an inference from the source that a probe row still
has to confirm. §9 lists those rows. Addresses and line numbers in §2-§7 are the
2026-10-19 ones.

🔴 **The audit found live defects (§2).** The string evaluator recurses with **no
stack test at all**. A numeric `B=(((((…1…)))))` makes that recursion go 6 B
deeper per leading parenthesis, *before* the first `stk_guard` of the statement
runs. Near the memory edge this writes return addresses into the top of the
arrays. A separate defect: an array auto-DIMmed inside a deep expression is sized
against the pool top and ignores the live `SP`.

---

## 1. The goal

Near the memory edge, an expression that the VG-8020 completes must complete on
zerobas. An expression that the VG-8020 refuses with `Out of memory` (7) must be
refused here as well: the same verdict, at the same point. Under no circumstances
may zerobas's own machine stack write into the variable or array region.

D-FREPLUS14 fixed the top-level edge to the byte. The DIM fits from K=109 on both
machines
([`dimedge_scan_131e.out`](../scratchpad/dimedge_scan_131e.out),
[`dimedge_scan_131o.out`](../scratchpad/dimedge_scan_131o.out);
`STK_EDGE_RESERVE` 131). What is left is the evaluator's economy below that edge,
which comes in three parts:

* **The reserve.** Every factor refuses unless `STK_EVAL_RESERVE` (128) is free
  under it. That number is held up by work that runs *below* a passing guard. The
  biggest such case is the string-heap tenant reached from the string operators:
  65 B below the last guard, 71 B with PLAY running
  ([`guardattr_strcmp.out`](../scratchpad/guardattr_strcmp.out),
  [`guardattr_strcmp_play.out`](../scratchpad/guardattr_strcmp_play.out)).
* **The safety holes.** These are paths whose descent has no test at all (§2).
* **The per-level cost.** One `(` cost 12 B here and 6 B on the VG-8020 (§5.3).
  Lowering the reserve closes only the *constant* term. The slope was a separate
  item, D-EVALSLOPE: since 2026-10-20 one `(` costs 6 B here too (§5.3, as built).

The measurement history this rests on, in TODO.md order:

* The first edge bisection: [`dimedge_run.out`](../scratchpad/dimedge_run.out).
* High-water marks:
  * [`stackhw_run.out`](../scratchpad/stackhw_run.out): 20 parentheses reached
    756 B, 32 `ABS` reached 1332 B.
  * [`stackhwdisk_run.out`](../scratchpad/stackhwdisk_run.out): disk verbs.
  * [`stackhwref_run.out`](../scratchpad/stackhwref_run.out): 79 B on the VG-8020
    against 147 B here.
* Attribution: [`stackattr_run.out`](../scratchpad/stackattr_run.out).
* The climber slices:
  [`stackhwref_after_s1.out`](../scratchpad/stackhwref_after_s1.out) and
  [`stackhwref_after_s2.out`](../scratchpad/stackhwref_after_s2.out), with a 22 B
  gap left after S2.
* The corruption rows: [`stackcorrupt_run.out`](../scratchpad/stackcorrupt_run.out).
* The leaf sweep: [`leafdepth_run.out`](../scratchpad/leafdepth_run.out).
* Unguarded depths:
  * [`lowpoint_disk2.out`](../scratchpad/lowpoint_disk2.out) and
    [`lowpoint_dm.out`](../scratchpad/lowpoint_dm.out): the editor at 92 B.
  * [`flatguard_run.out`](../scratchpad/flatguard_run.out).
* Edge safety:
  * [`edgesafe_run.out`](../scratchpad/edgesafe_run.out): closest approach 44 B.
  * [`edgesafe_knife.out`](../scratchpad/edgesafe_knife.out).
* The S3 edge:
  * [`dimedge_s3.out`](../scratchpad/dimedge_s3.out).
  * [`dimedge_ref_fine.out`](../scratchpad/dimedge_ref_fine.out) and
    [`dimedge_ref_raw.out`](../scratchpad/dimedge_ref_raw.out).
* Guard attribution:
  [`guardattr_chain.out`](../scratchpad/guardattr_chain.out) (58 B) and
  [`guardattr_var.out`](../scratchpad/guardattr_var.out) (39 B).
* The reference's per-construct costs:
  [`freshape_run3.out`](../scratchpad/freshape_run3.out), tabulated in
  [spec-basic-frelive.md](spec-basic-frelive.md).

### 1.1 Two corrections to the 2026-10-12 plan in TODO.md

1. **`call_strheap` and `SH_ERR` no longer exist.** D-WSZERO S16 (2026-10-16)
   made the gateway [`sh_go`](../basic/str-engine.asm) (`basic/str-engine.asm:74`).
   It takes a parameter block on the Z80 stack and returns the tenant's error in
   **A** (Z iff 0). The audit table's line numbers are stale. §3 supersedes them.
2. **"Fail by setting SH_ERR so their OOM arms run" reports the wrong error.**
   Under `CLEARPOOL` (on) those arms defer `FPERR_STROOM` = 11, which is **ERR 14,
   Out of string space** (`basic/sysvars.inc:558`). A stack failure is ERR 7. The
   skip must therefore defer `FPERR_OOM` (6) *first*. The arms' own
   `penderr_set` then loses under first-error-wins (`penderr_set`,
   `basic/str-engine.asm:337`).

🎯 **The 2026-10-12 finding was that a guard at the gateway is unsafe because a
skipped call leaves a stale descriptor behind.** That finding is correct, but its
cause is the *values the skip returns*, not where the guard sits. With the skip
contract of §4.3 (P1: publish only `STR_EMPTY` / `DE=0`, never the caller's own
registers), the guard can sit at one gateway entry. The callers still need a
per-site audit, and §3.2 is that audit.

---

## 2. Live defects (by reading — rows in §8.1 must confirm)

| # | defect | where | reproduction idea |
|---|---|---|---|
| **LB1** | The string probe's recursion through `(` has no stack test. `ev_rel` offers every operand to `str_eval` first (`basic/expr.asm:222`, and the right side at `:258`). That goes `str_eval_one` → `str_eval_paren` → `str_eval` → … at **6 B per leading `(`** and declines only at the innermost operand. At level 0 **no guard has run yet** (`stk_guard` sits in `ev_f`, *after* the probe). The probe therefore descends against nothing but `STK_EDGE_RESERVE`. [`guardattr_chain.out`](../scratchpad/guardattr_chain.out) already shows the frames below the last guard: `str_eval_paren+5` / `str_eval+3`, four times over. | [`basic/strvar.asm:178`](../basic/strvar.asm) | `10 CLEAR 200:ON ERROR GOTO 90:X=0:X=INT((FRE(0)-200)/8):DIM A(X):A(X)=12345` / `20 B=` + 40×`(` + `1` + 40×`)` / `90 PRINT A(X);ERR:END`. The probe needs about 36+240 B against a gap of about 220 B, and `stk_guard` then refuses (ERR 7). Expected here: ERR 7 **with `A(X)` overwritten** (garbage, or a broken array chain). VG-8020: ERR 7 with `A(X)`=12345 (a 40×6 = 240 B nest does not fit its gap either). The existing `k300p20` / `k900p32` rows (`stackcorrupt_run.out`) stayed clean only because 20×6 and 32×6 fit their gaps. |
| **LB2** | Unary `+` in the same probe costs **2 B per `+`**, because `str_eval_plus` *recurses* (`call str_eval_one`). The numeric arm costs **0** (`ev_f_pos` is `jp ev_f`, `basic/expr.asm:993`). So an expression that **completes** can still corrupt memory, silently. | [`basic/str-engine.asm:489`](../basic/str-engine.asm) | `20 B=` + 120×`+` + `1` at a gap of about 200 B. Expected here: `B`=1, **no error**, `A(X)` corrupt. VG-8020: completes; its cost per unary `+` is unmeasured (Q2). |
| **LB3** | A `LEFT$`/`RIGHT$`/`MID$` *source* nest also has no test: `str_arg_open` → `str_arg_snap` → `str_eval` → `str_eval_one` → `str_func_ff`, at **8 B per level**. The count argument (`eval`, which is guarded) is only evaluated *after* the inner level returns. At the deepest level a heap snapshot (§3, about 32 B) runs on top of the nest. | [`basic/str-engine.asm:1372`](../basic/str-engine.asm) | `20 B$=` + 25×`LEFT$(` + `A$` + 25×`,1)`, same harness. |
| **LB4** | **Auto-DIM inside a deep expression ignores the live SP.** The array ceiling is `strheap_varceil − STK_EDGE_RESERVE`, which is CSP−131 (`sub/arrays.asm:1122-1125`, and `:675-678` for a new scalar). That is right at statement level, where `SP` is within 131 of CSP. Mid-expression, `SP` can be hundreds of bytes lower, and a first-touch `Z(1,1)` auto-DIMs 11×11 elements (484 B single, 968 B double). When the gap lies between `size+131` and `size+depth`, the new array covers the live stack, the tenant's own frames included. | [`sub/arrays.asm:1122`](../sub/arrays.asm) | `X=INT((FRE(0)-1150)/8):DIM A(X)` then `B=` + 15×`(` + `Z#(1,1)` + 15×`)`. Expected here: a crash or a wild return. VG-8020: ERR 7 is expected (its ceiling is its live SP); unmeasured (Q5). |

None of these is the economy item. They are memory-safety defects, and the item's
rule ("never memory corruption") makes them **TIER 1**. They should be filed as
their own item, or fixed first in the build order of §4. Their reachability does not
depend on lowering any reserve.

---

## 3. Inventory: every site that consumes stack or heap below a test

"Below a test" means: after the last `stk_guard` (`basic/expr.asm:902`, called at
`:470` in `ev_f` and `:189` in `ev_not_do`), or with no test at all. "Failure"
means what the site does when its own resource runs out today. "Publishes" means
the value a caller reads after a failure.

### 3.1 Class R: recursion arms of the string evaluator (no test today)

| id | site | consumes | failure today | publishes | verdict |
|---|---|---|---|---|---|
| R1 | `str_eval_paren` [`basic/strvar.asm:178`](../basic/strvar.asm) | 6 B of stack per `(`; reached from every string probe | none: unbounded, up to about 125 levels per line | — | **UNSAFE, LB1** |
| R2 | `str_eval_plus` [`basic/str-engine.asm:489`](../basic/str-engine.asm) | 2 B per `+` | none | — | **UNSAFE, LB2** |
| R3 | `str_arg_open` / `str_arg_snap` [`basic/str-engine.asm:1372`](../basic/str-engine.asm), `:1151` | 8 B per `LEFT$`/`RIGHT$`/`MID$` source level | none | — | **UNSAFE, LB3** |
| R4 | `str_fn_string`, second argument [`basic/str-engine.asm:1996`](../basic/str-engine.asm) | the `STRING$` nest | the count is `inc_eval` → `ev_f` → `stk_guard` at the same level (`:1983`), so every level passes a guard about 2 B above its recursion | — | SAFE |
| R5 | `str_ev_fn` → `fn_call` [`basic/deffn.asm:149`](../basic/deffn.asm), `:170` | a pool frame plus about 10 B of stack per string FN level | `fnf_save` tests **where SP would land** against `CTL_FRAME_MARGIN` 256 (`sub/deffn.asm:527-545`) → ERR 7, raised eagerly | — | SAFE, but its economy is unmatched (256 mid-expression, Q6) |
| R6 | `sct_loop`'s operand [`basic/str-engine.asm:787`](../basic/str-engine.asm) | iteration only | recursion goes only through R1–R5 | — | SAFE once R1–R3 are |
| R7 | `ev_f` / `ev_not_do` [`basic/expr.asm:470`](../basic/expr.asm), `:189` | numeric recursion | `stk_guard`: defers `FPERR_OOM`, DE=0, drops its own frame | 0 | SAFE (the existing guard) |

### 3.2 Class H: string-heap tenant calls (`sh_go` → `sc_call` → `subrom_call` → CALSLT, DI)

Today each of these runs below a guard that may sit several frames up. The guard's
128 covers them (65/71 B measured), which is exactly why the 128 cannot come down.
"Skip outcome" is what the caller does with the §4.3 skip contract (A=6, NZ,
HL=`STR_EMPTY`, DE=0, BC unchanged).

| id | site (op) | allocates | failure today (heap) | publishes on that failure | skip outcome under §4.3 | verdict with the skip |
|---|---|---|---|---|---|---|
| H1 | `str_temp_alloc` [`str-engine.asm:639`](../basic/str-engine.asm) (op 3); callers STR$ `:1304`, INKEY$ `:1946`/`:1961`, `INPUT$` [`strvar.asm:537`](../basic/strvar.asm), SPRITE$ [`graphics.asm:1173`](../basic/graphics.asm) | a temp slot plus a body | OOM: STROOM deferred, the neutralised `[0][0]` slot in HL, DE=0. Overflow: FPERR 9, `STR_EMPTY` | a valid empty slot / `STR_EMPTY` | `cp 2` fails → STROOM (loses) → `ret_de0`: HL=`STR_EMPTY`, DE=0. Callers skip the fill (`DE=0`). `INPUT$` raises ERR 7 at its `check_expr_errors` before taking a key | SAFE |
| H2 | `sst_op` [`str-engine.asm:718`](../basic/str-engine.asm) (ops 4/16/21): `str_snapshot_to_temp` (INSTR `:2113`/`:2124`, `fn_sn` [`deffn.asm:341`](../basic/deffn.asm)), `_keep` (`str_set_at` `:231`, `str_set_key` [`vars.asm:1087`](../basic/vars.asm)), `_arg` (`sct_go` `:776`, `ev_rel_str` `:2392`, PRINT USING [`printusing.asm:224`](../basic/printusing.asm)), `_slice` (`str_arg_snap` `:1155`) | a temp copy | OOM: STROOM, then falls into `sh_publish` with the tenant's slot. Overflow: `STR_EMPTY` (`sst_overflow`, `:737`) | the tenant's neutralised slot / `STR_EMPTY` | STROOM (loses) → `sh_publish` HL=`STR_EMPTY` | SAFE with P1. **UNSAFE without P1:** a naive skip leaves HL = the SOURCE descriptor, which is then published as STRPTR, and a later slice or append writes through it (the 2026-10-12 🔴) |
| H3 | `sct_go` APPEND [`str-engine.asm:800`](../basic/str-engine.asm) (op 2) | R's new body | `sct_append_err` (`:857`): FPERR 14/16/15, R unchanged, the fold continues | R (valid) | A=6 → `cp 2` NC/NZ → `FPERR_STRLONG` (loses); R unchanged | SAFE |
| H4 | `str_temp_slice` [`str-engine.asm:931`](../basic/str-engine.asm) (op 5, a pushed fourth word) | none (in place) or a new result (`she_slice_new`) | the tenant always reports 0 | the temp | temp unsliced, still valid; the caller pops its own word | SAFE |
| H5 | `ev_ff_val` [`str-engine.asm:1102`](../basic/str-engine.asm) (op 13) | none (parse) | `evv_refuse` → `ev_f_defer`, E=4/1 | DE=0 | A=6 → E=4 → `ev_f_defer` (loses), DE=0 | SAFE |
| H6 | `shx_tail` [`str-engine.asm:1874`](../basic/str-engine.asm) (ops 6/7/8/14: CHR$ `:1242`, HEX$/OCT$/BIN$ `:1818`, SPACE$ `:1930`, STRING$ `:2034`) | a temp plus body | `shx_finish` (`:1886`): STROOM, then `sh_publish` HL / `STR_EMPTY` on overflow | the tenant's slot / `STR_EMPTY` | STROOM (loses) → HL=`STR_EMPTY` | SAFE |
| H7 | INSTR `efi_p_ok` [`str-engine.asm:2157`](../basic/str-engine.asm) (op 11) | none | no error path (ERR 0) | the position in HL | **HL=`STR_EMPTY` becomes the value 18648**, a plausible number | UNSAFE as a *verdict* (P3: needs DE=0) |
| H8 | `str_cmp_bits` [`str-engine.asm:2262`](../basic/str-engine.asm) (op 10), from `ev_rel_str` `:2425` | none; the tenant pops two temps | none | bits in A | A=6 → `and c` → −1/0. The two temps are not popped; `exec_stmt` empties the stack ([`interp.asm:608`](../basic/interp.asm)) | SAFE (a −1/0 value with ERR 7 pending) |
| H9 | `FRE` [`expr.asm:1798`](../basic/expr.asm) → `fre_go` [`main.asm:527`](../basic/main.asm) (ops 15/17), then `subrom2_call` into sub2 `frelive` | none | none | HL | HL=`STR_EMPTY` → 18648; the sub2 tenant still runs | UNSAFE as a verdict (P3), and the sub2 CALSLT would run with less than R free |
| H10 | `VARPTR(#n)` `ev_ff_varptrch` [`expr.asm:1485`](../basic/expr.asm) → `fch_ctx_addr` [`files.asm:1673`](../basic/files.asm) (op 18) | none | none | HL→DE | not routed through the guarded entry: `fch_ctx_addr` serves statement callers too | gets its own `stk_room` (§4.3) |
| H11 | `str_set_key` / `ssk_store` [`vars.asm:1076`](../basic/vars.asm), `:1117` (op 16 snapshot, then op 12 VAR_STORE). Expression-time through FN binding `fn_st_s` [`deffn.asm:328`](../basic/deffn.asm); statement-time through LET (`str_set_at`, `str-engine.asm:226`) | the variable's body | `jp str_heap_oom_error` → `fp_runtime_error` (eager, reads FPERR) | nothing written | a skipped op 12 is safe. **But the op-16 snapshot sits 2 B (`str_set_key`) / 4 B (`str_set_at`) deeper than the op-12 store**, so a skipped snapshot (`STR_EMPTY`) can be followed by a passing store that writes `""` into the variable before ERR 7 is raised | UNSAFE as a *value* (P2) |

**Statement-time, raw `sh_go`, exempt.** Each of these runs at statement depth, which
`STK_EDGE_RESERVE` 131 covers (sized over the deepest unguarded path, the editor at
92 B):

* `MID$()=` (op 9, `:1687`) and `mid_own` (op 0, `:1731`).
* `INPUT`'s `inp_val` (op 19, [`input.asm:412`](../basic/input.asm)).
* `ctl_reset` (op 20, `:309`).
* `fch_ctx_addr` for FIELD ([`field.asm:598`](../basic/field.asm)), file I/O
  ([`files.asm:892`](../basic/files.asm)), CLOAD ([`cload.asm:431`](../basic/cload.asm)),
  boot ([`program.asm:169`](../basic/program.asm)) and disk.rom
  ([`disk/kernel.asm:1118`](../disk/kernel.asm)).

### 3.3 Class S: other inter-slot leaves below a passing test (no new site; they set R)

| id | site | depth below the test | verdict |
|---|---|---|---|
| S1 | scalar / array read: `ev_f_var` [`expr.asm:587`](../basic/expr.asm), `ev_f_arr` [`arrays.asm:940`](../basic/arrays.asm) → `ary_engine_call` → `sc_call` → the arrays tenant | 39 B ([`guardattr_var.out`](../scratchpad/guardattr_var.out)) | SAFE under R ≥ 39; auto-DIM is LB4 |
| S2 | transcendentals / VAL / STR$ / HEX$ / INSTR leaves | 6–30 B ([`leafdepth_run.out`](../scratchpad/leafdepth_run.out), measured before S1/S2: re-measure) | SAFE under R ≥ 30 + overlay |
| S3 | DEF FN dispatch `deffn_subcall` ([`deffn.asm:191`](../basic/deffn.asm), `:295`, `:376`) | 12 B (leafdepth `fn`) | SAFE |
| S4 | disk.rom hooks reached from an expression: MKI$/MKS$/MKD$ ([`strvar.asm:368`](../basic/strvar.asm)), CVI/CVS/CVD, EOF/LOC/LOF/DSKF, `INPUT$(n,#f)`'s `arl_getbyte`, DSKI$ (`strvar.asm:605`) | **unmeasured below a test.** `stackhwdisk_run.out` reads statement totals of 143–147 against `A=1`'s 145 | Q7 |
| S5 | USR (`ev_usr`, [`usr.asm:144`](../basic/usr.asm)) | the user's machine code: unbounded | out of scope; the program owns its own code's stack, on the reference too |
| S6 | the interrupt overlay: `htimi_guard` ([`subromcall.asm:252`](../basic/subromcall.asm)) → traps + PLAY | about 24 B where interrupts are on ([`stackattr_run.out`](../scratchpad/stackattr_run.out)). Tenants run DI (`subromcall.asm:74-76`) | added to R |
| S7 | FRE(n)'s sub2 tenant | its scan stops 48 B above CTLLIM ([spec-basic-frelive.md](spec-basic-frelive.md)) | SAFE once H9 skips it after a failed test |

### 3.4 Class A: the variable region growing during an expression

| id | site | consumes | failure today | verdict |
|---|---|---|---|---|
| A1 | auto-DIM on first touch: `aal` ceiling [`sub/arrays.asm:1122-1125`](../sub/arrays.asm) | up to 968 B (2-D double default) | ERR 7 only against CSP−131 | **UNSAFE, LB4** |
| A2 | a new scalar (`scv_ceil_try`, [`sub/arrays.asm:675-678`](../sub/arrays.asm)): the LET/FOR target is created before the right side (D-LETNEWFIRST); a read or `VARPTR` creates one only if the read path inserts | ≤ 11 B block move of the arrays | as A1 | SAFE today under 128; the A1 fix covers it once R drops |

**Counts.** Expression-time sites, by class:

| class | SAFE | UNSAFE |
|---|---|---|
| R | 4 | 3 (LB1–LB3) |
| H, with the §4.3 contract | 8 | 3 (H7, H9 verdict; H11 value) |
| S | 6 | 1 unmeasured (S4), USR out of scope |
| A | 1 | 1 (LB4) |

H10 moves to its own test. The statement-time exempt list is 6 sites.

---

## 4. The design

### 4.1 One test primitive, non-dropping: `stk_room` (low region)

This is `stk_guard`'s arithmetic, against the same pointer: **CTLLIM** =
ARYEND+2 = STREND+2. Its single writer is `strheap_ctllim`
([`sub/strheap.asm:615`](../sub/strheap.asm)). `stk_room` differs from `stk_guard`
in two ways: it does **not** drop its caller's frame, and it preserves HL. It is
**not** a call added to `stk_guard`, which runs on every factor (TIER 5).

```
; stk_room -- CF set iff (call site's SP - 2) > CTLLIM + STK_EVAL_RESERVE:
; the very threshold stk_guard tests. On failure FPERR_OOM is deferred
; (first error wins) and it returns CF clear, A = FPERR_OOM.
; Preserves BC, DE, HL; A on success.
stk_room:
        push    hl
        push    bc
        ld      bc,STK_EVAL_RESERVE-2   ; -2: our own pushed HL (see below)
        ld      hl,(CTLLIM)
        add     hl,bc
        pop     bc
        sbc     hl,sp                   ; CF clear from the add (CTLLIM < $FF80)
        pop     hl                      ; (pop keeps F)
        ret     c
        ld      a,FPERR_OOM
        jp      penderr_set             ; returns OUR F (CF clear), A = 6
```

The −2: inside `stk_guard` the `sbc` sees the site's SP−2 (its return address).
Inside `stk_room` it sees SP−4 (return address plus HL). Loading R−2 makes both
tests mean exactly "site SP − 2 > CTLLIM + R", so a recursion arm and a factor
refuse at the same byte. `penderr_set` preserves its caller's flags and returns
A = the code ([`str-engine.asm:331-347`](../basic/str-engine.asm)).
Size: 19 B.

If §9's Q8 shows that the heap ops need more than the leaves, add a second entry
with its own constant: `stk_room_h: push hl / push bc / ld bc,STK_HEAP_RESERVE-2 /
jr sr_go`, which is +6 B.

### 4.2 Class R: test each recursion step, refuse by DECLINING (rule P4)

| site | change | refusal path |
|---|---|---|
| R1 `str_eval_paren` (page 1) | after its `push hl`: `call stk_room` / `jr nc,sep_decline` | `sep_decline` restores HL to the `(` and returns CF clear, exactly the D-STRPAREN decline every caller already handles |
| R2 `str_eval_plus` (low) | **made a loop, no test**: `push hl` / skip every `PLUS_TOKEN` / `call str_eval_one` / `pop de` / `ret c` / `ex de,hl` / `ret` | unchanged: a decline leaves HL on the first `+`. Constant depth for any number of `+`, which is what the numeric arm already costs (0) |
| R3 `str_arg_open` (low) | at entry: `call stk_room` / `jr nc,sao_empty` | CF clear → each caller's own `jr nc,str_arg_empty` → defers 4 (loses to 6) → `str_eval_no` |
| R5 `str_ev_fn` (page 1) | after the numeric-FN decline: `call stk_room` / `jp nc,str_eval_no` | decline with HL on the FN token. The numeric re-drive's `ev_f` guard refuses too |

🎯 **Why a probe refusal never refuses a NUMERIC expression the numeric path
would accept.** From `ev_rel`:

* The probe's first `str_eval_paren` test sits at `SP_rel − 8`: `push ix`,
  `call str_eval_ix`, `call str_eval_one`, then its own `push hl`.
* Level k of the probe sits at `SP_rel − 8 − 6(k−1)`.
* The numeric path's `stk_guard` at level k sits at `SP_rel − 8 − 12k + …`, which
  is at least as deep for every k ≥ 1. It is *equal* at the first level.

With the same R, the probe therefore refuses only where the numeric descent would
refuse anyway. The deferred ERR 7 is the numeric path's verdict, reached earlier.

### 4.3 Class H: one guarded entry, `sh_go_g`, with a SAFE skip contract (P1)

`sh_go_g` sits in the low region, immediately before `sh_go`, and falls through:

```
sh_go_g:
        call    stk_room            ; A (the op) kept on success
        jr      nc,shg_skip
sh_go:  ... unchanged ...           ; ret
shg_skip:                           ; FPERR_OOM already deferred, A = 6
        ld      hl,STR_EMPTY        ; P1: the ONLY descriptor a skip may publish
        ld      de,0                ; P1: "no body to fill" / a numeric 0
        or      a                   ; NZ, CF clear: what every caller reads as
        ret                         ; a failed op. BC and a pushed 4th word untouched.
```

`STR_EMPTY` is `$48D8`: main page 1 ROM ([`vars.asm:1046`](../basic/vars.asm)), still
mapped while a page-0 tenant runs. A later op that *writes* through it (an APPEND
onto it, a slice of it) writes ROM and is ignored. `sh_append` returns from
`sap_try_extend` on lenR = 0 before reading its pointer.

**Rules for the callers:**

* **P1, publish safely.** A skip publishes only `STR_EMPTY` / `DE=0`, never the
  caller's own registers.
* **P2, no visible store while a fault is pending.** `ssk_store` starts with
  `call fperr_test` / `jr nz` to the existing tail's `pop hl`. That tail
  (`ld (TEMPPT),hl` / `ret z` / `jp str_heap_oom_error`) then raises the pending
  code eagerly through `fp_runtime_error`. The variable keeps its old value, as on
  the reference, whose error is eager. This also closes the same shape for a heap
  OOM in LET's own snapshot, which today stores the neutralised `""` before ERR 14
  (unmeasured, Q9).
* **P3, a numeric result of a skipped op is 0.**
  * INSTR: `jr nz,+1` before its `ex de,hl`. On a skip DE is already 0 (+2 B).
  * FRE: `fre_go` returns 0 on NZ for both forms (`jr nz,fre_zero` after
    `pop de`), and skips the sub2 CALSLT. FRE(s$) goes through a 6 B
    `call sh_go_g / ret z / jr fre_zero`.
  * VARPTR(#n): `call stk_room` / `jp nc,ret_de0` before `fch_ctx_addr` (+6 B).
  * VAL's 0 already comes from `ev_f_defer`.
  * CMP's −1/0 is accepted: no consumer raises eagerly on a relational value.

  P3 exists because eager raises (`raise_error`, [`interp.asm:1344`](../basic/interp.asm))
  do **not** consult FPERR. A plausible garbage number reaching one inside the same
  statement would report the wrong code.

**Sites switched from `sh_go` to `sh_go_g`, 0 B each (same `call`/`jp`):**

* `str_temp_alloc`, `sst_op`, `sct_go`, `str_temp_slice`, `ev_ff_val`, `shx_tail`.
* INSTR, `str_cmp_bits`, `ssk_store`, and both `fre_go` calls.

The raw `sh_go` keeps its statement-time users (§3.2) and `ctl_reset`.

**Shallower-after-deeper, checked shape by shape (the 2026-10-12 🔴):**

* `LEFT$`: the slice's test site is **2 B shallower** than the snapshot's
  (`str_fn_left`: snapshot depth 8 = `call str_arg_open` + `call str_arg_snap` +
  `push hl` + `call str_snapshot_slice`; slice depth 6 = `push hl` +
  `call str_temp_slice` + `push bc`). It can pass after the snapshot skipped. It
  then slices `STR_EMPTY`: not a temp, so `she_slice_new`, count 0, nothing
  written. SAFE.
* `sct_go`: the append's test is at the same depth as the snapshot's. Even when it
  passes, R = `STR_EMPTY` writes only ROM. SAFE.
* `str_set_key` / `str_set_at`: the store is 2 / 4 B shallower. That is P2's case.

**How the deferred error surfaces.**

1. `penderr_set` writes `FPERR_OOM` (`sysvars.inc:584`) set-if-empty.
2. It is raised at the first reader:
   * `check_expr_errors` / `check_fperr_only` ([`interp.asm:1831`](../basic/interp.asm));
   * `cepb_fp` (`:1853`);
   * `fp_stmt_done` (`:976`);
   * `stmt_error`'s D-STMTPEND check (`:1200`);
   * failing all of those, `exec_stmt`'s `check_fperr_only` at the next statement
     head (`:605`).
3. `fp_runtime_error` (`:1283`) maps it through `fperr_to_err`
   ([`islands.asm:372`](../basic/islands.asm)) to ERR 7 on both CLEARPOOL arms.

### 4.4 Class S: no new test unless a measurement demands one

Their depth is what R must cover (§5). If Q7 shows a disk leaf deeper than the
chosen R, that leaf's entry gets a `stk_room` test (+5 B each). The candidates are
the MKI$ hook (`strvar.asm:368`), `dsk_core` and `arl_getbyte`'s expression
callers.

### 4.5 Class A: the variable ceiling also respects the live SP (sub page 0)

In `scv_ceil_try` and `aal`, after `add hl,de` (ceiling = varceil − 131), add
`call sp_ceil`, which returns HL = min(HL, SP − `STK_ALLOC_RESERVE`):

```
sp_ceil:                            ; HL = a ceiling -> min(HL, SP_caller - R_A)
        push    de
        ex      de,hl               ; DE = the static ceiling
        ld      hl,4-STK_ALLOC_RESERVE  ; +4: our return + pushed DE
        add     hl,sp
        push    hl
        or      a
        sbc     hl,de               ; CF iff the SP ceiling is the lower
        pop     hl
        jr      c,spc_sp
        ex      de,hl
spc_sp: pop     de
        ret
```

`STK_ALLOC_RESERVE` is the arrays tenant's own depth below this point to the end of
the allocation (block move or zero fill, DI), measured in Q10 and predicted 16–24.
It does **not** need to cover the rest of the expression: the next factor's test
runs against the *new* CTLLIM.

🎯 **The top-level edges must not move.** At statement level the tenant's SP is
about CSP−75, so SP − R_A ≈ CSP−99, which lies above CSP−131. The static ceiling
still binds there, and `dimedge-acceptance` (10/10) is the regression guard.

---

## 5. Lowering `STK_EVAL_RESERVE`

> **Done 2026-10-20: R = 84, measured** (max 76 B below any passing test, in the string
> GC, + 8; `scratchpad/rmeasure_run.out`, `rmeasure_gc.out`). Matching the reference's
> refusal POINT with a constant turned out impossible (each statement shape wants a
> different R -- TODO D-EDGEONERR), so R stays at the safety floor, which never refuses
> where the VG-8020 completes on the shapes measured; the remainder is the slope
> (§5.3), TODO D-EVALSLOPE.
>
> **Then R = 115, matched (D-EVALSLOPE, 2026-10-20).** With the one-loop climber
> (§5.3.1) the shapes nearly agree, and reading each 8-byte-element shape in all eight
> FRE(0) phases (`scratchpad/deepctl_edge_probe.py`) put the remaining spread at 4 B:
> a plain store and a PRINT of string literals are the VG-8020's at 119, while a PRINT
> of numeric items needs 4 B more. 115 matches the PRINT shapes in every phase and is
> 4 B more lenient on the simple ones; `dimedge-acceptance` rows `eval-p4-*` /
> `eval-p5-*` pin it to the byte (R = 114 and R = 116 each redden exactly one row).

### 5.1 What R must cover once §4 is in

R must cover the deepest stack write below **any passing test** (`stk_guard`,
`stk_room`, `sh_go_g`) before the next test or the return, plus the interrupt
overlay wherever interrupts are on. The heap chain no longer counts from the last
*factor* guard; it counts from `sh_go_g`.

| contributor | bytes | source |
|---|---|---|
| a heap op below its own call (snapshot; DI inside) | ~32 | `guardattr_strcmp.out`: the return into `sst_op` at 33 B, deepest 65 |
| the GC inside `heap_alloc` | **unmeasured** | Q8 |
| a scalar/array read through the arrays tenant | 39 | `guardattr_var.out` |
| math / VAL / STR$ / INSTR leaves | ≤ 30 | `leafdepth_run.out` (re-measure after S1/S2) |
| the interrupt overlay (EI points, main side) | ~24 | `stackattr_run.out` |
| disk hooks | **unmeasured** | Q7 |

**Prediction: R = 56 ± 8.** The rule: R = the measured maximum + 8, never less.
It is set from the probe, not from this table.

### 5.2 How R is measured

1. Build §4 with R = 128 unchanged.
2. Extend [`guardattr_probe.py`](../scratchpad/guardattr_probe.py) so that its
   breakpoint keeps the last passing test of all three kinds. A test passes when
   `stk_room` returns CF set, or when `stk_guard` returns.
3. Run its statement set together with `edgesafe_probe.py`'s `WORK` and the §8.1
   rows, on both machines (`LP_DISK=1` and nodisk), with PLAY running.
4. Set R, then run knife K-DX9 (§8.2).

### 5.3 What lowering buys, and what it cannot

At the DIM edge the first factor of a top-level statement has about
131 − (24..42) − 2 B free ([`flatguard_run.out`](../scratchpad/flatguard_run.out)).
With 128 a flat `PRINT 1` there refuses here and completes on the VG-8020: TODO's
"(a)", measured before D-FREPLUS14 (re-measure, Q1). With R ≈ 56 it completes.

The **slope** was the rest. Per pending construct, zerobas and the VG-8020 cost:

| construct | zerobas (from the source, after S1/S2) | VG-8020 (frelive) |
|---|---|---|
| `(` | **12**: `call ev_logic` 2 + [min] 2 + `call ev_not` 2 + `call ev_e` 2 + [min] 2 + `call ev_f` 2 | 6 |
| pending `+ − * / ^` | **20**: [entry] 2 + lhs 2 + `push_lhs_frame` 10 + `call evk_min` 2 + [min] 2 + `call ev_f` 2 | 8 + width |
| pending `AND OR XOR EQV IMP` | 16 | 8 |
| pending `MOD \` | 10 | 8 |
| unary minus | 6 | 6 |
| `NOT` | 2 | 6 |
| unary `+` | 0 (string probe: 2 → 0 after R2) | unmeasured (Q2) |
| `DEF FN` call | 13 | 14 |
| relational, function call, subscript | not derived here | 10+w / 10 / 18 |

So at a gap G, N nested parentheses fit here when base + 12N + R ≤ G, against
base′ + 6N + X ≤ G on the reference. R can match the intercept (once X is measured,
Q1). Only a cheaper climber frame can match the slope.

### 5.3.1 As built: one climber (D-EVALSLOPE, 2026-10-20)

The three precedence layers (`ev_logic` → `ev_not` → `ev_rel` → `ev_e` → `ev_f`)
are ONE loop in `basic/expr.asm` with an operator stack on the machine stack: the
caller pushes a sentinel word whose code is the loosest level it accepts, the loop
calls `ev_f` for an operand and looks the next token up in `cl_lvtab` (one indexed
read, `basic/islands.asm`), then shifts (the lhs, for `+ − * / ^` and the
relationals its FACTYP+FAC frame, under a one-word entry) or reduces (the leaf from
`cl_leaf`, `basic/field.asm`) until the sentinel says the operator is the caller's.
NOT is a prefix entry with its own inline stack test (`cl_not`, stk_guard's floor
to the byte); a string comparison (`ev_rel_str`, unchanged) is called and the
chain goes on at the relational level and looser.

MEASURED on the host Z80 ([`evalslope_before.out`](../scratchpad/evalslope_before.out)
/ [`evalslope_after.out`](../scratchpad/evalslope_after.out),
[`evalslope_probe.py`](../scratchpad/evalslope_probe.py)): bytes per extra nesting
level of each shape, each level pending while the next is parsed (the VG-8020's
column is frelive's per-construct costs summed for the same shape, integer
operands):

| shape, per level | before | as built | VG-8020 |
|---|---|---|---|
| `(` | 12 | **6** | 6 |
| `1+(`, `1*(`, `1/(` (pending `+ − * /`, `^` the same frame) | 30 | **20** | 16 (10 + `(`) |
| `1<(`, `1=(` (pending relational) | 26 | **20** | 18 (12 + `(`) |
| `1AND(` … `1IMP(` | 20 | **10** | 14 (8 + `(`) |
| `1MOD(`, `1\(` | 20 | **10** | 14 |
| `-(` (unary minus) | 18 | **12** | 12 |
| `NOT NOT …` | 2 | **2** | 6 |
| `NOT(` | 14 | **8** | 12 |
| `ABS(` (a function call) | 18 | **12** | 16 |

Per construct, as built: `(` 6 (`call ev_logic` 2 + sentinel 2 + `call ev_f` 2);
a pending `+ − * / ^` or relational 14 (entry 2 + FACTYP+FAC 10 + lhs 2); a pending
`AND OR XOR EQV IMP MOD \` 4 (entry 2 + lhs 2); `NOT` 2 (its entry); unary minus 6
(`call ev_pw` 2 + sentinel 2 + `call ev_f` 2). A plain factor reaches 18 B under
`eval`'s entry where it reached 20.

**The typed frame (built 2026-10-20, host-measured; the machine battery is still
to run).** A pending `+ − * / ^` or relational kept the lhs as DE plus a fixed
10-byte FACTYP+FAC copy, 14 B for any type, where the VG-8020 keeps 8 + its own
width (10 for an integer, 12 single, 16 double). `push_lhs_frame` now sizes the
frame by the lhs's type -- [FACTYP] over the lhs DE (int16), FAC+0..3 (single) or
FAC+0..7 (double) -- and `pop_lhs_and_probe` pops it by the same `cp 2` / `cp 5`
split; each type keeps exactly what its readers read (FP_LHSVAL only under
LHS_FACTYP = 2, `widen_lhsframe_to` 4 bytes for any type but 8). Per pending
typed operator: 6 B (int16), 8 (single), 12 (double), the [entry] word included
([`evalslope_typed_before.out`](../scratchpad/evalslope_typed_before.out) →
[`evalslope_typed.out`](../scratchpad/evalslope_typed.out)):

| shape, per level | fixed frame | typed frame | VG-8020 |
|---|---|---|---|
| `1+(`, `1*(`, `1/(` | 20 | **12** | 16 |
| `1<(`, `1=(` | 20 | **12** | 18 |
| `1.5+(`, `1.5*(`, `1.5<(` | 20 | **14** | 18 |
| `1#+(`, `1#*(`, `1#/(`, `1#<(` | 20 | **18** | 22 |

So every typed nest is now at or below the reference -- more lenient, never
stricter. Every path is as fast or faster (a typed op on an int16 lhs −230 T,
single −112, double −16; the logical ops −2 from two `jr` → `jp`), and 185 outcome
rows (DE, FACTYP, FPERR, ERRMARK, cursor and all 8 FAC bytes) are identical
between the builds. NEXT shares the protocol and needed only its `push de` gone.
**Where it is below:** the strict-int operators and NOT (4 and 2 against 8 and 6),
which keep only the converted lhs. Near the edge zerobas can now complete a richly
nested logical expression the VG-8020 refuses -- the opposite direction from the
item this closes; the FRE(0) tenant models the reference's costs and is untouched.

**Speed (TIER 5).** Every construct got faster, because the three layers re-read
the token and scanned three tables after EVERY operand (the arithmetic table to
its end on any operand not followed by `+`); the loop does one indexed read. Whole
`call eval`, T-states, before → after: a constant 2590 → 1481; `(1)` 4981 → 2763;
`1+2` 4954 → 3380; `2*3` 8333 → 6483; `7MOD3` 6486 → 4837; `6AND3` 5685 → 3658;
`-2` 3636 → 2072; `NOT0` 2974 → 1814; `1=1` 5424 → 3993; `ABS(-3)` 6676 → 4003;
`PEEK(0)` 5597 → 3379. Per extra nested level every shape is cheaper too, the NOT
chain included (384 → 333 T a NOT: an int16 operand skips the conversion, and the
reduce goes straight back to the comparison).

`R` is unchanged (84). Its measurement (§5.1, the deepest write below a passing
test) is a property of the leaves, not of the climber, but a re-bisect on the
machine is what says so.

`CTL_FRAME_MARGIN` 256 as applied to FN frames mid-expression (R5) is a second
intercept to bring down later. Its reference counterpart is Q6.

---

## 6. Speed (TIER 5)

**Per-factor path: 0 T added.** `stk_guard`, `ev_f`, the `evk`/`evc` loops and
`ev_rel`'s numeric path are untouched.

| new test | on whose path | T-states added (success) |
|---|---|---|
| `stk_room` itself | — | `call` 17 + `push hl` 11 + `push bc` 11 + `ld bc` 10 + `ld hl,(nn)` 16 + `add` 11 + `pop bc` 10 + `sbc hl,sp` 15 + `pop hl` 10 + `ret c` 11 = 122, + the site's `jr nc` 7 = **129** |
| R1 `str_eval_paren` | every `(` the string probe enters: once per `(` operand, but `ev_rel` re-probes at every nesting level, so N leading `(` cost 129·N(N+1)/2 | +129 per probed `(` (the probe level itself is about 130 T: roughly doubled) |
| R2 `str_eval_plus` loop | each unary `+` | **saves** ~140 T per `+` (no `str_eval_one` re-dispatch) |
| R3 `str_arg_open` | each LEFT$/RIGHT$/MID$ (each already costs a snapshot plus a slice, ≥ 1500 T) | +129 |
| R5 `str_ev_fn` | each string FN call (several tenant bounces) | +129 |
| `sh_go_g` | every expression-time heap op (≥ ~700 T each: block, CALSLT, dispatch, body) | +129 (≤ ~18% of the cheapest CMP) |
| INSTR P3 | INSTR | +7 |
| FRE P3 | FRE(n) / FRE(s$) | +136 / ~+160 |
| VARPTR(#) | VARPTR(#n) | +129 |
| P2 `ssk_store` | each copying string store | +51 (`fperr_test` 44 + `jr` 7) |
| A `sp_ceil` | each scalar/array allocation (tenant) | ~95 |

⚠️ **R1 is the one test on a hot shape.** Two cheaper variants exist, both left as
options:

1. **(a) A stored floor cell.** STKFLOOR = CTLLIM + R, written beside CTLLIM by its
   single writer. The test becomes `ld hl,(STKFLOOR)` / `scf` / `ccf` /
   `sbc hl,sp`: 42 T inline. `stk_guard` would take the same cell and lose 34 T on
   **every factor**: a net TIER 5 win. It costs a 2 B RAM cell, which needs a
   RAM-tier ruling from Joost (D-WSZERO keeps the work area at zero).
2. **(b) Stop the probe from descending numeric parentheses at all.** That removes
   the O(N²) re-probe too, but it is an evaluator change, out of scope.

---

## 7. Byte budget

`make basic-reloc` today reads **low 156 B, main page 1 452 B, sub page 0 184 B**.
Low and page 1 share one budget through promotion
([`promote_scout.py`](../scratchpad/promote_scout.py)), so the main ROM has 608 B
between them.

| item | region (address today) | bytes |
|---|---|---|
| `stk_room` | low | 19 |
| `sh_go_g` + `shg_skip` | low (`sh_go` $2790) | 13 |
| R2 `str_eval_plus` loop | low ($2889) | +7 |
| R3 `str_arg_open` test | low ($2B03) | +5 |
| H7 INSTR P3 | low (`efi_p_ok` $2D6C) | +2 |
| **low subtotal** | | **46** |
| R1 `str_eval_paren` test | page 1 ($4994) | +5 |
| R5 `str_ev_fn` test | page 1 ($54F4; `str_eval_no` is out of `jr` reach) | +6 |
| H10 VARPTR(#) test | page 1 ($4F68) | +6 |
| H9 `fre_go` P3 | page 1 tail past the pins ($7E1A) | +7 |
| H11 P2 `ssk_store` | page 1 ($48F3) | +5 |
| **page-1 subtotal** | | **29** |
| A `sp_ceil` + 2 calls | sub page 0 | 22 |
| optional `stk_room_h` entry | low | +6 |

Total: **75 B main** (out of 608) and **22 B sub**. No promotion is needed. The
low-region sites are all of class H plus R2, R3 and the primitive. `sh_go` and its
callers live in `basic/str-engine.asm`, which is included in the low region.

---

## 8. Tests

### 8.1 Edge rows (zerobas, with the VG-8020 as oracle where it can express them)

* **Add to [`edgesafe_probe.py`](../scratchpad/edgesafe_probe.py)'s `WORK`.** The
  watchpoint margin must be ≥ 0 at K 109…224, on both machines:
  * `deepprobe`: `B=` + 40×`(` + `1` + 40×`)` (LB1)
  * `uplus`: `B=` + 120×`+` + `1` (LB2)
  * `strparen`: `B$=` + 40×`(` + `"X"` + 40×`)`
  * `leftnest`: `B$=` + 25×`LEFT$(` + `S$` + 25×`,1)` (LB3)
  * `strfn`: `DEF FNA$(X$)=X$` nested 20 deep
  * `heapdeep`: `B$=(((((S$+S$)+S$)+S$)+S$)+S$)` in a loop under `CLEAR 30`, which
    forces the GC
  * `autodim`: `B=` + 15×`(` + `Z#(1,1)` + 15×`)` at the LB4 gap
* **Add to [`stackcorrupt_probe.py`](../scratchpad/stackcorrupt_probe.py)'s
  `ROWS`, on both machines:**
  * `k200p40` and `k200u120`: §2's reproductions.
  * `k200s40`: the string-paren form.
  * `k110flat`: `PRINT 1` at the DIM edge, the "(a)" row.
  * `kNNa2`: LB4.

  Each row's verdict *and* `A(X)` must equal the VG-8020's.
* **`dimedge-acceptance`**
  ([`basic_probe_dimedge.py`](../probes/basic/basic_probe_dimedge.py)) must stay
  10/10. It is the guard against §4.5 moving the top-level edge.
* **A new gate, `deepexpr-acceptance`,** built from the stackcorrupt rows. The
  rows the reference completes or refuses at a *different* nesting depth (the
  slope, §5.3) are KNOWN_DIVERGE, so they fail loudly the day the climber item
  lands.

### 8.2 Knives (a new runner, `deepexpr_knives.py` in the scratchpad, to be written; hash the ROM around every plant)

| knife | plant | must redden |
|---|---|---|
| K-DX1 | remove R1's test | `deepprobe`, `strparen` (margin < 0) |
| K-DX2 | restore R2's recursion | `uplus` |
| K-DX3 | remove R3's test | `leftnest` |
| K-DX4 | remove R5's test | `strfn` (expected **inert** while `fnf_save`'s 256 binds; say so in advance) |
| K-DX5 | per H class: route that one site back to raw `sh_go` (snapshot, append, temp-alloc, slice, CMP, INSTR, VAL, radix/fill, FRE, VAR_STORE) | `heapdeep` / the matching unit row, once R < 65 |
| K-DX6 | `shg_skip` publishes the caller's HL instead of `STR_EMPTY` | U3's stale-descriptor row; an edge row where `A$` changes after `B$=…A$+"X"…` |
| K-DX7 | remove P2 | U3's store row; a trapped ERR 7 leaves `A$=""` instead of `"KEEP"` |
| K-DX8 | remove `sp_ceil` | `autodim` (crash / NO READING) |
| K-DX9 | `STK_EVAL_RESERVE` R → 16 | edgesafe CORRUPT on every workload (as K-ER1 did for the edge reserve) |

### 8.3 Unit tests (`tests/test_deepexpr_guard.py`, host Z80)

These follow `test_control_flow.py`'s pattern of poking CTLLIM to place SP exactly.
One test per failure-publish rule:

* **U1 `stk_room`.** Check the boundary on both sides: site SP−2 = CTLLIM+R+1
  passes, = CTLLIM+R refuses. Also check that HL/BC/DE are preserved, that
  FPERR := 6 only on refusal, and that a pre-set FPERR=4 survives
  (first-error-wins).
* **U2 the `sh_go_g` skip contract.** The tenant is not entered (sub absent, or a
  counter). Returns A≠0, NZ, CF clear, HL=`STR_EMPTY`, DE=0, BC unchanged, and SP
  is balanced with a caller-pushed fourth word (ops 5/9).
* **U3, one row per caller (P1/P2/P3):**
  * `str_temp_alloc` → `STR_EMPTY`/DE=0
  * the three snapshot entries → STRPTR=`STR_EMPTY`
  * APPEND → R unchanged
  * SLICE → temp unchanged
  * INSTR → DE=0
  * FRE → 0, with no sub2 call
  * VAL → DE=0, FPERR=6
  * `ssk_store` with FPERR pending → the variable unchanged and the pending code
    raised
* **U4, the R arms.** `str_eval_paren`, `str_arg_open` and `str_ev_fn` refusals →
  CF clear, HL back on the `(` / selector / FN token, FPERR=6.
* **U5 `str_eval_plus` loop.** `+++A$` gives the value. `+++5` declines with HL on
  the first `+`. The stack depth is constant in the count.
* **U6 `sp_ceil`.** Both orderings of min(), and the +4 offset.

---

## 9. Open questions (each is a concrete probe row)

1. **Q1, the VG-8020's intercept.** At K ∈ {120, 150, 200, 300}, bisect the
   largest N for which `B=` + N×`(` + `1` + N×`+1)` completes. The slope should
   read 6 B. The intercept X is the reference's own stack margin, which sets the R
   that matches flat expressions. Also run `k110flat` (`PRINT 1` just past the
   DIM edge) on both machines, after D-FREPLUS14.
2. **Q2, unary `+`.** freshape-style: `A=+++++FRE(0)` against `A=FRE(0)`, and
   `B$=+++A$` with FRE in its sibling, giving the cost per `+` on the VG-8020.
3. **Q3, string `(` and string-function nesting.** `B$=(((STR$(FRE(0)))))` against
   `B$=STR$(FRE(0))`, and `B$=LEFT$(LEFT$(STR$(FRE(0)),9),9)`: the reference's
   cost per string paren and per LEFT$ level, which sets the "same point" for
   R1/R3.
4. **Q4, the reference's verdict on LB1/LB2.** Rows `k200p40` and `k200u120`:
   the error, and `A(X)` afterwards.
5. **Q5, auto-DIM mid-expression on the reference.** At a fixed nesting (15
   parens), bisect K for `Z#(1,1)`. This settles whether the VG-8020's ceiling is
   SP-relative, and with what margin (sets `STK_ALLOC_RESERVE` for "same point",
   beyond safety).
6. **Q6, FN near the edge.** `B=FNA(1)` and `B$=FNA$("X")` at K 110…300 on both
   machines. zerobas refuses with less than 256 B below SP (`fnf_save`); measure
   the reference's edge.
7. **Q7, disk leaves (zerobas only).** `guardattr_probe.py` on the disk machine
   for `A=LOF(1)`, `A=EOF(1)`, `A=LOC(1)`, `A$=INPUT$(1,#1)`, `A=DSKF(0)`,
   `A$=DSKI$(0,0)`, `A$=MKS$(1)`, `A=CVS(B$)`, `A=VARPTR(#1)`: the depth below the
   last passing test.
8. **Q8, GC depth (zerobas only).** The `heapdeep` workload with a watchpoint
   armed at `sh_go_g`'s SP, under `CLEAR 30` so `strheap_gc` / `gc_slow` /
   `sg_shellsort` run, with PLAY on. This decides between one reserve and two.
9. **Q9, the target after a trapped ERR 14 in LET (a possible existing
   divergence).** `CLEAR 12:B$=STRING$(8,"B"):A$="KEEP":ON ERROR GOTO 90:A$=B$`,
   with `90 PRINT A$;ERR`, on both machines: does the reference keep `KEEP`?
   P2 assumes it does.
10. **Q10, the arrays tenant's own depth (zerobas only).** A write watchpoint during
    `DIM Z#(10,10)` and an auto-DIM, from the `scv_ceil_try`/`aal` check to the
    tenant's return. This sets `STK_ALLOC_RESERVE`.
11. **Q11, the relational and function-call slope on zerobas.** `stackhwref_probe.py`
    rows: `A=1<(1<(1<…))` and `A=ABS(ABS(…))`, to fill §5.3's missing cells.

---

## 10. Build order

1. ✅ BUILT 2026-10-20 (code and unit tests; the §8.1 emulator rows and the
   emulator knives still to run). LB1–LB3 + LB4, as a TIER 1 slice: `stk_room`,
   R1–R3, R5, `sp_ceil`, the §8.1 rows, K-DX1–4 and K-DX8. R stays 128.
2. ✅ BUILT 2026-10-20, in the same slice. `sh_go_g` + P1–P3: the H sites, U2/U3,
   K-DX5–7. ~~R is still 128, so behaviour cannot change yet.~~ 🔴 That was wrong:
   see §11.4 -- every `sh_go_g` test sits deeper than the factor guard that used to
   cover its op, and P2 changes what a store does with a fault pending.
3. Re-measure (§5.2), lower R, K-DX9, `deepexpr-acceptance`, full battery.
4. File the per-level climber item (§5.3) and the FN-margin item (Q6).

---

## 11. As built (2026-10-20)

### 11.1 Where each piece went, and its cost

The six pins forced the shape. Every byte added in front of `$3297` (low) or
`$6CF3` (page 1) must be refilled to the byte, so each page-1 site is reached by a
call that *replaces a call of the same size* there, and the bodies sit past the
pins. Nothing in front of a pin moved; `pin_plan.py --check --budget 4` reads 6/6,
4 B waste, as before. No existing label moved either (the resident ABI files did
not change).

| site | as built | inline bytes | T-states added (its own path, success) |
|---|---|---|---|
| `stk_room` | as §4.1, the RAM-free variant (`ld hl,(CTLLIM)` + `add`). Low region's end (`basic/main.asm`) | — | 122 incl. call/ret |
| R1 `str_eval_paren` | `call str_eval` → `call sep_eval` (`call stk_room` / `jp c,str_eval` / `ret`), page 1 past the pins. The `jp` keeps the level at 6 B | 0 | 132 per probed `(` |
| R2 `str_eval_plus` | a loop, as §4.2; the body moved to the low region's end (its old 7 B in `str-engine.asm` pay for R3 + H7) | −7 | saves the re-dispatch per extra `+` |
| R3 `str_arg_open` | `call stk_room` / `jr nc,sao_empty`, inline | +5 | 129 per LEFT$/RIGHT$/MID$ |
| R5 `str_ev_fn` | `call fn_call` → `call sef_fn` (test, `jp c,fn_call`; refusal drops str_ev_fn's return and jumps to `str_eval_no`) | 0 | 132 per string FN |
| `sh_go_g` | `call stk_room` / `jp c,sh_go` / the §4.3 skip. NOT a fall-through into `sh_go`: that would put 13 B in front of `$3297` | — | 132 per heap op |
| H sites | `str_temp_alloc`, `sst_op`, `sct_go`, `str_temp_slice`, `ev_ff_val`, `shx_tail`, INSTR, `str_cmp_bits`, both `fre_go` ops → `sh_go_g` | 0 | (in `sh_go_g`) |
| H7 INSTR P3 | `jr nz,efi_skipped` over the `ex de,hl` | +2 | 7 |
| H9 `fre_go` P3 | as §4.3 (`frg_pool` / `fre_zero`), past the pins | +7 | FRE(n) 139, FRE(s$) ~160 |
| H10 VARPTR(#n) | `call fch_ctx_addr` → `call fch_ctx_g` (test, `jp c,fch_ctx_addr`, else HL = 0) | 0 | 132 |
| H11 P2 | `call sh_go` → `call ssk_go`: `ld b,a` / `ld a,(FPERR)` / `or a` / `ld a,b` / `jp z,sh_go_g` / `ret` (op 12 reads no blk+6, so B is free) | 0 | 35 + `sh_go_g`'s 132 |
| A `sp_ceil` | as §4.5 but without the DE save (both callers reload DE next): 13 B + 2 calls. CLEARPOOL arm only, as the static ceiling is | — | ~100 per allocation |

Per-factor path (`stk_guard`, `ev_f`, the climber, `ev_rel`'s numeric path):
**0 T added.** Walls (`make basic-reloc`): low 156 → **109 B**, main page 1 452 →
**408 B**, sub page 0 184 → **165 B**.

`STK_ALLOC_RESERVE` = **24** (`basic/sysvars.inc`), the spec's upper prediction.
The host test (`tests/test_deepexpr_guard.py` U6) sweeps a real `ary_alloc` of
`Z#(10,10)` upward in SP from just above the array: every SP refuses or fits with
the data intact and the stack above the array; the tenant's deepest write there was
24 B below its call site (Q10's harness half; the machine half is still open).

**Q5 answered, and `STK_ALLOC_RESERVE` = 88 (D-EVALSLOPE, 2026-10-20).** Once a `(`
cost 6 B here as on the VG-8020 (§5.3.1), row LB4 fitted here and refused there.
Bisected with `scratchpad/autodim_edge_probe.py`: the VG-8020's auto-DIM edge is
K = 1106 + 6 B per paren (P = 0 / 5 / 15 / 30 → 1106 / 1136 / 1196 / 1286), so its
array growth is bounded by the live stack at every depth. At 24, zerobas read
1090 / 1132 for P = 0 / 15. At 88 all four depths match the VG-8020 exactly
([`autodim_edge_r88.out`](../scratchpad/autodim_edge_r88.out),
[`autodim_edge_r88b.out`](../scratchpad/autodim_edge_r88b.out)). The statement-level
edges did not move, because the static ceiling still binds there:
`dimedge-acceptance` 10/10, and the four D-EDGEONERR shapes SAME
([`allocres88_edgeonerr.out`](../scratchpad/allocres88_edgeonerr.out)). The
tenant's own 24 B is inside the 88.

### 11.2 Not built

* The stored floor cell (§6 option (a)): it needs a 2 B RAM cell, which is
  Joost's call (D-WSZERO). `stk_room` is the variant that needs none.
* `stk_room_h` (§4.1): no second reserve until Q8 asks for one.
* The non-CLEARPOOL arm of `ev_fre_close` keeps a raw `call sh_go` (a scaffold
  build, a different machine).

### 11.3 Unit tests and knives (host)

`tests/test_deepexpr_guard.py` (U1-U6 of §8.3, 29 rows). U1 finds `stk_room`'s and
`stk_guard`'s refusal thresholds by sweep and requires the SAME byte. U4/U5 track
the lowest main-side SP and require it to stay above CTLLIM for the 40-deep string
paren, the 20-deep LEFT$ nest and 120 unary `+`. U3's INSTR / VAL / LEN / FRE("")
rows sweep CTLLIM from tight to loose: the right value with nothing pending, or ERR
7 pending and never 18648 (STR_EMPTY's address). Each of K-DX1, -2, -3, -6, -7, -8
and the INSTR P3 knife, planted in the source, reddens this file. Three older
tests' `set_var` helpers now clear FPERR first (a statement boundary): P2 had sent
their stores down the raise funnel on a fault a previous case armed on purpose.

### 11.4 Behaviour that DOES change at R = 128 (§10's old claim corrected)

1. **Statement-level string ops at the very edge.** `sh_go_g` asks for R below the
   op itself, a few frames under where the factor guard used to answer for it. A
   string LET or INPUT has no factor guard at all (`A$=B$`, `INPUT A$`), so at the
   DIM edge such a statement can now refuse with ERR 7 where it completed. A flat
   numeric expression already refuses there (§5.3), so this widens an existing
   economy gap; lowering R (step 3) narrows both.
2. **P2 is visible.** A string store with ANY fault pending (`A$=B$+5`'s type
   mismatch, `A$=X$+X$` over 255, a pending division by zero) now stores nothing
   and raises at the store, as the reference's eager error does. Before, the
   variable took the value and the error was raised after. Trapped rows that read
   the variable afterwards will move toward the reference.

