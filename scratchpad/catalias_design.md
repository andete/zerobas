# D-CATALIAS — design (Fable design pass, 2026-11-12)

Commissioned on Joost's ruling *"we need to be compatible, think harder (fable agent)"*:
`V$=V$+<computed>` must reach the VG-8020's string-space capacity exactly, with no
dangling pointer. A read-only design pass; nothing built yet. Line references are as of
commit fb2d8b37 and must be re-checked before building.

## 1. What the code does today
- `str_concat_tail` (basic/str-engine.asm:805) calls `str_alias_or_snap`
  (basic/program.asm:2754, page 1) BEFORE operand 2. A program-text literal gets a bodiless
  ALIAS slot `[len][ptr into text]` (D-CONCATLIT); everything else goes to
  `str_snapshot_arg` = `str_snapshot_keep` (str-engine.asm:689) -> op 16, which copies a
  VARIABLE's body (only a temp is kept as-is).
- The first `+` is op 2 (`sh_append`, sub/strheap.asm:1707): `sap_try_extend` grows R in
  place iff `R.ptr == FRETOP` (:1848); otherwise, and for every later `+` (op 22), the
  realloc path allocates `lenR+lenTk` while both are live, re-reading descriptors after the
  alloc (:1729-1750). `sap_release` pops Tk if it is the newest temp (:1770-1793).
- GC (strheap.asm:897-1010) sorts root descriptor addresses by ptr and moves each body ONCE;
  its header states the load-bearing premise, *root ptrs are DISTINCT* (:877-881), and
  `sh_temp_push_alloc` names the failure of a second root on one body: "phantom root ->
  double-move corruption" (:1619-1622). `sg_inrange`: a descriptor is a root iff `len>0 AND
  OLD_FRETOP <= ptr < CEIL` (:1378).
- The four users of "a temp uniquely owns a heap body": `she_snap_keep` (:345),
  `she_slice` (:433), `sh_var_store` adoption (:2661), `aeng_copy_str` adoption
  (sub/arrays.asm:330).
- Precedent for keeping a VARIABLE unsnapshotted across a sub-expression: op 21
  `she_snap_slice` (:372-411) keeps a scalar's descriptor as-is (its address is stable: new
  scalars insert at ARYTAB, basic/vars.asm:757-766) and gives an array element a bodiless
  OFFSET slot `[len][elem-ARYTAB]` (bit 15 clear, GC-skipped); its consumer `she_slice_ofs`
  (:530) allocates, re-finds the element via ARYTAB, copies, and the slot becomes the result.
- Stores refuse a pending fault: `ssk_go` (basic/main.asm:712) and the array LET's
  `fperr_test` (basic/arrays.asm:997) — a concat's error-path value is never stored.

## 2. Arithmetic (why 66 vs 100)
zerobas, computed op: V$ (N) + snapshot R (N) + op-2 temps (~3) + realloc N+2 -> 3N+5 <= 200
-> N <= 65 -> **66** (62 with a 12-byte Q$). Literal op: the snapshot extends in place ->
N + (N+2) -> **100**. Matches strspace_run5.out exactly.

Reference model (black-box): peak = old V$ + new result = 2N+2 (+ live strings). 2N+2 <= 200
-> 100; +12 -> 94; +40 -> 80. All six measured rows fit. FRE("") = LEN at the error says V$
is intact and nothing else survives. The model cannot tell whether the VG-8020 also frees
Tk before the alloc — at CLEAR 200 both variants give 100 / 94 / 80. Discriminating row in §5.

## 3. Routes rejected
- **(a) a new root kind holding `[len][ptr]` of V$'s body** — wherever it lives it is a
  SECOND root on V$'s body: double-move corruption (:877, :1619). Dead.
- **(b) relax unique ownership** — the same GC fact, before any of the four users is
  reached. Dead.
- **Hold the scalar descriptor ADDRESS in main with no slot** — GC-safe, but the result slot
  would be created AFTER Tk's, so `sap_release` could no longer pop Tk (D-TEMPPOL counts
  regress); needs a slot collapse. Inferior to (c).

## 4. Chosen: (c) an INDIRECT bodiless slot, pushed BEFORE operand 2
Generalise D-CONCATLIT + op 21. In `str_alias_or_snap`, after the text test:
- scalar (`STRPTR` in `[VARTAB,ARYTAB)`): push slot `[len][descriptor ADDRESS]`, return op
  **23**;
- array element (in `[ARYTAB,STREND)`): `call str_snapshot_slice` (op 21's offset slot,
  existing), return op **24**;
- else: `str_snapshot_arg` as today, op 2.

`sct_go` stores the returned op in `[op]` instead of the constant 2 (str-engine.asm:825).
Ops 23 / 24 in `she_table` (inside `IF CLEARPOOL`, :175-181) enter `sh_append` through a
resolve prologue: read the slot's ptr (op 24: `+ (ARYTAB)`, as `she_slice_ofs` :541-545),
stash the SLOT in blk+6 (free for op 2: `sh_go` pops BC, which `sct_loop` never reads,
str-engine.asm:75-90), put the RESOLVED descriptor in blk+4. `cp 2` (:1722) already routes
23 / 24 to the realloc path, so `sap_try_extend` never sees a variable body (that would
alias `W$=V$+"X"`). The final write (:1744-1749) goes to blk+6 = the slot, which thereby
becomes an owned temp holding the new body — exactly `she_slice_ofs`'s shape. The op 2 / 22
entry copies blk+4 -> blk+6 so the write is uniform. Peak: N + Tk + (N+2) — the reference's.

Why no pointer dangles: the slot's ptr is a descriptor address (below the stack, below the
pool floor) or an offset (< $8000) — outside `[OLD_FRETOP,CEIL)`, never a root; the real
root is the scalar / element itself (`sg_walk_scalars` / `_arrays`), fixed up normally and
re-read at op time. Scalar address stability: vars.asm:757; array offset stability: op 21's
argument (:385-391). DEF FN as operand 2 with V$ as its parameter: the slot holds the
argument during the body and the shadow holds V$ (`sg_walk_fnframe`), restored before op 23
reads it.

**The unresolved slot must never leave `str_concat_tail`.** Three exits: `sct_err2` (no op
ran), `sct_append_err` (an op failed, or `sh_go_g`'s D-DEEPEXPR skip never entered the
tenant — so the SUB cannot neutralise; main must), and success. Fix: move
`ld (hl),SH_OP_APPEND2` (:845) after the `jr nz` so `[op]` still reads 23 / 24 on the error
arm; both error arms then write `[0][0]` into R when `[op] >= 23`. A `[0][0]` is safe for every
consumer; the partial value changes from "a copy of V$" to "" only on paths where no store
happens (ssk_go / fperr_test). Without this, `X$=MID$(V$+Q$,2)` under OOM would have
`she_slice` move bytes INSIDE THE VARIABLE TABLE.

Invariants touched: (1) "a temp owns a heap body" gains a third bodiless kind, alive only
between `sct_go` and the first op — list it beside D-CONCATLIT / op 21 in `sh_src_is_temp`'s
header (:300); (2) `sap_try_extend`'s prose "that body is the operand-1 snapshot
str_concat_tail made" (:1806-1808) and docs/spec-concatpeak.md become FALSE for variable
operands — invert, don't delete; (3) D-CATFIX's "R (the partial result) as the value"
(:860-890) narrows; (4) `switch-build-check`: the new ops and the main arm under
`IF CLEARPOOL`, else `str_snapshot_to_temp`.

ROM: ~22 B page 1 (`str_alias_or_snap`), ~16 B low region (`sct_go` / error arms), ~30 B sub
page 0 (2 rows + prologue + blk+6 write). Variant: resolve in MAIN at op time (pass the
resolved DE, the slot BC) -> sub ~10 B, main +12 B. All three walls were tight at last
reading — run `make basic-reloc` from clean, never a number from memory; carve first. Note
vars.asm's offset is `ARYTAB-elem` (:792) while op 21's is `elem-ARYTAB` — opposite signs; do
not share them.

## 5. Verification
Rows (strspace_probe `--limit`, expected `[M 14 100 100]`, `94 94` x4, `80 80`): rh_noq rh_q12
hex_q12 cat_q12 rt_q12 grow_*. Add:
- **Discriminator** `CLEAR 201`, op `CHR$(65)`: Tk-live model -> 100, Tk-freed -> 101.
  Measure on the VG-8020 FIRST.
- GC during op 2: `CLEAR 200:V$=STRING$(60,"A"):W$=STRING$(60,"B"):W$="":V$=V$+STRING$(70,"C")`
  -> `LEN 130, LEFT$ "A", RIGHT$ "C"`.
- Aliasing: `W$=V$+"X":MID$(W$,1,1)="Z":PRINT LEFT$(V$,1)` (V$ unchanged); `V$+V$`,
  `V$+(V$+"A")`.
- Array: `DIM A$(2):A$(1)=STRING$(60,"A"):A$(1)=A$(1)+N$` with N$ NEW (an ARYTAB shift), and the
  GC-forcing variant.
- FN: `DEF FNA$(X$)=X$+"Z"`: `V$+FNA$("q")`, and with V$ as the parameter name.
- Error path: OOM inside `X$=MID$(V$+Q$,2)`, then PRINT another variable (the table intact);
  `ON ERROR` -> `LEN(V$)`, `LEFT$`, `RIGHT$` intact.
- spec-basic-strlong §5 rows `f.128 f.200 s.200`: predict they flip to ERR 15 (no copy before
  `sh_append`'s length test) — score it.

Knives (each must turn a row red): revert the scalar arm (-> 66); let 23 reach
`sap_try_extend` (the aliasing row); store `[len][bodyptr]` in the slot (the GC row); drop the
neutralise (the MID$-under-OOM row).

Suites: string, clearpool, concat3, catusr, catcopy, deepexpr, litref, stackpool, instr128,
strparen, prstrfn, switch-build-check; probes tempst_probe.py (slot counts unchanged: 1 R +
Tk), strtemp_probe.py, sliceoom_probe.py. Gate in a worktree.

## 6. Unsure / measure on the VG-8020 before building
1. Tk-live vs Tk-freed (the CLEAR 201 row). 2. V$'s CONTENT, not just LEN, after the error.
3. The VG-8020's figure for an ARRAY-element left operand and for `W$=V$+op` (the same
2N+2?). 4. Real wall figures. 5. Whether any operand-1 kind besides scalar / array / temp /
text reaches `str_alias_or_snap` (RVDESC / STRSCR / FIELD — all fall to the snapshot arm, so
they stay safe, merely uncarved).
