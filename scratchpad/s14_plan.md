# D-WSZERO S14 — the code slice, designed (read-only prep, 2026-10-16)

Tree: HEAD `5e7fd9e1` + the staged S12 work; build syms of 2026-10-16 00:21 (= the S12 tree:
TKDIG/MULPROD at $F82A, PU_NUM at $F756, the S12 BUF guests at $F5A0). Nothing in the repo was
written, built or run. Instruments in this directory (read-only, `python3 -B`):

| file | what |
|---|---|
| `floortop.out` | `tools/ram_map.py --floor-top F380` on this tree: **103 untagged names**, 77 DISK-/BOOT-ONLY |
| `symat.py LO HI` | every name of the four syms at each address in a range (host occupancy) |
| `argbscan.py` / `argbscan2.py` | heuristic: any ARGB reference that follows a CVT-running call (`fp_*`, `round_*`, `flt_to_int16`, `fac_to_int_*`) with no ARGB write between (§2.1's proof) |

**(unverified)** marks every claim not read off code or syms. "T" = live only inside one routine /
tenant call; "Tx" = live across an expression evaluation (USR, DEF FN, INPUT$, the GC, hooks).
Pin geometry (s9_plan.md §0): seg A $2765-$3297, **B** $3299-$3FC7 (57 B free), C $4000-$6CF3,
D $6CF6-$73AC, E $73AC-$73E5, **F** $73E8-.. (152 B free). A/C/D/E must net 0 — and
`tools/pin_plan.py --check` gates the total pad at **<= 4 B**, so a SHRINK there is as illegal as
a growth unless refilled (pin_plan's REFILL list). Sub p0 12 B, sub p1 1240 B.

---------------------------------------------------------------------------------------------------

## 0. Verdict in one screen

**S14 needs ~100 B of sub p1, 2 B of sub p0, and nets main to roughly −35 B. Every group has a home.
Only ONE of the five slices touches a pinned segment, and that change is a SAVING.** The brief's
"expensive" groups get cheap answers from facts nobody had used yet:

| lever | what it unlocks | ROM |
|---|---|---|
| **ARGB is dead whenever `domain_convert_core` runs** (every fp op sets ARGB fresh and consumes it before its `round_and_finalize` tail; `argbscan2.out`: 0 counter-examples) | CVT (18 B, FPNUM-shaped = ARGB's exact size) → ARGB | 0 |
| **DSCTMP $F698-$F69A is idle** (TEMPBASE is the pool's exclusive top, never written: sub/strheap.asm:244-248, 1590-1595) | RVDESC → DSCTMP, the reference's own temp descriptor (rule e) | 0 |
| **the DAC tail's TK bytes are leaf-only** (tk_float calls nothing external, S11) | CVT_MODE, VARTYPE, VS_TARGET_TYPE, VS_INT_VAL, MC_TYPE overlay them | 0 |
| **the KEY-bar repaint never needs the render window** (paint/blank write VRAM; only LIST/KEY n/defaults drain it) | dispatch paint/blank BEFORE `db_begin` → DB_WIN + 16 B of detok state become statement-only → BUF $F5E8-$F65D | sub p0 +2 |
| **BUF+256..257 ($F65E-$F65F) lie past every STRSCR / INPUT$ / read_line write** (STRMAX 255, LINEMAX 255) | a 2-B **statement-exclusive Tx slot** "WSTX": CLR_SAVE, LOC_*, OO_*, LHS_VARTYPE, IN_RDLEN | 0 |
| **INPUT$ into a heap temp, like INKEY$ already does** (str-engine.asm:1924-1943) — the reference's own way | BUF+9..$F59F stops being written by any evaluation: a 57-B **statement-exclusive Tx host** "BUFTX" for FOR, PRINT USING, DRAW | seg C **−~29** (refilled from seg F) |
| **a callee-saved scratch block**: the 9 math tenants run to completion (no raise, no eval, no USR), so a wrapper saves a host to the Z80 stack, runs, restores | SQRT_X/Y/K/ITER/POW10 (39 B, all MATH_*/HORNER_*/RND_LE/RND_STATE aliases) → the DEF FN slots | sub p1 ~+99, seg B −9 |
| the Z80 stack | MIDS_DEST (MID$: `ex (sp),hl`) | seg A −1 |

**Slices, cheapest first** (each self-contained and gateable; §5): **S14a** equates with fresh
proofs (~35 B) → **S14b** the render window (114 B, sub p0 +2) → **S14c** WSTX + MID$ on the stack
(~13 B) → **S14d** the INPUT$ lever + BUFTX (~90 B) → **S14e** the math block (39 B). Then **S15**,
the ceiling, once (§6).

**Residual risks, stated:** (1) BUFTX/WSTX cells are exposed to a USR routine that uses BUF as
scratch *during* that statement's own evaluation (FOR's limit, a PRINT USING item, a COLOR
argument) — legal on the VG-8020, whose FOR frame is on the stack; far smaller than today's exposure
(the program-owned window), but real: filed as a TIER-6 row, §4.6. (2) The math wrapper costs
~1.8k T-states per SQR/RND/^ call (TIER 5). (3) If S13 is refused, SH_* (18 B), WSRC_TYP (2) and
FCH_RDMODE (1) still have no home (§7).

---------------------------------------------------------------------------------------------------

## 1. The remainder, re-listed (`floortop.out` minus the S13 set)

S13 set (excluded, Joost's ruling pending): SH_* 18, PU_FMTLEN..PU_FLAGS 5,
GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG 5, GFX_PTX/PTY 2, DB_MORE/DB_RESUME/DB_CUR 4, WSRC_TYP 2,
PRDEST/PRDEV 2, ERRMARK 1, INDLR_N 1, DISKOP_OP (+LE_OP/FOPEN_SEL/AUDIO_VMASK) 1, and FCH_RDMODE 1
(it sits inside TSV_NAME's span at $EF66; the brief's S13 list omits it, ram_map lists it).

| group (old home) | B | users | lifetime / why no equate-move so far | S14 home | slice |
|---|---|---|---|---|---|
| GFX_BAD+STRENG_SPARE $ECFC, GFX_DJ $EFDC | 2 | sub/graphics.asm:118-167 `graphics_selftest` (GFX_OP=0), only from probes/basic/basic_probe_graphics_floor.py (writes GFX_OP=0 itself) | probe-only; STRENG_SPARE is a "1 B free" anchor for MIDS_DEST | BUF $F5F8/$F5F9; STRENG_SPARE deleted | b / a |
| MIDS_DEST $ECFD | 2 | MID$ stmt (str-engine.asm:1576-1666 → vars.asm:523 `tgt_desc_fix`); LSET/RSET call-back (field.asm:642, 686) | Tx: across n, m and the RHS (str-engine.asm:1543) | MID$: the Z80 stack; LSET keeps the cell as DISK-ONLY `LRSET_DESC` | c |
| GFX_DFTOP/DFSTK $ED38 | 33 | DRAW tenant sub/graphics.asm:2978, 3147-3243 | Tx: persists across every round trip to the resident's substitution eval (gdo_want) | BUFTX | d |
| GFX_DEXP $ED67 | 24 | gdrw_sub_scan writes (sub/graphics.asm:3261), the resident EVALUATES it (basic/graphics.asm:993/999) | Tx: it IS the eval's source | BUFTX | d |
| DB_WIN $ED9D + DB_SKIP, DB_RESSKIP, DB_SP, DT_TOK, DT_TOKN, DB_RESPTR | 108 | sub/detok.asm, sub/keystr.asm, sub/printusing.asm, basic/list.asm:266-296, basic/printusing.asm:270/353 | **coupling**: `keystr_tenant` runs `db_begin` (writes DB_WIN[0], DB_CUR, DB_MORE, DB_RESUME) for EVERY op incl. the KEY-bar paint reached from INKEY$/read_line (sub/keystr.asm:159-161; basic/subromcall.asm:152-156) → eval-reachable | BUF $F5E8-$F5F7 + DB_WIN $F600-$F65D (94 B) | b |
| DISKOP_STATUS (+LE_STATUS, CM_STATUS, BN_STAT, AUDIO_STATUS, DEFT_STATUS) $EE39 | 1 | tenant → main dispositions; disk.rom via the generated ABI (tools/gen_resident_abi.py:116) | T, but shared by ~6 tenants incl. eval-reachable ones; no free byte known | FLBMEM $FCAE (S11's verified-idle spare) | a |
| CLR_SAVE $EE7B | 2 | COLOR: clr_prep/clr_commit (main.asm:207-222, seg B) + screen.asm:195/208 | Tx across the colour evals (D-PARTIAL) | WSTX $F65E | c |
| FOR_CUR..FOR_SIGN $EF0A | 26 | ex_for (basic/fat.asm:261-329, **seg C**: it is the $6CF3 pin's refill), for_name/for_key/slot_store (program.asm:1804-1830), ex_next (program.asm:2099-2260), for_get/for_set (vars.asm:981-991); unit tests poke it by sym | FOR: Tx (key across init/limit/step, limit across STEP); NEXT: T, no eval (the parked sentinel is dead before tgt_parse_req's eval) | BUFTX | d |
| OO_DEVTYPE $EF3A, OO_RECLEN_CHAN $F09C | 2 | OPEN (files.asm:573-609, 713-1036, seg C/D), sub/fatprim.asm:327/348 | Tx across the `AS #n` / `LEN=` evals | WSTX | c |
| TSV_PTR(=SSE_OUT) $EF5D, TSV_CNT $EF61, TSV_NAME $EF62-$EF67, IN_RDLEN $EF63 | 9 (+IN_RDLEN inside) | tape CSAVE/BSAVE (save.asm), RESUME NEXT's scan (sub/errtrap.asm), INPUT#/LINE INPUT# (files.asm:1425-1487), INPUT$ (strvar.asm:561-590) | TSV_NAME Tx (BSAVE's address evals follow the name); PTR/CNT T in the write loop; IN_RDLEN: INPUT$ is eval-reachable with CHGET hooks inside | TSV_NAME → FILNAM $F866 (rule e); PTR/CNT → BUF $F5FA-$F5FC; IN_RDLEN → WSTX (after S14d INPUT$ no longer uses it) | a, c |
| LOC_COL/LOC_ROW $EFDF | 2 | LOCATE (missing.asm:150-235, seg F) | Tx across the argument evals | WSTX | c |
| RVDESC $EFF2 | 3 | mk_rvdesc/strscr_desc (str-engine.asm:416-430), vars.asm:382-426, field.asm:741, sub/fldlook.asm:95-97; tests read it by sym | T producer→consumer, but the consumer may print through CHPUT (hooks): not T-only, so no USR-exposed host | DSCTMP $F698 (rule e) | a |
| PU_FDESC $F08D, PU_WP=PU_COMMAS/PU_DEC $F095 | 5 | printusing.asm:207-225, 372-375; sub/punum.asm (COMMAS/DEC) | Tx across every item's eval (field state set by the scan, read by the render) | BUFTX | d |
| DB_SP, DT_TOK, DT_TOKN, DB_RESPTR $F0A0 | (in the 108) | | | | b |
| CVT $F0E6 | 18 | domain_convert_core (float-arith.asm:1219-1335) — the tail of EVERY round_and_finalize | T, but runs inside fp_mul/fp_div's tails and inside the math tenants: S12 rejected the leaf host | ARGB $F818 | a |
| CVT_MODE $F11E | 1 | fac_to_int_go (float-arith.asm:1349), flt_to_int16 (float.asm:376), read at :1285 | T, leaf | DAC tail $F7FE (TKNZPOS overlay) | a |
| VARTYPE $F168 | 1 | var_name_key writes (vars.asm:152/182), ~20 readers right after | T (eval-reachable), leaf | DAC tail $F7FF | a |
| VS_TARGET_TYPE $F169, VS_INT_VAL $F16A | 3 | var_store_fac (vars.asm:711-760), ary_store_write (arrays.asm:844-879) | T across round/fac_to_int/var_alloc_or_find (our own tenant; no hook, no USR) | DAC tail $F800, $F801-$F802 | a |
| LHS_VARTYPE $F16C | 1 | ex_let (interp.asm:922-934) | Tx across the RHS eval | WSTX | c |
| MC_TYPE $F16D | 1 | evmc_sub1 (expr.asm:2127-2134) | T across fp_sub (leaf: no hook, no USR) | DAC tail $F803 | a |
| SQRT_X..SQRT_POW10 $F16E-$F194 (+MATH_T/A/SIGN/N/RECIP/BREAK/J, HORNER_G, RND_LE, RND_STATE) | 39 | sub/fp_sqrt/atan/exp/log/pow/sin/rnd.asm (all p1); main cpow writes MATH_N/MATH_J (float-arith.asm:2057-2089) | T inside one math tenant, but live across fp_add/mul/div calls and reachable from ANY expression (INPUT targets, DEF FN bodies, DRAW…): no host is idle at every such moment | the DEF FN slots $F756-$F77C, **saved/restored** by a wrapper | e |

Sum ≈ 287 B (+4 B of S13's DB_MORE/DB_RESUME/DB_CUR, which S14b takes along).

---------------------------------------------------------------------------------------------------

## 2. The new facts (proofs)

### 2.1 CVT → ARGB
* CVT is written and read only inside `domain_convert_core` and its leaf helpers
  (`dcc_bound5`, `dig15_cmp`, `dig_to_word`, `neg_de`, `widen_fac_to`): float-arith.asm:1219-1335;
  CVT_MODE at float.asm:376. No reader outside (grep: float-arith.asm only).
* Callers: `round_and_finalize`'s tail `jp flt_to_int16` (every fp op), `fac_to_int_strict/addr`
  (\ MOD AND OR XOR NOT, POKE/VPOKE/HEX$ args, subscripts arrays.asm, input.asm, interp.asm,
  str-engine.asm, vars.asm, sub/circleparse.asm).
* ARGB's discipline (sysvars.inc:4954-4960, float-arith.asm:787-790 "ARGB is transient scratch,
  dead after this call"): every op is preceded by a fresh ARGB write (`widen_*`/`cpy_*argb`/
  `widen_both_operands`/`caddsub_widen_both`) and consumes ARGB before its round tail. The one
  routine that needs ARGB across a CVT-running call — fp_pow's frac path across `fp_log` — saves it
  on the machine stack (sub/fp_pow.asm:255-276).
* `argbscan2.py` over sub/fp_*.asm, circleparse, expr, float-arith, float: every ARGB reference
  that follows a CVT-running call is a WRITE (`cpy_*argb`, or `ld hl,ARGB` + widen; 8 sampled
  by hand: fp_atan:233, fp_pow:268, fp_sin:236, fp_sqrt:282/398/529/632, circleparse:488).
  **(heuristic: linear scan, labels reset; a hand-read of fp_cmp's callers and of cpow (reads ARGB
  digits with dig_to_word, never through CVT) closes it)**.
* USR exposure: ARGB = HOLD8+18; domain_convert_core makes no out-call (S11's T-only rule).
* disk.rom: references ARGA, not ARGB (disk.sym).

### 2.2 RVDESC → DSCTMP $F698-$F69A
* TEMPBASE ($F698) is the temp pool's EXCLUSIVE top: slots are [TEMPPOOL, TEMPBASE)
  (sub/strheap.asm:236-248), overflow fires when the new TEMPPT > TEMPBASE (1590-1595), so no slot
  ever covers $F698. No sym has a cell at $F698-$F69A (`symat.py F698 F69A`: TEMPBASE only, a
  boundary). FRETOP is $F69B.
* `sh_hl_is_temp` on RVDESC=$F698: `sbc hl,TEMPBASE` = 0 → CF clear → "not a temp" — RVDESC's
  "excluded from GC roots by construction" survives the move.
* Same job: DSCTMP is the reference's temporary string descriptor. **(unverified: C-BIOS writes
  nothing there — an S10.0-style fill row, or pubfree_map.py, before shipping.)**

### 2.3 DAC-tail TK overlays ($F7FE-$F803)
Current guests (S11): TKNZPOS $F7FE, TKDCOUNT $F7FF, TKSTORED $F800, TKFLAGS $F801, TKPC $F802,
TKLEAD $F803 — tk_float only, zeroed at its entry (sub/tkfloat.asm:45-53), **no external call**.
TKVALEND/FOSIGCOUNT $F804-$F805 stay untouched (tokenise/VAL → INPUT's read-back, flt_out).
New guests, each T and making no out-call (USR, hook) while live:

| byte | guest | why it never meets tk_float or another guest |
|---|---|---|
| $F7FE | CVT_MODE | domain_convert_core calls no tk_float; tk_float calls nothing |
| $F7FF | VARTYPE | var_name_key → reader, no call between; tokenise never runs var_name_key |
| $F800 | VS_TARGET_TYPE | var_store_fac/ary_store_write: round, fac_to_int (CVT_MODE: other byte), arga_widen (WIDIG/MUL_I: leaf host), var_alloc_or_find → ARY tenant (grep: no TK*/DAC+ in sub/arrays.asm, sub/strheap.asm, basic/vars.asm, disk/) |
| $F801-$F802 | VS_INT_VAL | as above |
| $F803 | MC_TYPE | evmc_sub1 → widen_uint_to, fp_sub → round → CVT_MODE (other byte) |

INPUT's numeric path: tk_float (TK cells) finishes, THEN var_store_fac runs — sequential.
USR exposure: none of the five is live across a USR call (`A=USR(0)`: LHS type is latched in WSTX
before the eval; `USR(0)+A`: var_name_key runs after USR returns). **Needs S12's dry-run tooling
(`sim.py`'s pair matrix) + one overlay-fit guard per byte; the claim "the ARY tenant touches no DAC
byte" is a grep, not a reach set (unverified).**

### 2.4 The render window is statement-only once the KEY-bar paint skips `db_begin`
* `keystr_tenant` (sub/keystr.asm:154-170) runs `call db_begin / ld (de),a` before dispatching.
  Its ops: 0 defaults (boot), 1..10 KEY n (ex_key, drained), 255 KEY LIST (drained), FNKPAINT
  (zks_p2 ← zb_chsns ← INKEY$ and read_line; key_repaint; key_disp; boot), FNKBLANK (key_disp).
  Paint/blank write VRAM only (ks_paint/ks_blank: no pchar/DB_*), and none of their callers drains
  the window ("NO print_string DRAIN HERE", screen.asm:463-465). So moving the paint/blank dispatch
  in front of `db_begin` removes the only eval-reachable writer of DB_WIN/DB_CUR/DB_MORE/DB_RESUME.
* What remains: LIST, ASCII SAVE (detok), KEY LIST / KEY n, PRINT USING (pu_to_field, pu_tail,
  pu_emit tenants) — statements. In each, the window is rendered and DRAINED before the next
  evaluation (PRINT USING: item eval → render → print_string, printusing.asm:289-356; string items
  print straight from their bodies, :402-447; the format is snapshotted or copied at pu_hold_fmt).
  DB_SKIP/DB_RESSKIP/DB_RESPTR span re-runs inside ONE detok_emit loop (list.asm:266-296), with only
  print_string → CHPUT between (hooks: a user H.CHPU that writes BUF is impossible on the reference's
  own terms while it echoes INPUT — S12 §7's argument).
* BUF while those statements run: dead (a direct LIST executes from KBUF, sysvars.inc:1919-1926; no
  interrupt-time BUF user, S12 F2). KEY n,"…" stages its string in STRSCR and db_begin then writes
  DB_WIN[0] = STRSCR+$A2 — harmless: ks_store copies at most KEYMAX=15 bytes (keystr.asm:189-198).
* Co-live with DB_WIN inside those statements: ASCII SAVE to tape writes through TSV_PTR/TSV_CNT
  (kept on distinct bytes, §3.3); PRINT USING's own Tx state (BUFTX, distinct bytes).
* **(unverified: a disk ASCII SAVE's sequential write path touches no BUF byte — disk/ grep shows
  STRSCR/STRSCR+1 users only at name staging and MKI$/DSKI$.)**

### 2.5 WSTX — BUF+256/257 ($F65E-$F65F)
Every writer of BUF and how far it reaches:
* STRSCR staging (INPUT$, MKx$, DSKI$, READ, INPUT#, KEY, file names): [len] + at most STRMAX=255
  bytes → **≤ $F65D**; `fname_expr` adds a `"` terminator → **≤ $F65E** for a 255-byte name.
* read_line / console INPUT: LINEMAX 255 incl. the terminator from LINEBUF (sysvars.inc:975), the
  answer at LINEBUF+1 → ≤ $F65D **(unverified at the screen-editor capture)**.
* the crunch overshoot: TOKBUF+575 = $F65E (line entry only, sysvars.inc:1029-1036).
* S14b's DB_WIN: $F600-$F65D (one page; DB_WINSZ 96 → 94).
So nothing an EVALUATION runs can reach $F65F, and only statements that are never co-live with a
WSTX user reach $F65E. A WSTX guest must be (a) used by ONE statement (exclusive with every other
guest), (b) not that statement's own `fname_expr` victim. Guests: CLR_SAVE (COLOR), LOC_COL/ROW
(LOCATE), OO_RECLEN_CHAN $F65E + OO_DEVTYPE $F65F (OPEN: LEN= comes after the name), LHS_VARTYPE
(LET), IN_RDLEN $F65F (INPUT#/LINE INPUT#: its terminator, if any, lands ≤ $F65E). Traps run at
statement boundaries; an error aborts the statement; RESUME re-executes it from scratch.
USR-reachable pinned entries: $73AC (RUN resets everything), $6CF3 (BLOAD: SWPTMP/TEMP*), $73E5
(PLAY: no WSTX cell), $3297 — none writes WSTX.

### 2.6 The INPUT$ lever and BUFTX ($F567-$F59F)
* Today INPUT$ stages up to 255 bytes in STRSCR (strvar.asm:553-590) — the ONLY evaluation that
  writes BUF beyond STRSCR+8. MKI$/MKS$/MKD$ write STRSCR+0..8 (strvar.asm:332-380), DSKI$
  STRSCR+0 (:618); INKEY$ already allocates a heap temp (str-engine.asm:1924-1943); SPRITE$ fills
  VBUF then a temp; STR$/HEX$/OCT$ use NUMBUF/heap.
* After INPUT$ allocates its result with `str_temp_alloc` (as the reference allocates in string
  space), no evaluation writes $F567-$F65F. A statement's Tx cells there are then safe from
  everything but USR code that scribbles BUF (residual, §4.6), PROVIDED the statement itself does not
  stage into STRSCR while they are live:
  * FOR: no staging. PRINT USING: the format is snapshotted (heap) or descriptor-copied; string items
    print from their bodies. DRAW: frame 0 may be an MKx$ value in STRSCR+1..8 (below BUFTX) or an
    INPUT$ temp (heap now); X-strings are variables (heap / program text); its substitution evals are
    variable references (D-DRAWSUBVAR). CIRCLE (if S13 is refused): numeric args only.
  * BUFTX users are pairwise exclusive (different statements), so they may share bytes.
* Co-live inside those statements: PRINT USING ↔ DB_WIN + detok cells (distinct bytes);
  DRAW ↔ Bresenham (FN slots), DRAW's TRPTBL/RS2IQ cells (elsewhere); CIRCLE ↔ the S12 BUF guests
  $F5A0-$F5E7 (distinct).
* **(to verify before S14d: a reach scan that no eval-reachable label writes LINEBUF/STRSCR+9..
  — the list above is a grep of STRSCR/LINEBUF users, not a reach set.)**

### 2.7 The math block, callee-saved
* The 9 math entries are the p1 jump table (sub/sub.asm:458-503). Bodies call each other only
  internally (fp_pow → fp_log/fp_exp; fp_tan → sin/cos; four call fp_poly_horner); no other tenant
  calls a math body (grep). Main writes only MATH_N/MATH_J (cpow, float-arith.asm:2057-2089).
* A page-1 tenant cannot raise (main page 1 is switched out); errors are deferred through FPERR
  (penderr_set) — so a wrapper's restore ALWAYS runs **(unverified for every math exit: grep
  raise_error/jp *_error in sub/fp_*.asm before shipping)**.
* So the scratch can live in ANY RAM that (a) the fp core (ARGA/ARGB/leaf host/DAC+ARG tails/
  FOUTBUF) never touches and (b) no interrupt-time code reads — and whatever was live there (an FN
  frame's formals, INPUT's unread answer, a PU_NUM render) is saved on the Z80 stack and put back.
  Host: the DEF FN slots $F756-$F77C (PARM2; the reference's FN area; disk.rom's BDOS console bytes
  in it are BDOS-call-only).

---------------------------------------------------------------------------------------------------

## 3. The edits, slice by slice

### 3.1 S14a — equates with fresh proofs (≈ 35 B of window, 0 ROM bytes)

basic/sysvars.inc (each with its `; $XXXX:` wall-literal annotation and a guard):
```
CVT             equ     ARGB            ; $F818: unpack scratch (18) -- ARGB is dead at every
                                        ; domain_convert_core (s14_plan §2.1)
CVT_MODE        equ     $F7FE           ; DAC tail, overlays TKNZPOS (tk_float-only) (1)
VARTYPE         equ     $F7FF           ; overlays TKDCOUNT (1)
VS_TARGET_TYPE  equ     $F800           ; overlays TKSTORED (1)
VS_INT_VAL      equ     $F801           ; overlays TKFLAGS/TKPC (2)
MC_TYPE         equ     $F803           ; overlays TKLEAD (1)
RVDESC          equ     $F698           ; the reference's DSCTMP (3) -- TEMPBASE is the pool's
                                        ; exclusive top, never a slot
DISKOP_STATUS   equ     $FCAE           ; FLBMEM, idle (S11 §1.1 spare) (1)
TSV_NAME        equ     $F866           ; FILNAM, the reference's own name cell (6); overlays
                                        ; CAS_WANT (tape search -- never in a tape SAVE)
STRENG_SPARE                            ; deleted (MIDS_DEST re-anchors in S14c)
```
* Guards (IF … db ERROR_SYMBOL, after S12's): `CVT == ARGB`, `FPNUM_SIZE == 18`;
  `MC_TYPE < TKVALEND`; the five DAC-tail guests pairwise distinct; `RVDESC == TEMPBASE`
  (+ `TEMPBASE+3 == FRETOP`).
* disk ABI: regenerate disk/basic-resident-abi.inc (DISKOP_STATUS moves; tools/gen_resident_abi.py
  lists it) and rebuild disk.rom (byte change only in the mirrored address).
* OO_RECLEN_CHAN: **only if** the `LEN=` clause is unreachable diskless (FCH_RECLENS is DISK-ONLY,
  files.asm:566-609 — **unverified**: trace whether a diskless `OPEN"CAS:X" AS #1 LEN=5` reaches
  oo_endok) tag it DISK-ONLY and leave it; otherwise it goes to WSTX in S14c.
* Bookkeeping: ram-width-allow (the MATH_* disputes stay until S14e), docs/ram-map.md regen,
  ram_map A17, wall-literal rule B annotations; tests read CVT/RVDESC/VARTYPE by sym (no edit).
* TSV_NAME's overlay of CAS_WANT: **(unverified: no tape-WRITE path reads CAS_WANT/CAS_WANT_ON;
  an OPEN"CAS:" FOR INPUT channel does not consult CAS_WANT after its OPEN — D-CASCHANLOAD's
  question)**. Fallback: TSV_NAME → BUFTX after S14d (it is Tx for BSAVE's address evals).
* Risk: low — no instruction changes; the exposure is the proofs. Gates most exposed:
  test_float / float-arith / math-pack probes (CVT on every op), circle probes (circleparse's
  ARGB use), string-engine/strvar tests (RVDESC), float_vars / lvfix / arrays / deffn (VS_*),
  math_conv (INT → MC_TYPE), tokenise/VAL/INPUT rows (TK overlays), diskbasic- and
  nodisk-acceptance + lineedit/casmatch/PLAY/DEFINT gates (DISKOP_STATUS), cas_verbs (TSV_NAME).

### 3.2 S14b — the render window into BUF (114 B; sub p0 +2)

sub/keystr.asm `keystr_tenant` — before (23 B):
```
keystr_tenant:  call db_begin / ld (de),a / ld a,(KEYARG) / or a / jr z,ks_defaults
                cp 255 / jr z,ks_list / cp KEYOP_FNKPAINT / jp z,ks_paint
                cp KEYOP_FNKBLANK / jr z,ks_blank
```
after (25 B, +2):
```
keystr_tenant:  ld a,(KEYARG)
                cp KEYOP_FNKPAINT / jp z,ks_paint   ; the KEY-bar paint never touches
                cp KEYOP_FNKBLANK / jr z,ks_blank   ; the render window (s14 §2.4)
                push af
                call db_begin                        ; A=0, DE=DB_WIN
                ld (de),a
                pop af
                or a / jr z,ks_defaults / cp 255 / jr z,ks_list
                ; KEY n falls through as before
```
basic/sysvars.inc:
```
DB_WIN          equ     $F600   ; BUF's last page, one page (94 B) -- statement-only
DB_WINSZ        equ     94      ; was 96: $F65E-$F65F are WSTX (§2.5)
DB_SKIP         equ     $F5E8   (2)    DB_RESSKIP equ $F5EA (2)   DB_SP    equ $F5EC (2)
DT_TOK          equ     $F5EE   (2)    DT_TOKN    equ $F5F0 (2)   DB_RESPTR equ $F5F2 (2)
DB_CUR          equ     $F5F4   (2)    DB_MORE    equ $F5F6 (1)   DB_RESUME equ $F5F7 (1)   ; S13's 4 B
GFX_DJ          equ     $F5F8   (1)    GFX_BAD    equ $F5F9 (1)   ; probe-only self-test results
```
* The one-page assert (sysvars.inc:2527) holds ($F600..$F65D); both `cp low(DB_WIN+DB_WINSZ-1)`
  idioms (sub/detok.asm:75, sub/printusing.asm:53) become `cp $5D` — page-safe. ws_shift.py cannot
  see `low(` (S12 finding 4): do this one by hand.
* 94 B: KEY LIST's re-run step (list.asm:293) and LIST's resume are size-generic; PRINT USING's
  widest field is 24 + sign/exponent forms (≤ 13 B per spec-basic-pufloat §14) and literals stream
  through DB_MORE (printusing.asm:272) **(unverified: no PRINT USING path assumes 96)**.
* probes/basic/basic_probe_graphics_floor.py reads GFX_DJ/GFX_BAD from the sym — no edit.
* Bytes: sub p0 12 → 10. Main 0.
* Risk: moderate (TIER 1 LIST / KEY / PRINT USING paths). Gates: test_list, linemax list-max,
  keyscout / keystr rows, pulong / puwide / pufloat / pusign, ASCII SAVE rows, fnkline / keyshift /
  dspfnk (the paint path), subrom-acceptance, graphics_floor.

### 3.3 S14c — WSTX, MID$ on the stack, the tape-save cells (≈ 13 B; seg A −1)

basic/sysvars.inc:
```
WSTX            equ     LINEBUF + 256   ; $F65E: statement-exclusive Tx slot, 2 B (s14 §2.5)
CLR_SAVE        equ     WSTX            ; COLOR (2)
LOC_COL         equ     WSTX            ; LOCATE (1)     LOC_ROW equ WSTX+1
OO_RECLEN_CHAN  equ     WSTX            ; OPEN, LEN= (1) (unless S14a tagged it DISK-ONLY)
OO_DEVTYPE      equ     WSTX + 1        ; OPEN (1) -- $F65F: past fname_expr's terminator
LHS_VARTYPE     equ     WSTX            ; LET (1)
IN_RDLEN        equ     WSTX + 1        ; INPUT#/LINE INPUT# (1); INPUT$ stops using it in S14d
                                        ; -- until then INPUT$ is eval-reachable: keep IN_RDLEN
                                        ; where it is if S14c ships before S14d
TSV_PTR         equ     $F5FA           ; tape write loop (2) (= SSE_OUT, RESUME NEXT)
TSV_CNT         equ     $F5FC           ; (1) -- distinct from DB_* (ASCII SAVE to tape runs both)
LRSET_DESC      equ     $ECFD           ; DISK-ONLY: LSET/RSET's target descriptor (2)
                                        ; (MIDS_DEST's old cell; reachable only through disk.rom's
                                        ; H.LSET call-back -- a diskless LSET is ERR 5 at the gate)
```
Guards: `LINEBUF + STRMAX + 1 == WSTX` (i.e. STRSCR's reach ends at $F65D), `DB_WIN + DB_WINSZ
== WSTX`, `LINEMAX <= 255`.

MID$ (basic/str-engine.asm, **seg A**) — the lookup, before → after (−3 B):
```
push hl / call tgt_desc / ld (MIDS_DEST),hl / pop hl
push hl / call tgt_desc / ex (sp),hl          ; [dest]; HL = cursor
```
the store, before → after (+2 B):
```
pop de / pop bc / push hl / ld (SH_NUM),de / ld (SH_START),bc / ld hl,(STRPTR) / ld (SH_SRC),hl
       / call tgt_desc_fix / ld (SH_DEST),hl
pop de / pop bc / ex (sp),hl / push hl / ld (SH_NUM),de / ld (SH_START),bc
       / ld hl,(STRPTR) / ld (SH_SRC),hl / pop hl / call tgt_desc_fix / ld (SH_DEST),hl
```
Error tails (ems_err_pop2/1, ems_typecheck) now leave one more word: harmless — raise_error resets
SP (interp.asm:1422; D-MIDOP's K-MD2 deleted both pops and moved 0 of 9 rows,
interp.asm:1831). ems_range still sees [cursor] (`pop hl / jp gb_illegal`) ✓.
basic/vars.asm `tgt_desc_fix` (**seg C**, 0 B — a label, the instruction stays):
```
tgt_desc_fix_lr:                            ; LSET/RSET (field.asm:686)
                ld      hl,(LRSET_DESC)
tgt_desc_fix:                               ; in: HL = what tgt_desc returned
                ld      de,(TGT_ADDR) ...   ; unchanged
```
basic/field.asm: lrset_tgt (**seg E**) `ld (MIDS_DEST),hl` → `ld (LRSET_DESC),hl` (0 B);
lrset_rhs (seg F) `call tgt_desc_fix` → `call tgt_desc_fix_lr` (0 B).
* Bytes: seg A −1 (the `ds $3297-$` pad grows 1 B: inside pin-check's 4-B budget; or spend it —
  "no growing holes" is Joost's rule, so state it in the commit). Others 0.
* Risk: low/moderate. Gates: lvfix / lvsites (MID$ into an array element across an ARYTAB move:
  m.ary, m.ctldrift), midop, midspace, LSET/RSET rows on the disk machine (field), D-PARTIAL COLOR
  rows, LOCATE rows, OPEN rows (badfnum, fcbhdr, opengrp, casfch), seqeof / inputdn, F3 cross-type
  LET (A%=A#), cas save rows, RESUME NEXT (errtrap s2b).

### 3.4 S14d — the INPUT$ lever and BUFTX (≈ 90 B; seg C ≈ −29, refilled)

basic/strvar.asm (**seg C**), INPUT$'s read — before: `sid_read` (16 B) + `str_inputd_read`
(49 B) = 65 B (strvar.asm:540-590). After (≈ 36 B):
```
sid_read:                                   ; stack: [cursor]; INDLR_N = n
                ld      a,(INDLR_N)
                or      a
                jp      z,gb_illegal        ; INPUT$(0): 5 (D-INPUTDN)
                call    str_temp_alloc      ; A = n -> HL = temp desc, DE = body (0 on OOM:
                                            ; FPERR pending, as INKEY$; ROM writes are inert)
                ld      (STRPTR),hl         ; the result: an owned temp, as on the reference
                ex      de,hl               ; HL = the body
sidr_lp:
                push    hl
                call    arl_getbyte         ; through the vector (console / CAS / disk)
                pop     hl
                jp      c,gp_past_eof       ; 55, the target keeps its old value (R3)
                ld      (hl),a
                inc     hl
                ld      a,(INDLR_N)
                dec     a
                ld      (INDLR_N),a
                jr      nz,sidr_lp
                jp      sfi_done            ; pop hl (cursor) + str_eval_ok (INKEY$'s tail)
```
`str_inputd_read` and the strscr_desc call disappear; IN_RDLEN loses its INPUT$ user; STRMAX's
clamp was dead (n ≤ 255). **(unverified: no GC can run inside the loop — arl_getbyte's three
sources allocate nothing; the body is garbage until filled, which a GC would only copy.)**
Behaviour changes to MEASURE (both machines): an INPUT$ result now takes a temp slot (the 10-deep
`String formula too complex` budget — the reference's INPUT$ result is a temp too, 🔮 SAME);
`A$=INPUT$(200)` with no string space raises 14 (🔮 the reference too, but before or after
reading the keys? 🔮 BEFORE on the VG-8020 → if so add `ld a,d / or e / jp z,<raise>` +4 B).
* seg C refill: the ~29 B hole in front of $6CF3 must be filled (pin-check budget 4 B):
  `tools/pin_plan.py` (PLAN mode) lists REFILL candidates — self-contained seg-F chunks, entered
  only by call/jp — to move into the hole, as D-WSZERO S9 / D-BASICINT did (ex_for, cont_record,
  ctl_put, ex_on_key). **Net effect: seg F gains ≈ +29 B free.** (unverified that a set of
  chunks sums exactly; a `jr`-bridge or a 1-3 B residual within the 4-B budget is the fallback.)

basic/sysvars.inc:
```
BUFTX           equ     LINEBUF + 9     ; $F567..$F59F: statement-exclusive Tx host (57 B),
                                        ; past MKx$'s STRSCR+0..8, below the S12 BUF guests
FOR_CUR         equ     BUFTX           ; FOR/NEXT (26) -- FOR_LIM/STEP/LINE/BODY/SIGN follow
PU_FDESC        equ     BUFTX           ; PRINT USING (3)
PU_COMMAS       equ     BUFTX + 3       ; (1)  PU_WP equ PU_COMMAS (2)
PU_DEC          equ     BUFTX + 4       ; (1)
GFX_DEXP        equ     BUFTX           ; DRAW (24)
GFX_DFTOP       equ     BUFTX + 24      ; $F57F (1)
GFX_DFSTK       equ     GFX_DFTOP + 1   ; $F580: … 32 B total (keep this exact equ shape:
                                        ; tools/check_wall_literals.py:242 matches it)
```
Guards: `GFX_DFSTK + 4*GFX_DFCAP - 1 < GFX_POVF` (= $F5A0, S12's first BUF guest);
`BUFTX >= STRSCR + 9`; the BUFTX users' extents ≤ 57.
* FOR: 0 B (equate). NEXT is T with no evaluation in FOR_CUR's live range (program.asm:2099-2260:
  the parked sentinel at nx_head is overwritten by for_key on every path that evaluates).
  Unit tests (test_control_flow, test_statements, test_vars) poke FOR_CUR by sym — no edit.
* DRAW: 0 B. Optional hardening (+4 B sub p0, measure first): reject bytes ≥ $80 and `"` inside a
  substitution in gdrw_sub_scan's loop — today a crafted string can smuggle a function token into
  the resident's eval (s12 finding 6); the reference answers ERR 5 for anything but a variable
  reference **(unverified for these two shapes)**.
* If S13 is refused: PU_FMTLEN..PU_FLAGS → BUFTX+5..+9 and GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG →
  BUFTX+0..4 (CIRCLE: Tx across its argument co-routine; co-live with the S12 CIRCLE guests at
  $F5A0+, distinct) — both 0 B.
* Risk: high-traffic (FOR is in every program) but mechanical; the lever is the only code. Gates:
  forvar / forfloat / nxlist / nxary / ctlcross / forfast, test_control_flow / test_statements,
  pu* rows, g6 DRAW + drawinplace / drawsubvar / drawerr, inputdn / inpdcon / casinp / seqeof,
  tempst (10-deep), string-space rows, pin-check, `make basic-reloc` walls.

### 3.5 S14e — the math block, callee-saved (39 B; sub p1 ≈ +99, seg B −9)

basic/sysvars.inc:
```
MW_HOST         equ     FN_PAREA        ; $F756: saved/restored around every math tenant
MW_N            equ     39
SQRT_X          equ     MW_HOST         ; (18)   MATH_T/HORNER_G/RND_LE alias it, unchanged
SQRT_Y          equ     MW_HOST + 18    ; (18)   MATH_A/RND_STATE
SQRT_K          equ     MW_HOST + 36    ; (1)    MATH_SIGN/MATH_N(2)
SQRT_ITER       equ     MW_HOST + 37    ; (1)    MATH_RECIP
SQRT_POW10      equ     MW_HOST + 38    ; (1)    MATH_BREAK/MATH_J
```
sub/sub.asm p1 table: indexes 1-9 `jp fp_sqrt` … `jp fp_rnd` → `jp mw_sqrt` … `jp mw_rnd`.
New, sub p1 (≈ 94 B):
```
mw_sqrt:        ld      ix,fp_sqrt          ; 9 stubs, 6 B each (IX is free: every resident
                jr      math_wrap           ;  caller saves its own IX across subrom_call)
  ... mw_atan / mw_exp / mw_log / mw_pow / mw_sin / mw_cos / mw_tan / mw_rnd ...
math_wrap:                                  ; DE/HL = the caller's params (POW only)
                exx                         ; keep them in the shadow set
                ld      hl,-MW_N
                add     hl,sp
                ld      sp,hl
                ex      de,hl               ; DE = the save area on the Z80 stack
                ld      hl,MW_HOST
                ld      bc,MW_N
                ldir                        ; host -> stack
                exx
                call    mw_jpix             ; the body (results in FAC/FACTYP/FPERR)
                push    af
                ld      hl,2
                add     hl,sp
                ld      de,MW_HOST
                ld      bc,MW_N
                ldir                        ; stack -> host
                pop     af
                ld      hl,MW_N
                add     hl,sp
                ld      sp,hl
                ret
mw_jpix:        jp      (ix)
```
sub/fp_pow.asm entry (+5 B): `ld a,(MATH_J)` → `ld (MATH_N),de / ld a,l / ld (MATH_J),a`.
basic/float-arith.asm cpow (**seg B**, −9 B): delete `ld (MATH_N),de` (cpow_int_have_n) and both
`ld (MATH_J),a`; add `ld l,a` at cpow_dispatch (A = j on both paths; DE = n survives to
subrom_call, whose push/pop de hands it to the tenant, subromcall.asm:68-75).
* ram-width-allow: the two MATH_* "disputed" pins re-anchor or go; docs/ram-map.md; S12's
  FN-slot overlay guards gain one "SAVED overlay" exception (the block overlaps PU_NUM/PU_DIG by
  design). C-BIOS's ISR saves the shadow set **(unverified: cbios-repack has patches only; check the
  KEYINT source)**.
* Cost: +2×39-byte LDIR ≈ 1.6-1.8k T per SQR/ATN/EXP/LOG/SIN/COS/TAN/RND/^ call (TIER 5; RND in a
  game loop pays it — measure against the VG-8020 with the existing speed rows).
* Risk: moderate. Gates: every math-pack probe (sqr/atn/exp/log/sin/cos/tan/rnd/pow, rndx_probe),
  ovfn / deffn (formals across a math call), CIRCLE (circleparse shares fp_sqrt.asm's helpers),
  subrom-acceptance, sub walls.

### 3.6 Alternatives considered and REJECTED (with the reason)
* **IX/SP frames inside the math tenants**: ~160 absolute accesses (counts in §1's users column) at
  +1..+5 B each → 300-600 B. The save/restore wrapper is ~100 B.
* **A Z80-stack frame for DRAW's X stack passed to the tenant in DE**: needs a 2-B frame-pointer
  cell anyway (the tenant's registers are busy deep in the parser), sub p0 has 10 B, and ex_draw is
  seg C. BUFTX costs 0.
* **Evaluating DRAW's substitution in place instead of copying to GFX_DEXP** (`ld hl,GFX_DEXP` →
  `ld hl,(GFX_DVAL)` is byte-neutral in seg C): works, ~+5 B sub p0, but needs the `"`/token
  rejection to stay bounded; BUFTX is simpler. Keep as the fallback if BUFTX is refused.
* **FOR building its frame in the pool first**: an error between the evals leaves a half frame
  that a bare NEXT matches (no per-statement CSP restore exists: raise_error unwinds FN frames only,
  interp.asm:1297-1305) — the reference pushes nothing on such an error.
* **FOR on the Z80 stack** (reference-faithful; no USR residual): un-hoist ex_for from fat.asm
  (seg C, the $6CF3 refill) back to program.asm's ELSE copy (seg F), refill seg C via pin_plan,
  then build the 26-B frame SP-relative and copy the key into FOR_CUR before for_set/slot_store
  (which read FOR_CUR, vars.asm:981-991, program.asm:1824). ≈ +30 B seg F. **This is the fidelity
  follow-up for §4.6, not S14.**
* **CLR_SAVE on the stack** (clr_prep leaves the shadow under its return address; clr_commit pops
  it): exact and +3 B in seg B — WSTX is 0 B with the same exposure as every BUFTX cell; take the
  stack form only if §4.6 is ruled a defect.
* **LHS_VARTYPE / MC_TYPE via push/pop** (−4 B each in seg C): would add to seg C's refill; the
  equates are 0 B.

---------------------------------------------------------------------------------------------------

## 4. Witness (the S11/S12 pattern) and knives

All rows: `basic_probe_wszero.py`, a $A5 load over the WHOLE window under `CLEAR 100,&HE000`,
then the users; **vacated-sum** rows sum the bytes the slice vacated (frozen spans, VG-8020 =
165 × n, the S12 lesson: count the `ret` byte at the load's first address correctly); **overlay**
rows run a host's users and its guests' users in ONE program and must read as the VG-8020 does.

### 4.1 S14a
* `s14eq` (vacated-sum over $EE39, $EF62-$EF67 minus $EF63/$EF66, $EFF2-$EFF4, $F0E6-$F0F7,
  $F11E, $F168-$F16D): POKE/VPOKE/HEX$ with float args, `A=1.5:B%=A\1:C=A MOD 1` (CVT, CVT_MODE),
  `X=INT(-1.5)` (MC_TYPE), `A%=2.5:A#=A%` (VS_*), `A$="AB"+"C":PRINT"LIT"` (RVDESC), a line typed
  in direct mode + `DEFINT I` + `PLAY"C"` (DISKOP_STATUS: lineedit/DEFT/AUDIO), `K=VAL("12.5")`.
  🔮 before: DIVERGES (sum ≠ 165·n), after: SAME.
* `ovdac` (overlay): `INPUT A%` answered `2.5E1` (tk_float then var_store_fac), `A(VAL("1"))=
  INT(-2.5)`, `B=1.5*2.25+INT(VAL("-0.5"))`, `DEF FNC(X%)=X%\2:Z=FNC(7.9)` (FN binding →
  var_store_fac → fac_to_int → CVT_MODE). 🔮 SAME before and after.
* `ovargb` (overlay): `PRINT SQR(2);ATN(1);2^0.5;EXP(1);LOG(2);SIN(1);(1/3)\1` — CVT inside
  every math op's round tail while the math tenants use ARGB. 🔮 SAME.
* Knives: K-WS56 CVT back at $F0E6 (literal) → `s14eq`; K-WS57 RVDESC back at $EFF2 → `s14eq`;
  K-WS58 the five DAC-tail cells back → `s14eq`; K-WS59 DISKOP_STATUS back → `s14eq`.
  **Negative controls**: K-WS60 CVT onto ARGA (live: flt_out unpacks into ARGA,
  float.asm:55-71) → `ovargb` DIVERGES (🔮: digits of a printed float); K-WS61 VS_INT_VAL onto
  TKVALEND ($F804, INPUT's read-back) → `ovdac` DIVERGES.
* BLIND, stated: TSV_NAME (no tape write in this harness — S12's SV_OP/SV_STAT note).

### 4.2 S14b
* `s14lst` (vacated-sum over $ED9D-$EDFC, $EFEC-$EFF1, $F0A0-$F0A7, $F123-$F124): LIST of a
  200-char line (resumable render), KEY LIST, `PRINT USING"&";STRING$(120,"A")` (literal stream),
  `KEY 1,"ABC"`. 🔮 before DIVERGES, after SAME.
* `ovkey` (overlay — the decoupling's witness): a LINE INPUT answered with 170 characters while
  the KEY bar is ON (read_line → zb_chsns → paint), then `PRINT LEN(B$);ASC(MID$(B$,163))`, then
  `LIST` and `KEY LIST` in the same program. 🔮 SAME.
* Knives: K-WS62 DB group back at the literal old homes → `s14lst`. **Negative control K-WS63**:
  S14b's equates, but `keystr_tenant` reverted (db_begin first) → `ovkey` DIVERGES (the paint writes
  DB_WIN[0] = $F600 = LINEBUF+$A2 into the typed answer; 🔮 `ASC` reads 0 or the line is cut).
* graphics_floor's own gate is the GFX_DJ/BAD witness (it reads the sym).

### 4.3 S14c
* `s14stx` (vacated-sum over $ECFD-$ECFE, $EE7B-$EE7C, $EF3A, $EF5D-$EF5E, $EF61, $EFDF-$EFE0,
  $F09C, $F16C): `COLOR 15,4`, `LOCATE 5,5`, `OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"X":CLOSE`,
  `A$="ABCDE":MID$(A$,2)="XY"`, `A%=1.5`, RESUME NEXT after an error. 🔮 before DIVERGES, after SAME.
* `ovstx` (overlay): each WSTX statement with the longest STRSCR / INPUT$ next to it —
  `COLOR LEN(INPUT$(255))-240,4` (typed keys), `LOCATE LEN(INPUT$(250))-245,3`,
  `OPEN"CRT:"FOR OUTPUT AS#LEN(INPUT$(1))`, `DIM A$(3):A$(1)="ABCDE":MID$(A$(1),LEN(INPUT$(255))-252)
  =STRING$(2,"Q")` with a new variable created inside the RHS (VARPTR → ARYTAB move: the lvfix
  shape), `A%=LEN(INPUT$(255))`. 🔮 SAME before and after.
* Knives: K-WS64 WSTX group back → `s14stx`; K-WS65 MID$'s stash back in a cell at $ECFD →
  `s14stx`. **Negative control K-WS66**: WSTX at $F65D (inside STRSCR's reach) → `ovstx` DIVERGES.

### 4.4 S14d
* `s14buf` (vacated-sum over $ED38-$ED58, $ED67-$ED7E, $EF0A-$EF23, $F08D-$F08F, $F095-$F096):
  FOR/NEXT with STEP and a float limit, PRINT USING `##.##` and `#,###`, DRAW with an `X` nested 3
  deep and `=V;` substitutions. 🔮 before DIVERGES, after SAME.
* `ovbuftx` (overlay — the lever's witness): `FOR I=1 TO LEN(INPUT$(40)) STEP LEN(INPUT$(2))`,
  `PRINT USING"##.##";LEN(INPUT$(60))`, `DRAW INPUT$(30)` whose text contains `XA$;` with
  `A$="R5D5"`, `A$=INPUT$(3)+INPUT$(3)` (temp budget), INPUT$ from an open CAS: channel.
  🔮 SAME before and after.
* `inpoom` (measurement, both machines first): `CLEAR 10:A$=INPUT$(50)` with keys typed — when is
  14 raised, and are the keys consumed?
* Knives: K-WS67 BUFTX guests back → `s14buf`. **Negative control K-WS68**: BUFTX in place, INPUT$
  reverted to STRSCR staging → `ovbuftx` DIVERGES (INPUT$(40) overwrites FOR_CUR's limit).

### 4.5 S14e
* `s14math` (vacated-sum over $F16E-$F194): SQR, ATN, EXP, LOG, SIN, COS, TAN, RND(1), RND(-3),
  `2^0.5`, `2^10`. 🔮 before DIVERGES, after SAME.
* `ovmath` (overlay — the save/restore witness): `DEF FNA(A,B,C,D,E,F,G,H,I)=SQR(A)+A+B+C+D+E+F+
  G+H+I+ATN(I)`, `INPUT X,Y(SQR(4))` answered `1,2`, `PRINT USING"##.###";SQR(2)` (PU_NUM shares
  the host), `CIRCLE(128,96),40,15,,,1.5`, `Z=2^FNA(1,2,3,4,5,6,7,8,0.5)`. 🔮 SAME.
* Knives: K-WS69 math block back at $F16E → `s14math`. **Negative control K-WS70**: the wrapper's
  restore LDIR removed → `ovmath` DIVERGES (the FN formals after SQR; Y's unread `2`).

### 4.6 The residual, FILED not gated
`usrbuf`: a USR routine that fills $F55E-$F65F with $A5 and returns 3, called inside
`FOR I=1 TO USR(0)`, inside a `PRINT USING` item and inside `COLOR USR(0)+12`. 🔮 VG-8020 correct;
zerobas after S14c/d DIVERGES. File as a 🎚️ TIER-6 fidelity item ("statement Tx state on the Z80
stack", §3.6's FOR/COLOR stack forms) — the same class the window had, at 1/20 of the surface.

### 4.7 The full battery after each slice
`make gates` + the uncollected suites (`*-acceptance` that `make gates` does not collect —
[[parallel-gate-battery]]), `make basic-reloc` (five walls), `pin-check`, `switch-build-check`,
`ram-map-check`, `ram-claim-check`, `wall-literal-check`, disk ABI regen check, `nodisk-acceptance`,
`diskbasic-acceptance`, `wszero-acceptance` (now ~45 rows).

---------------------------------------------------------------------------------------------------

## 5. Slice order (cheapest first) and the window bytes each frees

| slice | frees (window B) | ROM | depends on | gate added |
|---|---|---|---|---|
| **S14a** equates: CVT→ARGB, RVDESC→DSCTMP, 5 DAC-tail overlays, DISKOP_STATUS→FLBMEM, TSV_NAME→FILNAM, STRENG_SPARE out | ≈ 35 | 0 (disk.rom rebuilt for the ABI) | S12 tooling (sim.py) for the overlay pair matrix | s14eq, ovdac, ovargb |
| **S14b** keystr reorder; DB_WIN (94) + 16 B of detok state → BUF; GFX_DJ/BAD → BUF | ≈ 114 (incl. S13's 4) | sub p0 +2 | — | s14lst, ovkey |
| **S14c** WSTX (CLR, LOC, OO, LHS_VARTYPE, IN_RDLEN*), MID$ on the stack, TSV_PTR/CNT → BUF | ≈ 13 | seg A −1 | S14b (DB_WINSZ 94) | s14stx, ovstx |
| **S14d** INPUT$ into a heap temp; BUFTX: FOR_CUR, PU_FDESC/COMMAS/DEC, DRAW's 57 B | ≈ 90 | seg C ≈ −29 → refilled from seg F (seg F ≈ +29 free) | — (S14c's IN_RDLEN* waits for it) | s14buf, ovbuftx, inpoom |
| **S14e** math block callee-saved in the FN slots | 39 | sub p1 ≈ +99, seg B −9 | — | s14math, ovmath |

\* IN_RDLEN goes to WSTX only after S14d (INPUT$ is eval-reachable until then).
After S14a-e: **`ram_map --floor-top F380` lists only the S13 set** (minus the 4 DB cells S14b
took): 37 B. Walls after S14 (estimates): main page 1 ≈ 181 B (152 + 29), low ≈ 66 B (57 + 9),
sub p0 10 B, sub p1 ≈ 1141 B.

---------------------------------------------------------------------------------------------------

## 6. S15 — the ceiling, once (checklist)

1. **Census first**: `python3 tools/ram_map.py --floor-top F380` lists NOTHING untagged. Then a
   WRITE census, which ram_map does not do: every store to a DISK-ONLY/BOOT-ONLY name on a diskless
   path (S9 found fld_init, seq_end, LSET; re-run that sweep over all 77 tags) — a tag says "the
   diskless machine never uses it", the code must agree.
2. `TXTMAX_NODISK equ $F380` (sysvars.inc:2495). Boot (interp.asm:202-212): `cp high TXTMAX`
   ($E3) vs C-BIOS's HIMEM $F380 → NC → TXTCEIL = HIMEM = $F380, the reference's value; a disk ROM
   that lowered HIMEM still takes TXTMAX. heap_reset/ctl_reset follow (:220-221). Check every
   `BASIC_WS_CEIL`-style constant and assert that compared against _NODISK (S6's FN_PAREA_CEIL /
   BASIC_WS_CEIL hand edits), and CLR_HIMEM_TOP ($F380) — `CLEAR ,&HF380` must then behave as on
   the VG-8020 (row).
3. **Fills whose base is a former window name** (sysvars.inc names now DISK-/BOOT-ONLY below
   $F380): grep every `ldir` / fill loop / `ld bc,N` block op whose base resolves into
   [$ECF8,$F380) — trap_init, init_filechan's `ifc_zero`, fld_init(_g), clear_vars, the FAT engine
   init, cpt_* — each must be disk-gated or have moved; a diskless boot / NEW / RUN / CLEAR must
   write NO byte of [$ECF8,$F380) (an S10.0-style fill row over the whole range, both machines).
4. **FRE(0)**: today −1658 vs the VG-8020 (S6); the ceiling gains $F380−$ECF8 = 1672 B →
   🔮 +14 (zerobas ABOVE the reference). Whether SP lands at the reference's ~$F09E depends on
   POOLSIZE + the channel blocks below the ceiling vs the reference's FCB area (~738 B)
   (unverified) — measure SP at the noclear rows' failing line on both machines; if zerobas ends
   above the reference, that is a TIER-4 RAM item, not S15's.
5. **Probes whose ranges assume the window**: basic_probe_wszero.py derives `freed`, `q1..q4`,
   `all` from `TXTMAX_NODISK` (lines 57-67) — at $F380 `_q` = 0 and `all` is empty. Freeze the
   pre-S15 window (`WINDOW_LO = 0xECF8`) as a constant; `all`/`q*` keep loading over it (now
   program RAM: every row must stay SAME). The S11/S12/S14 vacated-sum rows keep their frozen spans.
   Also: test_ctl_reloc / test_tokenise / any unit test seeding TXTMAX_NODISK from the sym (S5/S3
   notes), basic_probe_ramfree / s10_parm1_fill instruments, himem / clear / fremem probes,
   docs (memory-map, CLEAR pages; their examples re-run), docs/ram-map.md regen.
6. **The `noclear` rows**: `noclear` ($E000-$E7FF) and `noclear2` ($E800-$E97F) stop being
   witnesses (boot's stack leaves them). Add `noclear3`: no CLEAR, a load just under the
   VG-8020's SP (e.g. $E000-$F07F) — 🔮 DIVERGES on the S14 build, SAME after S15; knife K-WS71
   (`TXTMAX_NODISK` back at $ECF8) → `noclear3` diverges. Then the real tapes (one-off, outside the
   repo): the RESET class (Boulder Dash I/II, Blow Up, Exterminator, Finders Keepers, Knight Tyme,
   Formula 1 Simulator) is the prediction to score.
7. `CLEAR 27000` / `CLEAR 28000` rows (S6: the VG-8020 accepts 28000) re-scored.
8. The disk machine is untouched by the ceiling, but S14 changed shared equates: diskbasic-,
   bdos-, fat-error- and nodisk-acceptance all green before S15 starts.

**If S13 is REFUSED** (no SLTWRK slot-0 sub-slot bytes, no PROCNM), S15 waits on these, with homes:

| S13 cell | B | home without S13 | cost |
|---|---|---|---|
| DB_MORE / DB_RESUME / DB_CUR | 4 | BUF (S14b already) | 0 |
| PU_FMTLEN..PU_FLAGS | 5 | BUFTX+5..+9 (S14d) | 0 |
| GFX_MODE/ASPMAJ/ARCF/SNEG/ENEG | 5 | BUFTX (CIRCLE) | 0 |
| INDLR_N | 1 | the Z80 stack inside S14d's INPUT$ rewrite (push n across the `,f` eval; the loop counts on the stack) | ≈ 0 in seg C (inside the refill) |
| DISKOP_OP (+LE_OP/FOPEN_SEL/AUDIO_VMASK) | 1 | NLONLY $F87C (spare) | 0 |
| ERRMARK | 1 | FLKINP $F6A6 (spare; FLGINP's slot) | 0 |
| GFX_PTX/PTY | 2 | the leaf host (POINT is a closed tenant op; no leaf family is live across it — add to S12's pair matrix) | 0 |
| PRDEST / PRDEV | 2 | PTRFIL $F864-$F865, the reference's "output goes to a file" cell (idle: no sym) — interim, D-FCBSHAPE will want PTRFIL for real | 0 |
| **SH_*** (string-engine param block) | 18 | **no home**: eval-core, written by main before the tenant call (save/restore impossible), live while VAL→tk_float and SPRITE$→VBUF run inside it (so not the leaf host). Options: (i) the MSX1 RS-232 work bytes $FB03-$FB20 (idle without an RS-232 cartridge; provenance unverified — same class of ruling as S13), (ii) a Z80-stack param block whose address rides DE into the strheap tenant (~60 SH_* sites main+sub: est. 120-200 B) | 0 / large |
| **WSRC_TYP** | 2 | no DAC-tail room left (§2.3 uses $F7FE-$F803; flt_out's widen runs while FOSIGCOUNT is live) → with SH_* | — |
| **FCH_RDMODE** | 1 | INPUT$ sets it (eval-reachable, hooks inside) → with SH_* | — |

So a refusal leaves **21 B** (SH_*, WSRC_TYP, FCH_RDMODE) needing either a second ruling (the RS-232
bytes) or the expensive stack param block.

---------------------------------------------------------------------------------------------------

## 7. What this does NOT prove (blind spots)

* Every exclusivity claim here is a grep + read of the named lines, not a reach set; S12's
  `reach.py`/`sim.py` (session scratchpad, not in the repo) must be re-run for S14a's DAC-tail
  overlays, S14d's "no eval-reachable BUF writer past STRSCR+8", and S14e's "no math exit raises" (a grep of sub/fp_*.asm for raise_error / stmt_error / gb_illegal found none).
* `argbscan2.py` is linear (labels reset) — a branch that reaches an fp op from above a label
  without passing an ARGB write is invisible to it.
* The disk machine: disk.rom's own BUF / DAC-tail / DSCTMP / FILNAM use was grepped, not traced
  (disk/kernel.asm STRSCR users only at name staging, MKI$, DSKI$).
* C-BIOS writes to DSCTMP, FLBMEM, NLONLY, FLKINP, PTRFIL: not checked here (S11 verified the three
  spares idle; DSCTMP and PTRFIL need a runtime fill row).
* Byte counts in §3.4/§3.5 are hand counts; the pin pads and walls are read from the brief and
  s9_plan.md, not re-measured (`make basic-reloc` was not run).
* §4's predicted values (🔮) are predictions, not measurements.

## 8. Findings in passing (not S14's to fix)

1. **`keystr_tenant` writes the render window on every KEY-bar repaint** — today that is
   $ED9D, program RAM after S15; with no S14b it would be a load-sensitive LIST/PRINT USING
   corruption source. S14b fixes it as a side effect.
2. **INPUT$ uses no temp slot today** (RVDESC over STRSCR) — so `"A"+…` nesting with INPUT$ may hit
   the reference's 10-temp limit one level later than the VG-8020 (unmeasured; S14d's `ovbuftx`
   row scores it).
3. **ems_typecheck / ems_err_pop2's "popping is correct under both readings" comment
   (str-engine.asm ~1740)** becomes stale once MID$ keeps a third word: S14c must invert it, not
   delete it ([[a-fix-falsifies-the-justification-beside-it]]).
4. **The brief's S13 list omits FCH_RDMODE** ($EF66, inside TSV_NAME's declared span), which ram_map
   lists untagged; after S14a moves TSV_NAME the span's other bytes vacate and FCH_RDMODE stands
   alone at $EF66.
5. **OO_RECLEN_CHAN may already be disk-only** (it feeds FCH_RECLENS, DISK-ONLY) — S14a's check.
