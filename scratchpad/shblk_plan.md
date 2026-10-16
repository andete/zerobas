# D-WSZERO S16 — SH_* off the workspace: a Z80-STACK parameter block (design, read-only)

2026-10-16. Read-only design; nothing in the repo was built, run or written. Inputs:
[TODO.md](TODO.md) D-WSZERO (S13 refused, "WHAT THE REFERENCE DOES"),
[scratchpad/s14_plan.md](scratchpad/s14_plan.md) §6, [scratchpad/s9_plan.md](scratchpad/s9_plan.md) §0,
`build/basic-reloc.sym` / `build/sub.sym` (built 2026-10-16 07:38, i.e. HEAD af47ae40's tree — the
segment of every main routine below is read from that sym). Raw instruments, beside this file:
`shrefs.py` -> `shrefs.out` (every code line naming an SH_* cell, with routine, region, R/W),
`group.py` -> `grouped.md` (the same, grouped by op; reproduced in Appendix A).

🔮 = prediction, ⚠️ UNVERIFIED = a claim nobody measured. Byte counts are HAND counts.

---------------------------------------------------------------------------------------------------

## 0. Verdict in one screen

* **189 code references** (comment lines excluded): main 62 (seg A 52, seg C 7, seg D 2, seg F 1),
  tenant 127 (all in [sub/strheap.asm](sub/strheap.asm), sub page 0). No other tenant, no disk.rom
  code and no sub2 code touches an SH_* cell; no `equ SH_*` alias exists. **Nobody borrows the
  block as scratch.** Non-code mentions: [sub/equates.inc](sub/equates.inc):69 (comment),
  [tools/ram-width-allow.txt](tools/ram-width-allow.txt):26 (`basic SH_BASE/SH_OP disputed` — a
  ratchet line that FAILS ram-map-check once nothing matches it: delete it in the same commit),
  [tools/ram_map.py](tools/ram_map.py):287/1184 and
  [disk/docs/spec-diskcode-eviction.md](disk/docs/spec-diskcode-eviction.md):2852 (literal sample
  text, not live), [tests/test_str_engine.py](tests/test_str_engine.py):186 (comment).
* **The design (Variant B, recommended): `sh_go`** — one 21 B main helper. The caller loads the op
  in A and up to three argument words in HL / DE / BC (a 4th, MID$'s `m`, is pushed by the caller
  before the `call`). `sh_go` pushes BC, DE, HL, AF — that IS the block, 8 B on the Z80 stack —
  passes its address in HL through `subrom_call` (HL/DE pass through: [basic/subromcall.asm](basic/subromcall.asm):75),
  and on return pops AF, HL, DE, BC: **A = ERR (flags set), HL/DE/BC = the slots the tenant
  overwrote with results, or the caller's own values where it did not.** The tenant does
  `push hl / pop iy` once and addresses the block as `(iy+d)`. Results live in RAM (the block), so
  nothing depends on what CALSLT preserves on the way back (the tree's lore conflicts on that, §2.6).
* **The main side SHRINKS** (≈ −130 B in seg A, −20 in seg C, −6 in seg D, −2 in seg F, hand
  count): almost every `ld (SH_x),rr` / `ld rr,(SH_x)` becomes nothing, because the value already
  is, or is wanted, in a register. The shrink is NOT free: seg A..E are pinned, `pin_plan.py --check`
  allows ≤ 4 B of total pad, so every slice must REFILL the shrunken segment (seg A from seg B, seg
  C/D from seg F). Net: main low and main page 1 each GAIN roughly what the glue loses.
* **The tenant side is roughly byte-neutral** (🔮 −30 ± 40 B, the weakest number here): indexed
  16-bit loads cost +2/+3 each, but four helpers make re-reads/re-writes byte-neutral, args arrive in
  DE/BC registers, and the result tails collapse into shared helpers. Sub page 0 has **10 B** free,
  so S16a carves first (shared tails, a jump-table dispatch: ≈ −45 to −90 B, absolute addressing,
  behaviour-neutral); contingency: evict a self-contained sub-p0 tenant to sub2 page 0 (≈ 16 KB
  free) the way D-TOKOVF moved BEEP (§3.4).
* **A blocker nobody has hit yet: the unit-test harness cannot see a stack block.**
  [tests/msxtest.py](tests/msxtest.py):229-286 runs a page-0 tenant on a PRIVATE stack that starts at
  $F380 — the same addresses as the caller's own stack — copies back only `[$8000,$F300) +
  [$F380,$10000)`, and passes HL/DE in, HL/DE/A out, **not BC**. Every string unit test would break.
  S16.0 fixes the harness first, with its own before/after witness (§4).
* **No GC, abort, interrupt or relocation hazard found** (§2): the GC never scanned SH_* and does
  not scan the stack; its sort buffer is below the live SP; the block holds descriptor ADDRESSES
  (stable during an op) and results consumed before the next allocation; no tenant op raises; no
  strheap op calls back into main (closure checked: strheap.asm and tkfloat.asm call nothing outside
  sub/); `ctl_reloc` (the only code that moves SP) runs at statement level only.
* **Slices:** S16.0 harness + tenant carve (neutral) → S16.1/.2/.3 the op groups behind a second
  table index (each gateable; the vacated-sum row flips only at .3) → S15 unblocked for SH_* (WSRC_TYP
  and FCH_RDMODE are separate, per TODO).

---------------------------------------------------------------------------------------------------

## 1. The census (task 1)

Appendix A lists all 189 lines (file:line, routine, op, side, region). Summary:

### 1.1 By op and side

| op | name (tenant handler) | main writer (args) | tenant reads | tenant writes | main reader (results) |
|---|---|---|---|---|---|
| — | dispatch | `sh_call_op` str-engine.asm:62 (6 call sites), `ctl_reset` :273, `sst_op` :693, `str_temp_slice` :922, `ev_ff_val` :1084, `shx_op_tail` :1857, `sfg_close` :2018, expr.asm:1751/1770/1782, vars.asm:1112 | strheap.asm:111 | — | — |
| 0 | ALLOC (`she_alloc`) | `mid_own` :1710 (LEN) | :194 | :197 PTR, :199/:203 ERR | `mid_own` :1713 ERR, :1725 PTR, **:1716 re-reads SH_DEST** (op 9's arg, after op 0 ran) |
| 1 | GC (`she_gc`) | **no main caller found** (grep) | — | :189 PTR, :191 ERR | — |
| 2 | APPEND (`sh_append`, `sap_*`, `sate_*`) | `sct_loop` :774 SRC, :777 DEST | :1668..:1864 (SRC ×4, DEST ×6) | ERR ×5 | `sct_loop` :782, `sct_append_err` :862 |
| 3 | TEMP_ALLOC | `str_temp_alloc` :607 LEN | :212 | :215 PTR, :216 PTR2, :218/:222 ERR | :610 ERR, :620/:623 PTR, :624 PTR2 |
| 4/16/21 | SNAPSHOT / KEEP / SLICE-SRC | `sst_op` :695 SRC | :232, :274, :299, :304, :310, :321, :335 | :275/:320/:340 PTR, ERR ×5 | :697 ERR, `sh_publish` :713 PTR |
| 5 | SLICE (`she_slice*`) | `str_temp_slice` :916 SRC, :918 START, :920 COUNT | :379, :380, :432..:504 (13) | :184 ERR | none |
| 6/7/14 | HEX/OCT/BIN | `str_fn_radix` :1831 NUM | :1924, :2188, :2237 | PTR ×3, ERR ×6 | `shx_finish` :1870, `sh_publish` |
| 8 | FILL | `str_fn_chr` :1227/:1229, `str_fn_space` :1909/:1911, `sfg_close` :2014/:2016 | :2327, :2339, :2341 | :2330 PTR, :2332/:2349 ERR | `shx_finish`, `sh_publish` |
| 9 | MID_STORE | `ems_close` :1661 NUM, :1662 START, :1665 SRC, :1669 DEST | :2365..:2415 (6) | :2433/:2437 ERR | `ems_close` :1674 |
| 10 | CMP | `str_cmp_bits` :2254/:2255 | :164/:165/:175/:177 | :167 LEN (result), :170 ERR | :2258 LEN |
| 11 | INSTR | `efi_p_ok` :2141/:2144/:2145 | :2533 (→IX), :2534 (→IY), :2535 | :2564/:2606/:2631 PTR, :161 ERR | :2148 PTR |
| 12 | VAR_STORE | `str_set_key` vars.asm:1093 SRC (**stashed across `var_alloc_or_find`**), :1110 DEST | :2661..:2688 (7) | ERR ×3 | vars.asm:1118 |
| 13/19 | VAL / VAL over STRSCR | `ev_ff_val` (op only); `inp_val` input.asm:406 (op only) | :2854 (own LEN) | LEN :2720/:2728/:2907, SRC-as-result :2752/:2833/:3032, PTR :2922/:2968/:3035, ERR ×4 | `ev_ff_val` :1096/:1104, `inp_num` input.asm:380/:384, `inm_ok` :399, **`inp_store` :451 and `exr_nan` program.asm:2392 — one and two levels ABOVE the call** |
| 15/17 | FRE | expr.asm:1751/1770/1782 (op, **stored BEFORE `evsp_close`**) | — | :2037/:2078 PTR, ERR | `inm_ok` (via expr.asm:1787) |
| 18 | CHAN_ADDR | `fch_ctx_addr` files.asm:1637 LEN | :2154 | :2164 PTR, :2166 ERR | files.asm:1640 |
| 20 | CTL_RESET | `ctl_reset` :273 (op; raw `sr_inl0`) | — | :2121 PTR, :2124 ERR | none (both results unread) |

(`:n` without a file = [basic/str-engine.asm](basic/str-engine.asm) for main rows,
[sub/strheap.asm](sub/strheap.asm) for tenant rows.)

### 1.2 By region (main segments per s9_plan §0, re-read from today's sym)

| region | routines | refs |
|---|---|---|
| main seg A `$2765..$3297` (pinned) | str-engine.asm: sh_call_op, ctl_reset, str_temp_alloc, sst_op, sh_publish, sct_loop, sct_append_err, str_temp_slice, ev_ff_val, str_fn_chr, ems_close, mid_own, str_fn_radix, shx_op_tail, shx_finish, str_fn_space, sfg_close, efi_p_ok, str_cmp_bits; input.asm: inp_num, inm_ok, inp_store | 52 |
| main seg B `$3299..$3FBE` (low, 66 B free) | — | 0 |
| main seg C `$4000..$6CF3` (pinned) | vars.asm `str_set_key` ($48E4), expr.asm `ev_ff_fre` / `ev_fre_num` / `ev_fre_close` ($5027..) | 7 |
| main seg D `$6CF6..$73AC` (pinned) | files.asm `fch_ctx_addr` ($6F82) | 2 |
| main seg E | — | 0 |
| main seg F `$73E8..` (171 B free) | program.asm `exr_nan` ($7A9F) | 1 |
| sub p0 (10 B free) | strheap.asm `strheap_engine` $1129 .. $1DA3 | 127 |
| sub p1, sub2, disk | — | 0 |

Note: today's sym puts `ex_on_key` at $739C (before the $73AC pin), not in seg E as s9_plan §0
says — the pin geometry moved since; the pins themselves ($3297, $6CF3, $73AC, $73E5) are the same.

### 1.3 The LIFETIME hazards (the census rows that are not "write, call, read")

These are the sites a stack block breaks if converted mechanically — each needs the value carried
in a register or on the stack instead:

1. **FRE stores SH_OP before `evsp_close`** (expr.asm:1751/1770) — carry the op in C (`ev_sp` /
   `evsp_close` touch A and IX; ⚠️ UNVERIFIED that C survives — read expr.asm:342 and
   `ixsp_unwind` before relying on it; else `push bc`).
2. **`str_set_key` stashes SH_SRC across `var_alloc_or_find`** (vars.asm:1093, its own comment:
   "survives the target alloc ... no CPU-stack relay needed") — becomes a `push hl`, and the
   `ssk_target_oom` exit must pop it.
3. **`ems_close` stages four args, then `mid_own` runs a NESTED op 0**, and `mid_own` re-reads
   SH_DEST after it (str-engine.asm:1716). Stack discipline handles the nesting by construction
   (the inner block is pushed below the outer arguments); `mid_own` must keep A$'s descriptor on
   the stack across its own `sh_go`.
4. **VAL's results are read one and two levels above the call**: `inp_store` reads SH_LEN after
   `inp_num` returned (input.asm:451), and READ's `exr_nan` reads SH_ERR after `inp_num` returned CF
   (program.asm:2392). Both become REGISTER results: A survives every `pop`/`push`/`jr` between
   (checked at input.asm:112-117, program.asm:2349-2352, input.asm:428-430).
5. **`inm_ok` is a shared tail** (input.asm:398) reached by VAL (str-engine.asm:1107), FRE
   (expr.asm:1787) and `inp_num`: it disappears; each caller gets DE from `sh_go` directly.

---------------------------------------------------------------------------------------------------

## 2. The calling convention (task 2)

### 2.1 The main helper

```
; sh_go -- run string-heap op A on a Z80-STACK parameter block (D-WSZERO S16).
; in : A = op; HL = W0, DE = W1, BC = W2 (per-op meaning, §2.3); MID$ only: the
;      caller pushed W3 immediately before `call sh_go`.
; out: A = ERR (or the op's 1-byte result), Z iff 0, CF = 0;
;      HL/DE/BC = W0/W1/W2 as the tenant left them (results, or the caller's own
;      values where the op writes none -- so BC is PRESERVED by every op but VAL).
; Clobbers IX, IY (CALSLT). Raises (sc_call) only if the sub ROM is absent.
sh_go:
                push    bc                  ; blk+6  W2
                push    de                  ; blk+4  W1
                push    hl                  ; blk+2  W0
                push    af                  ; blk+1  OP -> ERR,  blk+0 = F (junk)
                ld      hl,0
                add     hl,sp               ; HL = blk (rides through subrom_call/CALSLT)
                ld      ix,SUBROM_ENTRY_BASE_P0 + 3*SUBROM_IDX_STRHEAP
                call    sc_call
                pop     af                  ; A = ERR (the tenant overwrote OP)
                pop     hl
                pop     de
                pop     bc
                or      a                   ; Z iff ERR=0, CF = 0
                ret
```
21 B. It replaces `sh_call_op` (3 B) and `call_strheap` (7 B), whose every user converts. Layout as
the tenant sees it (offsets from IY; equates `SHB_*`, NOT cells — name them in
[sub/equates.inc](sub/equates.inc) or mark them NOT-A-CELL so ram_map does not read them as RAM):

| off | slot | in | out |
|---|---|---|---|
| +0 | F | junk | — |
| +1 | OP / ERR | op | ERR or the 1-byte result |
| +2 | W0 | HL | result word 0 |
| +4 | W1 | DE | result word 1 |
| +6 | W2 | BC | result C (VAL type) |
| +8 | sh_go's return address | — | — |
| +10 | W3 (MID$ `m`) | pushed by `ems_close` | — |

### 2.2 The tenant side

```
strheap_engine:
                push    hl
                pop     iy                  ; IY = the block for the whole op
                ld      a,(iy+SHB_OP)       ; dispatch exactly as today (or the S16a table)
```
* **Why IY, not IX:** IX is clobbered by `strheap_gc` (its frame, never restored — "Clobbers ...
  IX", strheap.asm:832), by `tk_float` (its TKDIG cursor, tkfloat.asm:54) and by INSTR
  (strheap.asm:2533). IY is clobbered only by `heap_alloc` (its 4 B frame, strheap.asm:697) and by
  INSTR (:2534); `strheap_gc` PRESERVES IY (its header says heap_alloc's retry flag depends on it);
  `ary_stride` and `str_body_copy` do not touch it. So: **`heap_alloc` must save/restore IY**
  (`push iy` before its frame, `pop iy` on its shared exit: ≈ +3 B; harmless to its array callers,
  which already cannot rely on IY across it) and INSTR must `push iy` before loading b$ into IY and
  `pop iy` before it publishes (≈ +4 B).
* **Args arrive in registers too.** DE and BC at tenant entry ARE W1/W2: `subrom_call` preserves DE
  and never touches BC; the inline stubs (`inl_go`) restore HL and leave DE/BC alone; CALSLT passes
  the main register set to the target (the tree already relies on this: DE as an arg,
  subromcall.asm:68; L as DEF FN's phase, [basic/deffn.asm](basic/deffn.asm):256 /
  docs/spec-basic-deffnland.md:154). ⚠️ UNVERIFIED FOR BC specifically (nothing measured BC). The
  plan uses the register copies only as a byte saving; every op can fall back to `ld c,(iy+6) /
  ld b,(iy+7)` (+2 B a site) if the S16.1 witness rows say BC does not arrive.
* **Four 7 B helpers make every RE-read / RE-write byte-neutral** (a re-read was 3 B, a call is 3 B):
  `she_w0` (`ld l,(iy+2) / ld h,(iy+3) / ret`), `she_w1`, `she_put0` (`ld (iy+2),l / ld (iy+3),h /
  ret`), `she_put1`. Cost ≈ +27 T per use (TIER 5 only).
* **Result tails collapse** (this is where the tenant pays for itself): the pattern
  `ld (SH_PTR),hl / xor a / ld (SH_ERR),a / ret` (8 B) stands at ~10 sites (`she_gc`, `she_alloc`,
  `she_snapshot`, `sfg_have`, `sfv_have`, `sca_have`, `sbb_have`, `sho_last`, `sh_ctl_reset`, …)
  → `jp she_ok0` (3 B); and `call sh_temp_push_alloc / jr nc,full / ld (SH_PTR),hl / ld a,b /
  ld (SH_ERR),a / or a` stands at six (temp_alloc, snapshot, hex, oct, bin, fill) → one helper.
  Both carves work TODAY with absolute addressing — so S16a takes them first (§4).

### 2.3 Per-op slot assignment (chosen to make the MAIN side free)

| op | W0 = HL in | W1 = DE in | W2 = BC in | A out | HL out | DE out | C out |
|---|---|---|---|---|---|---|---|
| 0 ALLOC | L = len | — | — | ERR 0/1 | body | — | — |
| 1 GC | — | — | — | 0 | FRETOP | — | — (no main caller: candidate to delete, ⚠️ grep only) |
| 2 APPEND | SRC (operand desc) | DEST (R) | — | ERR 0/1/2/3 | — | — | — |
| 3 TEMP_ALLOC | L = len | — | — | ERR 0/1/2 | slot | body | — |
| 4/16/21 SNAPSHOT | SRC | — | — | ERR | slot | — | — |
| 5 SLICE | SRC (temp) | D = start, E = count | — | 0 | — | — | — |
| 6/7/14 HEX/OCT/BIN | — | NUM | — | ERR | slot | — | — |
| 8 FILL | — | — | C = len, B = byte | ERR | slot | — | — |
| 9 MID_STORE | SRC (B$) | DEST (A$) | n (16-bit) + W3 = m | ERR 0/3 | — | — | — |
| 10 CMP | lhs | rhs | — | **bits 1/2/4** | — | — | — (BC preserved: the caller's C survives with no push) |
| 11 INSTR | a$ | b$ | p | 0 | — | **position** | — |
| 12 VAR_STORE | SRC | DEST | — | ERR 0/1 | — | — | — |
| 13/19 VAL | — | — | — | ERR 0/4/5 | end of number | int16 | type 0/4/8 |
| 15/17 FRE | — | — | — | 0 | — | free bytes | — |
| 18 CHAN_ADDR | L = channel | — | — | 0 | block address | — | — |
| 20 CTL_RESET | — | — | — | 0 | — (drop the PTR write: unread) | — | — |

**Aliasing rule (results overwrite args):** a result may go in a slot only after the op's LAST read
of the arg in that slot. Checked against every handler; **one violation:** `she_snap_slice` writes
SH_PTR (strheap.asm:320) and then reads SH_SRC (:321) — with PTR in W0 it would read its own
result. Fix: load BC from W0 before the PTR store (≈ 0 B, reorder). Also: `she_snap_asis` becomes
"ERR := 0" only (PTR == SRC already sits in W0: −6 B). Every ERR=1 exit that main then PUBLISHES
(`sst` falls into `sh_publish`, `shx_finish` likewise) must have written PTR first — today a missed
write publishes the PREVIOUS op's stale SH_PTR, after S16 it would publish the caller's junk HL.
Audited: she_temp_alloc :215, she_snapshot :340, sh_hex_build :1944, sh_fill :2330 write PTR before
ERR; ⚠️ sh_oct_build / sh_bin_build's OOM exits were not traced line by line — S16.2 must.

### 2.4 Nested string ops

* **No tenant op calls back into main** (closure: every `call`/`jp` target in strheap.asm and
  tkfloat.asm is defined in sub/ — checked with a read-only scan), so a block is never live while
  ANOTHER tenant call runs above it — except by construction in main:
* `ems_close` → `mid_own` (op 0) → `ems_close` (op 9): the outer arguments wait on the stack under
  the inner `sh_go`'s block; nothing aliases.
* `HEX$(LEN(A$))`, `"A"+MID$("XY"+"Z",1,2)+"B"`: every block is built AFTER the argument's own
  evaluation (`sct_loop` after `str_eval_one`, radix after `eval`, MID$ after the arg parse, FRE
  after `str_eval_ix`); only FRE's op crosses code (`evsp_close`, no evaluation) — in C.
* VAL → `tk_float`, SPRITE$ → VBUF: run INSIDE the tenant (tk_float) or outside any op (SPRITE$);
  the block is above the tenant's SP and nothing below it reaches up.

### 2.5 Abort, GC, interrupts, SP relocation

* **raise_error mid-op:** no strheap handler raises (they return ERR codes; `sc_call` raises only
  before the call when the sub ROM is absent). Every main-side raise that follows a call
  (`mo_oom`, `ems_range`, `str_heap_oom_error`, VAL's `ev_f_defer`) happens after `sh_go` popped the
  block. **No SH_* cell is read after an abort today** (deferred FPERR is decided from ERR at once,
  via `penderr_set`), so nothing is lost when the block vanishes.
* **GC:** roots are the temp pool, the FN frame chain, scalars and arrays (`sg_walk_*`); it never
  scanned SH_* and does not scan the stack. The block holds descriptor ADDRESSES (temps, variable
  slots, RVDESC, array elements — none moves during an op: the heap is its own partition since D-CLP,
  and array-region shifts happen in main before op 12) and RESULTS (body pointers from op 0/3)
  consumed before the next allocation — the same invariant SH_PTR/SH_PTR2 had. The sort buffer sits
  in `[ARYEND+2, SP − CTL_STACK_MARGIN)` (strheap.asm:858-890) — below the GC's own SP, which is
  below the block.
* **Interrupts:** `subrom_call` runs the tenant DI; an ISR (or the EI trampoline) pushes below SP.
* **SP relocation:** only `ctl_reloc` (program.asm:1993) moves SP, reached from `ctl_alloc` at
  statement level (GOSUB/FOR/trap record, program.asm:1565/1957, traps.asm:473, fat.asm:317) — never
  while a string op is in flight.
* **Stack depth:** +10 B per in-flight op (+12 with W3), peak ≈ +22 B (MID$ with its nested ALLOC),
  against `STK_EDGE_RESERVE` 116 B. 🔮 no measured edge moves; `ctllim-acceptance`,
  `stackpool-acceptance` and `ramfree-acceptance` are the rows that would show it.

### 2.6 What is NOT relied on

Results never ride back in registers through CALSLT: the tree's lore disagrees with itself —
"CALSLT does NOT preserve A" ([basic/expr.asm](basic/expr.asm):2202, [sub/errtrap.asm](sub/errtrap.asm):27,
[tests/test_msgsub.py](tests/test_msgsub.py):112) against "A = tenant's result"
([basic/subromcall.asm](basic/subromcall.asm):80, [basic/PROVENANCE.md](basic/PROVENANCE.md):1205). `sh_go`
pops its results from RAM, so either reading is fine. (Disclosure: while checking this I opened
C-BIOS's own `src/slot.asm` calslt source in the sibling checkout — source text, not a ROM image —
before the session's permission check stopped further reading; nothing in this design depends on
what it showed.)

---------------------------------------------------------------------------------------------------

## 3. Bytes, pins and walls (task 3)

### 3.1 Main, per site (hand counts; old → new)

| site | seg | old → new | Δ |
|---|---|---|---|
| `sh_call_op` + `call_strheap` → `sh_go` | A | 10 → 21 | +11 |
| `ctl_reset` (`ld a,20 / jp sh_go`; SUBSLOT_OK is already proven 1, so `sc_call`'s raise is unreachable) | A | 10 → 5 | −5 |
| `str_temp_alloc` (`ld l,a / ld a,3 / call sh_go / ret z / cp 2 / …`) | A | 39 → 19 | −20 |
| `sst_op` + `sh_publish` | A | 34 → 21 | −13 |
| `sct_loop` + `sct_append_err` (A already = ERR) | A | 25+3 → 13 | −15 |
| `str_temp_slice` (`ld h,b / ld l,c / ld a,5 / jp sh_go`) | A | 20 → 7 | −13 |
| `ev_ff_val` (DE = int, C = type) | A | 28 → 17 | −11 |
| `str_fn_chr` / `str_fn_space` / `sfg_close` (C/B) | A | 14+12+18 → 8+7+11 | −18 |
| `str_fn_radix` (NUM already in DE) + `shx_op_tail`/`shx_finish` (flags already set) | A | — | −11 |
| `efi_p_ok` (result → DE) | A | 31 → 18 | −13 |
| `str_cmp_bits` (`ld a,10 / jp sh_go`: result in A, BC preserved) | A | 18 → 5 | −13 |
| `ems_close` + `mid_own` (W3 push; A$ kept on the stack) | A | — | −3 |
| `inp_val` / `inp_num` / `inm_ok` / `inp_store` / `inu_got` | A | — | −8 |
| **seg A total** | | | **≈ −130** (range −100 … −140) |
| `str_set_key` (`push hl` stash, `sh_go`, flags survive `pop hl / ld (TEMPPT),hl`) | C | — | −13 |
| FRE: op in C (×2 arms), close (`ld a,c / push ix / call sh_go / pop ix / jp flt_int_result`) | C | — | −7 |
| `fch_ctx_addr` (`ld l,a / ld a,18 / jp sh_go`) | D | 12 → 6 | −6 |
| `exr_nan` (`ld c,a` on entry, `ld a,c` for `ld a,(SH_ERR)`) | F | — | −2 |

`inp_num`'s trailing-junk exit returns CF with A = the junk character today, and READ's `exr_nan`
then tests the separate SH_ERR (0) — with ERR in A, a junk byte of 5 would read as VAL's overflow
code. Add `xor a` before that `scf` (+1 B, counted). The CLEARPOOL-off arm (`switch-build-check`
flips it) needs its own FRE line (`ld c,15`) and keeps `str_snapshot_arg/slice` as aliases.

### 3.2 Pin safety (the part that decides the slice shape)

`pin_plan.py --check` fails when the total pad in front of the pins exceeds 4 B ("no growing
holes"), and a pad driven negative makes pasmo write an EMPTY binary with rc 0. A shrinking
segment is therefore as illegal as a growing one. Per slice:

* **seg A shrinks** → refill it from **seg B** (same low region, after the $3297 pin): move
  self-contained seg-B chunks (subromcall / edscreen / sound / title routines) into an A file, or
  site `sh_go` and new helpers there. Net: **main low (A+B) gains ≈ the shrink**. Candidates:
  `python3 tools/pin_plan.py` PLAN mode's REFILL list (it lists exactly "chunks AFTER P … that could
  be moved into the pad").
* **seg C and seg D shrink** → refill from **seg F** (past the last pin; moving an F chunk into C or
  D changes no other pinned segment's size). Main page 1 (F) gains the same.
* **seg F**: −2; +5 per site if the §3.4 contingency evicts `lrsetst`/`fldlook` (field.asm:696/741).
* Every slice ends with `make basic-reloc` (FIVE walls read, never quoted) and `pin_plan.py --check`.

### 3.3 Sub page 0 (the binding wall: 10 B)

Rough tenant delta under the full conversion (§2.2 helpers, args from registers, shared tails):
prologue +3, helpers +28, heap_alloc IY +3, INSTR IY +4, snap_slice reorder 0, VAL results +6 —
against first-read removals (DE/BC arrive: hex −4, oct −4, bin −2, slice −2, MID −4, VAR_STORE −4,
CMP −4), the CMP result into A (−3), snap_asis (−6), result tails (≈ −45), dead op 1 (≈ −12 if
deletion is approved) → **🔮 ≈ −30 ± 40 B**. Because the error bar crosses the wall, **carve before
spending**:

* **S16a carve (absolute addressing, behaviour-neutral):** the two shared result tails above
  (≈ −45 B), and a **jump-table dispatch** for `strheap_engine`'s 20-deep `cp n / jp z` chain
  (strheap.asm:111-156, ≈ 100 B → ≈ 12 B + 2 B a slot ≈ 56 B: ≈ −45 B; also faster for high ops).
  ⚠️ Both hand counts.

### 3.4 Contingency: evict a self-contained sub-p0 tenant to sub2 page 0

sub2 page 0 ends at `__MEAS_SUB2_P0_END` $0096 (≈ 16 KB free). D-TOKOVF set the precedent (BEEP,
[basic/sound.asm](basic/sound.asm):180-190: open-coded `ld ix / call subrom2_call / jp c,subrom_absent_error`,
+3..+5 B main per site). Checked self-contained (every call/jump target inside its own file):
[sub/lofu32.asm](sub/lofu32.asm) (≈ 81 B; caller expr.asm:1422, seg C — its +5 B fits the seg-C shrink),
[sub/lrsetst.asm](sub/lrsetst.asm) (≈ 66 B; field.asm:696, seg F),
[sub/fldlook.asm](sub/fldlook.asm) (≈ 47 B; field.asm:741, seg F). Not self-contained: keystr
(`gfx_vram_wr`, `pchar`), deftype (`is_letter`, `upcase`), readdata (`read_one_value`). Sizes are
label-span estimates from build/sub.sym.

### 3.5 Speed (TIER 5)

≈ +90 T in `sh_go` (4 push, 4 pop, `add hl,sp`) and ≈ +60..120 T in the tenant (`push hl/pop iy`,
indexed loads, helper calls) per string op, on top of a CALSLT round trip of several hundred T.
🔮 ≈ 10-20 % on a dispatch-bound string loop; measure (§4, `spd` row) — `str_set_key`'s open-coded
`sc_call` was kept "for speed", and it joins `sh_go` here.

### 3.6 The cheaper hybrid, if Variant B does not fit

**Variant R (reference-style, registers both ways):** one sub-p0 jump-table ENTRY per op (3 B each,
append-only, indices 18+) instead of the dispatch chain (5 B an op), args in HL/DE/BC, MID$'s B$ read
by the tenant from STRPTR (main already puts it there), results back in A/HL/DE. Deletes `sh_go` and
the block entirely; ≈ −38 B sub p0 for the dispatch; each main site becomes `call sc_inl0 / db entry`
(4 B). **It rests on CALSLT returning AF/HL/DE intact** — the lore conflict of §2.6, and the
harness already returns exactly HL/DE/A. Only after a one-slice measurement (a ping tenant that
returns known A/BC/DE/HL, both repack machines) — not recommended as the first move. A middle
variant (Variant B's block, but op = table entry instead of a block byte) saves the dispatch chain
and costs nothing else.

---------------------------------------------------------------------------------------------------

## 4. Slice plan, witnesses, knives (task 4)

Every slice: `make gates-fast` while iterating, full battery once before commit, `make basic-reloc`
walls read, `pin_plan.py --check`, `make switch-build-check` (CLEARPOOL arms), `make
nodisk-acceptance` and `diskbasic-acceptance` (both machines run this code: op 18 is the disk
channel path).

### S16.0 — the harness, then the carve (behaviour-neutral)

**(a) [tests/msxtest.py](tests/msxtest.py) `_install_subrom_bridge`:** run the island on the CALLER's
SP (set `sub0.cpu.sp = mach.cpu.sp`, `keep_sp=True`) and copy back all of `[$8000,$10000)` (the
island's own frames land below the caller's SP, i.e. dead stack, exactly as on the machine); pass
`bc` in and return `bc` (and keep A). Same for the page-1 bridge.
*Witness (before/after, OLD ABI):* a unit test that stages SH_SRC = a temp, SH_DEST = an address in
`$F300..$F37F` (the band the bridge drops today) and runs op 12 — 🔮 the descriptor does NOT arrive
before the fix, does after. *Knife K-WS75:* restore the private stack → that test fails.
*Control:* the whole unit suite unchanged.

**(b) tenant carve:** shared result tails, the `sh_temp_push_alloc` publish helper, the jump-table
dispatch, drop `sh_ctl_reset`'s unread PTR write; delete op 1 only if Joost agrees it is dead
(⚠️ grep-only). Gate: sub p0 free rises (read the wall), `test_str_*.py`, `string-acceptance`,
`clearpool-acceptance`, `binfre-acceptance`, `instr128-acceptance`. No behaviour change → no row
flips; the knife is per-helper (break the publish helper's ERR store → `x.oom3`-style rows in
string-acceptance diverge).

### S16.1 — `sh_go` + group 1 (the temp / concat core: ops 3, 4, 16, 21, 5, 2)

Transitional: a second table index `SUBROM_IDX_STRHEAPB` → `strheap_engine_b` (`push hl / pop iy /
ld a,(iy+1) / jr` into the shared dispatch). +3 B sub p0 (append-only entry). Legacy ops keep
`call_strheap` and SH_* until S16.3. `heap_alloc` IY save lands here (group 1 is its main user).
Edits: `str_temp_alloc`, `sst_op`/`sh_publish`, `sct_loop`/`sct_append_err`, `str_temp_slice`;
tenant `she_temp_alloc`, `she_snapshot`, `she_snap_keep`/`asis`/`slice` (the reorder),
`she_slice*`, `sh_append` + `sap_*`/`sate_*`; refill seg A.
Witness rows (probes/basic/basic_probe_wszero.py, the S11/S12 overlay pattern — load $A5 over the
whole window, run, print, VG-8020 is the oracle; 🔮 SAME before and after, they guard behaviour):
`ovcat` (`A$="A"+MID$("XY"+"Z",1,2)+"B"`, `LEN(X$+X$+X$)` at the STRMAX edge → ERR 15),
`ovslice` (LEFT$/RIGHT$/MID$ of a scalar, an array element and a temp under `CLEAR 60` — D-SLICEOOM's
three source kinds), `ovgc` (`CLEAR 300`, 30-element string array refilled in a loop so op 3 hits
the GC retry; `FRE("")` printed).
Knives: **K-WS76** `heap_alloc` no longer restores IY → op 3 publishes into the freed frame:
`ovgc`/`test_str_engine.py` diverge. **K-WS77** undo the `she_snap_slice` reorder → `ovslice`'s
scalar case returns garbage. ⚠️ BC-arrival: no group-1 op takes BC, so it is first exercised in .2.

### S16.2 — group 2 (6, 7, 14, 8, 10, 11, 9 + its nested 0, 12)

Edits: `str_fn_radix`, `shx_*`, `str_fn_chr`/`space`, `sfg_close`, `str_cmp_bits`, `efi_p_ok`,
`ems_close`/`mid_own`, `str_set_key` (seg C: refill from F); tenant hex/oct/bin/fill, CMP, INSTR
(IY save), MID (W3 at +10), VAR_STORE. Audit the oct/bin OOM exits (§2.3).
Rows: `ovfill` (`STRING$(3,"*")`, `SPACE$(2)`, `CHR$(65)`, `HEX$(LEN(STRING$(17,"A")))`, `OCT$(8)`,
`BIN$(5)` — a nested op inside the radix argument), `ovcmp` (`"AB"<"ABC"`, `"B">"AB"`, a compare
inside a 9-term sum: D-TEMPPOL's pop-both path), `ovinstr` (`INSTR(2,"ABCABC","BC")`,
`INSTR("AB","")`, `INSTR(256,…)` → ERR 5), `ovmid` (`READ R$:MID$(R$,2,2)="QQ"` — op 0 nested in
op 9 — then `RESTORE:READ R$` shows the DATA unchanged; `MID$(A$,4)="X"` on a 3-char A$ → ERR 5),
`ovlet` (`A$=B$` scalar + array element + RVDESC source under `CLEAR 100`, the D-CLP 100-B row).
Knives: **K-WS78** W3 offset +8 instead of +10 → `ovmid` diverges. **K-WS79** tenant takes W2 from
the register but main stops loading BC (MID's `n`) → `ovmid`/`ovinstr` diverge — this is ALSO the
BC-arrival witness (if it does not diverge for the right reason, the register path is not real:
fall back to block reads).

### S16.3 — group 3 (13/19, 15/17, 18, 0's last user, 20) and the deletion

Edits: `ev_ff_val`, `inp_val`/`inp_num`/`inp_store`/`inu_got` (input.asm), `exr_nan` (program.asm,
seg F), FRE (expr.asm, seg C), `fch_ctx_addr` (files.asm, seg D: refill from F), `ctl_reset`; tenant
VAL (both entries), FRE, CHAN, CTL. Then: point index 5 at `strheap_engine_b` and retire the legacy
prologue (index B either stays as an alias or, being the LAST entry, is dropped — ⚠️ check the
table's append-only rule allows dropping the last), **delete SH_BASE..SH_ERR** from
[basic/sysvars.inc](basic/sysvars.inc):1996-2030, the `ram-width-allow.txt` line, the stale prose
(sysvars.inc:933, :1451, :1843-1879, :1978; sub/equates.inc:69; strheap.asm's headers; str-engine's
"canonical shape" comments; [docs/spec-basic-arrays-slice4a-string-heap.md](docs/spec-basic-arrays-slice4a-string-heap.md) §9/§10
— invert, do not delete the old analysis).
**The vacated-sum row `s16sh`:** load $A5 over the window, run every op once (the program below),
then `S=0:FOR J=61386 TO 61403:S=S+PEEK(J):NEXT:PRINT"[S";S;"]"` — the frozen old home
$EFCA..$EFDB. VG-8020: 165 × 18 = **2970**. 🔮 DIVERGES on S16.2's build (ops 13/15/17/18/19/20
still write it), SAME on S16.3's. Program: concat, LEFT$/MID$, STRING$/SPACE$/CHR$, HEX$/OCT$/BIN$,
`MID$(…)=`, INSTR, `A$<B$`, `A$=B$`, `VAL("1.5")`, `READ N` (op 19), `FRE("")`, `FRE(0)`, `CLEAR`
(op 20), `OPEN "CAS:X" FOR OUTPUT AS #1:CLOSE` (op 18 — ⚠️ check a diskless CAS OPEN reaches
`fch_ctx_addr`; the `chan` row's program already opens one).
Plus rows `ovval` (`VAL("&H1F")`, `VAL(" 1.5E2")`, `VAL("12X")`, `VAL("&")` → ERR 2,
`VAL("&H1FFFF")` → ERR 6), `ovread` (`DATA 1.5,&H10,12X` → ERR 2 in the DATA line; `DATA 1E99` →
ERR 6 — exr_nan's A path), `ovinp` (`INPUT A` answered `1-2` → ?Redo, then `42` — the s12inp
`@WAIT` pattern), `ovfre` (`FRE("")`, `FRE(0)`, `FRE(-1)`), `ovsprite` (`SPRITE$(0)=STRING$(8,255):
PRINT LEN(SPRITE$(0))`), and `spd` (a timed 2000-iteration concat/compare loop, both machines —
the TIER-5 reading, not a pass/fail row).
Knives: **K-WS80** `sh_go` also copies its 8 B block to $EFCA (`ld de,$EFCA / ld bc,8 / ldir`) →
`s16sh` diverges. **K-WS81** `sh_go` returns A = 0 (drop the `pop af`, `xor a`) → `ovcat`'s ERR 15
and `ovread`'s ERR 6 vanish. **K-WS82** `inp_num`'s junk exit without `xor a`, junk byte 5 — a unit
row in tests/test_input.py (not typeable on the machine). (Names K-WS75..82: ⚠️ check they are free.)

### Regression gates most exposed

Unit: [tests/test_str_engine.py](tests/test_str_engine.py), `test_str_fn.py`, `test_str_verbs.py`,
`test_str_compare.py`, `test_strvar.py`, `test_mid_stmt.py`, `test_input.py` (inp_num),
`test_program.py` + `test_control_flow.py` (READ), `test_arrays.py` (heap_alloc's IY, aeng_copy_str),
`test_statements.py`, `test_msgsub.py`. Acceptance: `string-acceptance`, `clearpool-acceptance`,
`binfre-acceptance`, `instr128-acceptance`, `str-domain-acceptance`, `strparen-acceptance`,
`litref-acceptance`, `readref-acceptance`, `readflt-acceptance`, `readerl-acceptance`,
`readvar-acceptance`, `input-acceptance`, `inputary-acceptance`, `catterm-`/`catusr-acceptance`,
`tmfp-acceptance`, `ramfree-acceptance`, `ctllim-`/`stackpool-`/`ctlcross-acceptance` (op 20, stack
depth), `asavechan-`/`fcb0-`/`fcbhdr-acceptance` (op 18), `kwsweep`, `wszero-acceptance`,
`nodisk-acceptance`, `diskbasic-acceptance`, `ram-map-check`, `switch-build-check`.

### After S16

S15's "refused" table loses its SH_* row. WSRC_TYP (→ a register, VALTYP's job) and FCH_RDMODE
(→ FLKINP, equates) are the other two TODO items and stay separate.

---------------------------------------------------------------------------------------------------

## 5. Blind spots / unverified

1. Every byte figure is a hand count; the sub-p0 estimate (−30 ± 40) is the weakest number.
2. BC arriving in the tenant through CALSLT (§2.2) — the K-WS79 row settles it.
3. `ev_sp` / `evsp_close` preserving C (FRE's op carrier).
4. Op 1 (GC) has no caller found by grep (main, sub, disk); not proven dead by a reach set.
5. `tgt_desc_fix` was not checked for STRPTR writes — the plan keeps reading STRPTR BEFORE it, as
   today, so it does not matter.
6. sh_oct_build / sh_bin_build OOM exits: PTR-before-publish not traced.
7. Segment addresses are from the 2026-10-16 07:38 build; the walls (low 66, page 1 171, sub p0 10,
   sub p1 1142) are the brief's, not re-measured.
8. The harness fix (S16.0a) changes what EVERY page-0 tenant test runs on; a test that passed only
   because the island had a private stack would now fail — that is a finding, not a regression.

## 6. Found in passing

* [basic/sysvars.inc](basic/sysvars.inc):1996-1998 — SH_BASE's comment still says the block "ends at
  $E21E, one below TRAPPEND $E21F"; SH_BASE is $EFCA (the D-MERGEWIN prose survived a move).
* [tests/msxtest.py](tests/msxtest.py):229-286 — the bridge silently drops tenant writes into the caller's
  top 128 B of stack and gives the island the caller's stack addresses: a latent blind spot for
  ANY tenant that writes through a pointer into the caller's frame (none found today).
* The CALSLT-preserves-A lore conflict (§2.6) is in five places across code, tests and PROVENANCE;
  one measurement would retire it.

---------------------------------------------------------------------------------------------------

## Appendix A — every SH_* code reference, by op

(Generated by `shrefs.py` / `group.py` beside this file. "side" is the instruction's direction;
tenant writes of SH_LEN/SH_SRC under ops 13/19 are VAL's RESULTS.)

| op | side | file:line | routine | region | cell | instruction |
|---|---|---|---|---|---|---|
| 0 | tenant reads arg | [sub/strheap.asm:194](sub/strheap.asm:194) | she_alloc | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 0 | tenant writes result | [sub/strheap.asm:197](sub/strheap.asm:197) | she_alloc | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 0 | tenant writes result | [sub/strheap.asm:199](sub/strheap.asm:199) | she_alloc | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 0 | tenant writes result | [sub/strheap.asm:203](sub/strheap.asm:203) | she_oom | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 0 (nested inside 9) | main writes arg | [basic/str-engine.asm:1710](basic/str-engine.asm:1710) | mid_own | main seg A | SH_LEN | `ld (SH_LEN),a` |
| 0 (nested inside 9) | main reads result | [basic/str-engine.asm:1713](basic/str-engine.asm:1713) | mid_own | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 0 (nested inside 9) | main reads result | [basic/str-engine.asm:1716](basic/str-engine.asm:1716) | mid_own | main seg A | SH_DEST | `ld hl,(SH_DEST)` |
| 0 (nested inside 9) | main reads result | [basic/str-engine.asm:1725](basic/str-engine.asm:1725) | mid_own | main seg A | SH_PTR | `ld de,(SH_PTR)` |
| 1 | tenant writes result | [sub/strheap.asm:189](sub/strheap.asm:189) | she_gc | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 1 | tenant writes result | [sub/strheap.asm:191](sub/strheap.asm:191) | she_gc | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 2 | main writes arg | [basic/str-engine.asm:774](basic/str-engine.asm:774) | sct_loop | main seg A | SH_SRC | `ld (SH_SRC),hl` |
| 2 | main writes arg | [basic/str-engine.asm:777](basic/str-engine.asm:777) | sct_loop | main seg A | SH_DEST | `ld (SH_DEST),hl` |
| 2 | main reads result | [basic/str-engine.asm:782](basic/str-engine.asm:782) | sct_loop | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 2 | main reads result | [basic/str-engine.asm:862](basic/str-engine.asm:862) | sct_append_err | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 2 | tenant reads arg | [sub/strheap.asm:1668](sub/strheap.asm:1668) | sh_append | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant reads arg | [sub/strheap.asm:1671](sub/strheap.asm:1671) | sh_append | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 2 | tenant reads arg | [sub/strheap.asm:1692](sub/strheap.asm:1692) | sap_ok | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant reads arg | [sub/strheap.asm:1694](sub/strheap.asm:1694) | sap_ok | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 2 | tenant reads arg | [sub/strheap.asm:1698](sub/strheap.asm:1698) | sap_ok | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant writes result | [sub/strheap.asm:1705](sub/strheap.asm:1705) | sap_ok | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 2 | tenant reads arg | [sub/strheap.asm:1708](sub/strheap.asm:1708) | sap_empty | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant writes result | [sub/strheap.asm:1715](sub/strheap.asm:1715) | sap_empty | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 2 | tenant reads arg | [sub/strheap.asm:1726](sub/strheap.asm:1726) | sap_release | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 2 | tenant writes result | [sub/strheap.asm:1745](sub/strheap.asm:1745) | sap_oom | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 2 | tenant writes result | [sub/strheap.asm:1749](sub/strheap.asm:1749) | sap_toolong | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 2 | tenant reads arg | [sub/strheap.asm:1791](sub/strheap.asm:1791) | sap_try_extend | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant reads arg | [sub/strheap.asm:1841](sub/strheap.asm:1841) | sate_fits | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant reads arg | [sub/strheap.asm:1855](sub/strheap.asm:1855) | sate_fits | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 2 | tenant reads arg | [sub/strheap.asm:1864](sub/strheap.asm:1864) | sate_write | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 2 | tenant writes result | [sub/strheap.asm:1872](sub/strheap.asm:1872) | sate_write | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 3 | main writes arg | [basic/str-engine.asm:607](basic/str-engine.asm:607) | str_temp_alloc | main seg A | SH_LEN | `ld (SH_LEN),a` |
| 3 | main reads result | [basic/str-engine.asm:610](basic/str-engine.asm:610) | str_temp_alloc | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 3 | main reads result | [basic/str-engine.asm:620](basic/str-engine.asm:620) | str_temp_alloc | main seg A | SH_PTR | `ld hl,(SH_PTR)` |
| 3 | main reads result | [basic/str-engine.asm:623](basic/str-engine.asm:623) | sta_ok | main seg A | SH_PTR | `ld hl,(SH_PTR)` |
| 3 | main reads result | [basic/str-engine.asm:624](basic/str-engine.asm:624) | sta_ok | main seg A | SH_PTR2 | `ld de,(SH_PTR2)` |
| 3 | tenant reads arg | [sub/strheap.asm:212](sub/strheap.asm:212) | she_temp_alloc | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 3 | tenant writes result | [sub/strheap.asm:215](sub/strheap.asm:215) | she_temp_alloc | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 3 | tenant writes result | [sub/strheap.asm:216](sub/strheap.asm:216) | she_temp_alloc | sub p0 | SH_PTR2 | `ld (SH_PTR2),de` |
| 3 | tenant writes result | [sub/strheap.asm:218](sub/strheap.asm:218) | she_temp_alloc | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 3 | tenant writes result | [sub/strheap.asm:222](sub/strheap.asm:222) | she_ta_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 4 | tenant writes result | [sub/strheap.asm:355](sub/strheap.asm:355) | she_sn_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 4 (+16/21 fallthrough) | tenant reads arg | [sub/strheap.asm:335](sub/strheap.asm:335) | she_snapshot | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 4 (+16/21 fallthrough) | tenant writes result | [sub/strheap.asm:340](sub/strheap.asm:340) | she_snapshot | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 4 (+16/21 fallthrough) | tenant writes result | [sub/strheap.asm:342](sub/strheap.asm:342) | she_snapshot | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 4/16/21 | main writes arg | [basic/str-engine.asm:693](basic/str-engine.asm:693) | sst_op | main seg A | SH_OP | `ld (SH_OP),a` |
| 4/16/21 | main writes arg | [basic/str-engine.asm:695](basic/str-engine.asm:695) | sst_op | main seg A | SH_SRC | `ld (SH_SRC),hl` |
| 4/16/21 | main reads result | [basic/str-engine.asm:697](basic/str-engine.asm:697) | sst_op | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 4/16/21 + 6/7/8/14 (shared) | main reads result | [basic/str-engine.asm:713](basic/str-engine.asm:713) | sh_publish | main seg A | SH_PTR | `ld hl,(SH_PTR)` |
| 5 | main writes arg | [basic/str-engine.asm:916](basic/str-engine.asm:916) | str_temp_slice | main seg A | SH_SRC | `ld (SH_SRC),bc` |
| 5 | main writes arg | [basic/str-engine.asm:918](basic/str-engine.asm:918) | str_temp_slice | main seg A | SH_START | `ld (SH_START),a` |
| 5 | main writes arg | [basic/str-engine.asm:920](basic/str-engine.asm:920) | str_temp_slice | main seg A | SH_COUNT | `ld (SH_COUNT),a` |
| 5 | main writes arg | [basic/str-engine.asm:922](basic/str-engine.asm:922) | str_temp_slice | main seg A | SH_OP | `ld (SH_OP),a` |
| 5 | tenant writes result | [sub/strheap.asm:184](sub/strheap.asm:184) | she_slice_op | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 5 | tenant reads arg | [sub/strheap.asm:379](sub/strheap.asm:379) | she_slice | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 5 | tenant reads arg | [sub/strheap.asm:380](sub/strheap.asm:380) | she_slice | sub p0 | SH_START | `ld bc,(SH_START)` |
| 5 | tenant reads arg | [sub/strheap.asm:432](sub/strheap.asm:432) | she_slice_new | sub p0 | SH_COUNT | `ld a,(SH_COUNT)` |
| 5 | tenant reads arg | [sub/strheap.asm:444](sub/strheap.asm:444) | she_slice_new | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 5 | tenant reads arg | [sub/strheap.asm:449](sub/strheap.asm:449) | she_slice_new | sub p0 | SH_START | `ld a,(SH_START)` |
| 5 | tenant reads arg | [sub/strheap.asm:454](sub/strheap.asm:454) | she_slice_new | sub p0 | SH_COUNT | `ld a,(SH_COUNT)` |
| 5 | tenant reads arg | [sub/strheap.asm:466](sub/strheap.asm:466) | she_slice_ofs | sub p0 | SH_COUNT | `ld a,(SH_COUNT)` |
| 5 | tenant reads arg | [sub/strheap.asm:472](sub/strheap.asm:472) | she_slice_ofs | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 5 | tenant reads arg | [sub/strheap.asm:484](sub/strheap.asm:484) | she_slice_ofs | sub p0 | SH_START | `ld a,(SH_START)` |
| 5 | tenant reads arg | [sub/strheap.asm:489](sub/strheap.asm:489) | she_slice_ofs | sub p0 | SH_COUNT | `ld a,(SH_COUNT)` |
| 5 | tenant reads arg | [sub/strheap.asm:493](sub/strheap.asm:493) | she_slice_ofs | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 5 | tenant reads arg | [sub/strheap.asm:504](sub/strheap.asm:504) | sso_empty | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 6 | tenant reads arg | [sub/strheap.asm:1924](sub/strheap.asm:1924) | sh_hex_build | sub p0 | SH_NUM | `ld de,(SH_NUM)` |
| 6 | tenant writes result | [sub/strheap.asm:1944](sub/strheap.asm:1944) | sh_hex_build | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 6 | tenant writes result | [sub/strheap.asm:1946](sub/strheap.asm:1946) | sh_hex_build | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 6 | tenant writes result | [sub/strheap.asm:1966](sub/strheap.asm:1966) | shb_hex_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 6/7/14 | main writes arg | [basic/str-engine.asm:1831](basic/str-engine.asm:1831) | str_fn_radix | main seg A | SH_NUM | `ld (SH_NUM),de` |
| 6/7/8/14 | main writes arg | [basic/str-engine.asm:1857](basic/str-engine.asm:1857) | shx_op_tail | main seg A | SH_OP | `ld (SH_OP),a` |
| 6/7/8/14 | main reads result | [basic/str-engine.asm:1870](basic/str-engine.asm:1870) | shx_finish | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 7 | tenant reads arg | [sub/strheap.asm:2237](sub/strheap.asm:2237) | sh_oct_build | sub p0 | SH_NUM | `ld de,(SH_NUM)` |
| 7 | tenant writes result | [sub/strheap.asm:2265](sub/strheap.asm:2265) | sho_last | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 7 | tenant writes result | [sub/strheap.asm:2267](sub/strheap.asm:2267) | sho_last | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 7 | tenant writes result | [sub/strheap.asm:2287](sub/strheap.asm:2287) | shb_oct_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 8 | main writes arg | [basic/str-engine.asm:1227](basic/str-engine.asm:1227) | str_fn_chr | main seg A | SH_LEN | `ld (SH_LEN),a` |
| 8 | main writes arg | [basic/str-engine.asm:1229](basic/str-engine.asm:1229) | str_fn_chr | main seg A | SH_FILLBYTE | `ld (SH_FILLBYTE),a` |
| 8 | main writes arg | [basic/str-engine.asm:1909](basic/str-engine.asm:1909) | str_fn_space | main seg A | SH_LEN | `ld (SH_LEN),a` |
| 8 | main writes arg | [basic/str-engine.asm:1911](basic/str-engine.asm:1911) | str_fn_space | main seg A | SH_FILLBYTE | `ld (SH_FILLBYTE),a` |
| 8 | main writes arg | [basic/str-engine.asm:2014](basic/str-engine.asm:2014) | sfg_close | main seg A | SH_FILLBYTE | `ld (SH_FILLBYTE),a` |
| 8 | main writes arg | [basic/str-engine.asm:2016](basic/str-engine.asm:2016) | sfg_close | main seg A | SH_LEN | `ld (SH_LEN),a` |
| 8 | main writes arg | [basic/str-engine.asm:2018](basic/str-engine.asm:2018) | sfg_close | main seg A | SH_OP | `ld (SH_OP),a` |
| 8 | tenant reads arg | [sub/strheap.asm:2327](sub/strheap.asm:2327) | sh_fill | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 8 | tenant writes result | [sub/strheap.asm:2330](sub/strheap.asm:2330) | sh_fill | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 8 | tenant writes result | [sub/strheap.asm:2332](sub/strheap.asm:2332) | sh_fill | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 8 | tenant reads arg | [sub/strheap.asm:2339](sub/strheap.asm:2339) | shf_fill | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 8 | tenant reads arg | [sub/strheap.asm:2341](sub/strheap.asm:2341) | shf_fill | sub p0 | SH_FILLBYTE | `ld a,(SH_FILLBYTE)` |
| 8 | tenant writes result | [sub/strheap.asm:2349](sub/strheap.asm:2349) | shf_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 9 | main writes arg | [basic/str-engine.asm:1661](basic/str-engine.asm:1661) | ems_close | main seg A | SH_NUM | `ld (SH_NUM),de` |
| 9 | main writes arg | [basic/str-engine.asm:1662](basic/str-engine.asm:1662) | ems_close | main seg A | SH_START | `ld (SH_START),bc` |
| 9 | main writes arg | [basic/str-engine.asm:1665](basic/str-engine.asm:1665) | ems_close | main seg A | SH_SRC | `ld (SH_SRC),hl` |
| 9 | main writes arg | [basic/str-engine.asm:1669](basic/str-engine.asm:1669) | ems_close | main seg A | SH_DEST | `ld (SH_DEST),hl` |
| 9 | main reads result | [basic/str-engine.asm:1674](basic/str-engine.asm:1674) | ems_close | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 9 | tenant reads arg | [sub/strheap.asm:2365](sub/strheap.asm:2365) | sh_mid_store | sub p0 | SH_START | `ld bc,(SH_START)` |
| 9 | tenant reads arg | [sub/strheap.asm:2373](sub/strheap.asm:2373) | sh_mid_store | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 9 | tenant reads arg | [sub/strheap.asm:2380](sub/strheap.asm:2380) | sh_mid_store | sub p0 | SH_NUM | `ld de,(SH_NUM)` |
| 9 | tenant reads arg | [sub/strheap.asm:2394](sub/strheap.asm:2394) | smd_have_cap | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 9 | tenant reads arg | [sub/strheap.asm:2409](sub/strheap.asm:2409) | smd_k | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 9 | tenant reads arg | [sub/strheap.asm:2415](sub/strheap.asm:2415) | smd_k | sub p0 | SH_START | `ld hl,(SH_START)` |
| 9 | tenant writes result | [sub/strheap.asm:2433](sub/strheap.asm:2433) | smd_done | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 9 | tenant writes result | [sub/strheap.asm:2437](sub/strheap.asm:2437) | smd_range | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 10 | main writes arg | [basic/str-engine.asm:2254](basic/str-engine.asm:2254) | str_cmp_bits | main seg A | SH_SRC | `ld (SH_SRC),hl` |
| 10 | main writes arg | [basic/str-engine.asm:2255](basic/str-engine.asm:2255) | str_cmp_bits | main seg A | SH_DEST | `ld (SH_DEST),de` |
| 10 | main reads result | [basic/str-engine.asm:2258](basic/str-engine.asm:2258) | str_cmp_bits | main seg A | SH_LEN | `ld a,(SH_LEN)` |
| 10 | tenant reads arg | [sub/strheap.asm:164](sub/strheap.asm:164) | she_cmp_op | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 10 | tenant reads arg | [sub/strheap.asm:165](sub/strheap.asm:165) | she_cmp_op | sub p0 | SH_DEST | `ld de,(SH_DEST)` |
| 10 | tenant writes result | [sub/strheap.asm:167](sub/strheap.asm:167) | she_cmp_op | sub p0 | SH_LEN | `ld (SH_LEN),a` |
| 10 | tenant writes result | [sub/strheap.asm:170](sub/strheap.asm:170) | she_cmp_op | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 10 | tenant reads arg | [sub/strheap.asm:175](sub/strheap.asm:175) | she_cmp_op | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 10 | tenant reads arg | [sub/strheap.asm:177](sub/strheap.asm:177) | she_cmp_op | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 11 | main writes arg | [basic/str-engine.asm:2141](basic/str-engine.asm:2141) | efi_p_ok | main seg A | SH_SRC | `ld (SH_SRC),hl` |
| 11 | main writes arg | [basic/str-engine.asm:2144](basic/str-engine.asm:2144) | efi_p_ok | main seg A | SH_DEST | `ld (SH_DEST),hl` |
| 11 | main writes arg | [basic/str-engine.asm:2145](basic/str-engine.asm:2145) | efi_p_ok | main seg A | SH_P | `ld (SH_P),bc` |
| 11 | main reads result | [basic/str-engine.asm:2148](basic/str-engine.asm:2148) | efi_p_ok | main seg A | SH_PTR | `ld de,(SH_PTR)` |
| 11 | tenant writes result | [sub/strheap.asm:161](sub/strheap.asm:161) | she_instr_op | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 11 | tenant reads arg | [sub/strheap.asm:2533](sub/strheap.asm:2533) | sh_instr_search | sub p0 | SH_SRC | `ld ix,(SH_SRC)` |
| 11 | tenant reads arg | [sub/strheap.asm:2534](sub/strheap.asm:2534) | sh_instr_search | sub p0 | SH_DEST | `ld iy,(SH_DEST)` |
| 11 | tenant reads arg | [sub/strheap.asm:2535](sub/strheap.asm:2535) | sh_instr_search | sub p0 | SH_P | `ld bc,(SH_P)` |
| 11 | tenant writes result | [sub/strheap.asm:2564](sub/strheap.asm:2564) | sis_empty_result | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 11 | tenant writes result | [sub/strheap.asm:2606](sub/strheap.asm:2606) | sis_cmp | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 11 | tenant writes result | [sub/strheap.asm:2631](sub/strheap.asm:2631) | sis_zero | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 12 | main writes arg | [basic/vars.asm:1093](basic/vars.asm:1093) | str_set_key | main seg C | SH_SRC | `ld (SH_SRC),hl` |
| 12 | main writes arg | [basic/vars.asm:1110](basic/vars.asm:1110) | str_set_key | main seg C | SH_DEST | `ld (SH_DEST),hl` |
| 12 | main writes arg | [basic/vars.asm:1112](basic/vars.asm:1112) | str_set_key | main seg C | SH_OP | `ld (SH_OP),a` |
| 12 | main reads result | [basic/vars.asm:1118](basic/vars.asm:1118) | str_set_key | main seg C | SH_ERR | `ld a,(SH_ERR)` |
| 12 | tenant reads arg | [sub/strheap.asm:2661](sub/strheap.asm:2661) | sh_var_store | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 12 | tenant reads arg | [sub/strheap.asm:2662](sub/strheap.asm:2662) | sh_var_store | sub p0 | SH_DEST | `ld de,(SH_DEST)` |
| 12 | tenant reads arg | [sub/strheap.asm:2665](sub/strheap.asm:2665) | sh_var_store | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 12 | tenant writes result | [sub/strheap.asm:2672](sub/strheap.asm:2672) | sh_var_store | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 12 | tenant reads arg | [sub/strheap.asm:2676](sub/strheap.asm:2676) | svs_copy | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 12 | tenant reads arg | [sub/strheap.asm:2681](sub/strheap.asm:2681) | svs_copy | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 12 | tenant reads arg | [sub/strheap.asm:2686](sub/strheap.asm:2686) | svs_copy | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 12 | tenant reads arg | [sub/strheap.asm:2688](sub/strheap.asm:2688) | svs_copy | sub p0 | SH_DEST | `ld hl,(SH_DEST)` |
| 12 | tenant writes result | [sub/strheap.asm:2696](sub/strheap.asm:2696) | svs_copy | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 12 | tenant writes result | [sub/strheap.asm:2700](sub/strheap.asm:2700) | svs_oom | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 13 | main writes arg | [basic/str-engine.asm:1084](basic/str-engine.asm:1084) | ev_ff_val | main seg A | SH_OP | `ld (SH_OP),a` |
| 13 | main reads result | [basic/str-engine.asm:1096](basic/str-engine.asm:1096) | ev_ff_val | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 13 | main reads result | [basic/str-engine.asm:1104](basic/str-engine.asm:1104) | ev_ff_val | main seg A | SH_LEN | `ld a,(SH_LEN)` |
| 13 | tenant writes result | [sub/strheap.asm:2728](sub/strheap.asm:2728) | sh_val_parse | sub p0 | SH_LEN | `ld (SH_LEN),a` |
| 13/15/17/19 (shared reader) | main reads result | [basic/input.asm:399](basic/input.asm:399) | inm_ok | main seg A | SH_PTR | `ld de,(SH_PTR)` |
| 13/19 | tenant writes result (VAL end) | [sub/strheap.asm:2752](sub/strheap.asm:2752) | svp_body | sub p0 | SH_SRC | `ld (SH_SRC),hl` |
| 13/19 | tenant writes result (VAL end) | [sub/strheap.asm:2833](sub/strheap.asm:2833) | svp_flt | sub p0 | SH_SRC | `ld (SH_SRC),hl` |
| 13/19 | tenant reads arg | [sub/strheap.asm:2854](sub/strheap.asm:2854) | svp_frel | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 13/19 | tenant writes result | [sub/strheap.asm:2869](sub/strheap.asm:2869) | svp_fok | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 13/19 | tenant writes result | [sub/strheap.asm:2907](sub/strheap.asm:2907) | svp_t_f | sub p0 | SH_LEN | `ld (SH_LEN),a` |
| 13/19 | tenant writes result | [sub/strheap.asm:2922](sub/strheap.asm:2922) | svp_done | sub p0 | SH_PTR | `ld (SH_PTR),de` |
| 13/19 | tenant writes result | [sub/strheap.asm:2924](sub/strheap.asm:2924) | svp_done | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 13/19 | tenant writes result | [sub/strheap.asm:2966](sub/strheap.asm:2966) | svp_berr | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 13/19 | tenant writes result | [sub/strheap.asm:2968](sub/strheap.asm:2968) | svp_berr | sub p0 | SH_PTR | `ld (SH_PTR),de` |
| 13/19 | tenant writes result (VAL end) | [sub/strheap.asm:3032](sub/strheap.asm:3032) | svp_bfin | sub p0 | SH_SRC | `ld (SH_SRC),de` |
| 13/19 | tenant writes result | [sub/strheap.asm:3035](sub/strheap.asm:3035) | svp_bfin | sub p0 | SH_PTR | `ld (SH_PTR),de` |
| 13/19 | tenant writes result | [sub/strheap.asm:3037](sub/strheap.asm:3037) | svp_bfin | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 14 | tenant reads arg | [sub/strheap.asm:2188](sub/strheap.asm:2188) | sh_bin_build | sub p0 | SH_NUM | `ld hl,(SH_NUM)` |
| 14 | tenant writes result | [sub/strheap.asm:2206](sub/strheap.asm:2206) | sbb_have | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 14 | tenant writes result | [sub/strheap.asm:2208](sub/strheap.asm:2208) | sbb_have | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 14 | tenant writes result | [sub/strheap.asm:2233](sub/strheap.asm:2233) | sbb_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 15 | main writes arg | [basic/expr.asm:1751](basic/expr.asm:1751) | ev_ff_fre | main seg C | SH_OP | `ld (SH_OP),a` |
| 15 | tenant writes result | [sub/strheap.asm:2037](sub/strheap.asm:2037) | sfg_have | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 15 | tenant writes result | [sub/strheap.asm:2039](sub/strheap.asm:2039) | sfg_have | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 15/17 | main writes arg | [basic/expr.asm:1782](basic/expr.asm:1782) | ev_fre_close | main seg C | SH_OP | `ld (SH_OP),a` |
| 16/21 | tenant reads arg | [sub/strheap.asm:274](sub/strheap.asm:274) | she_snap_asis | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 16/21 | tenant writes result | [sub/strheap.asm:275](sub/strheap.asm:275) | she_snap_asis | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 16/21 | tenant writes result | [sub/strheap.asm:277](sub/strheap.asm:277) | she_snap_asis | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 16/21 (helper) | tenant reads arg | [sub/strheap.asm:232](sub/strheap.asm:232) | sh_src_is_temp | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 17 | main writes arg | [basic/expr.asm:1770](basic/expr.asm:1770) | ev_fre_num | main seg C | SH_OP | `ld (SH_OP),a` |
| 17 | tenant writes result | [sub/strheap.asm:2078](sub/strheap.asm:2078) | sfv_have | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 17 | tenant writes result | [sub/strheap.asm:2080](sub/strheap.asm:2080) | sfv_have | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 18 | main writes arg | [basic/files.asm:1637](basic/files.asm:1637) | fch_ctx_addr | main seg D | SH_LEN | `ld (SH_LEN),a` |
| 18 | main reads result | [basic/files.asm:1640](basic/files.asm:1640) | fch_ctx_addr | main seg D | SH_PTR | `ld hl,(SH_PTR)` |
| 18 | tenant reads arg | [sub/strheap.asm:2154](sub/strheap.asm:2154) | sh_chan_addr | sub p0 | SH_LEN | `ld a,(SH_LEN)` |
| 18 | tenant writes result | [sub/strheap.asm:2164](sub/strheap.asm:2164) | sca_have | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 18 | tenant writes result | [sub/strheap.asm:2166](sub/strheap.asm:2166) | sca_have | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 19 | tenant writes result | [sub/strheap.asm:2720](sub/strheap.asm:2720) | sh_val_scr | sub p0 | SH_LEN | `ld (SH_LEN),a` |
| 19 (reader) | main reads result | [basic/input.asm:380](basic/input.asm:380) | inp_num | main seg A | SH_ERR | `ld a,(SH_ERR)` |
| 19 (reader) | main reads result | [basic/input.asm:384](basic/input.asm:384) | inp_num | main seg A | SH_SRC | `ld hl,(SH_SRC)` |
| 19 (reader, 1 level up) | main reads result | [basic/input.asm:451](basic/input.asm:451) | inp_store | main seg A | SH_LEN | `ld a,(SH_LEN)` |
| 19 (reader, 2 levels up: READ) | main reads result | [basic/program.asm:2392](basic/program.asm:2392) | exr_nan | main seg F | SH_ERR | `ld a,(SH_ERR)` |
| 20 | main writes arg | [basic/str-engine.asm:273](basic/str-engine.asm:273) | ctl_reset | main seg A | SH_OP | `ld (SH_OP),a` |
| 20 | tenant writes result | [sub/strheap.asm:2121](sub/strheap.asm:2121) | sh_ctl_reset | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 20 | tenant writes result | [sub/strheap.asm:2124](sub/strheap.asm:2124) | sh_ctl_reset | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| 21 | tenant reads arg | [sub/strheap.asm:299](sub/strheap.asm:299) | she_snap_slice | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 21 | tenant reads arg | [sub/strheap.asm:304](sub/strheap.asm:304) | she_snap_slice | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 21 | tenant reads arg | [sub/strheap.asm:310](sub/strheap.asm:310) | she_snap_slice | sub p0 | SH_SRC | `ld hl,(SH_SRC)` |
| 21 | tenant writes result | [sub/strheap.asm:320](sub/strheap.asm:320) | she_snap_slice | sub p0 | SH_PTR | `ld (SH_PTR),hl` |
| 21 | tenant reads arg | [sub/strheap.asm:321](sub/strheap.asm:321) | she_snap_slice | sub p0 | SH_SRC | `ld bc,(SH_SRC)` |
| 21 | tenant writes result | [sub/strheap.asm:330](sub/strheap.asm:330) | sss_full | sub p0 | SH_ERR | `ld (SH_ERR),a` |
| all (writer of OP) | main writes arg | [basic/str-engine.asm:62](basic/str-engine.asm:62) | sh_call_op | main seg A | SH_OP | `ld (SH_OP),a` |
| dispatch | tenant reads op | [sub/strheap.asm:111](sub/strheap.asm:111) | strheap_engine | sub p0 | SH_OP | `ld a,(SH_OP)` |
