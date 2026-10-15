# D-WSZERO S12 — overlays on published buffers, provable pair by pair (read-only prep, 2026-10-16)

Tree: HEAD `7369a98c` + the staged S11 work; build syms of 2026-10-15 23:16 (= the S11 tree).
Nothing in the repo was written, built or run. Instruments, all in this directory, run from the
repo root with `python3 -B` (no `__pycache__` in the repo):

| script | what it does | output |
|---|---|---|
| `tools/ram_map.py --floor-top F380` (repo, read-only) | the untagged diskless names still below $F380 | `floortop.out` |
| `../s11/refs.py` (S11's) | every reference of every remaining name, enclosing label | `refs_all.out`, `refs_compact.out`, `refs_hosts.out` |
| `reach.py FILES ENTRIES CELLS` | label reachability (call/jp/jr/djnz + fall-through) inside the named files; prints each entry's EXTERNAL targets and which cells its reach set touches | `reach_gfx.out` + inline runs quoted below |
| `addrof.py`, `idioms.py` | address-of + block-walk scan; `high`/`low`/`& $FF` scan (wider than ws_shift's: also `low(`) | inline |
| `sim.py` | **the dry run**: re-resolves both components with the S12 equates + 3 comment rewrites substituted IN MEMORY; checks every moved name, every follower, no other name changes; overlaps; the ram-width ratchet; the freed window bytes; `--floor-top`; the per-host **byte-sharing pair matrix** with a co-live check | `sim.out` (VERDICT OK) |
| `repl.py` | the exact line replacements | `s12_replacements.md` |

**(unverified)** marks every claim not read off code/syms. "T" = transient inside one routine or
tenant call; "Tx" = live across an expression evaluation (which can run USR code, a DEF FN call,
VAL, INPUT$, the string GC, a hook).

## 0. Verdict in one screen

* **89 names move (+6 followers), 290 window bytes freed** (`sim.out` §4: 876 → 586 B covered;
  27 spans). `--floor-top F380`: **200 → 103** untagged names. Ratchet green after deleting two
  stale pins (CVT_MODE, DISKOP_A/PLY_NUMOVF — the good direction). 0 ROM bytes (equates, 3
  comment rewrites, 23 assembler guards).
* **Four hosts, each with its own exclusivity rule:**

| host | bytes | guests (bytes) | the rule that makes it provable |
|---|---|---|---|
| **BUF** $F55E-$F65F (zerobas LINEBUF = STRSCR) | 258 | PAINT cursors + arc mask + box + CIRCLE draw-phase + RENUM: 72 B at $F5A0-$F5E7 | the guests live only inside a LINE/CIRCLE/PAINT/RENUM call, statements that take **no string argument**; every STRSCR value is consumed before such a call; no BUF writer is reachable from inside it; nothing the evaluator can reach touches the guests |
| **DEF FN shadow slots** FN_PAREA $F756-$F7B8 (PARM2) | 99 | PRINT USING render 64, Bresenham 17, read_line 7, SAVE 2, PLN 4, MERGE 2, TKLNUM 1 (+READ/DEFINT 5 overlaid on PU_DIG): 97 B used | every slot read is bounded by FN_FEND, which equals `low FN_PAREA` whenever no FN call is in progress; the guests' users are statements the evaluator cannot reach, and their live ranges contain no evaluation |
| **MULPROD+DIVPAD** $F82A-$F84C (HOLD8 tail / HOLD2 / HOLD / ARG head) | 35 | TK* 35, VBUF 32, cmul 8, WIDIG 5, PLF 4, ISRCH 4, MUL_I/PP 3, PLAY 3, FP_SHIFTAMT 1, FP_OPMODE 1 (all overlaid) | **leaf scratch**: every family here is a routine that calls no other family while its cells are live and is never called from inside another (reach sets: no external call into any other family), and none makes a USR/hook call while live (the S11 T-only rule for published math scratch) |
| **FBUFFR+0 and FBUFFR+25..42 + DECTMP..DECCNT** $F7C5, $F7DE-$F7F5 | 25 | TKOVF 1, DIVREM 15, LHS_FAC 8, LHS_FACTYP 1 (exclusive bytes) | **no zerobas user at all** (flt_out writes FOUTBUF..+22, the math aliases end at +20); guests are T-only |

* **Rejected:** KBUF (a direct line executes from it and stays live across a direct GOSUB), the
  Bresenham cells in BUF (DRAW parses an `INPUT$` argument IN PLACE in STRSCR while it draws),
  every Tx cell in every host (GFX_DEXP, PU_FDESC, MIDS_DEST, CLR_SAVE, LOC_*, TSV_*, OO_*, LHS_VARTYPE,
  MC_TYPE …), CVT / HORNER_G / MATH_A in the leaf host (fp_mul/fp_div call flt_to_int16 while
  MULPROD/DIVPAD are live, and the math tenants call fp_mul), FILNAM/FILNM2, LINWRK/PATWRK, VOICAQ…
* **Left for S13/S14: ≈ 328 B** (294 by the map + HORNER_G/MATH_A's undeclared 17+17): S14 code
  ≈ 287, S13 (SLTWRK/PROCNM, Joost's call) ≈ 41. §6.

## 1. Inventory: the diskless remainder in $ECF8..$F37F (before S12)

`floortop.out`: 200 untagged names (one more is hidden — §8 finding 1: PLY_NUMOVF). Grouped by
user and lifetime (refs in `refs_compact.out`; "eval-reach." = runnable from inside an expression):

| group (bytes) | users | lifetime | eval-reach. | S12 |
|---|---|---|---|---|
| PAINT cursors GFX_POVF..PSPA 9, PSP/PBASE/PFLOOR 6, PPITCH 1 | sub/graphics.asm gfx_paint_op (reach: 59 labels, only external `strheap_aryend`, a pure walk sub/strheap.asm:767-777); POVF read by ep_draw basic/graphics.asm:871-874 right after the tenant | T (one tenant call) | no | BUF |
| arc mask GFX_CS_M1/M2 8 | gfx_circ_wedge_prep sub/graphics.asm:1489-1510 | T | no | BUF |
| box TX1..YSTEP 12 | gfx_box_outline/fill, gbf_*, gfx_paint_row (sub/graphics.asm:904-1240, 2787) | T | no | BUF |
| CIRCLE draw SVX..WS_O 28, WE_P/WE_O/WRAPF 4 | gfx_circle_op reach (117 labels, no external); CS_AX/AY also cpt_angle_from_arga (sub/circleparse.asm:346-350, consumed in the same entry: 369, 483-505) | T | no | BUF |
| Bresenham CX..SDY 17 | gfx_draw_seg/bres_* (sub/graphics.asm:646-880): LINE, box, CIRCLE spokes/points, PAINT rows, **DRAW** | T (gfx_draw_seg runs a whole segment and returns, :646-656) | no | FN slots |
| RN_PTR/RN_OLD 4 | ex_renum/ex_auto (basic/program.asm:1414,1476) → lineedit (sub/lineedit.asm:832-1004, 1175) | T within RENUM (round trips print only) | no | BUF |
| PU_NUM 32, PU_DIG 32 | basic/printusing.asm:310-356 → punum / pusign / puemit tenants | T: written after the item's eval, consumed into DB_WIN before `print_string` (:353-355) | no | FN slots |
| RL_* 7 | read_line basic/repl.asm:144-221, sub/readline.asm, sub2/edctrl.asm | T per line (re-set at rl_loop :157-162) | no | FN slots |
| PLN_NUM/PTR 4 | parse_lineno basic/program.asm:389-395, sole caller :94 (dispatch_line) | T | no | FN slots |
| MRG_PTR 2 | ascii_read_lines basic/files.asm:2365-2400, mrg_storeline :2557 | T per line | no | FN slots |
| SV_OP/SV_STAT 2 | sv_tenant basic/save.asm:793-803, save_tenant sub/save.asm:76-90 | T | no | FN slots |
| DEFT_PTR (=RDV_LINE), RDV_VAL, RDV_ST 5 | ex_deftype basic/usr.asm:272-278; read_one_value basic/program.asm:2481-2491 → exr (2330-2370: target parsed BEFORE the value; inp_num, no eval, between) | T | no | FN slots, overlaid on PU_DIG |
| TKLNUM 1 | the crunch only (basic/tokenise.inc; `tokenise` stub basic/interp.asm:310, callers: line entry, ASCII LOAD/MERGE/CLOAD) | T per line | no | FN slots |
| TK* 35 (TKDIG..TKSRCSAVE) | tk_float (sub/tkfloat.asm: **no external call**), dt_float (basic/detok.inc:278-330, writes only the DB_WIN window via pchar sub/detok.asm:63-104) | T per literal | **yes** (VAL, INPUT, READ) | leaf host |
| TKOVF 1 | crunch (tokenise :46 → tk_end :431) and VAL (svp_flt sub/strheap.asm:2823-2849) | T, but live across tk_float | yes | FBUFFR+0 |
| GFX_VBUF 32 | gfx_spr_* tenant ops; ev_f_sprite basic/graphics.asm:1150-1170 (fill → str_temp_alloc → copy); spr_mode_save/restore around CHGMOD (:1220-1229, basic/screen.asm:106-110) | T | yes (SPRITE$) | leaf host |
| MULCAND/MULTPLR/MUL32 8 | mul16x16_32 + cmul (basic/float-arith.asm:1760-1925); MUL32 dead before `jp fp_mul` (:1920-1925) | T | yes | leaf host |
| WIDIG 5 (+MUL_I) | widen_uint_to (:2237-2300; calls div10/zero_fill only) | T | yes | leaf host |
| MUL_I 1, MUL_PP 2 | fp_mul (:875-985), MUL_I also widen_uint_to | T | yes | leaf host, outside MULPROD |
| PLF_RA/RA2 4 | pop_lhs_and_probe (:1641-1675, external factyp_is2 only) | T | yes | leaf host |
| ISRCH_A/B 4 | sh_instr_search sub/strheap.asm:2532 (no external) | T | yes | leaf host |
| PLY_XSP 2, PLY_NUMOVF 1 | play_parse_tenant sub/playparse.asm:48 (78 labels, **no external**) | T | yes (USR → pinned $73E5 PLAY) | leaf host |
| FP_SHIFTAMT 1 | fp_add/fp_div's dig15_shr/shl | T | yes | leaf host, outside DIVPAD |
| FP_OPMODE 1 | caddsub_go/caddsub_disp (:1818-1872), live across pop_lhs_and_probe + the widen helpers | T | yes | leaf host, apart from PLF/WIDIG/MUL_I |
| DIVREM 15 | fp_div (:1022-1099) | T | yes | FBUFFR tail |
| LHS_FAC 8, LHS_FACTYP 1 | pop_lhs_and_probe → widen_lhsframe_to (pointer-addressed, :1447-1451); live across mul16x16_32 in cmul | T | yes | FBUFFR tail |
| GFX_DEXP 24 | DRAW: the RESIDENT evaluates it (basic/graphics.asm:993-999) | **Tx — it IS the eval's source** | — | rejected → S14 |
| PU_FDESC 3, PU_FMTLEN..PU_DEC 7 | PRINT USING format state across items | Tx | — | S14 / S13 |
| MIDS_DEST 2 | MID$ stmt (basic/str-engine.asm:1580 → tgt_desc_fix basic/vars.asm:524) | Tx | — | S14 |
| CLR_SAVE 2, LOC_* 2, OO_* 3, TSV_* 9 (+IN_RDLEN, FMT_*, FCH_RDMODE aliases), LHS_VARTYPE, VARTYPE, MC_TYPE, VS_* 3 | COLOR / LOCATE / OPEN / tape save / LET / arrays / math-call / var store | Tx, or not a leaf (var_store_fac calls round_and_finalize/sc_call) | — | S14 (S12b candidates: VS_*, RVDESC) |
| DB_WIN 96 + DB_* detok 12, GFX_DFTOP/DFSTK 33, FOR_CUR 29, CVT 18, HORNER_G 18, MATH_A 18, math singles | as classified (wszero_classify.md (ii) 7) | Tx / co-live with every host | — | S14 |
| SH_* 18, GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG 5, GFX_PTX/PTY 2, PRDEST/PRDEV, ERRMARK, INDLR_N, WSRC_TYP, DB_MORE/RESUME/CUR, DISKOP_OP group | | Tx / persistent-ish | — | S13 |

## 2. The hosts: who uses them, and when

### 2.1 BUF $F55E-$F65F (258 B)
Zerobas users (`refs_hosts.out`), all statement-level unless marked:
* **line entry / direct mode**: read_line (basic/repl.asm:145), dispatch_line/dl_cmd (program.asm:31,57)
  — the crunch's overshoot also reaches BUF (TOKBUF+575 = $F65E, sysvars.inc:1029-1036). A direct
  statement then **executes from its crunched copy in KBUF**, not from BUF (sysvars.inc:1919-1926).
* **console INPUT / LINE INPUT**: inp_readline (input.asm:245-268) puts the answer at LINEBUF+1 and
  keeps the UNREAD part there while the next target's subscripts are evaluated (input.asm:89-118:
  `inp_readline` → per variable `tgt_parse_req` (eval) → `read_into_strscr`).
* **STRSCR staging** (STRSCR = LINEBUF, sysvars.inc:1929): file-name expressions (files.asm:1175),
  INPUT#/LINE INPUT# (read_into_strscr :1425-1505), READ string items (readdata-body.inc:83-169),
  KEY n,"…" (screen.asm:432; keystr.asm:188 reads it), seq_end (files.asm:325), **and the
  eval-reachable INPUT$ (strvar.asm:585-589), MKI$/MKS$/MKD$ (:334-380), DSKI$ (:618)**. A STRSCR
  value is wrapped by `strscr_desc`/`mk_rvdesc` (str-engine.asm:410-430) and **consumed by its
  consumer** — copied to the heap, or (DRAW) read in place — before the next string sub-expression.
* AUTO's preset (program.asm:1494-1502), ASCII LOAD/MERGE line assembly (files.asm:2367-2397), disk
  hooks (disk/kernel.asm, disk/fat.asm: disk statements only).
* Interrupt time: none (no BUF name in traps/playsvc/keytrap/sprtrap/subromcall; C-BIOS has no BUF
  writer outside systemvars.asm — its INLIN is a stub that writes TEMP, not BUF:
  cbios/src/inlin.asm:63-180).

### 2.2 FBUFFR $F7C5 (43 B) + DECTMP/DECTM2/DECCNT $F7F0-$F7F5
* FOUTBUF = FBUFFR+1: flt_out writes at most sign + 20 + space + NUL from FOUTBUF (float.asm:100-135,
  ≤ FOUTBUF+22 = $F7DC, by the format rules **(bound unverified across every branch; declared 24)**).
  STR$ reads it (str-engine.asm:1287).
* The math pack's aliases: SQRT_R = MATH_R = HORNER_ACC = FOUTBUF (18 B FPNUM), HORNER_CNT = +18,
  HORNER_PTR = +19..+20 (sysvars.inc:4973-5062) — end $F7DA.
* **FBUFFR+0 ($F7C5) and $F7DE..$F7F5 have no zerobas user** (no sym value, no equate, no literal,
  no `FBUFFR+n`/`FOUTBUF+n` beyond +19, no walk reaches them; disk map and C-BIOS: none).
  So this is an idle published span, like S11's hosts — the guests need only S11's T-only rule.

### 2.3 MULPROD + DIVPAD $F82A-$F84C (35 B)
* MULPROD $F82A-$F845: fp_mul (float-arith.asm:886-997; `ld h,high MULPROD` + the page assert :920).
* DIVPAD $F83E-$F84C: fp_div (:1023-1074).
* RND_ACCLE..RND_K $F82A-$F83D: fp_rnd (sub/fp_rnd.asm; externals dig15_iszero, fsc_pack_arga →
  arga_pack_fac: 3 labels, no external).
* Nothing else in either component; no interrupt-time user. The range is the reference's HOLD8
  tail / HOLD2 / HOLD / ARG head: a USR routine may legally use it, so only T-only guests (no
  USR, no hook, no hook-carrying BIOS call while live).

### 2.4 The DEF FN shadow slots FN_PAREA $F756-$F7B8 (99 B; the reference's PARM2)
* Written only by the FN-call tenant (sub/deffn.asm:120-330) between `fn_call` and `fn_leave`.
* **Read only up to FN_FEND**: fn_shadow_find (sub/arrays.asm:552-583, every scalar lookup) and the
  GC's sg_walk_fnframe (sub/strheap.asm:1095-1110) stop at the first compare when
  `FN_FEND == low FN_PAREA` — "no FN call in progress" (sysvars.inc:4422-4425). raise_error resets
  it (interp.asm:1319-1320), boot sets it (usr.asm:49-50); nested frames are saved to the POOL, not
  here (deffn.asm:461-626). So between FN calls the 99 bytes are never read.
* Disk machine: disk.rom's MSX-DOS-phase code and its BDOS console scratch sit here too (WA_SEG
  $F756, CONOUT_CHAR/PG_SV_A8 $F771-$F772, CONIN_* $F7A5-$F7A8; disk/init.asm:290-312) — DOS phase
  or BDOS calls from user code only; pre-existing since S6 (the FN frame), see §8 finding 5.

### 2.5 KBUF (TOKBUF $F41F, 318 B) — REJECTED as a host
A direct statement executes from TOKBUF (sysvars.inc:1919-1926); `GOSUB` typed directly keeps the
line live for the whole subroutine (RETURN comes back into it); the crunch writes up to
TOKBUF+575; BROM_TEXT/SLOT use TOKBUF+0..2 at boot. No fixed tail of KBUF is idle while a direct
line is pending, and nothing in zerobas records whether one is.

### 2.6 Others — REJECTED
SWPTMP (full: BLOAD/SWAP/SAVE tenant), TEMP/TEMP2/3/8/9 (S1), TEMPST/TEMPPOOL (live across every
string expression), ARGA/ARGB (CIRCLE's DREQ 3 holds ARGA across a resume, float.asm:62-71),
FILNAM/FILNM2 (tape search; also BASIC-visible on the VG-8020 after a tape load — a later PEEK
would see graphics garbage), LINWRK/PATWRK (C-BIOS chput.asm:459-557, sub.asm:516, video.asm:1168),
VOICAQ.. (interrupt-time PLAY), the S10/S11 PARM1 head and tail (already persistent/S11 guests).

## 3. The placements and their proofs

Common facts (each is a line in `sim.out` §6, the pair matrix):
* **F1 — the graphics tenant is closed.** Every op entry's reach set inside sub/graphics.asm has no
  external target except PAINT's `strheap_aryend` (`reach_gfx.out`). POINT (op 2, eval-reachable)
  touches only GFX_PTX/PTY; SPRITE$ (op 8) only GFX_VBUF. So no guest of BUF or the FN slots is
  reachable from the evaluator through the graphics tenant.
* **F2 — no interrupt-time code names any guest or host** (traps.asm, playsvc.asm, keytrap.asm,
  sprtrap-body.inc, subromcall.asm: 0 hits; S7's SUB_INT_RAM is at $F92D).
* **F3 — traps are serviced at statement boundaries**; an FN body is an expression and has none.
  **(per the trap design S2 recorded; not re-read)**

### 3.1 BUF ← PAINT/arc/box/CIRCLE draw cells + RENUM (72 B, $F5A0-$F5E7, one page)
Proof: (a) the guests are written and read only inside one call of graphics ops 3/4/5 (LINE, CIRCLE,
PAINT) or of the RENUM/AUTO head — plus POVF read immediately after (graphics.asm:872-874) and
CS_AX/AY inside one circleparse entry; (b) those are statements, reached from no expression (F1;
none is a USR-pinned entry: $3297 pop/ret, $6CF3 BLOAD continuation, $73AC RUN, $73E5 PLAY);
(c) LINE/CIRCLE/PAINT/RENUM take no string argument, so when the tenant runs every STRSCR value
of the statement's own arguments has been consumed; console INPUT, line entry, ASCII LOAD and the
crunch are other statements; (d) inside the call nothing writes BUF (F1: no external calls; the
RENUM head prints via print_string/CHPUT); (e) no interrupt writes BUF (F2, C-BIOS); (f) user H.TIMI
hooks: the reference keeps BUF live with interrupts on (INLIN), so a hook cannot use it.
**Closest program**: `CIRCLE(LEN(INPUT$(250)),96),40,15,-.5,-2.5` — INPUT$ fills STRSCR up to
BUF+250 (over the guests' bytes) during CIRCLE's argument co-routine, and circleparse then writes
CS_AX/AY there; harmless, because LEN() consumed the string before the next entry, and the draw
cells are written only after the last argument. The program that WOULD break is DRAW (below).
Rejected here: **the Bresenham cells** — `DRAW INPUT$(n)` hands the tenant STRSCR+1 as the
command string (gdw_hand_string, graphics.asm:1021-1027: GFX_DVAL = the body pointer; D-DRAWINPLACE)
and DRAW draws through gfx_draw_seg while parsing it. Also rejected: GFX_VBUF (SPRITE$ is
eval-reachable — `INPUT A,B(ASC(SPRITE$(0)))` would stage into BUF over the unread answer), PU_*
(fine for BUF — pu_hold_fmt snapshots a non-text format to the heap, printusing.asm:207-225 — but
placed in the FN slots instead), GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG (Tx across the parse co-routine).

### 3.2 FN slots ← PU 64, Bresenham 17, SAVE 2, read_line 7, PLN 4, MERGE 2, TKLNUM 1 (+ READ/DEFINT 5 on PU_DIG)
Proof: every slot read is bounded by FN_FEND (§2.4), so between FN calls the bytes are free. The
guests' users are statements (PRINT USING, LINE/CIRCLE/PAINT/DRAW, SAVE, INPUT/LINE INPUT/direct
prompt, line entry, LOAD/MERGE, READ, DEFINT) that no expression reaches (F1; no pinned entry
reaches them except $73AC RUN — §8 finding 3), so none runs while a frame is live; and no guest's
live range contains an evaluation (PU_NUM: written after the item's `eval`, consumed by the emit
tenant before `print_string`, printusing.asm:290-356; Bresenham: one gfx_draw_seg; DRAW's
substitutions are evaluated BETWEEN tenant entries, when no segment is in flight; RDV_*: between
read_one_value and the store only `inp_num` runs, program.asm:2332-2345; read_line/PLN/MERGE/
SAVE/crunch: no eval). Co-tenancy RDV_*/DEFT_PTR on PU_DIG: READ/DEFINT and PRINT USING are
different statements and none is reachable inside another. Layout keeps read_line's cells
($F7A9-$F7AF, the only guests live across CHGET/CHPUT hooks) clear of disk.rom's BDOS console
scratch $F771-$F7A8 (guard). Page: all inside page $F7 (the FN area's own assert, sysvars.inc:4465).
**Closest programs**: `PRINT USING"###.##";FNA(1,2,3,4,5,6,7,8,9.5)` (a 9-formal call fills all 99
bytes, then PU_NUM is written over them — after fn_leave); `CIRCLE(FNA(…)+83,96),FNA(…),15`
(FN calls between circleparse entries, Bresenham only in the draw); `DEF FNE(X)=Y(99)` trapped by
ON ERROR, then LINE INPUT and `PRINT X` (raise_error resets FN_FEND, so read_line's writes are
never read as formals and X is the global). Note: MSX's DRAW `=var;` takes a variable, so a FN call
cannot run between DRAW entries **(syntax per the reference manual; not measured)**.

### 3.3 The leaf host MULPROD+DIVPAD ← TK* / VBUF / cmul / WIDIG / PLF / ISRCH / MUL_I,PP / PLAY / FP_SHIFTAMT / FP_OPMODE
Families and their reach (reach.py, inline runs): fp_mul — externals arga_dig_iszero, flt_to_int16
(→ domain_convert_core, CVT only), penderr_set, raf_zero_ok; fp_div/fp_add — + dcm_lt,
dshl_allzero (in-file tails); fp_rnd — dig15_iszero, fsc_pack_arga; tk_float — none (tk_loop/tk_end
are the crunch's continuation, TK* dead there); dt_float — pchar into DB_WIN only; sprites — tenant
ops none, + str_temp_alloc (she_temp_alloc/she_gc: no external), C-BIOS CHGMOD (no hook,
cbios/src/video.asm:318-345 + init*); mul16x16_32 — none; widen_uint_to — div10, zero_fill;
pop_lhs_and_probe — factyp_is2; sh_instr_search — none; play_parse_tenant — none. **No family's
reach contains another family's cells** (each run listed only its own), and none calls USR, a hook
or a hooked BIOS entry while its cells are live. So any two families may share bytes, except cells
ONE routine holds together, which the layout keeps apart and the guards pin: MUL_I/MUL_PP outside
MULPROD; WIDIG apart from MUL_I; FP_SHIFTAMT outside DIVPAD; FP_OPMODE apart from PLF/WIDIG/MUL_I
(caddsub holds it across pop_lhs_and_probe and widen_*); TKOVF/TKLNUM outside TK (other hosts).
`sim.out` §6 lists all 53 sharing family pairs; the co-live check found none violated.
**Closest programs**: `A$=SPRITE$(VAL("0"))` (VAL's TK cells dead before the tenant fills VBUF;
str_temp_alloc may GC — no family cell); `SCREEN 2,VAL("2")` (xsave → CHGMOD → xrest complete
before the trailing size argument is evaluated, screen.asm:103-118); `E=300*200` (MUL32 dead before
`jp fp_mul`, float-arith.asm:1920-1925); `F=A%+1.5` (FP_OPMODE at $F84C survives widen_uint_to's
WIDIG/MUL_I); `J=INSTR(STR$(1/3),"3")` (fp_div, then flt_out, then the search — sequential).

### 3.4 FBUFFR+0 / tail ← TKOVF, DIVREM, LHS_FAC, LHS_FACTYP (25 B, exclusive)
No zerobas user (§2.2), so no overlay proof is needed; T-only: fp_div, pop_lhs_and_probe/widen and
the crunch/VAL make no out-call. **Closest program**: `PRINT -7/3;STR$(-2/3);-1.23456789012345D-12`
— DIVREM (tail) then flt_out (head, ≤ $F7DC) in one statement.

## 4. The edit (exact lines: `s12_replacements.md`)

* `basic/sysvars.inc`: 89 literals, 6 follower annotations (`; $XXXX:` — wall-literal rule B),
  STRENG_SPARE re-anchored to `$ECFC` (else MIDS_DEST follows ISRCH), GFX_PSTK's range comment
  `($ED08..$ED33)` → `($F5A9..$F5B6)` (ram_map reads it as the width), TKDIG's `$F0AB..$F0C2` →
  `$F82A..$F841`, GFX_YSTEP's stale `-> ends $E126`, **CVT_MODE's `int16`** (ram_map reads a WORD
  from it; with PLF_RA gone the width would be trusted and cover $F11F), **GFX_PTY's stale
  `-> ends $E15A`** (with WRAPF gone the ratchet goes RED: "GFX_PTY undeclared" — found by the dry
  run). 23 guards appended after S11's (all FALSE on this layout; most hold with zero slack).
* Page idioms: TKDIG (`cp/sub low TKDIG`, detok.inc:313,318) stays in page $F8 (guard); MULPROD's
  own idioms unchanged; PU_NUM's `ld a,e / sub l` (punum.asm:292,575) is a low-byte difference
  (page-safe below 256 B); no other guest is in an idiom (`idioms.py`, which also catches `low(`).
  ws_shift.py cannot express this move (chained equates, overlays): `sim.py` is its stand-in.
* Hard-coded addresses: none of the moved cells' old or new addresses appears in tests/, probes/,
  tools/ (grep of 0x/$ forms); tests read names from the syms (test_graphics, test_input …);
  test_tokenise's 900-B scan ends $F7A2 — TKLNUM ($F7B6) and TK* ($F82A+) are outside it.
  disk/basic-resident-abi.inc mirrors none of the moved names.
* FREE-RAM: none consumed, none added (no claim lies in a host). Width pins: delete
  `basic CVT_MODE overruns`, `basic DISKOP_A/PLY_NUMOVF disputed` → ratchet rc 0 (verified).
* Prose: the G3/G4/G5 "LINEBUF overlay is retired" paragraphs (sysvars.inc:702,732,790) become
  FALSE — invert them; full list in `s12_replacements.md` §5.

## 5. Witness

S11's pattern: a transient cell is rewritten before it is read, so a load over its old home cannot
show the move; the rows show that its users **no longer write the window**. Plus overlay rows.

* **Vacated-sum rows** (load $A5 over the whole window under `CLEAR 100,&HE000`, run the users, sum
  the 290 vacated bytes — 27 spans frozen in the probe; VG-8020 = 165 × 290 = **47850**):
  `s12gfx` (SCREEN 2,2 + sprites, LINE B/BF, CIRCLE with angles, CIRCLE + PAINT, DRAW),
  `s12num` (READ, DEFINT, `1#/3#`, `1.5*2.25`, `300*200`, `A%+1.5`, VAL, INSTR, PLAY, PRINT USING
  `^^^^`), `s12inp` (INPUT `4.2`, LINE INPUT), `s12dir` (MERGE"CAS:" of an ASCII file after the load,
  RENUM, direct lines). 🔮 on the S11 build all four DIVERGE; after S12 all SAME.
* **Overlay rows** (both users in ONE program, no sum, compared line by line): `ovbuf` (DRAW
  INPUT$(24) + CIRCLE/PAINT/LINE BF + POINT readback), `ovfn` (9-formal FN in a PRINT USING item,
  in CIRCLE arguments, in a READ subscript; an error inside an FN body, then LINE INPUT and
  `PRINT X`), `ovleaf` (SCREEN 2,VAL / SPRITE$(VAL) / INSTR in PUT SPRITE / STR$(1/3) / cmul /
  caddsub / PLAY), `ovfbuf` (division + STR$ + the longest number forms). 🔮 SAME before and after.
* **Knives** (one group back at its literal old address; each build pin-checked): K-WS37 B:paint →
  s12gfx; K-WS38 B:box → s12gfx; K-WS39 B:circ → s12gfx; K-WS40 B:renum → s12dir; K-WS41 F:pu →
  s12num; K-WS42 F:read → s12num; K-WS43 F:bres → s12gfx; K-WS44 F:rl → s12inp (+s12dir); K-WS45
  F:pln+mrg+crunch → s12dir; K-WS46 L:tk + TKOVF → s12num, s12inp; K-WS47 L:spr → s12gfx;
  K-WS48 L:cmul/wu/plap/mul/shift/opmode → s12num; K-WS49 L:instr → s12num; K-WS50 L:play →
  s12num; K-WS51 Q:fbuf → s12num. **Negative controls on the exclusivity arguments** (a wrong
  placement must be SEEN): K-WS52 Bresenham into BUF at LINEBUF+8 → `ovbuf` DIVERGES (DRAW's
  in-place INPUT$ string); K-WS53 FP_OPMODE onto WIDIG's byte → `s12num`/`ovleaf` DIVERGE (`A%+1.5`
  becomes a subtraction); K-WS54 MUL_I inside MULPROD (e.g. $F82A+13) → `s12num` DIVERGES
  (`1.5*2.25`); K-WS55 a Tx cell (CLR_SAVE) into the FN slots at $F756 → a row `COLOR FNA(…),
  FNA(…)` (add to `ovfn`) DIVERGES. **Predicted BLIND, stated**: SV_OP/SV_STAT (F:sv) get no knife row — no row writes
  a tape in this harness **(unverified whether openMSX accepts a CAS write)**).

## 6. Sizes

| | bytes |
|---|---|
| window bytes freed by S12 (`sim.out` §4) | **290** (of S11's "~340": GFX_DEXP 24, PU_FDESC 3, MIDS_DEST 2, RDV-like Tx singles and the S11-listed TSV/OO/CLR/LOC cells could not be proven; PLAY 3, TKOVF/TKLNUM 2, FP_SHIFTAMT/FP_OPMODE 2 joined) |
| host bytes used | BUF 72 of 258 (186 spare for later statement-only guests), FN slots 97 of 99, leaf host 35 of 35 (96 guest bytes overlaid), FBUFFR 25 of 25 |
| remaining untagged diskless in the window | 294 B by the map + 34 B undeclared (HORNER_G 18, MATH_A 18 declared 1) ≈ **328 B**, 103 names |
| → S13 (SLTWRK/PROCNM, 🙋 Joost) | ≈ 41: SH_* 18, PU_FMTLEN..PU_FLAGS 5, GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG 5, GFX_PTX/PTY 2, DB_MORE/DB_RESUME/DB_CUR 4, WSRC_TYP 2, PRDEST/PRDEV 2, ERRMARK 1, INDLR_N 1, DISKOP_OP group 1 |
| → S14 (code) | ≈ 287: DB_WIN 96 + detok 12, GFX_DFTOP/DFSTK 33, FOR_CUR 29, GFX_DEXP 24, CVT 18, HORNER_G 18, MATH_A 18, math singles 9 (MATH_N 2, MATH_BREAK, CVT_MODE, VARTYPE, VS_* 3, LHS_VARTYPE, MC_TYPE), PU_FDESC 3 + PU_COMMAS/DEC 2, RVDESC 3, MIDS_DEST 2, CLR_SAVE 2, LOC_* 2, OO_* 3, TSV_* 9, DISKOP_STATUS group 1, GFX_DJ/GFX_BAD/STRENG_SPARE 2 (probe-only or dead: delete or tag) |
| stays below $F380 (DISK-/BOOT-ONLY) | 294 B |

S15 can rise to $F380 once S13+S14 clear the ≈ 328 B; BUF's 186 spare bytes are the cheapest home
for S14's statement-only cells once they stop being Tx (e.g. FOR's frame copy if the limit/step are
evaluated before it is written).

## 7. What this does NOT prove (blind spots, stated)

* Reach sets are per file group; a `jp (hl)` / vector (ARL_GETBYTE, hooks) is not an edge —
  arl_getbyte's vector targets (tape TAPIN wrapper, fat_io_getbyte) were not walked **(unverified
  that they touch no FN slot — they are file readers)**.
* User hook code that writes BUF / PARM2 / HOLD8 / FBUFFR from H.TIMI (asynchronous) is treated as
  impossible on the reference's own terms (it would corrupt the reference's INPUT / FN calls / math
  / PRINT); synchronous hooks inside a guest's live range: only read_line (H.CHGE/H.CHPU) and RENUM's
  message print (H.CHPU) — no standard routine writes PARM2 or BUF there.
* flt_out's ≤ FOUTBUF+22 bound is from the format rules, not every branch.
* Harness details of §5 (two typed answers, INPUT$ keys, a two-file tape for MERGE, run times).

## 8. Findings in passing (not S12's to fix)

1. **ram_map's DISK-ONLY tag detector reads the first 120 chars of the JOINED comment**
   (tools/ram_map.py:962-965), so PLY_NUMOVF's own S9b note ("an alias of a DISK-ONLY name would
   hide…", sysvars.inc:3781-3783) TAGS it: `--floor-top` lists 200 where 201 are untagged, and A17
   would accept PLY_NUMOVF on the diskless floor. S12 moves it (moot for this cell); the detector
   should read only the comment's head on the equ line.
2. **Pre-existing STRSCR hazard (unmeasured):** console INPUT keeps the unread answer in BUF while the
   next target's subscripts are evaluated; INPUT$ (and MKx$/DSKI$ on disk) in a subscript stage into
   STRSCR = BUF[0..] over it — e.g. `INPUT A,B(LEN(INPUT$(5)))` answered `1,2`. Run both machines.
3. **RUN (incl. the pinned $73AC) does not reset FN_FEND**; only raise_error and boot do. A USR
   routine called from a DEF FN body that jumps to $73AC runs the program with a stale frame —
   formals shadow globals today; after S12, statement guests also land in the "live" slots. A 5 B
   reset in RUN's path would close it (main ROM bytes; not equate-only).
4. ws_shift.py's page-idiom regex needs whitespace after `low`/`high`, so `cp low(DB_WIN + …)`
   (sub/detok.asm:75) is invisible to it — S14 (DB_WIN) must check by hand.
5. disk.rom's BDOS console scratch (CONOUT_CHAR, PG_SV_A8, CONIN_*: $F771-$F7A8) lies inside the DEF
   FN parameter area since S6: a USR routine calling BDOS from inside an FN body clobbers formals
   on the disk machine (pre-existing).
6. DRAW reads an INPUT$ argument in place in STRSCR; a substitution expression that itself calls
   INPUT$ would overwrite it mid-parse (pre-existing, contrived, unmeasured).
