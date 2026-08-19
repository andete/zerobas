# D-ARYLV — an ARRAY ELEMENT is a legal lvalue target for `READ` and `INPUT`

**Status: SPEC. Nothing implemented. No byte has moved.**
Scout + measurement: [`arylv-msx1-scout.md`](arylv-msx1-scout.md) (18 rows × 3
sides, both references agreeing on all 18), on top of
[`readvar-msx1-characterization.md`](readvar-msx1-characterization.md) and
[`inputary-msx1-characterization.md`](inputary-msx1-characterization.md).
Predecessor slice: [`spec-basic-readvar.md`](spec-basic-readvar.md), whose §5.1
deferred exactly this face.

---

## 1. The rule

> A `READ` / `INPUT` / `LINE INPUT` target is **any variable reference** — the
> same thing `LET` accepts on its left-hand side. That includes an **array
> element** with a full subscript list: any rank, any expression per subscript,
> at any position in the variable list.

zerobas implements the name and the type suffix (D-READVAR) and stops at the `(`.
Both references take it. **18 measured rows say so** and 0 rows lack an oracle.

The rule is *not* new to this tree — `LET` and `SWAP` both implement it already
(scout §4). This slice removes an inconsistency between verbs; it does not add a
capability.

---

## 2. What is wrong, in one sentence per site

`var_name_key` ([`basic/vars.asm:102`](../basic/vars.asm)) walks a name and a type
suffix and **never a subscript**, and all four target-parse sites call it and then
store through a **key**:

| # | site | file | today | the store it needs |
|---|---|---|---|---|
| 1 | `exr_lp` (`READ`) | [`basic/program.asm`](../basic/program.asm) | page 1 | numeric **and** string, mode-selected |
| 2 | `inpc_vloop` (`INPUT`, numeric) | [`basic/input.asm:97`](../basic/input.asm) | low region | numeric |
| 3 | `inpc_vstr` (`INPUT`, string) | [`basic/input.asm:117`](../basic/input.asm) | low region | string |
| 4 | `inpc_line` (`LINE INPUT`) | [`basic/input.asm:187`](../basic/input.asm) | low region | string |

---

## 3. Scope — what is IN, what is OUT, and why

**IN:** the four sites above, i.e. `READ`, `INPUT` and `LINE INPUT` from the
console. 18 divergent rows (12 in the scout battery + the 6 already filed).

**OUT, and MEASURED to be correctly out:**

* 🔴 **`FOR`.** `FOR A(1)=1 TO 3` is `Syntax error` on **both references**
  (`f.ary`). `ex_for` must keep refusing it. `f.ary` is carried in this slice's
  gate as a **negative control** and as a pin for any later `FOR` work.

**OUT, and filed as separate residuals:**

* 🔴 **`ex_for`'s single-letter NAME shim.** `FOR AB=1 TO 3` and `FOR A%=1 TO 3`
  read ` 4 ` on both references and are `Syntax error` here (`f.two`, `f.pct`).
  That is D-READVAR's own defect, still live in `ex_for`, and it is a *name*
  problem, not an *array* one. Mixing it in would make one slice's knives unable
  to separate two rules ([[one-row-cannot-separate-two-rules]]).
* ⚠️ **Four more lvalue-shaped parse sites, UNMEASURED** — `INPUT #n`
  ([`basic/files.asm:702`](../basic/files.asm)), `FIELD` and `LSET`/`RSET`
  ([`basic/field.asm:194`/`283`](../basic/field.asm)), `MID$(…)=`
  ([`basic/str-engine.asm:957`](../basic/str-engine.asm), whose own header already
  says *"array lvalues deferred"*). They need a file/`FIELD` fixture rather than a
  bare boot. **The "four parse sites" in the filed item is the count of sites
  measured to diverge, not the count of sites that parse an lvalue**
  ([[a-hand-listed-denominator-is-a-scope-claim]]).

**OUT, and stated so it is not silently assumed in:** a coercion-time `Overflow`
in the store. `read_one_value` and `input_num_field` both yield an int16, so no
value reaching either store can overflow any target type. The absence of an
`FPERR` check after `var_store_fac` on `exr_lp`'s numeric arm is therefore
**unreachable, not a hole**, and this slice does not add one.

---

## 4. Design

### 4.1 Three helpers, in page 1

All three go in [`basic/vars.asm`](../basic/vars.asm) — **49 of 49 labels in page
1**, and already the home of `var_name_key`, `var_store_fac`, `str_set_key` and
`ex_let_arr`'s relocated error tails. Low-region code calling page 1 is already
what all three `INPUT` sites do today.

```
; tgt_parse — a variable REFERENCE: name, type suffix, optional (subscripts).
; in:  HL = cursor at the name's first letter (a letter, checked by the caller)
;      A  = mode, exactly var_str_type's own return: 0 numeric / 1 string
; out: Z  = ok, NZ = the array resolve failed (FPERR already mapped+set)
;      BC = key; HL past the whole reference
;      (TGT_ADDR) = element address, or 0 for a SCALAR target
tgt_parse:      push    af                  ; the mode must survive var_name_key
                call    var_name_key        ; BC=key, HL past name+suffix, (VARTYPE)
                ld      a,(hl)
                cp      '('
                jr      z,tp_ary
                pop     af
                ld      de,0                ; 0 = "this is a scalar; use the key"
                xor     a                   ; Z = ok
                jr      tp_set
tp_ary:         pop     af                  ; A = mode
                or      a
                jr      nz,tp_res           ; string -> type 1, already in A
                ld      a,(VARTYPE)         ; numeric -> the resolved type
tp_res:         call    ary_op0_resolve     ; Z: DE=elem addr, HL past ')'
                ret     nz                  ; NZ: FPERR set; caller aborts
tp_set:         ld      (TGT_ADDR),de
                ret
```

```
; tgt_store_num — in: BC = key, DE = int16 value.  Clobbers everything.
tgt_store_num:  ld      a,2
                ld      (FACTYP),a          ; DE is a plain int16 (F3 contract)
                ld      hl,(TGT_ADDR)
                ld      a,h
                or      l
                jr      nz,tsn_ary
                ld      a,(VARTYPE)
                jp      var_store_fac       ; scalar: var[key] := DE, coerced
tsn_ary:        ld      a,(ARY_TYPE)        ; ⚠️ NOT VARTYPE — see §5.2
                jp      ary_store_write     ; array: element := DE, coerced
```

```
; tgt_store_str — in: BC = key, STRSCR = [len][bytes].  Clobbers everything.
tgt_store_str:  call    strscr_desc         ; HL = RVDESC over STRSCR
                ld      de,(TGT_ADDR)
                ld      a,d
                or      e
                jr      nz,tss_ary
                ex      de,hl               ; DE = RVDESC
                jp      str_set_key         ; scalar: var$[key] = the bytes
tss_ary:        ld      (STRPTR),hl         ; array: ex_let_arr_str's own tail
                ld      (ARY_ADDR),de
                ld      a,3
                ld      (ARY_OP),a          ; op 3 = COPY_STR
                jp      ary_engine_call
```

🎯 **`var_str_type` ALREADY RETURNS THE MODE**, and all four sites already call it
before `var_name_key`. That is the same reuse that funded 17 of D-READVAR's 32
bytes, and it is why `tgt_parse` needs no mode argument of its own.

🎯 **The array arm of `tgt_store_str` is `ex_let_arr_str`'s shipped tail byte for
byte** (`call`+`pop hl` → `jp`). It is a copy, not an estimate.

### 4.2 The call sites

Each site keeps its own `skip_spaces` / `is_letter` / `var_str_type` head, its own
stack discipline and its own `?redo` / `?extra` behaviour. Three edits each:

1. `call var_name_key` → `call tgt_parse` (0 B),
2. `+ jp nz,fp_runtime_error` (+3 B) — **depth-independent**, see §5.3,
3. the store sequence → `call tgt_store_num` / `call tgt_store_str` (−8 / −4 B).

### 4.3 RAM

`TGT_ADDR` — 2 B at **`$E555`**, in the 5-byte gap between `RDV_MODE` (`$E554`)
and `GFX_DSCALE` (`$E55A`), inside the same one-statement-at-a-time aliasing
window `RDV_VAL`/`RDV_ST`/`RDV_MODE` already occupy (a `READ`/`INPUT` and a `DRAW`
are never in flight together). The slice adds
`IF TGT_ADDR + 2 > GFX_DSCALE` beside the two asserts already guarding that
window.

⚠️ **Reusing `ARY_ADDR` as the discriminator was considered and REJECTED**, and not
because it fails: nothing between the parse and the store calls the array engine
today, so it would work. It is rejected on **blast radius** — the failure mode is
a *scalar* store writing to a stale element address, i.e. silent memory
corruption rather than an error, and the property that prevents it is "no future
callee in this window ever touches the array engine", which nothing enforces. 2 B
of RAM buys that away.

---

## 5. Forced constraints — each one is a thing the design is NOT free to choose

### 5.1 🔴 NO `ary_snapshot_offset` / `ary_apply_offset` — and this is an argument, not an omission

`ex_let_arr` guards its resolved element address across the RHS `eval` with a
before/after `ARYTAB` delta (arrays §13a), because `eval` can allocate a scalar
(`VARPTR`) and shift the whole array region. **This slice needs none of it**, and
the reason is the callee list between the resolve and the store:

| site | what runs between resolve and store | allocates a variable? |
|---|---|---|
| `exr_lp` | `read_one_value` — `subrom_call` + RAM reads only | no |
| `inpc_vloop` | `read_into_strscr` (calls only `arl_getbyte`), `input_num_field` | no |
| `inpc_vstr` | `read_into_strscr` | no |
| `inpc_line` | `read_line`, `read_into_strscr` | no |

The subscripts' own `eval` runs **inside** `ary_parse_call`, i.e. *before* the
address is produced, exactly as it does for `ex_let_arr`. A string store may GC,
but the source descriptor points into `STRSCR`, a fixed buffer, never the heap.

⚠️ **If a future change puts an allocator on any of those four paths, this
constraint breaks silently** — the symptom is a write to a stale address, not an
error. It is written here so the next reader of those paths meets it.

### 5.2 🔴 The array store reads `ARY_TYPE`, never `VARTYPE`

Resolving `A%(I)` evaluates the subscript, which re-runs `var_name_key` for `I`
and **overwrites `(VARTYPE)` with `I`'s type**. `ary_parse_call` latches the
target's own type in `ARY_TYPE` for exactly this reason. With an untyped `A(I)`
both cells hold the DEFtbl double and the substitution is invisible — which is why
`r.arypct` exists (scout §2.6) and why K-AL4 is a knife at all.

### 5.3 The resolve failure aborts through `fp_runtime_error`, not `stmt_error`

`ary_op0_resolve` returns NZ with `FPERR` already mapped from `ARY_ERR`, so
`fp_runtime_error` yields the reference's own wording — `Subscript out of range`
for `r.aryoor`/`i.aryoor`, which `SWAP` already produces for `SWAP A,Q(9)`.
Routing to `stmt_error` would answer `Syntax error`, i.e. **exactly what the tree
says today**, and the row would read as untouched rather than as wrong.

The abort is safe from the `INPUT` sites even with `[varstart]` live on the stack:
`fre_abort_low` does `ld sp,(SAVSTK)` as its own first act (landed `4d35b6d`), so
raising is depth-independent ([[abort-chain-returns-into-caller]]).

### 5.4 The shared code lives in page 1 because three of the four sites cannot afford it

`basic/input.asm` is the **low region, 3 B free**. `basic/program.asm` is page 1,
126 B free. Low → page 1 calls are already what `inpc_vloop` does for
`var_name_key`. Putting the helpers in page 1 makes all three low-region sites
*shrink* (scout §5.4): the low region ends at ≈10 B free, up from 3.

---

## 6. Cost

**+77 B main page 1 (126 → ≈49 free), −7 B main low region (3 → ≈10 free), +2 B
RAM.** Full table, per helper and per site, in
[`arylv-msx1-scout.md`](arylv-msx1-scout.md) §5.4.

⚠️ **A BOUND, not a measured cost.** Every figure is a hand count; the counter was
first calibrated against **313 B of the very routines this change edits or
copies, 8/8 exact** (scout §5.2), and every new part is anchored to a named
shipped twin. The real number comes from a build
([[filed-justification-is-a-claim]]).

✅ **GO — one slice, no carve.** Reservoir if that turns out wrong:
`basic/program.asm` 2407 B leaves page 1, `basic/vars.asm` 617 B.

---

## 7. Predicted GREEN — the reference column IS the prediction

After the fix, `make arylv-characterize` must read, on all three sides:

| row | prediction | row | prediction |
|---|---|---|---|
| `c.read` | ` 7 ` | `r.mixrev` | ` 7  8 ` |
| `c.let` | ` 7 ` | `i.aryvar` | ` 7 ` |
| `c.for` | ` 4 ` | `i.ary2d` | ` 7 ` |
| `r.aryvar` | ` 7 ` | `i.aryoor` | `Subscript out of range` |
| `r.aryexpr` | ` 7 ` | `i.mix` | ` 7  8 ` |
| `r.arypct` | ` 7 ` | **`f.ary`** | **`Syntax error`** 🔴 negative control |
| `r.arystrv` | `HI` | `f.two` | ` 4 ` — **DEFERRED**, stays red |
| `r.ary2d` | ` 7 ` | `f.pct` | ` 4 ` — **DEFERRED**, stays red |
| `r.aryoor` | `Subscript out of range` | | |
| `r.mix` | ` 7  8 ` | | |

⇒ **`make arylv-acceptance` scores 16/16, with 2 rows printed and DEFERRED** —
the `....` mechanism D-READVAR shipped, excluded from the tally in both
directions. `f.two`/`f.pct` belong to the `ex_for` name residual (§3), not here.

And the six rows already filed must go green in their own gates:
`readvar-acceptance` **24/24, 0 deferred** (up from 22/22 + 2), and
`inputary-characterize` **7/7** (at which point it can be promoted to
`inputary-acceptance`, which §"deliberately not an acceptance gate" currently
forbids because 4 of its rows can only be red).

⚠️ **Predicting 16/16 from a row COUNT is the mistake D-READVAR §10.3 records** —
it predicted 24/24 where its own §9 had already scoped the slice to 22. The 16
above is the SCOPE (§3), arrived at by subtracting the two named deferrals, not
by counting rows in the file.

---

## 8. Knives — each has a RED set and a GREEN set

Runner discipline is **not** restated here: read `docs/dev-workflow.md`
§"Knives" before writing one. `probe_report.parse()` ships — do not hand-roll a
row parser, and never diff report LINES. Restore in a `finally`, `rm -rf build` +
full rebuild before every run, and **assert all four ROM hashes moved after every
cut build** ([[knife-runner-needs-a-rom-hash-guard]]).

Subject = the probe invoked directly (`--sides zb`), never `make`.

⚠️ **K-AL7's shape is already verified, so the runner does not have to discover
it.** The exit-2 branch was exercised before this spec was written (scout §6.1):
it exits **2**, prints a **complete** report in the one grammar, and
`probe_report.parse()` reads it. One property to expect: **the failed control is
printed TWICE** — once as its `FAIL` row and again in the `....` not-scored block
— so a runner keying rows by label gets a collision on that one label. It is
benign (both rows read the same `results[side][control]`, so the two entries can
never disagree) and it is **pre-existing and shared** by
`basic_probe_readvar.py` and `basic_probe_inputary.py`, not new here. Expect it;
do not treat it as a truncated or doubled report.

| # | cut (byte-neutral unless noted) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-AL1** | `tgt_parse`: `cp '('` → `cp $01` | all 12 array rows + the 6 filed rows | `c.read`, `c.let`, `c.for`, `f.ary` — *and `f.ary` staying green is the point*: the fix must not have touched `FOR` |
| **K-AL2** | `tgt_store_num`: `jr nz,tsn_ary` → `jr z,tsn_ary` | every NUMERIC row, scalar and array — **including the positive control `c.read`** | every string row; `f.*` |
| **K-AL3** | `exr_lp`'s new `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`r.aryoor` ONLY** | 17 rows, **including `i.aryoor`** — which is what proves the cut is site-local rather than class-wide |
| **K-AL4** | `tgt_store_num`: `ld a,(ARY_TYPE)` → `ld a,(VARTYPE)` | 🎯 **`r.arypct` ONLY** | every other array row, because their arrays and their subscript variable are all the DEFtbl double (§5.2) |
| **K-AL5** | `tgt_parse`: `ld de,0` → `ld de,1` | every SCALAR row (`c.read` + `readvar-acceptance`'s 24) | every array row |
| **K-AL6** | `tgt_store_str`: `ld a,3` → `ld a,0` (op RESOLVE, not COPY_STR) | `r.arystrv` + filed `a.arystr`, `i.arystr`, `i.lineary` | every numeric row |
| **K-AL7** | delete `c.read`'s `DATA` line | exit **2**, 0 scored, `NOT MEASURED` | — (proves the probe fails closed) |

**K-AL3 and K-AL4 each redden exactly ONE row**, which is what a knife set has to
be able to do and what D-READVAR's own K-RV3 could not
([[rule-gated-structurally-has-no-knife]]).

🔴 **K-AL4's prediction is deliberately narrower than its class.** *"Substituting
`VARTYPE` for `ARY_TYPE` breaks numeric array stores"* is the class answer and it
is **wrong**: it breaks exactly the rows where the two cells differ, which is one.
The row that makes it observable was added *because* this knife was drafted
(scout §2.6). Predicting from the class rather than from the path is the
K-RV3b shape ([[a-count-is-predicted-by-reading-its-definition]]); this entry is
what it looks like to have learned it before the run instead of after.

---

## 9. Denominator

Scored by `arylv-acceptance`: **(subscript FORM: literal / variable / expression)
× (RANK: 1-D / 2-D) × (POSITION: list head / continuation) × (TYPE: DEFtbl double
/ `%` / `$`)**, plus the out-of-range row whose oracle is an **error**, plus the
three `FOR` rows that bound the class from outside. Six further rows come from
`readvar-acceptance` and `inputary-characterize`, including the unDIMmed row that
names the cause.

**Not covered, and named rather than implied:** the four unmeasured lvalue parse
sites of §3; a subscript that is itself an array element (`READ A(B(1))`); a
`CLEAR n`-constrained string pool during an array string store; and the `INPUT`
`?redo` path with an array target already resolved (structurally re-resolved on
re-read, but no row asks).

---

## 10. Residuals this scout FOUND and did not take

* 🔴 **`ex_for`'s single-letter name shim** — `f.two`, `f.pct`, measured. Filed.
* ⚠️ **`ex_let_arr_str` may swallow an OOM.** Its `call ary_engine_call` is
  followed by `pop hl` / `jp exec_stmt` with no `FPERR` check, under a comment
  reading *"always Z (op=3 cannot fail)"* — which `aeng_copy_str`'s own header
  ([`sub/arrays.asm`](../sub/arrays.asm)) contradicts in as many words: *"UNLIKE
  slice-3 … this now CAN fail"*, `ARY_ERR=4` on `heap_alloc` OOM, and `exec_stmt`
  clears `FPERR` at the next statement. So `A$(1)=<a big string>` under a tight
  `CLEAR` would print nothing and store nothing.
  ⚠️ **This is READ FROM THE SOURCE, NOT MEASURED — a claim, not a finding**
  ([[a-source-comment-about-the-emulator-is-a-claim]] applies to source comments
  about the tree's own code just as much). It needs one probe row before it is
  worth a byte.
* ⚠️ **Four unmeasured lvalue parse sites** (§3), each needing a file/`FIELD`
  fixture.

---

## 11. As-built

Implemented 2026-08-08 on `main`, based on `09fbe3b`.

### 11.1 What landed

| file | change |
|---|---|
| [`basic/vars.asm`](../basic/vars.asm) | the three new helpers — `tgt_parse`, `tgt_store_num`, `tgt_store_str` — exactly as §4.1 drafts them |
| [`basic/sysvars.inc`](../basic/sysvars.inc) | `TGT_ADDR` (`$E555`, 2 B) + the `IF TGT_ADDR + 2 > GFX_DSCALE` assert |
| [`basic/program.asm`](../basic/program.asm) `exr_lp` | `var_name_key` → `tgt_parse` + `jp nz,fp_runtime_error`; both stores → `tgt_store_num` / `tgt_store_str` |
| [`basic/input.asm`](../basic/input.asm) `inpc_vloop` / `inpc_vstr` / `inpc_line` | the same three edits per site |
| [`probes/basic/basic_probe_arylv.py`](../probes/basic/basic_probe_arylv.py) | the `DEFERRED` mechanism (`f.two`/`f.pct`) + `f.ary` labelled the NEGATIVE control |
| [`probes/basic/basic_probe_readvar.py`](../probes/basic/basic_probe_readvar.py) | `DEFERRED` is now **empty** — `a.ary`/`a.arystr` are scored |
| [`probes/basic/basic_probe_inputary.py`](../probes/basic/basic_probe_inputary.py) | promoted: it is a gate now, not a characterization |
| [`Makefile`](../Makefile) | `arylv-acceptance` and `inputary-acceptance`, both `.PHONY` |

### 11.2 The walls, measured from clean

`rm -rf build && make basic-reloc`:

| wall | at `09fbe3b` | §6 predicted | as built | |
|---|---|---|---|---|
| main low region | 3 B | ≈10 B | **10 B** | ✅ **7 B FREED** |
| **main page 1** | 126 B | ≈49 B | **49 B** | ✅ **+77 B used** |
| sub page 0 | 3769 B | unchanged | **3769 B** | ✅ |
| sub page 1 | 1483 B | unchanged | **1483 B** | ✅ |

🎯 **EVERY BYTE PREDICTION WAS EXACT — all twelve of them**, helper by helper and
site by site, off `build/basic-reloc.sym`:

| | scouted | as built |
|---|---|---|
| `tgt_parse` | 32 B | **32** (16+7+4+5) ✅ |
| `tgt_store_num` | 24 B | **24** (18+6) ✅ |
| `tgt_store_str` | 30 B | **30** (15+15) ✅ |
| `exr_lp` | 49 → 44 | **44** ✅ |
| `exr_str` | 11 → 7 | **7** ✅ |
| `inpc_vloop` | 45 → 40 | **40** ✅ |
| `inpc_vstr` | 22 → 21 | **21** ✅ |
| `inpc_line` | 53 → 52 | **52** ✅ |

⚠️ **This is not luck and it is not a reason to trust the next hand count.** The
instrument was calibrated against 313 B of these same routines *before* the
estimate was quoted (scout §5.2, 8/8 exact), and the three helper bodies were
written out in §4.1 as the assembly that was later assembled. A hand count of
code drafted to the instruction, checked against a counter proven on the
surrounding code, is a different object from a hand count of code imagined.

### 11.3 🔴 `sub.rom` MOVED WHILE ITS WALLS DID NOT, AND THE SPEC NEVER SAID EITHER WAY

| ROM | at `09fbe3b` | as built |
|---|---|---|
| `basic-reloc.rom` | `38d79ffd…` | **`7d78c4b6…`** |
| `sub.rom` | `33af21eb…` | **`de1ad5d0…`** |
| `disk.rom` | `2c630d3d…` | `2c630d3d…` (unmoved) |
| `zerobas-main-eu.rom` | `87afd9ea…` | **`85da929d…`** |

**No sub-side byte was written by this slice** — sub page 0 and page 1 are free
to the byte — and `sub.rom` still moved. `sub/basic-resident-abi.inc` is
generated from main's `.sym`, so shifting main page 1 rewrites the addresses the
sub ROM calls back through: same size, different bytes.

⚠️ **"The sub walls did not move, so `sub.rom` did not move" is a wrong
inference, and this slice is the row that shows it.** §7 predicted the gate
tallies and §6 the walls; **neither predicted the ROM hashes at all**, so this is
a gap in the prediction rather than a missed one — recorded as such. D-READVAR
§10.2 got the same answer from the other direction (it *did* move sub bytes, and
its conditional prediction held). The general rule is: a wall is a size, a hash
is an identity, and a relocation changes the second without the first.

### 11.4 The gates

| gate | before | after |
|---|---|---|
| `arylv-acceptance` | — (characterization, 4/18) | **16/16 agree, 2 deferred, 0 diverge** |
| `readvar-acceptance` | 22/22 + 2 deferred | **24/24, 0 deferred** |
| `inputary-acceptance` | — (3/7, gate refused) | **7/7**, promoted |

All 18 measured array-lvalue divergences are closed. `r.aryoor` / `i.aryoor`
answer **`Subscript out of range`**, the references' own wording, not
`Syntax error` — which §5.3 said was the failure mode with no observable
difference, and is why it was routed through `fp_runtime_error`.

🔴 **`f.ary` held at `Syntax error` on all three sides**, as the negative
control. `f.two` / `f.pct` are printed and DEFERRED, still divergent, still the
`ex_for` residual.

### 11.5 Knives — 7 cuts × 2 rounds, **14/14 rounds EXACT**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly (`--sides zb`); snapshot restore in a `finally`; `rm -rf build` + full
rebuild + repack before every run including each baseline; **ROM-hash guard per
knife** (6 cuts must move the ROMs, K-AL7 must not); rows parsed with
`probe_report.parse()`, compared as `{label → zb value}`, with a short-report
refusal.

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-AL1** | `cp '(' → cp $01` | 12 array rows | **12, exact** | ✅ ×2 |
| **K-AL2** | `jr nz,tsn_ary → jr z` | 10 numeric rows incl. the control `c.read` | **10, exact**, rc 2 | ✅ ×2 |
| **K-AL3** | `exr_lp`'s abort → 3 × `nop` | 🎯 **`r.aryoor` only** | **`r.aryoor` only** | ✅ ×2 |
| **K-AL4** | `ld a,(ARY_TYPE) → ld a,(VARTYPE)` | 🎯 **`r.arypct` only** | **`r.arypct` only** | ✅ ×2 |
| **K-AL5** | `ld de,0 → ld de,1` | 4 scalar-target rows incl. `c.read` | **4, exact**, rc 2 | ✅ ×2 |
| **K-AL6** | `ld a,3 → ld a,0` (op RESOLVE, not COPY_STR) | 🎯 **`r.arystrv` only** | **`r.arystrv` only** | ✅ ×2 |
| **K-AL7** | delete `c.read`'s `DATA` line | exit **2**, 0 scored | **rc 2**, ROMs correctly did **not** move | ✅ ×2 |

**Three cuts reddened exactly ONE row**, which is more than §8 demanded and more
than D-READVAR's set could produce.

🎯 **K-AL4 IS THE ONE THAT JUSTIFIES THE SCOUT'S LAST TWO ROWS.** Its *class*
prediction — "substituting `VARTYPE` for `ARY_TYPE` breaks numeric array stores"
— names seven rows. It broke **one**, exactly as §8 said it would, because
`r.arypct` is the only row where the two cells differ. On the row set that
existed before the knives were drafted it would have broken **none**, and the
gate would have shipped unable to tell the two cells apart (scout §2.6). The
knife did not merely falsify the fix; it had already fixed the denominator.

🟢 **The GREEN sets held in all 14 rounds** — no cut moved a row outside its
predicted set, so the rounds are exact on the whole 18-row report, not just on
the red half.

### 11.6 Corpus

See §11.7. ⚠️ `lnblank REPEAT` defaults to 1; write the loop in **bash**, not zsh,
so `make $t` word-splits.

### 11.7 The fix, as a program

Both columns are readings from the runs above — "before" is the scout's zerobas
column at `112f569`, "after" is this slice's `arylv-acceptance`.

```basic
10 DATA 7
20 DIM A(3)
30 I=1
40 READ A(I)
50 PRINT"[";A(1);"]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `[ 7 ]` |
| zerobas **before** | `Syntax error in 40` |
| zerobas **after** | `[ 7 ]` |

```basic
10 DIM A$(3)
20 LINE INPUT A$(1)
30 PRINT"[";A$(1);"]"
```
→ both references `[HI]`, zerobas **before** `Syntax error in 20`, **after**
`[HI]`.

And the row that is the point of having measured the ERROR face rather than
assumed it:

```basic
10 DATA 7
20 DIM A(3)
30 READ A(9)
```

| | screen after `RUN` |
|---|---|
| both references | `Subscript out of range in 30` |
| zerobas **before** | `Syntax error in 30` |
| zerobas **after** | `Subscript out of range in 30` |

A fix that answered `Syntax error` here would have printed **exactly what the
tree printed before it**, and the row would have read as untouched.
