# D-LVFIX — an ARRAY ELEMENT is a legal lvalue target for `MID$(…)=` and `INPUT #n`

**Status: SPEC. Nothing implemented. No byte has moved.**
Measurement: [`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md)
(10 rows, `make lvsites-characterize`), which found that **all four** of the
lvalue parse sites D-ARYLV never checked DO diverge on an array element.
Predecessor slice: [`spec-basic-arylv.md`](spec-basic-arylv.md), whose §3 named
these four as out-of-scope-and-unmeasured and whose three helpers this slice
re-uses. Its scout's pricing method — calibrate the hand-counter against the
`.sym` **before** quoting a number for code that does not exist — is repeated in
§6 ([`arylv-msx1-scout.md`](arylv-msx1-scout.md) §5.2).

🔴 **THIS SPEC COVERS FOUR SITES AND SHIPS TWO.** The carve scout (§6) prices all
four and **DECLINES `FIELD` and `LSET`/`RSET`** — not on bytes alone, but on a
design blocker the measurement could not see (§7). That half is filed as its own
slice with its own carve question. Splitting is the result, not a shortfall.

---

## 1. The rule

> A `MID$(<target>,n,m) = <expr>` target and an `INPUT #n` / `LINE INPUT #n`
> target are **any string variable reference** — the same thing `LET` accepts on
> its left-hand side, and the same thing D-ARYLV established for `READ` /
> `INPUT` / `LINE INPUT`. That includes an **array element** with a full
> subscript list: any rank, any expression per subscript, at any position in the
> variable list.

zerobas parses the name and the `$` suffix at both sites and stops at the `(`.
`MID$`'s own source header already conceded this in writing — *"array lvalues
deferred"* — so that half was known and merely unpriced.

⚠️ **The oracle is weaker on one of the two sites and this slice inherits that.**
The `MID$` rows need no disk and have **two** references agreeing. The `INPUT #n`
rows are Disk BASIC: a diskless Philips VG-8020 answers `Syntax error` to the
word and cannot express the question, so those rows rest on the **National
CF-3300 alone**. Carried forward, not quietly upgraded
([`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) §0).

---

## 2. What is wrong, in one sentence per site

`var_name_key` ([`basic/vars.asm`](../basic/vars.asm)) walks a name and a type
suffix and **never a subscript**. Both sites call it and then use the KEY:

| # | site | file | region | what it does with the key |
|---|---|---|---|---|
| 1 | `ex_mid_stmt` | [`basic/str-engine.asm:957`](../basic/str-engine.asm) | **LOW** | `str_get_key` → a **descriptor address**, stashed in `MIDS_DEST` across the whole arg parse |
| 2 | `inp_readvar` | [`basic/files.asm:702`](../basic/files.asm) | **page 1** | `strscr_desc` + `str_set_key` — a plain **store** |

🔴 **The regions are the opposite of the guess D-ARYLV's shape invites.**
`basic/str-engine.asm` has **0 of its 103 labels in page 1** — `ex_mid_stmt` is
the LOW-region site — and `basic/files.asm` has **104 of 104**. D-ARYLV's filed
bound was wrong for exactly this reason in the other direction
([[a-hand-listed-denominator-is-a-scope-claim]]); the check is cheap and it is
run in §6.1 for all three files before any byte is priced.

---

## 3. Scope

**IN:** `ex_mid_stmt` and `inp_readvar`. Six of this spec's rows are the two
filed divergences plus their denominator; `LINE INPUT #n` comes with
`inp_readvar` because it *is* the same site.

**OUT, DECLINED WITH NUMBERS, and filed as its own slice (§7):**

* 🔴 **`ex_field` (`FIELD`) and `lrset_common` (`LSET`/`RSET`).** They need a
  `FLD_TAB` identity change **and a third site nobody listed** — the FIELDed-read
  hook on the array path. ≈ **+80 B page 1** against the ~18 B this slice leaves,
  and `carve_scout --entries` says the obvious cluster is not evictable. Carried
  in this slice's gate as **DEFERRED rows**, printed and excluded from the tally
  in both directions (D-READVAR's `....` mechanism).

**OUT, and filed separately — do NOT fold in:**

* 🔴 **`LSET`/`RSET` on a NON-FIELDed variable** (`s.ctl`,
  [`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) §3).
  `lrset_notfld` is a deliberate `jp stmt_error` commented *"slice-1 limit"*.
  A different defect at the same site; mixing it in would leave one slice's
  knives unable to separate two rules ([[one-row-cannot-separate-two-rules]]).
* ⚠️ **Numeric `INPUT #n`.** `files.asm` rejects it with *"numeric INPUT# =
  Phase 3"* **before** any target parse, so `INPUT#1,A(1)` is red for a reason
  that has nothing to do with subscripts. This slice makes the STRING target
  accept a subscript; it does not open the numeric door, and no row here can
  measure one.
* ⚠️ **`ex_mid_stmt`'s stale source header.** *"stashed in MIDS_DEST (aliases
  NUMBUF, dead here)"* — `MIDS_DEST` was rehomed to `TMISMATCH + 1` by arrays
  slice-4a *precisely because* it could no longer alias `NUMBUF`
  ([`basic/sysvars.inc`](../basic/sysvars.inc)). Doc debt in a comment, not a
  defect; noted so the next reader of §4.2 is not misled about what survives the
  RHS `str_eval`.

---

## 4. Design

### 4.1 Two new helpers, in page 1

Both go in [`basic/vars.asm`](../basic/vars.asm), beside `tgt_parse` /
`tgt_store_num` / `tgt_store_str`, for the reason §5.4 of the predecessor spec
gives: the shared code has to be in page 1 because the LOW-region site cannot
afford it, and a low-region routine calling page 1 is what `ex_let_arr` already
does.

`inp_readvar` needs **no new helper at all** — `tgt_parse` + `tgt_store_str` are
already exactly its shape. The two helpers below exist entirely for `MID$`, whose
target is a **descriptor address held across an evaluation**, not a store.

```
; tgt_desc — the DESCRIPTOR ADDRESS of a target tgt_parse has just resolved,
; in the form that survives a mid-statement ARYTAB move (§5.1).
; in:  BC = key, (TGT_ADDR) = element address or 0 for a scalar
; out: HL = scalar: the STRTAB descriptor address, verbatim (uncorrectable, §5.2)
;           array : elem_addr - ARYTAB, an ARYTAB-RELATIVE OFFSET
tgt_desc:       ld      hl,(TGT_ADDR)
                ld      a,h
                or      l
                jp      z,str_get_key       ; scalar: today's behaviour, byte for byte
                ld      de,(ARYTAB)
                or      a
                sbc     hl,de               ; the §13a snapshot, folded into the value
                ret
```

```
; tgt_desc_fix — read back what tgt_desc stashed, corrected for any ARYTAB move
; that happened in between. in: (MIDS_DEST), (TGT_ADDR).  out: HL = the address.
tgt_desc_fix:   ld      hl,(MIDS_DEST)
                ld      de,(TGT_ADDR)
                ld      a,d
                or      e
                ret     z                   ; scalar: unchanged, §5.2
                ld      de,(ARYTAB)
                add     hl,de               ; offset + ARYTAB_now = §13a corrected
                ret
```

🎯 **The offset IS the snapshot.** `ex_let_arr` pushes a separate `[OFFSET]` word
(`ary_snapshot_offset`) because it must keep the raw address *and* a snapshot.
Here the stash cell already exists — `MIDS_DEST` — so storing the offset in it
instead of the address costs **no stack word, no error-tail pop, and no second
RAM cell**. That is why this comes to 32 B and not the ~55 B a faithful copy of
`ex_let_arr`'s frame would have cost.

🎯 **`tgt_parse` needs no change and no mode argument** — `var_str_type` already
returns the mode at both sites, and both already branch on it
(`or a` / `jp z,stmt_error`), which is the same reuse that funded D-READVAR's 17
bytes and D-ARYLV's whole head.

### 4.2 The call sites

**`inp_readvar`** ([`basic/files.asm`](../basic/files.asm)) — three edits, the
identical set D-ARYLV made at `inpc_vstr`:

1. `call var_name_key` → `call tgt_parse` (0 B)
2. `+ jp nz,fp_runtime_error` (+3 B) — depth-independent, §5.3
3. `call strscr_desc` / `ex de,hl` / `call str_set_key` → `call tgt_store_str`
   (**−4 B**)

The existing `push bc` / `pop bc` guard around `read_into_strscr` stays: the key
is still what the scalar arm stores through, and `(TGT_ADDR)` rides in RAM
across the read untouched.

**`ex_mid_stmt`** ([`basic/str-engine.asm`](../basic/str-engine.asm)) — three
edits, two of them byte-neutral:

1. `call var_name_key` → `call tgt_parse` (0 B)
2. `+ jp nz,fp_runtime_error` (+3 B)
3. `call str_get_key` → `call tgt_desc` (0 B), and at the tail
   `ld hl,(MIDS_DEST)` → `call tgt_desc_fix` (0 B)

### 4.3 RAM

**None.** `TGT_ADDR` (`$E555`, 2 B) is D-ARYLV's cell and is re-used as both the
element address and the scalar/array discriminator; `MIDS_DEST` is `MID$`'s own
existing 2-byte stash. No wall moves and no new assert is needed.

---

## 5. Forced constraints — each is a thing the design is NOT free to choose

### 5.1 🔴 `ex_mid_stmt` JOINS THE §13a CLASS THE MOMENT ITS TARGET CAN BE AN ARRAY ELEMENT

[`spec-basic-arrays-slice4b-scalar-reloc.md`](spec-basic-arrays-slice4b-scalar-reloc.md)
§13a is a landed HIGH-severity bug: *hold a relocatable (array-region) address
across an operation that can allocate a scalar*. Its site audit enumerated
**exactly two** vulnerable sites and **explicitly exempted this one**, in as many
words: *"`ex_mid_stmt` targets a **scalar** string in the fixed `STRTAB` pool …
so unaffected."*

**That exemption is a statement about the TARGET, and this slice changes the
target.** `MIDS_DEST` is captured before the arg parse and read after it, and
between them run `eval_pos_arg`, `eval_byte_arg` and the RHS `str_eval` — every
one of which can evaluate `VARPTR(<new var>)`, which §13a names as *the only*
eval-time scalar allocator, and which shifts the whole array region up by one
scalar entry.

So the ARYTAB-delta correction is **not** an optional hardening: without it this
slice ships a new instance of a bug the project has already paid for once, whose
symptom is a silent write to a neighbouring element rather than an error. §4.1
carries it, `m.arydrift` measures it, and **K-LV5 deletes exactly it** (§8) —
the one knife that would redden ZERO rows if that row had not been added.

⚠️ The correction is keyed on the `ARYTAB` delta *regardless of cause*, so a
heap GC or an auto-`DIM` inside the RHS is covered by the same arithmetic — an
auto-`DIM` appends above `ARYTAB` and moves nothing, and a string GC compacts
bodies, not the scalar chain.

### 5.2 🔴 THE SCALAR ARM IS LEFT EXACTLY AS IT IS, AND THAT IS A DECISION, NOT AN OVERSIGHT

`tgt_desc`'s scalar path is `jp z,str_get_key` — today's instruction, reached by
today's register contract, returning today's value. It is **not** corrected,
because the `ARYTAB` delta is the wrong correction for it: arrays all live above
`ARYTAB` and shift by exactly that delta, but a scalar-chain insert shifts only
the entries **above the insertion point**, by the same amount, and leaves the
ones below it alone. Applying the array correction uniformly would turn a
sometimes-stale scalar into an always-wrong one.

⚠️ **Whether the scalar arm is stale today is a live question this slice
MEASURES rather than assumes.** Arrays slice-4c unified string scalars into the
contiguous chain, which is after §13a's audit was written, so the audit's
premise (*"the fixed `STRTAB` pool"*) no longer describes the tree.
`m.ctldrift` is that row. If it comes back red on zerobas it is a **finding
about a pre-existing defect** — an ordinary divergence, scored, which scopes its
own arm — and it is filed, **not fixed here**
([[classify-a-control-failure-by-which-side-failed-it]], and the 2×2 discipline
the `LSET` site forced one document earlier).

### 5.3 The resolve failure aborts through `fp_runtime_error`, not `stmt_error`

`ary_op0_resolve` returns NZ with `FPERR` already mapped, so `fp_runtime_error`
yields the reference's own wording — `Subscript out of range` for `m.aryoor` /
`f.aryoor`. Routing to `stmt_error` would answer `Syntax error`, i.e. **exactly
what the tree prints today**, and both rows would read as untouched rather than
as wrong. The abort is depth-independent: `fre_abort_low` does
`ld sp,(SAVSTK)` as its own first act ([[abort-chain-returns-into-caller]]),
which is what makes it safe from `ex_mid_stmt` before its `[n]`/`[m]` frame
exists and from `inp_readvar` with the channel state live.

### 5.4 `(TGT_ADDR)` must survive `MID$`'s whole argument parse

`tgt_desc_fix` reads `(TGT_ADDR)` as the arm discriminator *after* the RHS is
evaluated, so nothing between may call `tgt_parse` again. Today nothing can:
`tgt_parse`'s six callers are all statement heads (`exr_lp`, `inpc_vloop`,
`inpc_vstr`, `inpc_line`, and this slice's two), and no statement head runs
inside an `eval`. ⚠️ **If a future expression-level caller of `tgt_parse` ever
appears, this breaks silently** — the symptom is a `MID$` writing to the wrong
place, not an error. Written here so the next reader of `tgt_parse` meets it.

### 5.5 `inp_readvar` needs no correction, for the reason D-ARYLV's §5.1 gives

Between its resolve and its store runs `read_into_strscr`, which calls only
`arl_getbyte` (`fat_io_getbyte`'s `DSKIO` or `cas_in_getbyte`) — sector I/O into
fixed buffers, no variable allocation. The store's own OOM is already caught:
`inp_readvar` runs `check_expr_errors` right after, which `ex_let_arr_str`
notably does not ([`spec-basic-arylv.md`](spec-basic-arylv.md) §10).

---

## 6. The carve scout

All spans off `build/basic-reloc.sym` from a clean `rm -rf build && make
basic-reloc` at `e797df6`; walls printed by that build (low **10 B**, page 1
**49 B**, sub p0 **3769 B**, sub p1 **1483 B**; `basic-reloc.rom 7d78c4b6…`,
`sub.rom de1ad5d0…`).

### 6.1 🔴 WHICH REGION EACH SITE LIVES IN — asked before anything is priced

`python3 tools/carve_scout.py build/basic-reloc.sym --files <f>`:

| file | labels in page 1 | region | site |
|---|---|---|---|
| `basic/str-engine.asm` | **0 of 103** | **LOW** | `ex_mid_stmt` `$2C04` |
| `basic/files.asm` | 104 of 104 | page 1 | `inp_readvar` `$6E4C` |
| `basic/field.asm` | 46 of 46 | page 1 | `ex_field` `$7221`, `lrset_common` `$72E3` |

**Page 1 is the binding wall at 49 B**, and three of the four sites sit in it.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source, checked against the `.sym`, **before** any number was
quoted for code that does not exist:

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `inp_readvar` | 48 | **48** | ✅ |
| `ex_mid_sel` | 53 | **53** | ✅ |
| `exf_item` | 64 | **64** | ✅ |
| `lrset_common` | 81 | **81** | ✅ |
| `fld_add` / `fadd_lp` / `fadd_free` | 4 / 20 / 31 | **4 / 20 / 31** | ✅ |
| `tgt_parse` (4 spans) | 16 / 7 / 4 / 5 | **16 / 7 / 4 / 5** | ✅ |
| `tgt_store_str` (2 spans) | 15 / 15 | **15 / 15** | ✅ |

**13/13 exact over 363 B**, and they are the routines this change edits or
copies. 🎯 It also caught a real counting error on the way: **`LD (nn),DE` is
4 bytes, not 3** (`ED 53 nn nn`) — `tp_set` is 5 B, and the first hand count said
4. Every `ld de,(ARYTAB)` in §4.1 is counted at 4 for that reason.

### 6.3 The cost — a BOUND, with the twin named for every part

New page-1 code in `basic/vars.asm`:

| helper | bytes | how it is counted |
|---|---|---|
| `tgt_desc` | **16** | 3+1+1+3+4+1+2+1; its scalar arm is `str_get_key`'s existing call, tail-jumped |
| `tgt_desc_fix` | **16** | 3+4+1+1+1+4+1+1 |
| | **32 B** | |

Per-site deltas (each replaced sequence `.sym`-checked in §6.2):

| site | region | today | after | Δ |
|---|---|---|---|---|
| `inp_readvar` string store (`strscr_desc`/`ex de,hl`/`str_set_key`) | p1 | 7 | 3 | **−4** |
| `inp_readvar` resolve abort | p1 | 0 | 3 | **+3** |
| `ex_mid_stmt` resolve abort | **low** | 0 | 3 | **+3** |
| `ex_mid_stmt` `str_get_key` → `tgt_desc` | low | 3 | 3 | 0 |
| `ex_mid_stmt` `ld hl,(MIDS_DEST)` → `tgt_desc_fix` | low | 3 | 3 | 0 |

| region | free now | Δ | free after |
|---|---|---|---|
| **main page 1** | 49 B | **+31 B used** | **≈18 B** |
| **main low region** | 10 B | **+3 B used** | **≈7 B** |
| RAM | — | **0** | — |

⚠️ **A BOUND, not a measured cost.** The instrument is calibrated (§6.2) and both
helper bodies are written out in §4.1 as the assembly that will be assembled, but
the real number comes from a build ([[filed-justification-is-a-claim]]).

### 6.4 ✅ VERDICT: **GO for two sites. DECLINE for two. No carve, and no carve is available for the half that is declined.**

---

## 7. 🔴 WHY `FIELD` AND `LSET` ARE A SEPARATE SLICE — a design blocker, then a price

The measurement says both diverge and both are the same *parse* shape. They are
not the same *fix*, and the reason is not bytes:

**1. The READ path is a third site, and nobody listed it.** `FLD_TAB` maps a
2-byte variable KEY to a (channel, offset, width) slice, and a fielded variable
behaves because `str_eval_one` ([`basic/strvar.asm:79`](../basic/strvar.asm))
calls `fld_lookup` **on the scalar path only**. `str_eval_arr`
([`basic/arrays.asm`](../basic/arrays.asm), **LOW region**) points `STRPTR`
straight at the element and never consults the table. So `s.fldary` —
`FIELD#1,10 AS A$(1)` / `LSET A$(1)="HI"` / `PRINT A$(1)` → `HI        ` —
**cannot read back** no matter what `FIELD` records. A fix that only taught the
two parse sites about subscripts would turn `d.ary` green *for the wrong reason*
(subscript parsed and discarded, so `A$(1)` and `A$(2)` collide in the table) and
leave `s.fldary` red.

**2. The table cannot identify an element.** An entry is 6 B keyed on the name;
an element needs a stable discriminator, and the natural one is the same
ARYTAB-relative offset §4.1 uses. That is `FLD_ENTSZ` 6 → 8, i.e. 128 B — but
`FLD_TAB` is `$EE64..$EEC3` and `GP_RECNO` sits at `$EEC4`
([`basic/sysvars.inc`](../basic/sysvars.inc)). So it costs either **`FLD_SLOTS`
16 → 12** (a user-visible capacity cut) or **+32 B of RAM** rehomed elsewhere.

**3. And then it does not fit.** Design sketch, **explicitly NOT a calibrated
hand count** — no such code was drafted, so this is a rough bound of a different
grade from §6.3: `ex_field` + `fld_add` aoff write ≈ +20, `lrset_common` +
`fld_find` aoff match ≈ +18, a shared aoff helper ≈ +14, the `str_eval_arr` read
hook ≈ +20 page 1 and ≈ +5 **LOW**, plus 2 × 3 B aborts ⇒ **≈ +80 B page 1,
≈ +5 B low**, against the ~18 B and ~7 B this slice leaves.

**4. And the obvious carve is not available.**
`carve_scout --entries ex_field,ex_lset,ex_rset,fld_add,fld_find` returns
**NOT page-0-evictable**: 313 absent-region callees reached through resident main
page 1 (the statement heads reach `stmt_error` → `raise_error` and `eval` → the
whole evaluator) and 7 absent-region DATA targets. `basic/field.asm` is 568 B and
`basic/files.asm` 1607 B if either file leaves page 1, but *as a page-0 tenant*
neither goes as it stands. **That slice needs its own carve scout**, which is
precisely the thing this document exists to avoid starting without.

---

## 8. Predicted GREEN — the reference column IS the prediction

After the fix, `make lvfix-characterize` must read, on every side that has an
oracle for the row:

| row | statement under test | refs | prediction |
|---|---|---|---|
| `m.ctl` | `MID$(A$,1,2)="XY"` | 2 | `XYLLO` 🟢 **control** |
| `m.ary` | `MID$(A$(1),1,2)="XY"` | 2 | `XYLLO` |
| `m.aryvar` | subscript is a variable | 2 | `XYLLO` |
| `m.aryexpr` | subscript is an expression | 2 | `XYLLO` |
| `m.ary2d` | `DIM A$(2,2)`, `A$(1,1)` | 2 | `XYLLO` |
| `m.aryoor` | `A$(9)` on `DIM A$(3)` | 2 | `Subscript out of range` |
| `m.ctldrift` | `MID$(A$,VARPTR(Q)*0+1,2)="XY"` | 2 | `XYLLO` — ⚠️ §5.2, may be a pre-existing RED |
| `m.arydrift` | the same, on `A$(1)` | 2 | `XYLLO` 🎯 the §13a row |
| `f.ctl` | `INPUT#1,A$` | 1 | `HI` 🟢 **control** |
| `f.ary` | `INPUT#1,A$(1)` | 1 | `HI` |
| `f.aryvar` | subscript is a variable | 1 | `HI` |
| `f.ary2d` | `DIM A$(2,2)` | 1 | `HI` |
| `f.aryoor` | `A$(9)` on `DIM A$(3)` | 1 | `Subscript out of range` |
| `f.arymix` | `INPUT#1,A$,B$(1)` — array at a CONTINUATION position | 1 | `HILO` |
| `f.linectl` | `LINE INPUT#1,A$` | 1 | `HI` 🟢 **control** |
| `f.lineary` | `LINE INPUT#1,A$(1)` — the shared-site twin | 1 | `HI` |
| **`d.ary`** | `FIELD#1,10 AS A$(1)` | 1 | **`OK` — DEFERRED, stays red** (§7) |
| **`s.fldary`** | FIELDed `LSET A$(1)="HI"` | 1 | **`HI        ` — DEFERRED, stays red** (§7) |

⇒ **`make lvfix-acceptance` scores 16/16, with 2 rows printed and DEFERRED.**

⚠️ **16 is the SCOPE (§3), not a row count.** D-READVAR §10.3 records predicting
a tally by counting rows in a file when its own scope section had already
excluded two ([[a-prediction-copied-into-the-result-column]]); the 16 above is
18 minus the two named `FIELD`/`LSET` deferrals.

⚠️ **`m.ctldrift` is a prediction about a path this slice does not touch.** If it
reads red it is scored red and filed (§5.2). The gate must be able to say so
without the run being called broken, and without disqualifying `m.arydrift`,
whose own arm is corrected.

And the two filed rows must go green in their own characterization:
`make lvsites-characterize` **6/10 agree** (up from 4/10) — `m.ary` and `f.ary`
close; `d.ary`, `s.ary`, `s.ctl`, `s.fldary` stay red and stay filed.

---

## 9. Knives — each has a RED set and a GREEN set

Runner discipline is **not** restated here: read
[`dev-workflow.md`](dev-workflow.md) §"Knives" before writing one.
`probe_report.parse()` ships — do not hand-roll a row parser, and never diff
report LINES. Restore in a `finally`, `rm -rf build` + full rebuild before every
run **including each baseline**, and **assert the four ROM hashes moved after
every cut build** ([[knife-runner-needs-a-rom-hash-guard]]). Subject = the probe
invoked directly (`--sides zb`), never `make`. Expect the exit-2 shape documented
in [`spec-basic-arylv.md`](spec-basic-arylv.md) §8: a complete report in the one
grammar, and **the failed control printed TWICE**.

| # | cut (byte-neutral) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-LV1** | `tgt_parse`: `cp '('` → `cp $01` | all 10 array rows, **both sites** | every scalar control; `d.ary`/`s.fldary` stay DEFERRED-red either way |
| **K-LV2** | `ex_mid_stmt`: `call tgt_desc` → `call str_get_key` | the 6 `m.ary*` rows | 🎯 **every `f.*` row** — which is what proves the two sites are independently wired |
| **K-LV3** | `ex_mid_stmt`'s new `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`m.aryoor` ONLY** | 15 rows, **including `f.aryoor`** — site-local, not class-wide |
| **K-LV4** | `inp_readvar`'s new `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`f.aryoor` ONLY** | 15 rows, **including `m.aryoor`** — the mirror of K-LV3 |
| **K-LV5** | **the §13a correction deleted**: both `ld de,(ARYTAB)` (4 B) → `ret` + 3 × `nop` | 🎯 **`m.arydrift` ONLY** | every other row, `m.ary` included — because with no allocation mid-statement the raw address is still right |
| **K-LV6** | `tgt_store_str`: `jr nz,tss_ary` → `jr z,tss_ary` | every `f.*` row, **the controls `f.ctl`/`f.linectl` included** | every `m.*` row |
| **K-LV7** | delete `f.ctl`'s `PRINT#1,"HI"` fixture line | exit **2**, 0 scored, `NOT MEASURED` | — (proves the probe fails closed) |

**K-LV3, K-LV4 and K-LV5 each redden exactly ONE row.**

🔴 **K-LV5 IS WHY `m.arydrift` AND `m.ctldrift` EXIST.** The knives were drafted
**before** the row set was frozen ([[draft-the-knives-before-freezing-the-row-set]]),
and asking *"which row moves?"* of the §13a correction answered **none**: every
other row runs a statement that allocates nothing, so the uncorrected address is
still correct and the cut is invisible. A cut with no row is a missing row, not a
bad cut — so the row was added, and with it the scalar twin that scopes it. This
is D-ARYLV's K-AL4 lesson arriving *before* the run instead of after.

⚠️ **K-LV1's class is wider than this probe.** `tgt_parse` is shared with
D-ARYLV's four sites, so the cut also reddens `arylv-acceptance` and
`readvar-acceptance`. The prediction above is scoped to **this probe's rows**,
which is the subject; the wider blast is expected and is not scored here.

---

## 10. Denominator

Scored by `lvfix-acceptance`: **(subscript FORM: literal / variable /
expression) × (RANK: 1-D / 2-D) × (POSITION: list head / continuation) ×
(VERB: `MID$=` / `INPUT #n` / `LINE INPUT #n`)**, plus the out-of-range row at
**each** site whose oracle is an *error*, plus the mid-statement-allocation pair
that §5.1 forces, plus the two `FIELD`/`LSET` rows carried as DEFERRED so the
declined half stays visible in a gate rather than only in a document.

**Not covered, and named rather than implied:** the `FIELD`/`LSET` site pair
(§7); `RSET`, which shares `lrset_common` and is therefore not separately
measurable even after that slice; numeric `INPUT #n` (§3); a subscript that is
itself an array element (`MID$(A$(B(1)),1,2)=`); `MID$`'s `m` argument
interacting with an array target (the tenant `sh_mid_store` reads a descriptor
address and cannot tell the two arms apart, so no row asks); and the
`CLEAR n`-constrained string pool during an array-element `INPUT #n` store.

---

## 11. As-built

Implemented 2026-08-08 on `main`, based on `e797df6`.

### 11.1 What landed

| file | change |
|---|---|
| [`basic/vars.asm`](../basic/vars.asm) | `tgt_desc` + `tgt_desc_fix`, exactly as §4.1 drafts them; `tgt_store_str`'s header widened to FIVE store paths |
| [`basic/str-engine.asm`](../basic/str-engine.asm) `ex_mid_stmt` | `var_name_key` → `tgt_parse` + abort; `str_get_key` → `tgt_desc`; `ld hl,(MIDS_DEST)` → `tgt_desc_fix`; the stale *"aliases NUMBUF"* header corrected |
| [`basic/files.asm`](../basic/files.asm) `inp_readvar` | the same three edits D-ARYLV made at `inpc_vstr` |
| [`probes/basic/basic_probe_lvfix.py`](../probes/basic/basic_probe_lvfix.py) | new, 20 rows, 3 positive controls, 6 DEFERRED |
| [`Makefile`](../Makefile) | `lvfix-characterize` + `lvfix-acceptance`, both `.PHONY` |

### 11.2 The walls, measured from clean — **all six byte predictions exact**

`rm -rf build && make basic-reloc`:

| wall | at `e797df6` | §6.3 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 49 B | ≈18 B | **18 B** | ✅ **+31 B used** |
| main low region | 10 B | ≈7 B | **7 B** | ✅ **+3 B used** |
| sub page 0 / page 1 | 3769 / 1483 | unchanged | **3769 / 1483** | ✅ |
| RAM | — | 0 | **0** | ✅ |

| | scouted | as built |
|---|---|---|
| `tgt_desc` | 16 B | **16** ✅ |
| `tgt_desc_fix` | 16 B | **16** ✅ |
| `inp_readvar` | 48 → 47 | **47** ✅ |
| `ex_mid_sel` | 53 → 56 | **56** ✅ |

⚠️ Same caveat D-ARYLV's §11.2 records: this is not luck and not a reason to
trust the next hand count. The counter was calibrated on 363 B of these same
routines first (§6.2, 13/13), **and the calibration caught a real error** —
`LD (nn),DE` is 4 bytes, not 3.

### 11.3 The ROM hashes

| ROM | at `e797df6` | as built |
|---|---|---|
| `basic-reloc.rom` | `7d78c4b6…` | **`96c7ec8a…`** |
| `sub.rom` | `de1ad5d0…` | **`20b14735…`** |
| `disk.rom` | `2c630d3d…` | `2c630d3d…` (unmoved) |
| `zerobas-main-eu.rom` | `85da929d…` | **`dfeea0a6…`** |

No sub-side byte was written and both sub walls held to the byte; `sub.rom` moved
anyway, because `sub/basic-resident-abi.inc` is generated from main's `.sym`.
That is D-ARYLV §11.3's lesson, and this slice applied it **to the knife runner's
hash guard but not to its own prediction** — §6 predicted the walls and §8 the
gate tally, and neither predicted these four hashes. Recorded as a gap, not a hit
([[a-wall-is-a-size-a-hash-is-an-identity]]).

### 11.4 The gates

| gate | before | after |
|---|---|---|
| `lvfix-acceptance` | — (new) | **14/14 agree, 6 deferred, 0 diverge** |
| `lvsites-characterize` | 4/10 | **6/10** — `m.ary` and `f.ary` closed |

Static counters, predicted from each check's own definition and then measured:

| gate | before | predicted | measured |
|---|---|---|---|
| `audit-citations` swept / basic | 741 / 191 | 743 / 192 | **743 / 192** ✅ |
| `injector-check` | 339 | 340 | **340** ✅ |
| `rowshape-check` | 180/33/9/9/0 | 181/34/10/10/0 | **181/34/10/10/0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **unchanged** ✅ |

### 11.5 🔴 THREE OF §8's PREDICTIONS WERE WRONG, AND EACH ONE COST A ROW OR NAMED A RESIDUAL

**(a) `f.arymix` was predicted GREEN. It reads `Syntax error` — and so does its
scalar twin.** `inp_readvar` has **no variable-LIST loop at all**: it parses ONE
target and falls into `jp exec_stmt`, so the leftover `,` is what errors. The
first draft of the probe had only the array half, which would have scored a LIST
defect as an array failure and blamed this slice for a gap it does not own. The
fix was a row — `f.mixctl` (`INPUT#1,A$,B$`, no subscript anywhere), `HILO` on
the CF-3300 and `Syntax error` here — and both are now DEFERRED and filed
([[row-with-two-candidate-causes]]). ⚠️ **POSITION is therefore NOT covered for
`INPUT #n`**, named in §10 rather than implied.

**(b) `m.ctldrift` / `m.arydrift` were predicted GREEN. BOTH REFERENCES ANSWER
`Illegal function call`** — and isolating it away from `MID$` entirely
(`X=VARPTR(Q)` with `Q` unset) shows why: **`VARPTR` of an unset variable is IFC
on the VG-8020 and `OK` here.** A separate, pre-existing domain divergence, filed.

🎯 **The consequence is larger than these two rows.** Arrays §13a names `VARPTR`
as *the only* eval-time scalar allocator — so on the **reference** the entire
§13a corruption class is not expressible, and it exists in this tree only because
zerobas's `VARPTR` accepts a domain the reference rejects. The correction §5.1
forces is therefore **right and reachable** (a zerobas program reaches it today,
and K-LV5 proves it) but **not oracle-able**: no program both references accept
can shift `ARYTAB` mid-statement. The rows stay, printed and DEFERRED, because
they are still the live detector for K-LV5
([[a-pinned-divergence-is-a-live-detector]]).

**(c) The gate tally.** §8 predicted 16/16. Measured **14/14 with 6 deferred** —
(a) moved two rows out of the tally and (b) two more, and `f.aryoortrap` added
one back. The number was right about the *scope* and wrong about which rows had
an oracle, which is the half a row count cannot predict.

### 11.6 Knives — 7 cuts × 2 rounds, **5 exact, 2 PREDICTED-RED MISSES**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly; snapshot restore in a `finally`; `rm -rf build` + full rebuild + repack
before every run including each baseline; ROM-hash guard per cut; rows via
`probe_report.parse()` compared as `{label → zb value}`, with a short-report
refusal. **Both rounds were identical on all seven cuts** — no flakiness.

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-LV1** | `tgt_parse`: `cp '(' → cp $01` | every array row, both sites | **12 = exactly the array set** | ✅ ×2 |
| **K-LV2** | `tgt_desc`: `jp z,str_get_key → jp str_get_key` | the MID$ array rows reaching `tgt_desc` | **5, exact** — `m.aryoor` correctly GREEN (it aborts earlier), every `f.*` GREEN | ✅ ×2 |
| **K-LV3** | `ex_mid_stmt`'s abort → 3 × `nop` | 🎯 `m.aryoor` only | 🔴 **NOTHING** — see below | ❌ ×2 |
| **K-LV4** | `inp_readvar`'s abort → 3 × `nop` | 🎯 `f.aryoor` / `f.aryoortrap` only | 🔴 **NOTHING** — see below | ❌ ×2 |
| **K-LV5** | the §13a correction deleted (both `ld de,(ARYTAB)` → `ret`+3 × `nop`) | 🎯 **`m.arydrift` ONLY** | **`m.arydrift` only** | ✅ ×2 |
| **K-LV6** | `tgt_store_str`: `jr nz,tss_ary → jr z` | every `f.*` row incl. its controls | **6, exact** | ✅ ×2 |
| **K-LV7** | a positive control's `CONTROL_WANT` made unmatchable | exit **2**, 0 scored | **rc 2**, ROMs correctly did **not** move | ✅ ×2 |

🎯 **K-LV5 IS THE ONE THAT JUSTIFIES ITS ROW.** Asking *"which row moves?"* of the
§13a correction, **before** the row set was frozen, answered **none** — every
other row runs a statement that allocates nothing mid-statement, so the
uncorrected address is still right and the cut is invisible. The row was added
because the knife was written first, and it is the only row the cut moves
([[draft-the-knives-before-freezing-the-row-set]]).

🔴 **K-LV3 AND K-LV4 ARE HONEST MISSES, AND THE ROM-HASH GUARD IS WHAT MAKES THAT
CLAIM POSSIBLE** — both cuts moved all four ROMs, so this is *"reddened
nothing"*, not *"the cut never reached the artifact"*
([[knife-runner-needs-a-rom-hash-guard]]). The mechanism, traced rather than
guessed:

* **The message is produced on two paths.** `ary_op0_resolve` leaves `FPERR` set,
  and `ex_mid_stmt`'s very next act is `eval_pos_arg` → `get_byte_arg` →
  `get_int16_checked` → **`check_fperr_only`**, which raises it; `inp_readvar`'s
  `check_expr_errors` does the same after the store. So cutting the abort leaves
  `Subscript out of range` **identical**. [[rule-gated-structurally-has-no-knife]].
* **What the abort actually prevents is a store through an address the resolve
  never produced** — and `f.aryoortrap` was added specifically to make that
  observable, by trapping the error with `ON ERROR` and printing the scalar. **It
  missed too**, and the reason is worth more than the row: `ary_op0_resolve`
  clobbers `BC`, so the wild store does not target `A$` either — it lands
  somewhere no row looks. The row is still a legitimate green scored reading (a
  trapped out-of-range leaves the scalar untouched, matching the CF-3300) and it
  *does* move under K-LV1.

⇒ **The resolve-abort at these two sites is not falsifiable by any row in this
gate.** It is kept for uniformity with the five other `tgt_parse` callers — at
`exr_lp`, whose next act is *not* an `eval`, D-ARYLV's K-AL3 **did** redden a row
— and its 3 bytes at `ex_mid_stmt` are filed as a carve candidate rather than
quietly defended.

⚠️ **Two knives had to be re-sited, both my error, both worth recording:**

* **K-LV2 as drafted was refused by a gate it was not aimed at.** Swapping the
  *call site* `call tgt_desc` → `call str_get_key` orphans `tgt_desc`, and
  `check_dead_code.py` stops the build with `1 unreachable span: tgt_desc`. Cut
  the label's **body**, not its reference — exactly D-MOUNTROW's finding
  ([[a-knife-reddens-its-own-target-row]]), re-derived one runner later. The
  re-sited cut is sharper than the original: it separates the DESCRIPTOR path
  from the RESOLVE path, which is why `m.aryoor` stays green under it.
* **K-LV7 missed TWICE for two different scope errors of mine**, and neither was
  a tree result. First the runner invoked the subject as `--sides zb`, and the
  exit-2 branch fires only when a control fails on a **REFERENCE** — a zb-only
  run can never produce one. Then the cut targeted `f.ctl`'s expectation while
  the run was scoped `--only m.ctl,m.ary`, so the cut control never ran. **A
  probe-only knife has to be sited against the invocation the runner actually
  makes**, which is a third thing to check beyond "is the cut string unique" and
  "did the ROMs move".

### 11.7 Corpus

Sequentially from clean (`rm -rf build`, bash), **25 targets, all rc=0**:
`unit-test` 59 · `audit-citations` CLEAN · `preflight-check` · `injector-check`
340 · `rowshape-check` · `latch-check` 16/16 · `deadcode` 0 · `lnblank-acceptance
REPEAT=2` · `lnblank-say-acceptance` 204/204 · `logicops-acceptance` ·
`float-acceptance` · `linemax-acceptance` 60/60 · `dexp5-pin` 16 ·
`editverb-acceptance` 61/61 · `lptverb-acceptance` · `dskmsg-acceptance` ·
`diskbasic-acceptance` · `fat-error-acceptance` · `runtail-acceptance` ·
`castail-acceptance` · `cassave-acceptance` · `readvar-acceptance` ·
`arylv-acceptance` · `inputary-acceptance` · **`lvfix-acceptance` 14/14**.
Plus `lvsites-characterize` **6/10** (not a gate).

### 11.8 The fix, as a program

Both columns are readings from the runs above.

```basic
10 DIM A$(3)
20 A$(1)="HELLO"
30 MID$(A$(1),1,2)="XY"
40 PRINT"[";A$(1);"]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `[XYLLO]` |
| zerobas **before** | `Syntax error in 30` |
| zerobas **after** | `[XYLLO]` |

```basic
10 OPEN"LV.TXT"FOR OUTPUT AS #1
20 PRINT#1,"HI"
30 CLOSE#1
40 OPEN"LV.TXT"FOR INPUT AS #1
50 DIM A$(3)
60 LINE INPUT#1,A$(1)
70 CLOSE#1
80 PRINT"[";A$(1);"]"
```
→ CF-3300 `[HI]`, zerobas **before** `Syntax error in 60`, **after** `[HI]`.

And the row that is the point of having measured the ERROR face rather than
assumed it:

```basic
10 DIM A$(3)
20 MID$(A$(9),1,2)="XY"
```

| | screen after `RUN` |
|---|---|
| both references | `Subscript out of range in 20` |
| zerobas **before** | `Syntax error in 20` |
| zerobas **after** | `Subscript out of range in 20` |
