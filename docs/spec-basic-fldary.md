# D-FLDARY — an ARRAY ELEMENT is a legal `FIELD` / `LSET` / `RSET` target

*Slice D-FLDARY, 2026-08-08, on `main`, based on `8c284ad` (D-LVFIX).*

The last two of the four lvalue parse sites
[`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) measured.
D-LVFIX shipped `ex_mid_stmt` and `inp_readvar` and
**DECLINED this pair with numbers** ([`spec-basic-lvsites.md`](spec-basic-lvsites.md) §7)
on four grounds: a third site nobody had listed, a table that cannot identify an
element, ≈ +80 B of page 1 against ~18, and no available carve.

**This document re-prices the decline against a design, and three of the four
reasons do not survive it.** The third site is real and is carried; the table
change is **not** needed (§4.2); the price is **+38 B**, not ≈ +80; and a carve
**is** available and is measured (§6.4). Reason 3 is the one that survives — 38 B
does not fit 18 — so the slice is funded by a carve rather than by a decline.

⚠️ **ONE REFERENCE, NOT TWO.** `FIELD` and `LSET`/`RSET` are Disk BASIC. The
Philips VG-8020 has no disk controller, answers `Syntax error` to all three
words, and **cannot express the question** — recording its answer would
manufacture an agreement out of an absent disk drive. Every row here rests on
the National CF-3300 alone. That is weaker than anything D-ARYLV rested on, it
is not upgraded anywhere below, and the probes print `[ONE REFERENCE ONLY]` per
row.

---

## 1. The rule

**Wherever `FIELD`, `LSET` or `RSET` accepts a string variable as its target, an
array element of that variable is equally legal, and behaves as the same field.**

Measured, CF-3300:

| | statement | CF-3300 | zerobas at `8c284ad` |
|---|---|---|---|
| `d.ctl` | `FIELD#1,10 AS A$` | `OK` | `OK` 🟢 control |
| `d.ary` | `FIELD#1,10 AS A$(1)` | `OK` | **Syntax error** 🔴 |
| `s.fld` | `FIELD#1,10 AS A$` / `LSET A$="HI"` / `PRINT A$` | `HI␣␣␣␣␣␣␣␣` | `HI␣␣␣␣␣␣␣␣` 🟢 control |
| `s.fldary` | the same on `A$(1)` | `HI␣␣␣␣␣␣␣␣` | **Syntax error** 🔴 |

## 2. What is wrong, in one sentence per site

* **`ex_field`** ([`basic/field.asm:225`](../basic/field.asm)) — `call var_name_key`
  and then straight to `fld_add`. A `(` after the name is never peeked at, so the
  cursor stops on it, the following `cp ','` fails and the statement is
  `Syntax error`.
* **`lrset_common`** ([`basic/field.asm:365`](../basic/field.asm)) — the identical
  shape, one `fld_find` later. ⚠️ **`RSET` shares this body with `LSET`**, so it is
  ONE parse site and is **not separately measurable even after the fix** (§10).
* **`str_eval_arr`** ([`basic/arrays.asm:1028`](../basic/arrays.asm), **LOW region**)
  — the READ side, and **the site nobody had listed**. A fielded variable behaves
  only because `str_eval_one` ([`basic/strvar.asm:79`](../basic/strvar.asm)) calls
  `fld_lookup` **on the scalar path**; the array path points `STRPTR` straight at
  the element and never consults `FLD_TAB`.

🔴 **The third site is why the two parse sites are not the fix.** Teaching only
`ex_field` and `lrset_common` about subscripts turns `d.ary` green **for the
wrong reason** and leaves `s.fldary` red. §9's K-FA2 is the knife that says so.

## 3. Scope

**In:** the string-array-element form of all three verbs, at both parse sites and
at the read hook; the subscript FORMs (literal / variable / expression), RANK
(1-D / 2-D), the out-of-range error face at each parse site, and the coexistence
of a scalar field and an element field **in one `FIELD` statement**.

**Out, and named rather than implied:**

* **`RSET` as a distinct site** — shares `lrset_common` (§10).
* **`LSET`/`RSET` on a NON-FIELDed variable** (`lrset_notfld`, a deliberate
  `jp stmt_error` commented *"slice-1 limit"*). 🔴 **A separate filed residual and
  it must not be folded in here.** This slice reaches the LSET site through the
  **FIELDed** arm, whose control `s.fld` is GREEN on zerobas — which is exactly
  what makes the array row beside it real evidence about the subscript
  ([`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) §3).
* **`ERASE` of a fielded array** — §5.4, a new named limit with a price and no
  oracle.
* **`GET`/`PUT` of a record into an element field** — the record I/O is keyed on
  the channel, not on the variable, so it is unchanged by this slice; no row asks.

---

## 4. Design

### 4.1 One new page-1 pair, in `basic/field.asm`

```
; tgt_parse_fld — parse an lvalue target and reduce it to its FLD_TAB key.
; in:  HL = cursor at the name's first letter, A = var_str_type's mode (1).
; out: BC = the key; HL = cursor past the whole reference; the array resolve's
;      failure aborts through fp_runtime_error and does not return.
tgt_parse_fld:  call    tgt_parse           ; 3
                jp      nz,fp_runtime_error ; 3   §5.3
                ld      de,(TGT_ADDR)       ; 4
                ld      a,d                 ; 1
                or      e                   ; 1
                ret     z                   ; 1   scalar: BC is already the name key
                                            ;    = 13, falls through
; fld_key_de — DE = an element address -> BC = its FLD_TAB key. Preserves HL
; (the caller's text cursor); clobbers A, DE.
fld_key_de:     push    hl                  ; 1
                ex      de,hl               ; 1
                ld      de,(ARYTAB)         ; 4
                or      a                   ; 1
                sbc     hl,de               ; 2   ARYTAB-RELATIVE offset (§4.2)
                set     7,h                 ; 2   -> the disjoint half of the key space
                ld      b,h                 ; 1
                ld      c,l                 ; 1
                pop     hl                  ; 1
                ret                         ; 1   = 15
```

Both call sites become **byte-neutral**: `call var_name_key` → `call tgt_parse_fld`.
`A` already holds the mode at both (`call var_str_type` / `or a` / `jp z,…` leaves
it), which is the same reuse that funded D-READVAR's 17 bytes and D-ARYLV's head.

### 4.2 🎯 THE TABLE DOES NOT CHANGE, AND THAT IS THE WHOLE PRICE DIFFERENCE

D-LVFIX §7 reason 2 says an element needs a stable discriminator, that the
discriminator is the ARYTAB-relative offset, that this makes `FLD_ENTSZ` 6 → 8,
and that 16 × 8 = 128 B does not fit the 96 B hole below `GP_RECNO` — so it costs
**`FLD_SLOTS` 16 → 12** or **+32 B of RAM rehomed**.

**It costs neither, because the discriminator does not have to be stored
*beside* the name key — it can BE the key.** An entry is
`[chan:1][k0:1][k1:1][off:2][wid:1]` and `fld_find` matches on `(k0,k1)` alone.
So:

| entry for | k0 | k1 |
|---|---|---|
| a scalar `A$` | `'A'` (upcased letter) | `'B'` / digit / `0` |
| an element `A$(1)` | `(elem − ARYTAB) >> 8` **│ $80** | `(elem − ARYTAB) & $FF` |

**The two key spaces are disjoint by construction**, so one 6-byte table holds
both and every one of `fld_init`, `fld_clear_chan`, `fld_find`, `fld_add`,
`fld_lookup` and the page-0 tenant `sub/fldlook.asm` is **untouched**. No RAM
grows, `FLD_SLOTS` stays 16, `FLD_ENTSZ` stays 6, and neither the tenant ABI nor
[`basic/PROVENANCE.md`](../basic/PROVENANCE.md) §random-access records moves.

🔴 **THE DISJOINTNESS IS AN ASSERT, NOT A HOPE.** `var_name_key`'s `k0` is the
upcased FIRST character of a name whose `is_letter` every caller has already
checked, so `k0 ∈ $41..$5A`, always `< $80`. An element key's `k0` is `≥ $80` iff
the offset fits 15 bits — and the variable region is bounded by
`TXTBASE = $8001` below and `min(HIMEM,TXTMAX) = TXTMAX = $BB00` above
([`basic/sysvars.inc`](../basic/sysvars.inc)), i.e. **at most 15 103 B, a factor
of 2.17 inside the bound**. That is a fact about the memory map and not about
this code, so it is checked **at assembly time**, next to the `set 7,h` that
depends on it:

```
    IF (TXTMAX - TXTBASE) > $7FFF
                db      FLD_ELEMENT_KEY_BIT15_NOT_FREE__ARRAY_REGION_MAY_EXCEED_32K
    ENDIF
```

⚠️ **`set 7,h` is not falsifiable by any row, and this is stated rather than
defended.** Without it the spaces are *still* disjoint today, because
`offset >> 8 ≤ $3A < $41`; a colliding program needs an array-region offset of
at least `$4100` = 16 640 B, which the 15 103 B ceiling forbids. The two bytes buy
the margin from **1.1×** to **2.17×** and survive a memory-map change that the
bare `< $41` argument would not. Its knife is the ASSERT (K-FA7), not a row —
the same disposition D-LVFIX gave its unfalsifiable aborts, arrived at before the
run instead of after ([[rule-gated-structurally-has-no-knife]]).

### 4.3 The READ hook, and why it lands in page 1

`str_eval_arr` is in [`basic/arrays.asm`](../basic/arrays.asm), which
`carve_scout --files` reports as **0 of 46 labels in page 1** — the **LOW**
region, which has **7 B**. The hook itself therefore goes to page 1, beside
`str_eval_one`, and the low region pays one byte for the jump:

```
; basic/strvar.asm, sited between str_eval_no and str_eval_ok so the tail FALLS
; THROUGH (worth 3 B).
sea_fld:        ld      (STRPTR),de         ; 4   default: the element, verbatim
                call    fld_key_de          ; 3
                call    fld_lookup          ; 3   CF set -> STRPTR = the slice
                                            ;    = 10, falls into str_eval_ok
```

```
; basic/arrays.asm, LOW: the success arm leaves, the deferred-error arm keeps
; today's tail verbatim.
str_eval_arr:   ld      a,1                 ; 2
                call    ary_op0_resolve     ; 3
                jp      z,sea_fld           ; 3   was `jr z,sea_have_de` (2)
                ld      de,STR_EMPTY        ; 3
                ld      (STRPTR),de         ; 4   was the shared sea_have_de tail
                jp      str_eval_ok         ; 3
                                            ;    17 -> 18 = +1 B LOW
```

🎯 **`ld (STRPTR),de` FIRST is what makes the hook 10 B instead of 14.**
`fld_lookup` is `call fld_find` / `ret nc` — on a miss it touches nothing, so
publishing the element address before the lookup and letting a hit overwrite it
removes the whole not-found branch.

⚠️ The deferred-error arm (`STR_EMPTY`) deliberately does **not** consult the
table: `ary_op0_resolve` failed, there is no element, and a lookup keyed on a
garbage offset is exactly the wild read the arm exists to prevent.

### 4.4 RAM

**None.** `TGT_ADDR` is D-ARYLV's existing cell; `FLD_TAB` keeps its address, its
96 bytes, its 6-byte entry and its 16 slots.

---

## 5. Forced constraints — each is a thing the design is NOT free to choose

### 5.1 🔴 THE DISCRIMINATOR MUST BE ARYTAB-RELATIVE, NOT AN ADDRESS

A `FIELD` and the `LSET` that uses it are different statements, with arbitrary
program between them. Every scalar allocation in that gap moves the **whole**
array region up ([`spec-basic-arrays-slice4b-scalar-reloc.md`](spec-basic-arrays-slice4b-scalar-reloc.md)
§13a), so a stored absolute element address is stale by the time it is matched
and would alias a neighbouring element **silently**. `ARYTAB` moves by the same
delta, so the relative offset is invariant under it. It is likewise invariant
under a new `DIM` (arrays append above the region) and under a string-heap GC
(which compacts bodies, not element slots).

### 5.2 🔴 THE READ HOOK IS PART OF THE SLICE, NOT A FOLLOW-UP

Shipping the two parse sites alone would make `d.ary` read `OK` — and it would
be **the wrong `OK`**: without §4.2's element key the subscript is parsed and
discarded, so `A$(1)` and `A$(2)` write the same table entry; and without §4.3
nothing reads the field back, so `s.fldary` stays red. The gate encodes both
halves: `s.fldary2` (two elements, **different widths**) is the row that a
subscript-discarding fix fails, and K-FA2 is the knife that reddens the read
half alone.

### 5.3 The resolve failure aborts through `fp_runtime_error`, not `stmt_error`

`ary_op0_resolve` returns NZ with `FPERR` already mapped, so `fp_runtime_error`
yields the reference's own `Subscript out of range`. Routing to `stmt_error`
would print `Syntax error` — **exactly what the tree prints today** — and both
out-of-range rows would read as untouched rather than as fixed. The abort is
depth-independent: `fre_abort_low` does `ld sp,(SAVSTK)` as its own first act
([[abort-chain-returns-into-caller]]), which is what makes it safe at `ex_field`
with the field WIDTH still pushed.

🎯 **Unlike D-LVFIX's two aborts, this one IS falsifiable, and the reason is a
property of the site rather than a hope.** `exec_stmt`
([`basic/interp.asm:152`](../basic/interp.asm)) **CLEARS** `FPERR` at every
statement boundary; it does not check it. `ex_field`'s next acts after the abort
are `fld_add` and `jp exec_stmt`, with no `check_expr_errors` between — so with
the abort cut, `FIELD#1,10 AS A$(9)` writes a garbage entry and prints `OK`. That
is K-FA5, predicted to redden exactly the two out-of-range rows.

### 5.4 🔴 `ERASE` OF A FIELDED ARRAY IS A NEW NAMED LIMIT, WITH A PRICE AND NO ORACLE

`aeng_erase` ([`sub/arrays.asm:196`](../sub/arrays.asm)) **compacts** the
descriptor list, sliding every FOLLOWING array down. An element key above the
erased array is then stale, and the next `LSET A$(1)` writes into a different
variable's field. Today's scalar-keyed entries are immune (a name key does not
move), so this is a class this slice CREATES.

It is documented rather than fixed, and the alternative is priced so the choice
is visible: an `fld_clear_ary` sweep (clear every entry whose `k0 ≥ $80`) is
**20 B of page 1 plus 3 B of the LOW region** at `ex_erase`'s call — and, more to
the point, **it has no oracle**. Whether the CF-3300 drops, keeps or dangles a
field across `ERASE` is unmeasured, both candidate behaviours are guesses, and
this project does not spend 23 bytes to pick between two unmeasured answers
([[answer-signoff-questions-by-measuring]]). Filed as a residual with the row
that would settle it.

⚠️ The neighbouring, **pre-existing** version of this is left alone: a bare
program EDIT reaches `vars_reset` (which re-anchors `ARYTAB`) without reaching
`clear_vars` (which is what calls `fld_init`), so a field entry can already
outlive the variables it names. That is true of scalar entries today and is not
this slice's to change.

### 5.5 `lrset_common`'s FIELDed arm is the one this slice enters

`lrset_notfld` is reached when `fld_find` misses, and it is a bare `jp stmt_error`
commented *"slice-1 limit"*. An element target that was never `FIELD`ed lands
there and reads `Syntax error`, exactly as a never-FIELDed scalar does today.
That is the separate residual of §3, not a regression, and `s.ary` in
[`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) stays red
for it.

---

## 6. The carve scout

All spans off `build/basic-reloc.sym` from a clean `rm -rf build && make
basic-reloc` at `8c284ad`; walls printed by that build (low **7 B**, page 1
**18 B**, sub p0 **3769 B**, sub p1 **1483 B**; `basic-reloc.rom 96c7ec8a…`,
`sub.rom 20b14735…`).

### 6.1 Which region each file lives in — asked before anything is priced

`python3 tools/carve_scout.py build/basic-reloc.sym --files <f>`:

| file | labels in page 1 | region | what this slice does there |
|---|---|---|---|
| `basic/field.asm` | **46 of 46** | page 1 | both parse sites, the new pair, the carve |
| `basic/strvar.asm` | **14 of 14** | page 1 | `sea_fld` |
| `basic/arrays.asm` | **0 of 46** | **LOW** | `str_eval_arr`'s one byte |
| `basic/vars.asm` | 59 of 59 | page 1 | `tgt_parse`, unchanged |

**Page 1 binds at 18 B and three of the four touched files sit in it.**

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **before** any number was
quoted for code that does not exist
([[calibrate-a-hand-counter-before-quoting-it]]):

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `fld_find` / `fldf_lp` / `fldf_back` / `fldf_next` | 3 / 18 / 2 / 16 | **3 / 18 / 2 / 16** | ✅ |
| `fld_add` / `fadd_lp` / `fadd_free` | 4 / 20 / 31 | **4 / 20 / 31** | ✅ |
| `lrset_store` / `lrs_fill` / `lrs_filled` | 15 / 5 / 22 | **15 / 5 / 22** | ✅ |
| `lrs_ncopy` / `lrs_copy` / `lrs_cp` | 15 / 4 / 7 | **15 / 4 / 7** | ✅ |
| `exf_item` | 64 | **64** | ✅ |
| `lrset_common` | 81 | **81** | ✅ |
| `fld_lookup` | 22 | **22** | ✅ |
| `pu_deref_body` | 8 | **8** | ✅ |
| `str_eval_arr` (to `sea_have_de`) | 10 | **10** | ✅ |
| `tgt_parse` | 16 | **16** | ✅ |

**19/19 exact over 373 B**, and they are the routines this change edits, moves or
copies. Two counts had to be repaired on the way and both are the same lesson
D-LVFIX recorded: `LD (nn),DE` / `LD DE,(nn)` are **4 bytes** (`ED 53`/`ED 5B`)
while `LD (nn),HL` / `LD HL,(nn)` are **3** — `lrs_filled`'s `ld de,(STRPTR)` and
`lrset_common`'s `ld (LRSET_OFF),de` are both counted at 4 for that reason, and
§4.1 prefers `ld de,(TGT_ADDR)` at 4 only where the fall-through pays for itself.

### 6.3 The cost — a BOUND, with the twin named for every part

| item | file | region | bytes |
|---|---|---|---|
| `tgt_parse_fld` | field.asm | p1 | **13** |
| `fld_key_de` | field.asm | p1 | **15** |
| `sea_fld` | strvar.asm | p1 | **10** |
| `ex_field`: `call var_name_key` → `call tgt_parse_fld` | field.asm | p1 | **0** |
| `lrset_common`: the same swap | field.asm | p1 | **0** |
| **page-1 subtotal** | | | **+38** |
| `str_eval_arr`: `jr z` → `jp z` + an unshared tail | arrays.asm | **LOW** | **+1** |

**38 B against 18 B free: 20 B short.** So the slice needs a carve, and §7 of the
predecessor is right that far.

### 6.4 The carve: `lrset_store` → a page-0 sub-ROM tenant

D-LVFIX ran `carve_scout --entries ex_field,ex_lset,ex_rset,fld_add,fld_find` and
got **NOT page-0-evictable** (313 absent-region callees through resident main
page 1, 7 DATA targets) — the statement HEADS reach `stmt_error`/`eval` and drag
the interpreter behind them. That kills the cluster, **not the slice**: the
leaf-only re-run is clean.

```
carve_scout --entries fld_add,fld_find,fld_clear_chan,fld_init,lrset_store
  closure 19 labels; 1 absent-region callee (0 BIOS); 0 absent-region DATA
      BLOCKER   pu_deref_body @ $2884          (directly called, re-expressible)
  reached THROUGH resident main page-1 : 0     <- FATAL if > 0
  VERDICT: page-0-tenant CLEAN
```

Of that set **`lrset_store` alone is taken**, and it is the right one for three
measured reasons rather than because it is biggest:

1. **68 B, one contiguous span** (`$7357..$739B`), 6 labels, one caller.
2. 🎯 **ZERO register marshalling.** Every input is a RAM cell — `LRSET_OFF`,
   `LRSET_W`, `LRSET_JUST`, `STRPTR`, `FSECTOR_BUF` (`$E5C0`, page 3) — and it
   returns nothing. Unlike `fld_find` (CF + HL out, which collides with
   `subrom_call`'s own CF meaning *"sub-ROM absent"*) there is nothing to smuggle
   past the ABI, so the resident stub is the minimum 11 B shape and no cell is
   invented for it.
3. **Its one blocker is 8 bytes.** `pu_deref_body` is `push af / inc hl /
   ld a,(hl) / inc hl / ld h,(hl) / ld l,a / pop af / ret`; A is dead across the
   call site (`ld a,(LRSET_W)` reloads it two instructions later), so **5 B
   inlined sub-side** replaces the 3 B `call`. Exactly the disposition
   `sub/fldlook.asm` already gives `mk_rvdesc`.

**Cold enough:** one CALSLT per `LSET`/`RSET` statement, already downstream of
`fch_select`'s 512-byte LDIR pair. The same argument `fld_lookup`'s carve made.

| | bytes |
|---|---|
| `lrset_store` body removed from page 1 | **−68** |
| resident stub (`ld ix,…` 4 + `call subrom_call` 3 + `jp c,subrom_absent_error` 3 + `ret` 1) | **+11** |
| **net page 1** | **−57** |
| sub page 0 (68 − 3 `call` + 5 inline) | **+70** |

### 6.5 The bottom line

| region | free at `8c284ad` | slice | carve | free after |
|---|---|---|---|---|
| **main page 1** | 18 B | +38 | −57 | **≈ 37 B** |
| **main low** | 7 B | +1 | 0 | **≈ 6 B** |
| **sub page 0** | 3769 B | 0 | +70 | **≈ 3699 B** |
| sub page 1 | 1483 B | 0 | 0 | **1483 B** |
| RAM | — | 0 | 0 | — |

⚠️ **A BOUND, not a measured cost.** The instrument is calibrated (§6.2, 19/19)
and every body above is written out as the assembly that will be assembled, but
the real number comes from a build ([[filed-justification-is-a-claim]]).

⚠️ **Predicted ROM hashes**, because D-LVFIX predicted its walls and its gate
tally and forgot these ([[a-wall-is-a-size-a-hash-is-an-identity]]):
`basic-reloc.rom` **MOVES**, `sub.rom` **MOVES** (both because it gains a tenant
*and* because `sub/basic-resident-abi.inc` is generated from main's `.sym`),
`zerobas-main-eu.rom` **MOVES**, `disk.rom` **HOLDS at `2c630d3d…`** (no disk-side
byte is written).

### 6.6 ✅ VERDICT: **GO, funded by a named carve.** 38 B does not fit 18; `lrset_store` returns 57.

---

## 7. Predicted GREEN — the reference column IS the prediction

`make fldary-characterize` must read, on the CF-3300 and on zerobas alike:

| row | statement under test | prediction |
|---|---|---|
| `d.ctl` | `FIELD#1,10 AS A$` | `OK` 🟢 **control, FIELD arm** |
| `d.ary` | `FIELD#1,10 AS A$(1)` | `OK` |
| `d.aryvar` | subscript is a variable | `OK` |
| `d.ary2d` | `DIM A$(2,2)`, `A$(1,1)` | `OK` |
| `d.aryoor` | `A$(9)` on `DIM A$(3)` | `Subscript out of range` 🎯 K-FA5's row |
| `s.fld` | FIELDed scalar `LSET` | `HI␣␣␣␣␣␣␣␣` 🟢 **control, FIELDed-LSET arm** |
| `s.fldary` | FIELDed `LSET A$(1)="HI"` | `HI␣␣␣␣␣␣␣␣` |
| `s.fldaryvar` | subscript is a variable | `HI␣␣␣␣␣␣␣␣` |
| `s.fldary2d` | `DIM A$(2,2)` | `HI␣␣␣␣␣␣␣␣` |
| `s.fldary2` | `FIELD#1,4 AS A$(1),6 AS A$(2)`, read back `A$(2)` | `BB␣␣␣␣` 🎯 **the row a subscript-discarding fix fails** |
| `s.fldarymix` | `FIELD#1,4 AS A$,6 AS B$(1)`, read both | `XX␣␣│YY␣␣␣␣` 🎯 **the row the two key spaces must both survive** |
| `s.fldaryoor` | `LSET A$(9)` on `DIM A$(3)` | `Subscript out of range` |
| `r.fldary` | `RSET A$(1)="HI"` | `␣␣␣␣␣␣␣␣HI` — the shared-body twin |

⇒ **`make fldary-acceptance` scores 13/13**, every row `[ONE REFERENCE ONLY]`.

⚠️ **13 is the SCOPE, not a row count** — the number is what §3 leaves in, and
D-READVAR §10.3 records predicting a tally by counting rows in a file after the
scope section had already excluded some
([[a-prediction-copied-into-the-result-column]]).

⚠️ **A CONTROL PER ARM, NOT PER SITE.** `d.ctl` scopes the `d.*` rows and `s.fld`
scopes the `s.*`/`r.*` rows; a red `d.ctl` must never be allowed to explain away
an `s.*` reading. One control per site was the natural first draft at this very
verb and it would have disqualified a good row
([`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) §3).

⚠️ **Classify a control failure by WHICH SIDE failed it** — red on the CF-3300 =
the fixture is broken (exit 2, score nothing); red on zerobas = an ordinary
divergence, scored, which scopes its own arm
([[classify-a-control-failure-by-which-side-failed-it]]).

And the two carried rows must move in the gates they already live in:

* `make lvfix-acceptance` — `d.ary` and `s.fldary` **promoted out of DEFERRED**
  and scored, with `d.ctl`/`s.fld` added as their per-arm controls: **18/18 agree,
  4 deferred**.
* `make lvsites-characterize` — **8/10** (up from 6/10); `s.ctl`/`s.ary` stay red
  as the separate non-FIELDed residual.

Static counters, each predicted from its own check's definition:
`audit-citations` 743 → **745** swept (+1 probe, +1 document), basic 192 → **193**;
`injector-check` 340 → **341**; `rowshape-check` 181/34/10/10/0 →
**182/35/11/11/0**; `preflight-check` **unchanged**; sub-ROM closures 723+15 →
**724+15** page-0 tenants **13 → 14**.

---

## 8. Knives — drafted BEFORE the row set was frozen

Runner discipline is **not** restated here: read
[`dev-workflow.md`](dev-workflow.md) §"Knives" first. `probe_report.parse()`
ships — do not hand-roll a row parser and never diff report LINES. Restore in a
`finally`; `rm -rf build` + full rebuild + repack before every run **including
each baseline**; **assert the ROM hashes MOVED after every cut build** (a
probe-only cut must NOT move them); run every cut TWICE. Cut a label's **BODY**,
not its reference — orphaning it gets the build refused by `check_dead_code.py`,
a gate the knife was not aimed at. Site a probe-only knife against **the
invocation the runner actually makes**.

| # | cut (byte-neutral unless noted) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-FA1** | `fld_key_de`: `sbc hl,de` → `sbc hl,hl` (both `ED xx`) — every element keys to offset 0 | 🎯 **`s.fldary2` and `s.fldarymix` ONLY** | every single-element row, both controls, `d.*` all green |
| **K-FA2** | `sea_fld`: `call fld_lookup` → 3 × `nop` — the READ hook alone | every `s.*`/`r.*` **array** row | 🎯 **`d.ary` and every `d.*` row**, and `s.fld` — the scalar read path is untouched |
| **K-FA3** | `ex_field`: `call tgt_parse_fld` → `call var_name_key` | every `d.*` array row **and** every `s.*` array row (nothing was recorded to find) | `d.ctl`, `s.fld` |
| **K-FA4** | `lrset_common`: `call tgt_parse_fld` → `call var_name_key` | every `s.*`/`r.*` array row | 🎯 **`d.ary`/`d.aryvar`/`d.ary2d`** — the mirror of K-FA3, and what proves the two parse sites are independently wired |
| **K-FA5** | `tgt_parse_fld`: `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 **`d.aryoor` and `s.fldaryoor` ONLY** | the other 11 rows |
| **K-FA6** | the `lrset_store` stub: `3*SUBROM_IDX_LRSETST` → `3*SUBROM_IDX_PING` | every `s.*`/`r.*` row, **`s.fld` included** | every `d.*` row — proves the tenant IS the store |
| **K-FA7** | the §4.2 assert: `> $7FFF` → `> $0100` | **the BUILD is refused**, 0 rows scored | — (proves the assert is not vacuous) |
| **K-FA8** | delete `d.ctl`'s `OPEN` fixture line | exit **2**, 0 scored, `NOT MEASURED` | — (proves the probe fails closed) |

**K-FA1 and K-FA5 each redden exactly the rows that exist for them.**

🔴 **K-FA1 IS WHY `s.fldary2` AND `s.fldarymix` EXIST.** Asking *"which row
moves?"* of the element discriminator, before the row set was frozen, answered
**none**: with a single fielded element, a `FIELD` that stores the wrong key and
an `LSET` that looks up the same wrong key still agree with each other, so
`d.ary` and `s.fldary` are green under a completely broken discriminator. A cut
with no row is a missing row, not a bad cut
([[draft-the-knives-before-freezing-the-row-set]]) — so **two** rows were added:
one where two elements must stay apart, and one where an element and a scalar
must stay apart.

⚠️ **K-FA3/K-FA4 share one abort, so K-FA5 cannot be split per site.** Both parse
sites reach `fp_runtime_error` through the single `tgt_parse_fld`; that is the
6 bytes §6.3 saves, and the price is that the abort's knife reddens two rows
rather than one. Site separation is what K-FA3 and K-FA4 are for.

⚠️ **K-FA2's blast is bounded by the read path only.** `fld_lookup` keeps its
`str_eval_one` caller, so the cut orphans nothing and `check_dead_code.py` stays
out of it.

---

## 9. Denominator

Scored by `fldary-acceptance`: **(subscript FORM: literal / variable) ×
(RANK: 1-D / 2-D) × (VERB: `FIELD` / `LSET` / `RSET`)**, plus the out-of-range
row at **each** parse site (whose oracle is an *error*, not a value), plus the
two IDENTITY rows §5.2 forces — two elements of one array, and an element beside
a scalar in one `FIELD` — plus one positive control **per arm**.

**Not covered, and named rather than implied:** `RSET` as a *distinct parse
site* (it shares `lrset_common`, so `r.fldary` measures the store's justify
direction, not a second parse); a subscript that is itself an array element
(`FIELD#1,10 AS A$(B(1))`); `FIELD` overflow past the record length (unchecked
today, unchanged here); `ERASE` of a fielded array (§5.4 — no oracle taken);
`LSET`/`RSET` on a non-FIELDed element (§5.5, the separate residual); numeric
arrays (`FIELD` targets are string variables by grammar); and the second
reference, which does not exist for any row in this document.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `8c284ad`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/field.asm`](../basic/field.asm) | `tgt_parse_fld` + `fld_key_de` + the §4.2 assert; both parse sites' `call var_name_key` → `call tgt_parse_fld`; `lrset_store`'s 68-byte body replaced by an 11-byte tenant stub |
| [`sub/lrsetst.asm`](../sub/lrsetst.asm) | **new** — `lrset_store_tenant`, the body verbatim with `pu_deref_body` inlined |
| [`sub/sub.asm`](../sub/sub.asm) / [`sub/equates.inc`](../sub/equates.inc) / [`basic/sysvars.inc`](../basic/sysvars.inc) | page-0 table row 13, `SUBROM_IDX_LRSETST`, and the stale *"LAST index that fits before the $0038 vector"* note corrected |
| [`basic/strvar.asm`](../basic/strvar.asm) | `sea_fld`, sited between `str_eval_no` and `str_eval_ok` so its tail falls through |
| [`basic/arrays.asm`](../basic/arrays.asm) | `str_eval_arr`'s success arm jumps to page 1; the two arms stop sharing a tail |
| [`probes/basic/basic_probe_fldary.py`](../probes/basic/basic_probe_fldary.py) | **new**, 13 rows, 2 positive controls — one per arm |
| [`probes/basic/basic_probe_lvfix.py`](../probes/basic/basic_probe_lvfix.py) | `d.ary` / `s.fldary` **promoted out of DEFERRED**, `d.ctl` / `s.fld` added beside them |
| [`Makefile`](../Makefile) | `fldary-characterize` + `fldary-acceptance`, both `.PHONY` |

### 10.2 The walls, measured from clean — **and two of the four were wrong**

`rm -rf build && make basic-reloc`:

| wall | at `8c284ad` | §6.5 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 18 B | ≈37 B | **35 B** | ❌ −2, see (a) |
| **main low region** | 7 B | ≈6 B | **6 B** | ✅ |
| **sub page 0** | 3769 B | ≈3699 B | **3696 B** | ❌ −3, see (b) |
| sub page 1 | 1483 B | unchanged | **1483 B** | ✅ |
| RAM | — | 0 | **0** | ✅ |

| routine | scouted | as built | |
|---|---|---|---|
| `tgt_parse_fld` | 13 B | **13** | ✅ |
| `fld_key_de` | 15 B | **15** | ✅ |
| `sea_fld` | 10 B | **12** | ❌ (a) |
| `lrset_store` stub | 11 B | **11** | ✅ |
| `str_eval_arr` | 17 → 18 | **18** | ✅ |
| `exf_item` / `lrset_common` | 64 / 81, unchanged | **64 / 81** | ✅ |

🔴 **(a) `sea_fld` IS 12 BYTES, NOT 10, AND THE GATE IS WHAT SAID SO.** §4.3's
draft omitted `push hl` / `pop hl`: **HL is the live text cursor on the array
path and `fld_lookup` clobbers it.** `str_eval_one`'s scalar arm guards it with
its own push/pop for exactly this reason — the array arm has none of its own,
because `str_eval_arr` advances HL past the subscripts and `str_eval_ok` returns
it. The first `--sides zb` run read **`<NO OUTPUT>` on all six `s.*`/`r.*` rows
while every `d.*` row stayed green**, which is what pointed at the READ hook
rather than at either parse site: the FIELD statements were being accepted, so
only the thing downstream of them could be wrong. Two bytes, caught by the
per-arm split in the row set rather than by re-reading the source.

⚠️ **(b) The sub-ROM's JUMP-TABLE ROW is 3 bytes and §6.4's table did not have a
line for it.** The carve was priced as *body − `call` + inline* = 70; a tenant
also costs one `jp` row in `sub_p0_table`, so it is **73**. A page-0 tenant is
never only its body, and this is the first index past the old `$0038` ceiling —
the row that D-P0BASE made room for is exactly the row that was forgotten.

### 10.3 The ROM hashes — **all four predicted, and predicted before the build**

| ROM | at `8c284ad` | §6.5 predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `96c7ec8a…` | MOVES | **`a494c9de…`** ✅ |
| `sub.rom` | `20b14735…` | MOVES | **`f4c16277…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `dfeea0a6…` | MOVES | **`7dbdf411…`** ✅ |

D-LVFIX §11.3 recorded predicting its walls and its gate tally and forgetting
these four ([[a-wall-is-a-size-a-hash-is-an-identity]]). §6.5 carries them
because of that, and the one that mattered is `disk.rom` **holding**: it is the
only positive statement in the set, and a moved `disk.rom` would have meant this
slice reached a component it has no business in.

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`fldary-acceptance`** | — (new) | 13/13 | **13/13 agree, 0 diverge** ✅ |
| `lvfix-acceptance` | 14/14 + 6 deferred | 18/18 + 4 deferred | **18/18 agree, 4 deferred** ✅ |
| `lvsites-characterize` | 6/10 | 8/10 | **8/10** ✅ |
| `audit-citations` swept / basic | 743 / 192 | 745 / 193 | **746 / 194** ❌ |
| `injector-check` | 340 | 341 | **341** ✅ |
| `rowshape-check` | 181/34/10/10/0 | 182/35/11/11/0 | **182/35/11/11/0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| sub page-0 closure | 723 + 15, **13** tenants | 724 + 15, **14** | **729 + 15, 14** ❌ |
| `deadcode` main / sub | 0 / 0 (+1 allowlisted) | unchanged | **0 / 0 (+1)** ✅ |
| `unit-test` · `latch-check` | 59 · 16/16 | unchanged | **59 · 16/16** ✅ |

⚠️ **Both misses are the same miss, one document apart from D-LVFIX's version of
it: a count predicted from what the slice *writes* rather than from what the
checker *walks*.** `audit-citations` sweeps FILES, and this slice adds **three**
(the spec, the probe, and `sub/lrsetst.asm`) — the sub-ROM source was left out of
both predictions because it is not where the *language* change lives. The
closure counter is worse: it counts **routines**, and a tenant with six labels
adds six, not one. Neither number is a regression and both were re-read from the
checker's own definition afterwards — which is the step that should have come
first ([[a-count-is-predicted-by-reading-its-definition]]).

### 10.5 🎯 THE DECLINE WAS RIGHT TO BE FILED AND WRONG IN THREE OF ITS FOUR PARTS

Set against [`spec-basic-lvsites.md`](spec-basic-lvsites.md) §7, measured:

| §7's reason | outcome |
|---|---|
| **1.** the READ path is a third site nobody listed | ✅ **STOOD, and it is the load-bearing one.** `sea_fld` is the hook, K-FA2 reddens six rows with every `d.*` row green, and without it `s.fldary` cannot go green at all |
| **2.** the table cannot identify an element → `FLD_ENTSZ` 6→8, so `FLD_SLOTS` 16→12 or +32 B RAM | ❌ **FELL.** The discriminator does not have to sit *beside* the key — it can BE the key (§4.2). `FLD_TAB` is byte-identical, `FLD_SLOTS` is still 16, RAM is still 0, and the page-0 tenant's ABI never moved |
| **3.** ≈ +80 B page 1, ≈ +5 B low against ~18 and ~7 | **HALF.** The real price is **+40 B page 1** (38 scouted + the 2 of §10.2a) and **+1 B low** — half the sketch, because reason 2 fell. But 40 > 18 still, so the slice needed funding, which is what §7 was fundamentally right about |
| **4.** and no carve is available | ❌ **FELL.** §7 tested the *cluster* (statement heads drag the interpreter); the **leaf-only** re-run is page-0-tenant CLEAN, and `lrset_store` alone returns **57 B** |

🎯 **The sketch in §7 was labelled "NOT a calibrated hand count" and it was
honest about being one.** What it could not do without a design is notice that
the entry format never has to change — and that single observation is worth
40 bytes, 4 field slots and 32 bytes of RAM. **A priced decline is a claim about
a design that does not exist yet**, and re-pricing it against one that does is a
different measurement, not a re-reading of the same one.

### 10.6 Knives — 8 cuts × 2 rounds, **6 EXACT, 1 PARTIAL, 1 re-sited**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly; snapshot restore in a `finally`; `rm -rf build` + full rebuild + repack
before every run including each baseline; ROM-hash guard per cut; rows via
`probe_report.parse()` compared as `{label → zb value}` with a 13-row refusal.
**Both rounds were identical on all eight cuts** — no flakiness.

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-FA1** | `fld_key_de`: `sbc hl,de` → `sbc hl,hl` (`ED 52`→`ED 62`) | `s.fldary2` + `s.fldarymix` | 🔴 **`s.fldary2` ONLY** | ❌ ×2 |
| **K-FA2** | `sea_fld`: `call fld_lookup` → 3 × `nop` | 6 read rows | **6, exact** — every `d.*` and `s.fld` GREEN | ✅ ×2 |
| **K-FA3** | `ex_field`: `call tgt_parse_fld` → `call var_name_key` | all 11 non-control rows | **11, exact** | ✅ ×2 |
| **K-FA4** | `lrset_common`: the same swap | 7 `s.*`/`r.*` rows | **7, exact** — 🎯 every `d.*` row GREEN, which is what proves the two parse sites are independently wired | ✅ ×2 |
| **K-FA5** | `tgt_parse_fld`: `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 `d.aryoor` + `s.fldaryoor` ONLY | **exactly those two** | ✅ ×2 |
| **K-FA6** | the stub's tenant index → another tenant's | 7 store rows, `s.fld` included | **7, exact** | ✅ ×2 (re-sited, below) |
| **K-FA7** | the §4.2 assert `> $7FFF` → `> $0100` | the BUILD is refused | **refused, and the log names `FLD_ELEMENT_KEY_BIT15…`** | ✅ ×2 |
| **K-FA8** | `CONTROL_WANT["d.ctl"]` made unmatchable | exit **2**, 0 scored | **rc 2**, and the ROMs correctly did **not** move | ✅ ×2 |

🔴 **K-FA1 IS A HONEST PARTIAL, AND THE HALF THAT MISSED IS A STATEMENT ABOUT THE
CLAIM, NOT ABOUT THE CUT.** Zeroing the offset makes every element key
`($80,$00)`, so `s.fldary2`'s two elements collide and it reads `BB␣␣` (entry 1,
width 4) instead of `BB␣␣␣␣` — exactly the row's purpose. `s.fldarymix` did not
move, and **could not have**: `set 7,h` survives the cut, so an element key is
still `≥ $80` and still disjoint from a scalar's letter. That is the same thing
§4.2 says in words — **no reachable program collides the two key spaces**, so no
row can redden a cut that only perturbs *which* element is named. `s.fldarymix`
is therefore a row for a claim whose falsifier is the **assert** (K-FA7), not a
cut; it stays because it is the only thing that measures a scalar field and an
element field coexisting in one table, and a green reading there is what makes
§4.2 a measurement rather than an argument
([[rule-gated-structurally-has-no-knife]]).

⚠️ **K-FA6's first siting was unbuildable, and the reason generalises.** The cut
re-pointed the stub at `SUBROM_IDX_PING` — which is defined in
[`sub/equates.inc`](../sub/equates.inc) and **is not visible to the main-ROM
assembly at all**; only the indices mirrored into
[`basic/sysvars.inc`](../basic/sysvars.inc) are. `pasmo` refused with *"Symbol
'SUBROM_IDX_PING' is undefined"* and the runner correctly scored `ABORT(build)`
rather than a miss. Re-sited to `SUBROM_IDX_FLDLOOK` (mirrored, hence visible) it
is exact ×2. 🎯 **The two `equ` mirrors are the ABI's known weak seam** — index
12's own comment says nothing cross-checks them — and a knife is one more way to
walk into it. Add it to the list beside *"cut a label's BODY, not its
reference"*: **a knife may only name symbols the side it edits can see.**

🎯 **K-FA5 IS THE ONE D-LVFIX COULD NOT GET.** That slice cut the identical
`jp nz,fp_runtime_error` at two other sites and reddened **nothing**, because at
both of them the next act is an `eval` whose `check_fperr_only` re-raises the
same error ([[rule-gated-structurally-has-no-knife]]). Here `exec_stmt`
**clears** `FPERR` at the statement boundary and `ex_field` runs no check between
the resolve and it, so the cut turns `Subscript out of range` into a silent `OK`.
The difference was **predicted from reading `exec_stmt`** (§5.3) rather than
discovered by the run — the same question asked one document earlier and answered
the other way.

### 10.7 Corpus

Sequentially from clean (`rm -rf build`, bash), **26 targets, all rc=0**:
`unit-test` 59 · `audit-citations` CLEAN (746 swept) · `preflight-check`
181/86/95/95/0 · `injector-check` 341 · `rowshape-check` 182/35/11/11/0 ·
`latch-check` 16/16 · `deadcode` 0/0 · `lnblank-acceptance REPEAT=2` ·
`lnblank-say-acceptance` · `logicops-acceptance` · `float-acceptance` ·
`linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` ·
`lptverb-acceptance` · `dskmsg-acceptance` · `diskbasic-acceptance` ·
`fat-error-acceptance` · `runtail-acceptance` · `castail-acceptance` ·
`cassave-acceptance` · `readvar-acceptance` · `arylv-acceptance` ·
`inputary-acceptance` · **`lvfix-acceptance` 18/18** · **`fldary-acceptance`
13/13**. Plus `lvsites-characterize` **8/10** (not a gate).

⚠️ `latch-check` exited **2** the first time and it was the RUNNER, not the tree:
it is the one target in the list with no `repack-machine` prerequisite, and it
was invoked immediately after `rm -rf build`, so `omsx_preflight` correctly
refused to measure against ROMs that did not exist. Re-run after a build: 16/16.
Recorded because that is the exit-2-is-the-instrument rule firing on my own
harness, which is the case it is easiest to misread as a regression.

### 10.8 The fix, as a program

Both columns are readings from the runs above.

```basic
10 DIM A$(3)
20 OPEN"FA.DAT"AS #1
30 FIELD#1,10 AS A$(1)
40 LSET A$(1)="HI"
50 PRINT"[";A$(1);"]"
```

| | screen after `RUN` |
|---|---|
| National CF-3300 | `[HI        ]` |
| zerobas **before** | `Syntax error in 30` |
| zerobas **after** | `[HI        ]` |

The row that a subscript-parsed-and-discarded fix would have failed — two
elements of one array, deliberately at **different widths** so the wrong entry
shows up in the padding:

```basic
10 DIM A$(3)
20 OPEN"FA.DAT"AS #1
30 FIELD#1,4 AS A$(1),6 AS A$(2)
40 LSET A$(1)="AA"
50 LSET A$(2)="BB"
60 PRINT"[";A$(2);"]"
```

| | screen after `RUN` |
|---|---|
| CF-3300 / zerobas **after** | `[BB    ]` |
| zerobas **before** | `Syntax error in 30` |
| under **K-FA1** (the discriminator cut) | `[BB  ]` — entry 1's width, i.e. the two elements collided |

And the error face, which is why §5.3 routes through `fp_runtime_error`:

```basic
10 DIM A$(3)
20 OPEN"FA.DAT"AS #1
30 FIELD#1,10 AS A$(9)
```

| | screen after `RUN` |
|---|---|
| CF-3300 | `Subscript out of range in 30` |
| zerobas **before** | `Syntax error in 30` |
| zerobas **after** | `Subscript out of range in 30` |
| under **K-FA5** (the abort cut) | `Ok` — the statement silently succeeds |
