# D-LRVAR — `LSET` / `RSET` on a NON-FIELDed variable

*Slice D-LRVAR, 2026-08-08, on `main`, based on `76685e9` (D-FLDARY).*

The last open item of the lvalue/FIELD surface.
[`lvsites-msx1-characterization.md`](lvsites-msx1-characterization.md) reads
**8/10** and `s.ctl` / `s.ary` are the only two rows still red — both of them the
same defect: `lrset_notfld` ([`basic/field.asm`](../basic/field.asm)) is a bare
`jp stmt_error` commented *"LSET/RSET on a non-fielded var (slice-1 limit)"*.

⚠️ **ONE REFERENCE, NOT TWO.** `LSET`/`RSET` are Disk BASIC. The Philips VG-8020
has no disk controller, answers `Syntax error` to both words and **cannot express
the question** — recording its answer would manufacture an agreement out of an
absent drive. Every row here rests on the National CF-3300 alone. That is weaker
than anything D-ARYLV rested on, it is not upgraded anywhere below, and the probe
prints `[ONE REFERENCE ONLY]` per row.

---

## 1. The rule — **measured before it was designed, not inferred**

🔴 **ONE DATA POINT IS NOT A RULE.** The filed residual carried exactly one
reading: `LSET A$="HI"` on `A$="XXXXX"` reads `HI␣␣␣` on the CF-3300. That is
consistent with at least three different implementations, which diverge on an
UNSET target, an EMPTY target, a source LONGER than the target, whether `LEN()`
moves, and `RSET` over all of the above. **Every one of those is a row in
`make lrvar-characterize`, measured 2026-08-08 BEFORE a byte was written**, and
the reference column below is the whole design input.

| | program | CF-3300 | zerobas at `76685e9` |
|---|---|---|---|
| `n.ctl` | `A$="XXXXX"` / `LSET A$="HI"` | `HI␣␣␣` | **Syntax error** 🔴 |
| `n.len` | …then `PRINT LEN(A$)` | `␣5␣` | **Syntax error** |
| `n.exact` | `A$="XX"` / `LSET A$="HI"` | `HI` | **Syntax error** |
| `n.long` | `A$="AB"` / `LSET A$="HELLO"` | `HE` | **Syntax error** |
| `n.unset` | `LSET A$="HI"` (never assigned) | `` / `␣0␣` | **Syntax error** |
| `n.empty` | `A$=""` / `LSET A$="HI"` | `` / `␣0␣` | **Syntax error** |
| `r.ctl` | `A$="XXXXX"` / `RSET A$="HI"` | `␣␣␣HI` | **Syntax error** |
| `r.long` | `A$="AB"` / `RSET A$="HELLO"` | `HE` | **Syntax error** |

**The rule, stated from the readings and from nothing else:**

> `LSET`/`RSET` on a target with no field **overwrite the target's CURRENT bytes
> in place**. The field width IS the target's current length; the length NEVER
> changes; the value is space-padded to it and left- (`LSET`) or right-justified
> (`RSET`); a source longer than the target keeps its **FIRST** `LEN(target)`
> bytes — for **both** verbs; and a target of length 0, whether never assigned or
> assigned `""`, is a **NO-OP** rather than an assignment or an error.

🎯 **THE THREE READINGS THAT DECIDED THE DESIGN ARE THE ONES THE FILED RESIDUAL
COULD NOT HAVE PREDICTED.** `n.len` (` 5 `) rules out "assign, then pad": the
length is not re-derived, it is *preserved*. `n.unset` (empty, `LEN` 0) rules out
"create the target": nothing is allocated, so a width-0 store must be a no-op and
not a wild write through an absent body pointer. And `r.long` reads `HE`, **not**
`LO` — `RSET` truncates from the same end `LSET` does, which is not what
"right-justify" suggests and is the one place a hand-written store would have
guessed wrong.

🎯 **AND THE RULE IS, BYTE FOR BYTE, WHAT THE EXISTING STORE ENGINE ALREADY
DOES.** `lrset_store_tenant` ([`sub/lrsetst.asm`](../sub/lrsetst.asm)) space-fills
`LRSET_W` bytes, copies `min(srclen, LRSET_W)` of them from the FIRST byte of the
source, and left- or right-aligns per `LRSET_JUST`. Set `LRSET_W` to the target's
current length and point the destination at the target's own body and **all eight
rows above fall out with no semantic code at all** (§4.3 walks each one). That
agreement is a result of the measurement, not an assumption behind it.

## 2. What is wrong, in one sentence

* **`lrset_notfld`** ([`basic/field.asm:404`](../basic/field.asm)) — reached when
  `fld_find` misses, it is `pop hl` / `jp stmt_error`. The **parse** half of this
  site is already complete: D-FLDARY's `tgt_parse_fld` hands `lrset_common` either
  a name key or an ARYTAB-relative element key and leaves the element address in
  `(TGT_ADDR)`. **What is missing is the STORE for a target that has no field.**

## 3. Scope

**In:** `LSET` and `RSET` on a non-FIELDed target, scalar **and** array element;
the subscript FORM (literal / variable) and RANK (1-D / 2-D); the out-of-range
error face on the new arm; the numeric-target error face; the coexistence of a
FIELDed and a non-FIELDed target in one program; and — forced by this slice,
§5.4 — **`ERASE` of an array whose sibling holds a field**.

**Out, and named rather than implied:**

* **`RSET` as a distinct parse site** — it shares `lrset_common` with `LSET`, so
  the `r.*` rows measure the STORE's justify direction over the new arm, not a
  second parse.
* **`LSET A$=A$`** — the store space-fills the destination *before* reading the
  source, so a target that is its own source is destroyed. Pre-existing on the
  FIELDed arm, inherited unchanged here, and **the reference's answer is not
  measured**. Named, not fixed.
* **A string GC moving the target's body DURING the RHS** — §5.2 shows the
  ordering that makes it safe, and it is not separately rowed because no program
  either reference accepts can force the collision
  ([`spec-basic-lvsites.md`](spec-basic-lvsites.md)'s `VARPTR` residual).
* **A subscript that is itself an array element** (`LSET A$(B(1))="X"`).

---

## 4. Design

### 4.1 🎯 THE STORE'S DESTINATION STOPS BEING IMPLIED AND BECOMES AN ADDRESS

`lrset_store` is the wrong engine as it stands, and it must **not** be reused
as-is: its destination is hard-wired to `FSECTOR_BUF + (LRSET_OFF)`, a channel's
record buffer. A non-FIELDed store writes into the **variable's own body**, at a
different address, in a different page, under a different width rule.

Two dispositions were priced rather than one being slid into:

| | main page 1 | sub page 0 | |
|---|---|---|---|
| **(a) keep the tenant, make the non-FIELDed arm fake an offset** — `LRSET_OFF := body − FSECTOR_BUF`, so `FSECTOR_BUF + off` still lands on the body (16-bit wrap does the work) | `ld de,-FSECTOR_BUF` 3 + `add hl,de` 1 + `ld (LRSET_OFF),hl` 3 = **+7** | 0 | a negative offset is a trick that has to be re-explained at every future read of either side |
| **(b) generalise the tenant: the cell holds the DESTINATION, and the FIELDed arm computes it** ✅ | fielded arm `ld hl,FSECTOR_BUF` 3 + `add hl,de` 1 + `ld (LRSET_DEST),hl` 3, minus the `ld (LRSET_OFF),de` 4 it replaces = **+3**; non-FIELDed arm `ld (LRSET_DEST),hl` = **+3** | `ld hl,(LRSET_OFF)`/`ld de,FSECTOR_BUF`/`add hl,de` (7) → `ld hl,(LRSET_DEST)` (3) = **−4** | one cell, one meaning, on both arms |

**(b) is taken.** It is 1 B cheaper on the binding wall, it is the honest
statement of what the cell now holds, and the tenant gets *smaller*. `LRSET_OFF`
is **renamed** `LRSET_DEST` at its existing address — same 2 bytes, **0 RAM**.

⚠️ **`FSECTOR_BUF` is a FIXED address (`$E5C0`), so computing the sum before
`fch_select` is safe**: `fch_select` swaps the buffer's *contents* per channel, it
does not move the buffer. The FIELDed arm therefore keeps computing its
destination where it already reads the entry, which is what makes (b) +3 and not
+7.

### 4.2 One arm discriminator, and it is a cell that already exists

```
                call    tgt_parse_fld       ; BC = key, (TGT_ADDR) = elem or 0
                push    hl                  ; guard the cursor
                call    fld_find            ; CF -> HL = entry (BC preserved)
                jr      nc,lrset_notfld
                <FIELDed: FLD_CHAN, LRSET_W, LRSET_DEST from the entry>
lrs_haveeq:     <shared: `=`, then str_eval — ONE copy, both arms>
                ld      a,(FLD_CHAN)
                or      a
                jr      z,lrs_var           ; 0 -> no field
                call    fch_select
                jr      lrs_store
lrs_var:        call    tgt_desc_fix        ; HL = the target's descriptor
                ld      a,(hl)              ; its CURRENT length IS the width
                ld      (LRSET_W),a
                call    pu_deref_body       ; HL = its body
                ld      (LRSET_DEST),hl
lrs_store:      call    lrset_store
lrset_notfld:   call    tgt_desc            ; snapshot the target (§5.2)
                ld      (MIDS_DEST),hl
                xor     a
                ld      (FLD_CHAN),a        ; 0 = "not fielded"
                jr      lrs_haveeq
```

🎯 **`FLD_CHAN = 0` IS A FREE DISCRIMINATOR AND IT IS NOT AN INVENTED
CONVENTION.** `0` is already "this slot is free" throughout `FLD_TAB`
(`fld_init` writes it, `fld_find` skips it), and `fch_check` rejects channel 0
with `ERR 59` before any statement can select it — so `fld_find` can only ever
return an entry whose chan is **non-zero**. No cell is invented, no RAM grows and
no flag is carried on the stack across `str_eval`.

⚠️ **The `=` parse and the whole RHS evaluation are SHARED between the arms, and
that is where the byte budget comes from.** The non-FIELDed arm re-enters the
existing body at `lrs_haveeq` rather than duplicating 19 bytes of `skip_spaces` /
`EQ_TOKEN` / `str_eval` / error tail.

### 4.3 Why no semantic code is written — the rule, walked against the tenant

`LRSET_W := (target descriptor).len`, `LRSET_DEST := deref(target descriptor)`:

| row | `LRSET_W` | source len | what `lrset_store_tenant` does | = reference |
|---|---|---|---|---|
| `n.ctl` | 5 | 2 | fill 5 spaces; `cp c` → 5 ≥ 2, copy 2 at the start | `HI␣␣␣` ✅ |
| `n.exact` | 2 | 2 | fill 2; 2 ≥ 2, copy 2 | `HI` ✅ |
| `n.long` | 2 | 5 | fill 2; 2 < 5 → `ld c,a`, copy the FIRST 2 | `HE` ✅ |
| `r.ctl` | 5 | 2 | fill 5; `LRSET_W − ncopy` = 3, copy 2 at start+3 | `␣␣␣HI` ✅ |
| `r.long` | 2 | 5 | fill 2; ncopy = 2, so `5 − 2`… → `2 − 2` = **0**, copy the FIRST 2 at start+0 | `HE` ✅ |
| `n.unset` / `n.empty` | **0** | 2 | `or a` / `jr z` skips the fill; `0 < 2` → `ld c,0`; `ld a,c` / `or a` / `ret z` → **nothing written** | no-op ✅ |

🔴 **`n.unset` IS WHAT MAKES THE WIDTH-0 PATH LOAD-BEARING RATHER THAN
DEFENSIVE.** An unset scalar resolves through `str_get_key`, which returns
`STR_EMPTY` — a `db 0` **in ROM** — and an unset array element is a `[0][garbage]`
slot. Dereferencing either yields a body pointer that points at nothing. The store
is safe on both **only because the width comes from the same descriptor as the
pointer**, so a length of 0 makes the tenant return before it reads the pointer's
target at all. That is not a happy accident: it is why the width is read from
`(hl)` *before* `pu_deref_body` consumes `HL`.

### 4.4 The numeric-target error face — **0 bytes**

Measured, and it is not the divergence anyone had listed:

| row | program | CF-3300 | zerobas |
|---|---|---|---|
| `n.num` | `A=1` / `LSET A=2` | **Type mismatch** | **Syntax error** 🔴 |

`lrset_common`'s `call var_str_type` / `or a` / `jp z,stmt_error` rejects a
numeric target as a *syntax* error. `type_mismatch_error`
([`basic/interp.asm:668`](../basic/interp.asm), `$426A`, page 1) is a `jp` target
of exactly the same width, so the fix is **`jp z,stmt_error` →
`jp z,type_mismatch_error`: byte-neutral**.

### 4.5 RAM

**None.** `LRSET_DEST` is `LRSET_OFF` renamed at its own address; `MIDS_DEST` is
D-LVFIX's existing stash cell (§5.3); `FLD_CHAN`, `LRSET_W` and `LRSET_JUST` are
unchanged.

---

## 5. Forced constraints — each is a thing the design is NOT free to choose

### 5.1 🔴 THE TWO ARMS DO NOT STORE DIFFERENTLY, AND THAT IS A MEASUREMENT OF THE TREE

The residual's own framing warns that a string SCALAR is stored inline in STRTAB
as `[name0][name1][len][bytes]` while an array element is a `[len][ptr]`
descriptor — i.e. that `n.ctl` and `n.ary` are two different stores. **That is
the pre-slice-4c layout and it has not been true since.**
[`spec-basic-arrays-slice4c-string-scalar-unification.md`](spec-basic-arrays-slice4c-string-scalar-unification.md)
§3c put string scalars into the SAME unified chain as arrays: `str_get_key`
returns `entry + 3`, a **`[len:1][ptr:2]` descriptor**, and an element slot is the
identical 3-byte shape. `pu_deref_body` reads both.

🎯 **So the arms differ only in HOW THE DESCRIPTOR IS FOUND, and `tgt_desc`
already forks exactly there** — one `call`, not two stores. The file header of
`basic/field.asm` still describes the old inline layout and is corrected by this
slice; **that stale comment is what the residual's framing was reading.**

### 5.2 🔴 THE TARGET MUST BE DEREFERENCED **AFTER** THE RHS, NOT BEFORE

The target's body lives in the string heap. `str_eval` on the RHS can allocate a
temp, and an allocation can run `strheap_gc`, which **compacts heap bodies** and
rewrites every root descriptor's `ptr`. A body address captured before the RHS is
therefore stale by the time it is written to — silently, into whatever now
occupies the old bytes.

**The descriptor is a GC root; the body pointer is not.** So the ordering is
forced: snapshot the *descriptor* before the RHS (it must survive an `ARYTAB`
move, §5.3), evaluate the RHS, and only then read `len` and dereference `ptr`.
This is the same shape `ex_mid_stmt` uses one file away, and for the same reason.

### 5.3 The `ARYTAB` snapshot is D-LVFIX's, reused rather than re-invented

`tgt_desc` / `tgt_desc_fix` ([`basic/vars.asm:348`](../basic/vars.asm)) already
solve "a target held across an evaluation": a scalar's descriptor address is
stashed verbatim, an element's is stashed as its **ARYTAB-relative offset** and
re-added afterwards, so an `ARYTAB` move between the parse and the store cannot
alias a neighbouring element. `MIDS_DEST` is the cell they are hardcoded on, so
reusing them means reusing it.

⚠️ **`MIDS_DEST` is safe to share and the argument is structural, not empirical.**
Its other tenant is `ex_mid_stmt`, a *statement head*; the window here is
`tgt_desc` → `str_eval` → `tgt_desc_fix`, and `str_eval` cannot reach a statement
head. The same walk is what `tgt_desc`'s own header already requires of `TGT_ADDR`
("nothing between `tgt_desc` and `tgt_desc_fix` may call `tgt_parse`… all six
`tgt_parse` callers are statement heads"). This slice becomes the **seventh**
`tgt_parse` caller and the **second** `MIDS_DEST` tenant, and both remain
statement heads.

🔴 **AND `tgt_desc_fix` IS MANDATORY ARITHMETIC, NOT A DRIFT GUARD — THIS
PARAGRAPH SAID THE OPPOSITE UNTIL K-LV9 REFUTED IT, AND §10.6 KEEPS THE
CORRECTION.** The draft predicted that cutting it would redden **nothing**, by
the same argument D-LVFIX attached to its own guards: the correction only matters
when `ARYTAB` moves inside `str_eval`, and no program either reference accepts can
move it (`VARPTR(<unset>)` is `Illegal function call` on both — the only
eval-time scalar allocator arrays slice-4b §13a names). **That argument is about
DRIFT, and drift is not what this call does.** `tgt_desc` stashes an element as
`elem − ARYTAB`, an **offset**; without the re-add, `HL` is a small number in page
0 rather than an address at all. The 3 bytes are the only thing that turns the
stash back into a target, and the knife reddens all five array rows.

⚠️ The drift-invariance is a *property of the encoding*, not the purpose of the
call — and inheriting the sibling slice's framing without re-deriving it is how a
load-bearing instruction got filed as an unfalsifiable one
([[filed-justification-is-a-claim]]).

### 5.4 🔴 THIS SLICE FORCES THE `ERASE` RESIDUAL, AND THE ORACLE REFUTES THE FIX THAT WAS PRICED FOR IT

D-FLDARY [§5.4](spec-basic-fldary.md) filed *"an `ERASE`d fielded array leaves a
stale `FLD_TAB` entry"*, priced an `fld_clear_ary` sweep (**clear every entry
whose `k0 ≥ $80`**) at ≈20 B page 1 + 3 B LOW, and **declined it for want of an
oracle** — whether the reference drops, keeps or dangles a field across `ERASE`
was unmeasured, and 23 bytes are not spent to choose between two guesses.

**The reading was taken here.** `e.erase` — `DIM A$(3),B$(3)` / `FIELD#1,10 AS
B$(1)` / `ERASE A$` / `LSET B$(1)="HI"` / `PRINT B$(1)` — with `e.ctl`, the same
program without the `ERASE`, as its own control:

| row | CF-3300 | zerobas at `76685e9` |
|---|---|---|
| `e.ctl` | `HI␣␣␣␣␣␣␣␣` | `HI␣␣␣␣␣␣␣␣` 🟢 **control** |
| `e.erase` | **`HI␣␣␣␣␣␣␣␣`** | **Syntax error** 🔴 |

🎯 **THE REFERENCE KEEPS THE FIELD, so the sweep that was priced is the WRONG
FIX.** "Clear every element entry" implements *drop*; the reference does not drop,
and a dropped entry would leave `e.erase` reading an empty string against
`HI␣␣␣␣␣␣␣␣` — still red, for 23 bytes. **A priced decline is a claim about a
design, and this one was priced for a design the oracle rejects**
([[a-priced-decline-is-a-claim-about-a-design]]).

🔴 **AND D-LRVAR MAKES THE DEFECT WORSE, WHICH IS WHAT MAKES CLOSING IT FORCED
RATHER THAN OPPORTUNISTIC.** Today a stale element key MISSES `fld_find` and the
statement is a loud `Syntax error`. After this slice a miss is no longer an
error — it is an ordinary non-FIELDed store into the (unset, length-0) element,
i.e. a **silent no-op**, and the program runs on. This slice cannot ship the rule
and leave the observability behind, so the residual is closed here.

**The correct fix is to FIX UP the keys, and re-sited it costs nothing on the wall
that binds.** An element key is `(elem − ARYTAB)`; `aeng_erase`
([`sub/arrays.asm:199`](../sub/arrays.asm)) compacts the descriptor list by
sliding everything above the erased array down by exactly one `stride`. So every
element key at or above the erased array's own offset moves by the same known
delta, and every key *inside* it names a variable that no longer exists:

| key's ARYTAB offset | action |
|---|---|
| `< DST − ARYTAB` | below the erased array — **untouched** |
| `[DST, SRC) − ARYTAB` | inside the erased array — **free the slot** (`chan := 0`) |
| `≥ SRC − ARYTAB` | above — **`off −= stride`**, `bit 7` re-set |

🎯 **D-FLDARY PRICED IT AT THE WRONG SITE.** Its ≈20 B page 1 + 3 B LOW was a
resident `fld_clear_ary` called from `ex_erase` — but `aeng_erase` is **already a
page-0 sub-ROM tenant**, it already holds `DST`, `SRC` and the stride at the
instant of the compaction, and a page-0 tenant reaches RAM, which is where
`FLD_TAB` (`$EE64`) lives. Sited there the sweep costs **0 B of main page 1** and
**≈96 B of sub page 0**, which has **3696**. The byte that was expensive was
never the sweep — it was the siting.

⚠️ The neighbouring **pre-existing** version is still deliberately left alone: a
bare program EDIT reaches `vars_reset` (which re-anchors `ARYTAB`) without
reaching `clear_vars` (which is what calls `fld_init`), so a field entry can
already outlive the variables it names — true of scalar entries today and not
this slice's to change.

### 5.5 The out-of-range face is already right, and it must stay that way

`n.aryoor` (`DIM A$(3)` / `LSET A$(9)="HI"`) reads `Subscript out of range` on
**both** sides at `76685e9` — `tgt_parse_fld`'s `jp nz,fp_runtime_error` fires
before `fld_find` is reached, so the new arm is downstream of it and inherits the
face unchanged. The row is carried as a **green-before, green-after** row, which
is the only kind that can catch this slice pushing the abort out of reach.

---

## 6. The carve scout

All spans off `build/basic-reloc.sym` from a clean `rm -rf build && make
basic-reloc` at `76685e9`; walls printed by that build (low **6 B**, page 1
**35 B**, sub p0 **3696 B**, sub p1 **1483 B**; `basic-reloc.rom a494c9de…`,
`sub.rom f4c16277…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 7dbdf411…`).

### 6.1 Which region each file lives in — asked before anything is priced

`python3 tools/carve_scout.py build/basic-reloc.sym --files <f>`:

| file | labels in page 1 | region | what this slice does there |
|---|---|---|---|
| `basic/field.asm` | **43 of 43** | page 1 | the whole main-ROM change |
| `basic/vars.asm` | 59 of 59 | page 1 | `tgt_desc`/`tgt_desc_fix`, **unchanged** |
| `basic/str-engine.asm` | **0 of 103** | **LOW** | `pu_deref_body`, **unchanged** — called, not edited |
| `basic/arrays.asm` | **0 of 45** | **LOW** | untouched |
| `sub/arrays.asm`, `sub/lrsetst.asm` | — | sub page 0 | the `ERASE` fix-up, the tenant's destination |

🎯 **EVERY ROUTINE THIS SLICE NEEDS ALREADY EXISTS, AND THE TWO THAT LIVE IN THE
LOW REGION ARE ONLY CALLED.** `pu_deref_body` (LOW, 8 B) and `tgt_desc` /
`tgt_desc_fix` (page 1, 16 B each) are used verbatim. **The low region — which
has 6 B — is not written to at all**, which is the difference between this slice
and D-ARYLV's, whose bound was set by a file nobody had checked the region of.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **before** any number was
quoted for code that does not exist
([[calibrate-a-hand-counter-before-quoting-it]]):

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `lrset_common` (head 23 + body 58) | **81** | **81** | ✅ 🎯 *the body being edited* |
| `lrset_notfld` | 4 | **4** | ✅ |
| `lrset_store` (the stub) | 11 | **11** | ✅ |
| `tgt_desc` | 16 | **16** | ✅ |
| `tgt_desc_fix` | 16 | **16** | ✅ |
| `pu_deref_body` | 8 | **8** | ✅ |
| `str_get_key` | 29 | **29** | ✅ |
| `tgt_parse` | 16 | **16** | ✅ |
| `tgt_parse_fld` | 13 | **13** | ✅ |
| `fld_key_de` | 15 | **15** | ✅ |
| `sea_fld` | 12 | **12** | ✅ |
| `fch_select` | 20 | **20** | ✅ |

**12/12 exact**, and the first row is the decisive one: `lrset_common` was counted
**instruction by instruction from the source**, not looked up, and came out at the
`.sym`'s 81 on the first pass. ⚠️ `LD (nn),DE` / `LD DE,(nn)` are **4** bytes
(`ED 53`/`ED 5B`) while `LD (nn),HL` / `LD HL,(nn)` are **3** — which is exactly
why replacing `ld (LRSET_OFF),de` with `ld (LRSET_DEST),hl` gives a byte back, and
why the arithmetic that earns it costs only 3 more.

### 6.3 The cost — a BOUND, with the twin named for every part

| item | file | region | bytes |
|---|---|---|---|
| FIELDed arm: `ld (LRSET_OFF),de` → width-first + `ld hl,FSECTOR_BUF`/`add hl,de`/`ld (LRSET_DEST),hl` | field.asm | p1 | **+3** |
| the arm test after `str_eval`: `or a` / `jr z,lrs_var` / `jr lrs_store` | field.asm | p1 | **+5** |
| `lrs_var`: `tgt_desc_fix` / width / `pu_deref_body` / `ld (LRSET_DEST),hl` | field.asm | p1 | **+13** |
| `lrset_notfld`: `tgt_desc` / `ld (MIDS_DEST),hl` / `xor a` / `ld (FLD_CHAN),a` / `jr` **minus** the `pop hl`+`jp stmt_error` it replaces | field.asm | p1 | **+8** |
| `jp z,stmt_error` → `jp z,type_mismatch_error` (§4.4) | field.asm | p1 | **0** |
| **main page-1 subtotal** (`lrset_common`+`lrset_notfld`: **85 → 114**) | | | **+29** |
| **main LOW** | | | **0** |
| tenant destination: `ld hl,(LRSET_OFF)`/`ld de,FSECTOR_BUF`/`add hl,de` → `ld hl,(LRSET_DEST)` | lrsetst.asm | sub p0 | **−4** |
| `aer_fldfix` body (§5.4) | sub/arrays.asm | sub p0 | **+87** |
| its call site in `aeng_erase` (3 push / `call` / 3 pop) | sub/arrays.asm | sub p0 | **+9** |

### 6.4 The bottom line — **no carve is needed, and that is the finding**

| region | free at `76685e9` | slice | free after |
|---|---|---|---|
| **main page 1** | **35 B** | **+29** | **≈ 6 B** |
| **main low** | 6 B | 0 | **6 B** |
| **sub page 0** | 3696 B | +92 | **≈ 3604 B** |
| sub page 1 | 1483 B | 0 | **1483 B** |
| RAM | — | 0 | — |

⚠️ **THE 35 B IS D-FLDARY'S CARVE PROCEEDS, NOT SLACK.** That slice carved 57 B
out of page 1 to fund 40; this one spends 29 of what is left. It fits **without a
carve of its own**, and the reason is worth naming rather than enjoying: every
expensive part of this change is a routine that already exists (§6.1), and the
one genuinely new body — the `ERASE` fix-up — was **re-sited out of the binding
wall entirely** (§5.4). Had it been taken at D-FLDARY's filed siting (`ex_erase`,
resident) the slice would have been +49 against 35 and would have needed one.

⚠️ **A BOUND, not a measured cost.** The instrument is calibrated (§6.2, 12/12)
and every body is written out as the assembly that will be assembled, but the real
number comes from a build ([[filed-justification-is-a-claim]]).

⚠️ **Predicted ROM hashes**, all four, including which should HOLD
([[a-wall-is-a-size-a-hash-is-an-identity]]):
`basic-reloc.rom` **MOVES**; `sub.rom` **MOVES** (both because `sub/arrays.asm`
and `sub/lrsetst.asm` gain bytes *and* because `sub/basic-resident-abi.inc` is
generated from main's `.sym`); `zerobas-main-eu.rom` **MOVES**; `disk.rom`
**HOLDS at `2c630d3d…`** — no disk-side byte is written, and a moved `disk.rom`
would mean this slice reached a component it has no business in.

### 6.5 ✅ VERDICT: **GO, unfunded.** 29 B fits 35, the LOW region is not touched, and the `ERASE` fix lands where there are 3696 bytes.

---

## 7. Predicted GREEN — the reference column IS the prediction

`make lrvar-characterize` must read, on the CF-3300 and on zerobas alike:

| row | prediction | |
|---|---|---|
| `n.fldctl` | `HI␣␣␣␣␣␣␣␣` | 🟢 **control, FIELDed arm** — green before **and** after |
| `n.fld2` | `BB␣␣␣␣` | 🎯 **K-LV2's row** — the field OFFSET survives §4.1(b); green before and after |
| `n.fldary` | `HI␣␣␣␣␣␣␣␣` | D-FLDARY regression; green before and after |
| `n.ctl` | `HI␣␣␣` | 🟢 **control, non-FIELDed arm** — **RED before**, green after |
| `n.len` | `␣5␣` | the length does not move |
| `n.exact` | `HI` | |
| `n.long` | `HE` | truncates from the right |
| `n.unset` | `␣␣0␣` (`` then `LEN` 0) | a no-op, not an assignment |
| `n.empty` | `␣␣0␣` | |
| `n.mix` | `HI␣␣␣␣␣␣␣␣\|LO␣␣␣` | 🎯 **the arm discriminator's row** |
| `r.ctl` | `␣␣␣HI` | |
| `r.long` | `HE` | 🎯 `RSET` truncates from the **same** end `LSET` does |
| `n.ary` | `HI␣␣␣` | |
| `n.aryvar` | `HI␣␣␣` | |
| `n.ary2d` | `HI␣␣␣` | |
| `n.arysep` | `XXXXX\|HI␣␣␣` | 🎯 **two elements must stay apart** |
| `n.aryoor` | `Subscript out of range` | §5.5 — green before **and** after |
| `r.ary` | `␣␣␣HI` | |
| `n.num` | `Type mismatch` | §4.4 — **RED before**, green after, 0 B |
| `e.ctl` | `HI␣␣␣␣␣␣␣␣` | 🟢 **control, ERASE arm** — green before and after |
| `e.erase` | `HI␣␣␣␣␣␣␣␣` | §5.4 — **RED before**, green after |

⇒ **`make lrvar-acceptance` scores 21/21**, every row `[ONE REFERENCE ONLY]`,
from **5/21** at `76685e9`.

⚠️ **21 is the SCOPE, not a row count.** §3 excludes `LSET A$=A$`, the GC-during-
RHS collision and a nested-element subscript, and the number above is what is left
after those, not what happened to be typed into the file
([[a-prediction-copied-into-the-result-column]]).

⚠️ **A CONTROL PER ARM, NOT PER SITE**, and this site has three arms to scope:
`n.fldctl` (FIELDed), `n.ctl` (non-FIELDed — **red on zerobas before the fix**,
which is an ordinary divergence and is scored) and `e.ctl` (the `ERASE` pair).
⚠️ **Classify a control failure by WHICH SIDE failed it** — red on the CF-3300 =
the fixture is broken (exit 2, score nothing); red on zerobas = an ordinary
divergence, scored, which scopes its own arm
([[classify-a-control-failure-by-which-side-failed-it]]).

And the document that has been counting this surface must move:

* `make lvsites-characterize` — **10/10** (up from 8/10); `s.ctl` and `s.ary` are
  the two remaining red rows and both are this slice's.
* `make fldary-acceptance` — **13/13, unchanged**. ⚠️ This is a *prediction that
  nothing moves*: `lrset_common` is rewritten under D-FLDARY's own rows.
* `make lvfix-acceptance` — **18/18 + 4 deferred, unchanged.**

Static counters, each predicted by reading its own check's definition rather than
by counting what this slice writes
([[a-count-is-predicted-by-reading-its-definition]] — D-FLDARY missed both of
these by predicting from the *language* change and forgetting the sub-ROM file):
`audit-citations` sweeps **FILES** and this slice adds **two** (this document and
the probe; `sub/arrays.asm` and `sub/lrsetst.asm` already exist), so 746 →
**748** swept, basic provenance-bearing 194 → **195** (+1 per real
`probes/basic/*.py`); `injector-check` 341 → **342**; `rowshape-check`
182/35/11/11/0 → **183/36/12/12/0**; `preflight-check` **181/86/95/95/0
unchanged**; `latch-check` **16/16 unchanged**; `deadcode` **0/0 (+1 allowlisted)
unchanged**; sub page-0 closure counts **ROUTINES**, and `aer_fldfix` adds
**one label** with its three internal `afx_*` locals — 729 + 15 → **733 + 15**,
tenants still **14**; sub page-1 closure **585 + 43 unchanged**; `unit-test`
**59 unchanged**.

---

## 8. Knives — drafted BEFORE the row set was frozen

Runner discipline is **not** restated here: read
[`dev-workflow.md`](dev-workflow.md) §"Knives" first. `probe_report.parse()`
ships — do not hand-roll a row parser and never diff report LINES. Restore in a
`finally`; `rm -rf build` + full rebuild + repack before every run **including
each baseline**; **assert the ROM hashes MOVED after every cut build** (a
probe-only cut must NOT move them); run every cut TWICE. Cut a label's **BODY**,
not its reference. Site a probe-only knife against **the invocation the runner
actually makes**. ⚠️ **And a knife may only name symbols the side it edits can
SEE** — D-FLDARY's K-FA6 was unbuildable for exactly that.

The knife subject is the probe **`--sides zb`** only: the CF-3300 column is a
constant and a cut in zerobas can only move zerobas, so re-measuring the
reference 20 times measures the printer.

| # | cut (byte-neutral unless noted) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-LV1** | `lrset_notfld`: `ld (FLD_CHAN),a` → 3 × `nop` — the non-FIELDed arm stops RESETTING the arm flag | 🎯 **`n.mix` ONLY** — `FLD_CHAN` is 0 from boot, so only a program that `FIELD`s something *first* can expose the missing reset | the other 20 rows |
| **K-LV2** | the FIELDed arm's destination: `add hl,de` → `nop` — every field starts at buffer offset 0 | 🎯 **`n.fld2` ONLY** | the other 20 rows, `n.fldctl` included (its single field IS at offset 0) |
| **K-LV3** | `lrs_var`: `call pu_deref_body` → 3 × `nop` — store into the DESCRIPTOR, not the body | the **12** non-FIELDed rows that write anything (**not** `n.unset`/`n.empty`, width 0 — see below) | every FIELDed row, `n.aryoor`, `n.num`, `e.*` — 🎯 which is what proves the arms are independently wired |
| **K-LV4** | `lrs_var`: `ld (LRSET_W),a` → 3 × `nop` — the width is whatever the last statement left | the **same 12**, and the coincidence is the point (below) | as K-LV3 |
| **K-LV5** | `ex_rset`: `ld a,1` → `xor a` + `nop` — `RSET` justifies left | 🎯 **`r.ctl`, `r.ary` ONLY** (`r.long` is width-limited: its justify offset is already 0) | all 18 `LSET` rows and `n.fld2` |
| **K-LV6** | `tgt_desc`: `jp z,str_get_key` → `jp str_get_key` — an element is keyed as the scalar of the same name | 🎯 **`n.ary`, `n.aryvar`, `n.ary2d`, `n.arysep`, `r.ary` ONLY** | every scalar row and every FIELDed row |
| **K-LV7** | `aeng_erase`: `call aer_fldfix` → 3 × `nop` | 🎯 **`e.erase` ONLY** | the other 20 rows, `e.ctl` included |
| **K-LV8** | `lrset_common`: `jp z,type_mismatch_error` → `jp z,stmt_error` | 🎯 **`n.num` ONLY** | the other 20 rows |
| **K-LV9** | `call tgt_desc_fix` → `ld hl,(MIDS_DEST)` — drop the `ARYTAB` correction | 🔴 **NOTHING, predicted in advance** (§5.3) | all 21 rows |
| **K-LV10** | `CONTROL_WANT["n.fldctl"]` made unmatchable (probe-only) | exit **2**, 0 scored, and the ROMs must **NOT** move | — (proves the probe fails closed) |

**Five cuts redden exactly the rows that exist for them** — K-LV1, K-LV2, K-LV7,
K-LV8, and K-LV5/K-LV6 within their classes.

⚠️ **K-LV3 AND K-LV4 ARE PREDICTED TO HAVE THE *SAME* RED SET, AND THAT IS SAID
UP FRONT RATHER THAN DISCOVERED.** The obvious expectation is that the width cut
also reddens `n.unset`/`n.empty` — it does not, because the width those rows want
is **0** and the width a cut leaves behind is the boot value, also **0**. A cut
whose wrong answer coincides with the right one is invisible, and §4.3's width-0
path is therefore knifed by the **host unit test** (`LSET w0 -> nothing written`,
[`tests/test_field.py`](../tests/test_field.py)), where the destination can be
poisoned and inspected directly, not by a screen row.

🔴 **K-LV1, K-LV2, `n.mix`, `n.fld2` AND `n.arysep` EXIST BECAUSE THE CUTS WERE
DRAFTED FIRST.**
Asking *"which row moves?"* of three planned changes answered **none**
([[draft-the-knives-before-freezing-the-row-set]]):

* **the destination generalisation** (§4.1b) — with a single field at buffer
  offset 0, a destination that dropped the offset entirely still reads back
  correctly, so `n.fldctl` and `n.fldary` are both green under a broken §4.1b.
  `n.fld2` FIELDs **two** widths so the second one's offset is visible.
* **the arm discriminator** (§4.2) — a discriminator stuck at "fielded" is caught
  by the non-FIELDed rows and one stuck at "not fielded" by the FIELDed rows, but
  neither says the choice is made **per target**. `n.mix` holds both kinds in one
  program.
* **the element resolve** — with one element in play, a resolve that always
  returned the same slot agrees with itself. `n.arysep` writes `A$(2)` and reads
  **both** elements back.

⚠️ **K-LV9's predicted miss is stated, not discovered.** A knife whose predicted
result is "nothing moves" is indistinguishable from a build that did not happen —
which is what the ROM-hash guard is for. Report it as a **predicted miss** with
the reason, never as "reddened nothing"
([[rule-gated-structurally-has-no-knife]]).

---

## 9. Denominator

Scored by `lrvar-acceptance`: **(VERB: `LSET` / `RSET`) × (TARGET FORM: scalar /
array element) × (SOURCE vs TARGET LENGTH: shorter / equal / longer)**, plus the
two degenerate target STATES a single reading cannot separate (never assigned /
assigned `""`), plus whether `LEN()` moves, plus the subscript FORM (literal /
variable) and RANK (1-D / 2-D), plus the out-of-range and numeric-target **error
faces**, plus the three IDENTITY rows §8's cuts forced, plus one positive control
**per arm**, plus the `ERASE` pair.

**Not covered, and named rather than implied:** `RSET` as a distinct *parse site*
(it shares `lrset_common`); a target that is its own source (`LSET A$=A$` — the
store space-fills before it reads, so an alias is destroyed, and the reference's
answer is **not measured**); a subscript that is itself an array element; a string
GC that moves the target's body *during* the RHS (unreachable — no program either
reference accepts allocates a scalar mid-statement); `ERASE` of the array a field
names *itself* (§5.4's middle row — the slot is freed, and the reference's answer
for that arrangement is not measured either); and the second reference, which does
not exist for any row in this document.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `76685e9`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/field.asm`](../basic/field.asm) | `lrset_common` restructured: the FIELDed arm computes `LRSET_DEST`, the `=`/RHS parse is shared, an arm test on `FLD_CHAN` picks the store setup, `lrs_var` resolves the target's descriptor → width + body, and `lrset_notfld` snapshots instead of erroring; `jp z,stmt_error` → `jp z,type_mismatch_error`; the header's pre-slice-4c string-layout claim corrected |
| [`basic/sysvars.inc`](../basic/sysvars.inc) | `LRSET_OFF` → `LRSET_DEST`, same address, **0 RAM** |
| [`sub/lrsetst.asm`](../sub/lrsetst.asm) | the tenant loads the destination instead of computing `FSECTOR_BUF + offset` — **4 B smaller** |
| [`sub/arrays.asm`](../sub/arrays.asm) | **new** `aer_fldfix` + its call in `aeng_erase` — the `ERASE` key fix-up (§5.4) |
| [`tests/test_field.py`](../tests/test_field.py) | the store cases re-poked on `LRSET_DEST`, **plus two new ones**: a destination outside `FSECTOR_BUF`, and the width-0 no-op with a poisoned destination |
| [`probes/basic/basic_probe_lrvar.py`](../probes/basic/basic_probe_lrvar.py) | **new**, 21 rows, 3 positive controls — one per arm |
| [`Makefile`](../Makefile) | `lrvar-characterize` + `lrvar-acceptance`, both `.PHONY` |

### 10.2 The walls, measured from clean — **all five exact**

`rm -rf build && make basic-reloc`:

| wall | at `76685e9` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 35 B | ≈6 B (+29) | **6 B** | ✅ |
| **main low region** | 6 B | 6 B (0) | **6 B** | ✅ |
| **sub page 0** | 3696 B | ≈3604 B (+92) | **3604 B** | ✅ |
| sub page 1 | 1483 B | unchanged | **1483 B** | ✅ |
| RAM | — | 0 | **0** | ✅ |

🎯 **THE PRICE WAS EXACT ON EVERY NUMBER, AND THE REASON IS §6.2.** The counter
was calibrated 12/12 against the `.sym` *before* it was quoted — including
`lrset_common` itself, hand-counted instruction by instruction to the byte at 81
([[calibrate-a-hand-counter-before-quoting-it]]). D-ARYLV recorded the same
result from the same discipline; this is the second slice in a row where
calibrating first turned a bound into a prediction.

### 10.3 The ROM hashes — **all four predicted before the build**

| ROM | at `76685e9` | §6.4 predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `a494c9de…` | MOVES | **`60419f46…`** ✅ |
| `sub.rom` | `f4c16277…` | MOVES | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `7dbdf411…` | MOVES | **`963246fa…`** ✅ |

`disk.rom` holding is the only positive statement in the set, and it is the one
that matters: a moved `disk.rom` would mean this slice reached a component it has
no business in.

### 10.4 The gates — **every counter landed on its predicted value**

| gate | before | predicted | measured |
|---|---|---|---|
| **`lrvar-acceptance`** | 5/21 | 21/21 | **21/21 agree, 0 diverge** ✅ |
| `lvsites-characterize` | 8/10 | **10/10** | **10/10** ✅ |
| `fldary-acceptance` | 13/13 | unchanged | **13/13** ✅ |
| `lvfix-acceptance` | 18/18 + 4 def | unchanged | **18/18 + 4 deferred** ✅ |
| `unit-test` | 59 | 59 | **59** ✅ |
| `audit-citations` swept / basic | 746 / 194 | 748 / 195 | **748 / 195** ✅ |
| `injector-check` | 341 | 342 | **342** ✅ |
| `rowshape-check` | 182/35/11/11/0 | 183/36/12/12/0 | **183/36/12/12/0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| `latch-check` | 16/16 | unchanged | **16/16** ✅ |
| sub page-0 closure | 729 + 15, 14 tenants | 733 + 15, 14 | **733 + 15, 14** ✅ |
| sub page-1 closure | 585 + 43 | unchanged | **585 + 43** ✅ |
| `deadcode` main / sub | 0 / 0 (+1) | unchanged | **0 / 0 (+1)** ✅ |

🎯 D-FLDARY missed `audit-citations` and the closure counter by predicting from
what the slice *writes* rather than from what the checker *walks*. Both were
re-derived from the checkers' own definitions here — files swept, not language
files; routines in the closure, not tenants — and both are exact
([[a-count-is-predicted-by-reading-its-definition]]).

### 10.5 🎯 THE DECLINE'S PRICE WAS RIGHT; ITS *FIX* WAS THE WRONG ONE

Set against [`spec-basic-fldary.md`](spec-basic-fldary.md) §5.4, measured:

| §5.4's claim | outcome |
|---|---|
| an `ERASE`d fielded array leaves a stale `FLD_TAB` entry | ✅ **STOOD.** `e.erase` is red at `76685e9`, and K-LV7b reddens it and nothing else |
| there is **no oracle** for it | ✅ **STOOD AT THE TIME, and the reading is now taken:** the CF-3300 **KEEPS** the field across `ERASE` of a sibling array |
| the fix is an `fld_clear_ary` sweep — *clear every entry whose `k0 ≥ $80`* | ❌ **REFUTED BY THE ORACLE.** That implements *drop*; the reference does not drop, so it would have left `e.erase` red — for 23 bytes |
| ≈20 B page 1 + 3 B LOW | ❌ **FELL WITH THE SITING.** `aeng_erase` is already a page-0 tenant holding both ends of the compaction, so the real fix is **0 B of main page 1** and 96 B of sub page 0 |

🎯 **Both of the decline's numbers were about a design, and the design was wrong
in the same way twice** — wrong *behaviour* (drop vs keep) and wrong *site*
(resident vs the tenant that already had the data). Declining it for want of an
oracle was nonetheless correct: had the 23 bytes been spent on the argument
available then, they would have bought a still-red row
([[a-priced-decline-is-a-claim-about-a-design]]).

### 10.6 Knives — 10 cuts × 2 rounds, **7 EXACT, 2 refuted a claim, 1 re-sited**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly, `--sides zb` (the reference column is a constant; a cut in zerobas can
only move zerobas). Snapshot restore in a `finally`; `rm -rf build` + full rebuild
+ repack before every run including each baseline; ROM-hash guard per cut; rows
via `probe_report.parse()` compared as `{label → zb value}` with a 21-row refusal.
**Both rounds were identical on all ten cuts** — no flakiness anywhere.

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-LV1** | `lrset_notfld`: `ld (FLD_CHAN),a` → 3 × `nop` | `n.mix` | 🔴 **14 rows** — `n.mix` swapped exactly as predicted, 13 others crashed | ❌ ×2, see (a) |
| **K-LV2** | FIELDed arm: `add hl,de` → `nop` | 🎯 `n.fld2` ONLY | **`n.fld2`, exact** | ✅ ×2 |
| **K-LV3** | `lrs_var`: `call pu_deref_body` → 3 × `nop` | the 12 writing non-FIELDed rows | **12, exact** — every FIELDed row, `e.*`, `n.aryoor`, `n.num` GREEN | ✅ ×2 |
| **K-LV4** | `lrs_var`: `ld (LRSET_W),a` → 3 × `nop` | the same 12 | 🔴 **5 rows** — and the 5 are the interesting ones | ❌ ×2, see (b) |
| **K-LV5** | `ex_rset`: `ld a,1` → `xor a` + `nop` | 🎯 `r.ctl`, `r.ary` ONLY | **exactly those two** | ✅ ×2 |
| **K-LV6** | `tgt_desc`: `jp z,str_get_key` → `jp str_get_key` | 🎯 the 5 array rows ONLY | **exactly those five** | ✅ ×2 |
| **K-LV7** | `aeng_erase`: `call aer_fldfix` → 3 × `nop` | `e.erase` ONLY | **BUILD REFUSED** — `check_dead_code.py`, *4 unreachable spans* | ❌ re-sited, see (c) |
| **K-LV7b** | `aer_fldfix`: `bit 7,a` → `bit 7,b` (`CB 7F`→`CB 78`) — every entry takes the "a NAME key never moves" exit | 🎯 `e.erase` ONLY | **`e.erase` ONLY**, `HI␣␣␣␣␣␣␣␣` → **`` (empty)** | ✅ ×2 |
| **K-LV8** | `jp z,type_mismatch_error` → `jp z,stmt_error` | 🎯 `n.num` ONLY | **`n.num`, exact** | ✅ ×2 |
| **K-LV9** | `call tgt_desc_fix` → `ld hl,(MIDS_DEST)` | 🔴 **NOTHING** | 🔴 **the 5 array rows** | ❌ ×2, see (d) |
| **K-LV10** | `CONTROL_WANT["n.fldctl"]` unmatchable, `--sides zb` | exit 2 | **rc 0** — the path is unreachable on that invocation | ❌ re-sited, see (e) |
| **K-LV10b** | the same cut against the GATE's `--sides cf3300,zb` | exit **2**, `NOT MEASURED` | **rc 2 + the banner**, ROMs correctly did **not** move | ✅ ×2 |

🔴 **(a) K-LV1's ROW WAS RIGHT AND ITS REASON WAS WRONG, AND THE DIFFERENCE IS A
FACT ABOUT THE TREE.** The prediction rested on *"`FLD_CHAN` is 0 from boot"*. It
is not: `fld_init` zeroes the field TABLE, and `FLD_CHAN` is a separate scratch
cell that **nothing initialises** — only `ex_field` and `lrset_common` ever write
it. So with the reset cut, a non-FIELDed `LSET` in a program that never opened a
channel calls `fch_select` on **uninitialised RAM**, and 13 rows read
`<NO OUTPUT>` instead of a wrong value. `n.mix` still moved exactly as drafted
(`HI␣␣␣␣␣␣␣␣|LO␣␣␣` → **`LO␣␣␣␣␣␣␣␣|XXXXX`** — the plain `B$` store went into
`A$`'s field and `B$` was left untouched), so the row keeps its place as the only
one that shows the *swap* rather than a crash. 🎯 **The `xor a` is therefore
load-bearing on EVERY non-FIELDed `LSET`, not only after a `FIELD`** — which is
strictly more than §4.2 claimed for it.

🔴 **(b) K-LV4 REDDENED FEWER ROWS THAN PREDICTED AND PROVED MORE.** The stale
width turned out to be **10**, not the 0 the draft assumed, and a too-large width
with **left** justification is *invisible on the target's own bytes*: the fill
runs off the end and `PRINT` only ever shows `LEN(target)` of them. So `n.ctl`,
`n.exact`, `n.long`, `n.len`, `n.ary`, `n.ary2d`, `n.aryvar` and `n.mix` all stayed
**green under a completely wrong width**. What moved is exactly what *can* see it:

* **`n.arysep`** — `XXXXX|HI␣␣␣` → **`␣␣␣␣␣|HI␣␣␣`**: the target is right and the
  **neighbouring element** was overwritten by the overrun. 🎯 The identity row
  drafted for the element resolve turned out to be the only row that can see a
  width overrun at all.
* **`r.ctl` / `r.ary` / `r.long`** — the justify offset is `width − ncopy`, so a
  wrong width moves the bytes *outside* the target entirely (`␣␣␣␣␣`, `␣␣`).
* **`n.unset`** — `| 0 ` → **`Syntax error`**: a width-10 store through an unset
  target's absent body pointer is a **wild write** that takes the program down.

🎯 **THAT LAST ONE CONFIRMS §4.3 BY EXPERIMENT.** The spec argued that width-0 is
what makes an unset target safe; K-LV4 removes the width and the unset row is the
one that *crashes*. And it corrects §8's own draft, which predicted `n.unset`
would **not** move because "stale 0 == correct 0" — the stale value is not 0, and
the safety is not a coincidence ([[knife-that-reddens-nothing-is-the-finding]] in
its inverse form: a knife that reddens a *different* set is the finding).

⚠️ **(c) K-LV7 IS THE DEAD-CODE RULE FIRING ON A KNIFE THAT HAD READ IT.**
`call aer_fldfix` → 3 × `nop` orphans the label **and its three `afx_*` locals**;
`make` stopped in `check_dead_code.py` with *"4 unreachable span(s)"* and the
runner correctly scored `ABORT(build)` rather than a miss. Re-sited into the
**body** — `bit 7,a` → `bit 7,b`, where `B` is the 16..1 slot counter so bit 7 is
always clear and every entry takes the *"a NAME key never moves"* exit — it is
exact ×2, the sweep still runs, no label is orphaned and no address outside
`FLD_TAB` is touched. D-MOUNTROW recorded this exact rule and D-DKNAME lost a
knife to it; **reading it is not the same as siting against it.**

🔴 **(d) K-LV9 IS THE ONE THAT CHANGED THE DOCUMENT.** It was drafted as a
*predicted miss* — "the `ARYTAB` correction is unfalsifiable, like D-LVFIX's" —
and it reddened all five array rows (`HI␣␣␣` → `XXXXX`, the store landing
nowhere). The inherited argument is about **drift**, and `tgt_desc_fix` does not
guard drift: `tgt_desc` stashes an element as `elem − ARYTAB`, an **offset**, so
the re-add is the only thing that makes it an address again. §5.3 is corrected
in place. 🎯 **A predicted miss is a claim like any other, and this one was
copied from a neighbouring slice instead of derived from this one**
([[filed-justification-is-a-claim]]).

⚠️ **(e) K-LV10 WAS SITED AGAINST THE RUNNER'S INVOCATION AND THE PROPERTY LIVES
ON THE GATE'S.** The probe's control check **skips `zb` by construction** — only a
REFERENCE can say the apparatus is broken — so with `--sides zb`, the invocation
the knife runner makes, the fail-closed path is structurally unreachable and the
cut scored rc 0. Re-sited against `--sides cf3300,zb` (three rows, to keep it
cheap) it is rc **2** with the `NOT MEASURED` banner, ×2. 🎯 dev-workflow says
*"site a probe-only knife against the invocation the RUNNER makes"*; the sharper
form this adds is **"…and check that the invocation the runner makes can still
REACH the property"** — a runner that narrows its sides for speed can narrow the
guard out of existence.

### 10.7 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`, so `lnblank-acceptance REPEAT=2` would be one target name),
**27 targets, all rc=0**: `unit-test` 59 · `audit-citations` CLEAN (748 swept) ·
`preflight-check` 181/86/95/95/0 · `injector-check` 342 · `rowshape-check`
183/36/12/12/0 · `latch-check` 16/16 · `deadcode` 0/0 ·
`lnblank-acceptance REPEAT=2` 539/539 · `lnblank-say-acceptance` 204/204 ·
`logicops-acceptance` 193/193 · `float-acceptance` · `linemax-acceptance` 60/60 ·
`dexp5-pin` 16 · `editverb-acceptance` 61/61 · `lptverb-acceptance` 44/44 ·
`dskmsg-acceptance` 5/5 · `diskbasic-acceptance` 34/34 verbs ·
`fat-error-acceptance` · `runtail-acceptance` 9/9 · `castail-acceptance` 31/31 ·
`cassave-acceptance` 20/20 · `readvar-acceptance` 24/24 · `arylv-acceptance`
16/16 · `inputary-acceptance` 7/7 · **`lvfix-acceptance` 18/18** ·
**`fldary-acceptance` 13/13** · **`lrvar-acceptance` 21/21**. Plus
`lvsites-characterize` **10/10** (not a gate).

⚠️ `latch-check` is still the one target in the list with **no
`repack-machine` prerequisite**, so the script builds explicitly before the loop
rather than letting the first target do it. D-FLDARY's run hit the exit-2 that
omission causes and recorded it; this one avoids it by construction, which is the
right disposition for a known apparatus trap.

### 10.8 The fix, as a program

Both columns are readings from the runs above.

```basic
10 A$="XXXXX"
20 LSET A$="HI"
30 PRINT "[";A$;"]";LEN(A$)
```

| | screen after `RUN` |
|---|---|
| National CF-3300 | `[HI   ] 5` |
| zerobas **before** | `Syntax error in 20` |
| zerobas **after** | `[HI   ] 5` |

🎯 **The length is the whole rule**, and `RSET` on a target too short for its
source is where a hand-written store would have guessed wrong:

```basic
10 A$="AB"
20 RSET A$="HELLO"
30 PRINT "[";A$;"]"
```

| | screen after `RUN` |
|---|---|
| CF-3300 / zerobas **after** | `[HE]` — the FIRST two bytes, not the last two |
| zerobas **before** | `Syntax error in 20` |

An array element is the same target, and the neighbour must not move —
the row that a resolve landing on one fixed slot would fail:

```basic
10 DIM A$(3)
20 A$(1)="XXXXX"
30 A$(2)="YYYYY"
40 LSET A$(2)="HI"
50 PRINT "[";A$(1);"|";A$(2);"]"
```

| | screen after `RUN` |
|---|---|
| CF-3300 / zerobas **after** | `[XXXXX|HI   ]` |
| zerobas **before** | `Syntax error in 40` |
| under **K-LV4** (the width cut) | `[     |HI   ]` — 🎯 the target is right and the NEIGHBOUR was overwritten by the overrun |

And the `ERASE` row, which is why §5.4 is in this slice and not the next one:

```basic
10 DIM A$(3),B$(3)
20 OPEN"LR.DAT"AS #1
30 FIELD#1,10 AS B$(1)
40 ERASE A$
50 LSET B$(1)="HI"
60 PRINT "[";B$(1);"]"
```

| | screen after `RUN` |
|---|---|
| CF-3300 | `[HI        ]` |
| zerobas **before** | `Syntax error in 50` — loud |
| zerobas **after** | `[HI        ]` |
| under **K-LV7b** (the fix-up cut) | `[]` — 🔴 **silent**, which is what the fix-up exists to prevent |
