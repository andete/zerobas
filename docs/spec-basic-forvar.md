# D-FORVAR — what a `FOR`/`NEXT` loop variable may BE

*Slice D-FORVAR, 2026-08-08, on `main`, based on `79f6bdb` (D-LRVAR).*

The last of D-READVAR's own class: `ex_for` still parses its loop variable with
the **single-letter shim `ex_read` stopped using**, in a verb that slice never
re-checked. `TODO.md` filed it with three measured rows and the note *"not
carve-scouted"*.

🎯 **BOTH REFERENCES, EVERY ROW.** `FOR`/`NEXT` is core BASIC and a diskless
VG-8020 answers it, so unlike the whole lvalue/FIELD arc (which rested on the
CF-3300 alone) every reading here has **two** independent oracles.

---

## 1. The rule — **measured before it was designed, not inferred**

🔴 **THREE READINGS ARE NOT A RULE.** The filed residual carried `f.two`,
`f.pct` and `f.ary`. Those say the NAME parse diverges. They do not say what the
rule *is*, and `FOR` differs from `READ` in the one way that matters: **`NEXT`
matches on the stored name**, so widening the name moves the match, the frame
layout and the nesting depth with it.

**32 rows, three sides, measured 2026-08-08 BEFORE a byte was written** —
[`forvar-msx1-characterization.md`](forvar-msx1-characterization.md) is the
table and **both references agree on all 32**. The rule that falls out:

> A `FOR` loop variable is an **ordinary scalar variable REFERENCE** — any name
> (2 significant characters), any explicit type suffix, the DEFtbl default when
> there is none. It is **not** an array element. `NEXT` matches a frame on the
> **whole identity**: both name characters **and the resolved TYPE**. A `$` name
> is `Type mismatch` as a `FOR` variable and **matches nothing** as a `NEXT`
> variable.

🎯 **THE FOUR READINGS THAT DECIDED THE DESIGN ARE ONES THE FILED RESIDUAL COULD
NOT HAVE PREDICTED**, and each is a byte:

| row | reading | what it forces |
|---|---|---|
| `n.xtype` — `FOR A%=1 TO 3` / `NEXT A` | **NEXT without FOR** | the frame key is `(name0,name1,TYPE)` and the compare is **3** bytes, not 2 |
| `n.prefix` — `FOR AB=1 TO 3` / `NEXT A` | **NEXT without FOR** | the shipped 1-char match is not merely too strict — here it is too **LOOSE**, and answers "match" |
| `n.strnx` — `FOR A=1 TO 3` / `NEXT A$` | **NEXT without FOR** | ⚠️ **NOT `Type mismatch`.** The obvious symmetry with `FOR`'s own guard would answer the wrong error |
| `f.defstr` — `DEFSTR A` / `FOR AB=1 TO 3` | **Type mismatch** | the guard is on the **resolved type**, not on the `$` character |

⚠️ **`n.strnx` IS THE ROW THE DESIGN TURNS ON.** A `$` `NEXT` name must be
*unmatchable*, not *rejected* — which is why §4.2 spends its bytes on the TYPE
CODE rather than on a parse-time guard, and why `ex_next` gains no error path at
all.

---

## 2. What is wrong, in one sentence

* **`ex_for`** ([`basic/program.asm:1488`](../basic/program.asm)) — `call
  is_letter` / `call upcase` / `ld (FOR_CUR),a` / `inc hl`: **one** byte of name,
  no suffix, no DEFtbl, and the frame it pushes has a **1-byte** variable field
  that `ex_next` compares with a single `cp c`.

---

## 3. Scope

**In:** the `FOR` loop variable's NAME (1-, 2-, 3+-character, letter+digit) and
its TYPE (`%` `!` `#`, the DEFtbl default, and `$` as an error face); `NEXT`'s
own name parse and its frame match including the TYPE; a bare `NEXT`, a
mismatching `NEXT`, a `NEXT` that closes an inner frame, and a bare `NEXT` that
follows a named one; nesting DEPTH; the `A`/`A%`/`A$` identity; and — forced by
§4.2, not chosen — **a `$` name reaching a NUMERIC factor** (`x.numstr`).

**Out, and named rather than implied:**

* 🔴 **The multi-variable `NEXT` (`NEXT B,A`).** Measured, DIVERGENT, and a
  **different rule**: `n.multi1` is the identical comma with the single-letter
  names `ex_for` already parses and is still `Syntax error`, so no name fix can
  turn it green. `nx_end`'s `jp exec_stmt` puts the `,` in statement position.
  Both rows stay **measured and printed, never scored**; filed as its own
  residual ([[one-row-cannot-separate-two-rules]]).
  ✅ **CLOSED 2026-08-08 by D-NXLIST** ([`spec-basic-nxlist.md`](spec-basic-nxlist.md)),
  which measured 28 rows on three sides and shipped for **−10 B of page 1**.
  Both rows are scored again and this slice's gate is **33/33** (§10.4).
  🎯 The deferral was worth more than a fold-in: the fix lives entirely in
  `nx_end`/`ex_next`'s comma path and touches nothing in §4's name rule
  ([[a-deferral-honoured-is-worth-more-than-one-filed]]).
* **`FOR A(1)=`** — `Syntax error` on both references, and it must **stay** so.
  Carried as a NEGATIVE control (`f.ary`).
* **A float-valued loop** (`STEP .5`) — the loop MATH is int16 in this tree by
  D-D and is not this slice's to change.
* **`NEXT A(1)`** — unmeasured; `for_name` parses the name and the `(` then
  reaches statement position, i.e. it inherits the multi-variable residual's
  shape rather than getting an answer of its own.
  📏 **MEASURED 2026-08-08 by D-NXLIST, and it is a THIRD rule, not this
  shape.** `NEXT A(1)` is **NEXT without FOR** and `NEXT A(99)` is **Subscript
  out of range** on both references — so a `NEXT` operand is a complete variable
  REFERENCE whose subscript is EVALUATED before any frame is matched. That
  refutes the 8-byte "unmatchable key on `(`" fix (it would answer the wrong
  error) and moves the item into the D-ARYLV / lvalue family. Three rows
  deferred in `nxlist-acceptance`; residual in `TODO.md`
  ([[a-priced-decline-is-a-claim-about-a-design]]).
* **A space between the name and its suffix** (`FOR A $=1`) — the shipped code
  runs `skip_spaces` before its `cp '$'` and this one does not (`var_name_key`
  is lexically contiguous). Unmeasured on either side; named, not fixed.

---

## 4. Design

### 4.1 🎯 THE FRAME STOPS HOLDING A LETTER AND STARTS HOLDING AN IDENTITY

`FOR_CUR` / the `FOR` stack frame, **9 → 11 bytes**:

| offset | before | after |
|---|---|---|
| 0 | loop variable, **1 char** | `name0` |
| 1 | limit | `name1` (letter/digit, or 0) |
| 2 | " | **type** (2 int / 4 single / 8 double) |
| 3..4 | step | limit |
| 5..6 | CURLINE | step |
| 7..8 | resume ptr | CURLINE |
| 9..10 | — | resume ptr |

**The TYPE is in the frame because `n.xtype` says so**, not for tidiness: the
reference refuses to match `FOR A%` with `NEXT A`, so the type is part of the
key and the compare is three bytes. It is *also* what `var_load_fac` /
`var_store_fac` need — `var_find_typed` keys on `(name0,name1,type)` — so one
field serves the match and the store.

### 4.2 🔴 THE `$` DISCRIMINATOR IS A TYPE CODE THAT ALREADY EXISTS, AND MAKING IT HONEST IS THE WHOLE TRICK

`var_name_key`'s `vnk_dollar` writes **`(VARTYPE)=8`** for a `$` suffix — byte
for byte a default-double `A`. Five comments in this tree exist to warn readers
about that lie (`basic/arrays.asm:535`, `:604`, `:654`, `basic/missing.asm:429`,
`basic/expr.asm:1851`). **This slice changes it to `DEFTBL_STR`**, the code the
*same cell* already carries for a DEFSTR'd unsuffixed name:

```
vnk_dollar:     ld      a,DEFTBL_STR        ; was: ld a,8
                ld      (VARTYPE),a
```

Byte-neutral (`ld a,n` either way), and it buys **three** things at once:

1. **`n.strnx`** — `NEXT A$` yields a frame key whose type is `3`, and no frame
   can hold `3` (§4.3 rejects it at `FOR`). It matches nothing, walks the stack
   out and raises **NEXT without FOR** — the measured answer, with **no guard
   and no bytes** on `ex_next` at all.
2. **`f.str` and `f.defstr`** — both become the *same* test on the resolved type
   (`cp DEFTBL_STR`), which is what `f.defstr` says the rule is.
3. 🔴 **`x.numstr`, a defect this slice's characterization FOUND.** `A$="X"` /
   `B=1+A$` reads `Type mismatch` on both references and **` 1 `** here: zerobas
   resolves `A$` to the numeric `A`, reads an unset 0 and **runs on with a wrong
   answer**. `ev_f_var` already guards this through `check_vartype_num`; the
   check works, its *input* lied. This is D-DEFSTR's own class
   ([`spec-basic-deftbl-strcode.md`](spec-basic-deftbl-strcode.md) §3.1 — *"`B=S`
   errored and `B=1+S` silently read 0"*) in the explicitly-suffixed form
   D-DEFSTR did not cover.

⚠️ **THE SAFETY ARGUMENT IS THE TREE'S OWN, RE-DERIVED RATHER THAN INHERITED.**
Ten routines read `(VARTYPE)`; every one is on a numeric arm behind a
`var_str_type` test, and `DEFTBL_STR` **already reaches all of them today** via
the DEFSTR path, so the new value lands in an equivalence class that is already
handled rather than in a new one. The one reader that is not behind such a test —
`check_vartype_num`, called unconditionally from `ev_f_var` — exists precisely to
turn this value into ERR 13, which is `x.numstr`'s measured answer. **K-FV3 is
the knife**, and it has rows.

### 4.3 One shared name parse, called from both verbs

```
; for_name: HL at the loop variable's first letter (caller has run is_letter).
; out: FOR_CUR[0..2] = (name0, name1, type); A = the type; HL past name+suffix.
for_name:       call    var_name_key        ; BC = key, HL past name + suffix,
                ld      (FOR_CUR),bc        ;   (VARTYPE) = the resolved type
                ld      a,(VARTYPE)
                ld      (FOR_CUR+2),a
                ret
```

`ex_for` follows it with the type error face; `ex_next` follows it with nothing:

```
ex_for:         inc     hl
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error
                call    for_name
                cp      DEFTBL_STR          ; f.str + f.defstr: ERR 13, not ERR 2
                jp      z,type_mismatch_error
                call    skip_spaces
                cp      EQ_TOKEN            ; `FOR A(1)=` lands HERE on `(` and is
                jp      nz,stmt_error       ;   Syntax error -- f.ary, unchanged
                ...
ex_next:        inc     hl
                call    skip_spaces
                call    is_letter
                jr      nc,nx_notletter     ; bare NEXT (or junk -> ERR 2)
                call    for_name            ; no `$` guard -- n.strnx wants a MISS
                jr      nx_find
```

🎯 **`FOR_CUR` IS ALSO `NEXT`'S KEY, AND THAT COSTS NO RAM.** `FOR_CUR` is
scratch that only `ex_for` and `nx_have` write, and `nx_have` writes it *after*
the match. So `ex_next` parks its parsed key there and `nx_scan` compares the
frame against it in place; the `ldir` that follows a match overwrites it with the
same three bytes.

A bare `NEXT` marks itself with `name0 = 0` — a value no real name0 can take,
because `is_letter` gated the parse:

```
nx_top:         xor     a
                ld      (FOR_CUR),a         ; 0 = match the TOP frame
```

### 4.4 The match becomes a 3-byte compare

```
nx_scan:        ld      hl,(FSP)
                ld      de,-FOR_FRAME
                add     hl,de               ; HL = top frame base
                ld      a,(FOR_CUR)
                or      a
                jr      z,nx_have           ; bare NEXT accepts the top frame
                push    hl
                ld      de,FOR_CUR
                ld      b,3                 ; name0, name1 AND TYPE -- n.xtype
nx_cmp:         ld      a,(de)
                cp      (hl)
                inc     hl                  ; INC touches no flag, so the CP result
                inc     de                  ;   survives to the JR below
                jr      nz,nx_miss
                djnz    nx_cmp
                pop     hl
                jr      nx_have
nx_miss:        pop     hl
                ld      (FSP),hl            ; mismatch -> close this inner frame
                ld      de,FOR_STK
                or      a
                sbc     hl,de
                jp      z,nx_nofor          ; ran out -> no matching FOR
                jr      nx_scan
```

⚠️ **The shipped `nx_scan` reloads `ld hl,(FSP)` on the line after `ld (FSP),hl`
— 3 dead bytes**, and this slice banks them. The frame-base computation becomes
`ld de,-FOR_FRAME` / `add hl,de` (arithmetic) while the two FOR_STK bound tests
keep `or a` / `sbc hl,de` (comparisons, where the Z flag **is** the result) — 2
more bytes, and the distinction is why they are not made uniform.

### 4.5 The two shims stop being single-letter, and `FOR_NEW` dies

`var_get` / `var_set` (`basic/vars.asm`) are documented as *"single-letter
compatibility shims … used by FOR/NEXT and READ"*. **D-READVAR retired READ's
use of them**, so `ex_for`/`ex_next` are their only three call sites. They are
renamed and re-pointed at the frame:

```
for_get:        ld      bc,(FOR_CUR)
                ld      a,(FOR_CUR+2)
                jp      var_load_fac        ; FAC/FACTYP=type, DE=int16 (tail)
for_set:        ld      bc,(FOR_CUR)
                ld      a,2
                ld      (FACTYP),a          ; the loop MATH stays int16 (D-D)
                ld      a,(FOR_CUR+2)
                jp      var_store_fac       ; coerced into the target's own type
```

Each loses `call upcase` / `ld b,a` / `ld c,0` / `call deftbl_num_type`, and each
call site loses its `ld a,(FOR_CUR)`. 🎯 **`deftbl_num_type` loses its only
callers and is deleted** — its `ERR 13 on a DEFSTR letter` job moved to parse
time, where `f.defstr` says the reference puts it.

And `nx_have`'s stepped value moves from the `FOR_NEW` cell to the **stack**:

```
                ld      hl,(FOR_CUR+5)      ; step
                add     hl,de               ; HL = stepped
                push    hl                  ; [stepped]
                ex      de,hl
                call    for_set
                ld      hl,(FOR_CUR+5)      ; the test depends on the step SIGN
                bit     7,h
                pop     hl                  ; HL = stepped (POP touches no flag)
                jr      nz,nx_neg
```

One `push`/`pop` replaces one store and **two** loads on mutually exclusive
branches: **−7 bytes and −2 RAM**.

### 4.6 RAM — the crowded page GAINS 72 bytes

| cell | before | after |
|---|---|---|
| `FOR_CUR` | `$E045`, 9 B | `$E045`, **11 B** — exactly the span `FOR_NEW` vacates, `GOSUB_STK` still at `$E050` |
| `FOR_NEW` | `$E04E`, 2 B | **DELETED** (§4.5) |
| `FOR_STK` | `$E070`, 8 × 9 = 72 B | **`$EA3A`**, 8 × 11 = **88 B**, `FOR_STK_END` `$EA92` |
| `$E070..$E0B8` | FOR stack | **72 B FREED** |

🔴 **`FOR_DEPTH` STAYS 8, AND THAT IS WHAT THE MOVE BUYS.** 8 × 11 = 88 does not
fit at `$E070` (`DATASTATE` is at `$E0B8`), and the page-`$E0` map is full — so
the honest choices were "relocate" or "6 nested loops instead of 8". `f.dep8` is
the row that makes that a measurement rather than a preference.

⚠️ **AND THE FREE-RAM WINDOW IS ONE BYTE SMALLER THAN THE TREE SAYS.**
`basic/sysvars.inc:3003` reads *"`$EA39..$EAFF` free"*; D-LPTVERB took `$EA39`
for `LPTPOS` and the comment was never updated. The real window is
**`$EA3A..$EAFF`** (198 B) and this slice corrects the comment as well as using
it. 110 B remain after the FOR stack.

---

## 5. Forced constraints — each is a thing the design is NOT free to choose

### 5.1 🔴 THE TYPE IS IN THE MATCH KEY BECAUSE `n.xtype` SAYS SO

The obvious frame key is the 2-byte `(name0,name1)` every other reference in this
tree uses, with the type re-derived from the DEFtbl at `NEXT` time. **`f.pct`
alone refutes the re-derivation** (`A%` resolves to int, `A`'s DEFtbl default is
double, so the loop would store into one entry and `PRINT A%` read another), and
**`n.xtype` refutes the 2-byte match** independently: the reference will not
match `FOR A%` with `NEXT A`. Two rows, two different failures, one field.

### 5.2 🔴 `NEXT A$` MUST *MISS*, NOT *ERROR*

Symmetry says `ex_next` should reject a `$` name the way `ex_for` does. The
reference says otherwise (`n.strnx` = **NEXT without FOR**), and a `jp
c,type_mismatch_error` there would have been 6 bytes spent to produce the wrong
message. §4.2's type code makes the miss automatic instead.

### 5.3 The loop MATH is untouched, and that is a boundary not an omission

`for_set` still tags the value `FACTYP=2` and the limit/step are still int16.
D-D deferred a float-valued loop and this slice does not reopen it: what changes
is **which cell the loop variable is**, not what arithmetic runs over it. That is
why `f.hash` (`FOR A#`) is a row — a double-typed loop variable holding int16
values is the shape this slice does ship.

### 5.4 🔴 THE `$` TYPE CODE REACHES BEYOND `FOR`, AND IT IS MEASURED THERE

§4.2 changes a routine every variable reference in the tree runs. The
consequences outside `FOR` are **not** assumed to be nil: `x.numstr` and
`x.strtop` are in this slice's own gate, on both references, precisely so the
side effect is a scored row rather than a silent behaviour change
([[a-rule-can-claim-more-than-its-evidence]]).

### 5.5 The `FOR` stack is emptied through its SYMBOL, so the move is free

`clear_vars` ([`basic/vars.asm:1018`](../basic/vars.asm)) resets `FSP` with `ld
hl,FOR_STK` — cold boot, `RUN`, `NEW` and `CLEAR`, the four sites D-DIR-2
established. Nothing anywhere hardcodes `$E070`. The one place the old address is
written down is a **docstring** in
[`probes/basic/basic_probe_direct_ctrl.py:21`](../probes/basic/basic_probe_direct_ctrl.py)
(*"57456 after any RUN"*), which this slice updates.

---

## 6. The carve scout

All spans off `build/basic-reloc.sym` from a clean `rm -rf build && make
basic-reloc` at `79f6bdb`; walls printed by that build (low **6 B**, page 1
**6 B**, sub p0 **3604 B**, sub p1 **1483 B**; `basic-reloc.rom 60419f46…`,
`sub.rom accce5a1…`).

### 6.1 Which region each file lives in — asked before anything is priced

`python3 tools/carve_scout.py build/basic-reloc.sym --files <f>`:

| file | labels in page 1 | region | what this slice does there |
|---|---|---|---|
| `basic/program.asm` | **152 of 152** | **page 1** | `ex_for`, `ex_next`, the new `for_name` |
| `basic/vars.asm` | **59 of 59** | **page 1** | `vnk_dollar`, `for_get`/`for_set` |
| `basic/arrays.asm` | **0 of 45** | **LOW** | `deftbl_num_type` deleted, `check_vartype_num` folded |
| `basic/input.asm` | 0 of 33 | LOW | untouched |
| `basic/str-engine.asm` | 0 of 103 | LOW | untouched |
| `basic/interp.asm` | 79 of 79 | page 1 | untouched |

🔴 **BOTH WALLS ARE AT 6 B AND THIS SLICE WRITES TO BOTH**, so which one binds is
a real question. It turns out to be page 1 — and the low region ends **richer**,
because the one thing this slice deletes lives there.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **before** any number was
quoted for code that does not exist
([[calibrate-a-hand-counter-before-quoting-it]]):

| routine | hand-count | `.sym` span | |
|---|---|---|---|
| `ex_for` | **70** | **70** | ✅ 🎯 *the body being edited* |
| `ef_step` | 4 | **4** | ✅ |
| `ef_havestep` | 48 | **48** | ✅ |
| `ef_over` | 10 | **10** | ✅ |
| `ex_next` | 16 | **16** | ✅ 🎯 *the other body being edited* |
| `nx_notletter` | 8 | **8** | ✅ |
| `nx_top` | 2 | **2** | ✅ |
| `nx_find` | 13 | **13** | ✅ |
| `nx_scan` | 34 | **34** | ✅ |
| `nx_have` | 52 | **52** | ✅ |
| `nx_neg` | 14 | **14** | ✅ |
| `nx_again` | 20 | **20** | ✅ |
| `nx_end` | 8 | **8** | ✅ |
| `nx_nofor` | 11 | **11** | ✅ |
| `var_get` | 12 | **12** | ✅ |
| `var_set` | 17 | **17** | ✅ |
| `deftbl_num_type` | 5 | **5** | ✅ |
| `check_vartype_num` + `dnt_check` | 3 + 6 | **3 + 6** | ✅ |

**18/18 exact**, and `ex_for`/`ex_next` — the two bodies this slice rewrites —
were counted **instruction by instruction from the source**, not looked up.
⚠️ `LD (nn),DE` / `LD DE,(nn)` are **4** bytes (`ED 53`/`ED 5B`), `LD (nn),BC` /
`LD BC,(nn)` are **4** (`ED 43`/`ED 4B`), and `LD (nn),HL` / `LD HL,(nn)` are
**3** — which is why the 2-byte key costs 4 to store and 4 to load, and is priced
that way below.

### 6.3 The cost — a BOUND, with the twin named for every part

| body | file | region | before | after | Δ |
|---|---|---|---|---|---|
| `ex_for` (loses `upcase`/`ld (FOR_CUR),a`/`inc hl`/`skip_spaces`/`cp '$'`+`jp z`, gains `call for_name`+`cp`+`jp z`, and `ld a,(FOR_CUR)` before the store) | program.asm | p1 | 70 | **63** | **−7** |
| **`for_name`** (new, §4.3) | program.asm | p1 | 0 | **14** | **+14** |
| `ex_next` (same head swap) | program.asm | p1 | 16 | **14** | **−2** |
| `nx_top` (a 1-byte sentinel becomes a store) | program.asm | p1 | 2 | **4** | **+2** |
| `nx_scan` + `nx_cmp` + `nx_miss` (3-byte compare; **−3** dead `ld hl,(FSP)`, **−2** `add hl,de`) | program.asm | p1 | 34 | **45** | **+11** |
| `nx_have` (**−7** `FOR_NEW`, **−3** the shim's `ld a,(FOR_CUR)`) | program.asm | p1 | 52 | **42** | **−10** |
| `nx_neg` (`FOR_NEW` load gone) | program.asm | p1 | 14 | **11** | **−3** |
| `var_get` → `for_get` | vars.asm | p1 | 12 | **10** | **−2** |
| `var_set` → `for_set` | vars.asm | p1 | 17 | **15** | **−2** |
| `vnk_dollar` `ld a,8` → `ld a,DEFTBL_STR` | vars.asm | p1 | — | — | **0** |
| **main page-1 subtotal** | | | | | **+1** |
| `deftbl_num_type` deleted, `dnt_check` folded into `check_vartype_num` | arrays.asm | **LOW** | 14 | **9** | **−5** |
| sub page 0 / page 1 | — | — | | | **0** |

### 6.4 The bottom line — **no carve is needed, and the reason is nameable**

| region | free at `79f6bdb` | slice | free after |
|---|---|---|---|
| **main page 1** | **6 B** | **+1** | **≈ 5 B** |
| **main low** | **6 B** | **−5** | **≈ 11 B** |
| sub page 0 | 3604 B | 0 | **3604 B** |
| sub page 1 | 1483 B | 0 | **1483 B** |
| RAM (`$E0xx`) | — | **−72 B claimed** | 72 B returned |
| RAM (`$EA3A` window) | 198 B | +88 | **110 B** |

⚠️ **THE MEMORY INDEX SAID "THE NEXT SLICE NEEDS A CARVE" AND THIS ONE DOES
NOT.** The reason is not luck and is not slack: **widening the key is what pays
for widening the key.** Three deletions fall out of the same change —
`upcase`/`ld c,0`/`deftbl_num_type` in both shims (−9), `FOR_NEW` (−7), and
`ex_for`'s bespoke `cp '$'` guard folded into a type check the DEFtbl path needed
anyway — and they cover the new `for_name`, the 3-byte compare and the sentinel
store with **1 byte** left over. Had `for_name` been inlined at both sites
instead of shared, the same design would have cost **+13** against 6 and needed
one ([[a-priced-decline-is-a-claim-about-a-design]] in its inverse form).

⚠️ **A BOUND, not a measured cost.** The instrument is calibrated (§6.2, 18/18)
and every body is written out as the assembly that will be assembled, but the
real number comes from a build ([[filed-justification-is-a-claim]]).

⚠️ **Predicted ROM hashes**, all four, including which should HOLD
([[a-wall-is-a-size-a-hash-is-an-identity]]):
`basic-reloc.rom` **MOVES**; `zerobas-main-eu.rom` **MOVES**; `disk.rom`
**HOLDS at `2c630d3d…`** — no disk-side byte is written; and 🎯 **`sub.rom`
HOLDS at `accce5a1…`**, which is the interesting one. `sub/basic-resident-abi.inc`
is generated from main's `.sym` and D-ARYLV recorded `sub.rom` moving while its
walls held — but every one of the 11 exported addresses (`$3279`…`$3DAD`) lies
**below** the only low-region edit, `deftbl_num_type` at **`$3FEC`, the last code
in the low region**. Nothing the sub-ROM can see moves.

### 6.5 ✅ VERDICT: **GO, unfunded.** +1 B fits 6, the low region ends 5 B RICHER, `FOR_DEPTH` stays 8, and no sub-ROM or disk byte is written.

---

## 7. Predicted GREEN — the reference column IS the prediction

`make forvar-characterize` must read, on the VG-8020, the CF-3300 and zerobas
alike (⚠️ **two references per row**, so a row that agrees agrees three ways):

| row | prediction | |
|---|---|---|
| `c.for` / `c.next` / `c.let` | ` 4 ` / ` 4 ` / ` 7 ` | 🟢 **controls** — green before **and** after |
| `f.two` `f.long` `f.dig` `f.alias` | ` 4 ` | the NAME axis |
| `f.pct` `f.bang` `f.hash` `f.twopct` | ` 4 ` | the TYPE axis |
| `f.str` | `Type mismatch` | green before and after — §4.2 must not re-route it |
| `n.xtype` | `NEXT without FOR` | 🎯 **the row that put the TYPE in the key** |
| `n.two` `n.pct` | ` 4 ` | the named match |
| `n.prefix` `n.wrong` | `NEXT without FOR` | 🎯 `n.prefix` is red because the OLD code is too **loose** |
| `n.strnx` | `NEXT without FOR` | 🎯 §5.2 — a MISS, not an error |
| `n.nest` | ` 3  3 ` | |
| `n.close` | ` 3  1 ` | the stack-walking compare |
| `n.mixnx` | ` 3  3 ` | 🎯 **K-FV9's row**, and it exists because the knife was drafted first |
| `f.dep8` | `OK` | 🔴 green before **and** after — the row that says the key was not bought with a nesting level |
| `f.coll` | ` 9  4 ` | `A` and `A%` are two variables |
| `f.colls` | ` 4 X` | green before and after |
| `f.defint` `f.step` | ` 4 ` / `-2 ` | |
| `f.defstr` | `Type mismatch` | §4.2 clause 2 |
| `f.ary` | `Syntax error` | 🔴 **NEGATIVE control** — green before **and** after |
| `x.numstr` | `Type mismatch` | §4.2 clause 3 — **RED before** (` 1 `), green after |
| `x.strtop` | `Type mismatch` | green before and after — the control on `x.numstr` |
| `n.multi` / `n.multi1` | ` 3  3 ` | ⏸ **DEFERRED**, printed, never scored (§3) |

⇒ **`make forvar-acceptance` scores 30/30** (32 cases − 2 deferred), from
**8/30** at `79f6bdb`.

⚠️ **30 is the SCOPE, not a row count** — §9 names what is left out
([[a-prediction-copied-into-the-result-column]]).

⚠️ **Classify a control failure by WHICH SIDE failed it** — red on a reference =
the fixture is broken (exit 2, score nothing); red on zerobas = an ordinary
divergence, scored ([[classify-a-control-failure-by-which-side-failed-it]]). All
three positive controls and the negative control are green on all three sides
**today**, so either side going red is the instrument.

And the document that has been counting this surface must move:

* `make arylv-acceptance` — **18/18** (up from 16/16): `f.two` and `f.pct` stop
  being DEFERRED there, because this is the slice they were deferred for. ⚠️ Its
  `f.ary` row must stay green — it is the same negative control.

Static counters, each predicted by reading its own check's definition rather than
by counting what this slice writes
([[a-count-is-predicted-by-reading-its-definition]]): `audit-citations` sweeps
**FILES** and this slice adds **three** (this document, the characterization
table and the probe), so 748 → **751** swept, basic provenance-bearing 195 →
**196** (+1 per real `probes/basic/*.py`); `injector-check` 342 → **343**;
`rowshape-check` 183/36/12/12/0 → **184/37/13/13/0**; `preflight-check`
**181/86/95/95/0 unchanged**; `latch-check` **16/16 unchanged**; `deadcode`
**0/0 (+1 allowlisted) unchanged** — ⚠️ *this one is load-bearing rather than
routine*: deleting `deftbl_num_type` while leaving `dnt_check` reachable only by
fallthrough is exactly what that gate refuses, which is why §4.5 folds the two
into one body; sub page-0 closure **733 + 15, 14 tenants unchanged**; sub page-1
closure **585 + 43 unchanged**; `unit-test` **59 unchanged**.

---

## 8. Knives — drafted BEFORE the row set was frozen

Runner discipline is **not** restated here: read
[`dev-workflow.md`](dev-workflow.md) §"Knives" first. `probe_report.parse()`
ships — do not hand-roll a row parser and never diff report LINES. Restore in a
`finally`; `rm -rf build` + full rebuild + repack before every run **including
each baseline**; **assert the ROM hashes MOVED after every cut build** (a
probe-only cut must NOT move them); run every cut TWICE. Cut a label's **BODY**,
not its reference. ⚠️ **A knife may only name symbols the side it edits can
SEE**, and ⚠️ **check that the invocation the runner makes can still REACH the
property being cut** (D-LRVAR's K-LV10 scored a false miss for exactly that).

The knife subject is the probe **`--sides zb`** for every cut except K-FV10: the
reference columns are constants and a cut in zerobas can only move zerobas.

| # | cut (byte-neutral unless noted) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-FV1** | `nx_cmp`: `ld b,3` → `ld b,1` — `NEXT` matches on `name0` alone, i.e. the OLD one-char rule | 🎯 **`n.prefix`, `n.xtype`, `n.strnx`** — the three rows where a first letter is not the whole identity | the other 26, `n.two`/`n.pct`/`n.wrong`/`n.close` included |
| **K-FV2** | `nx_cmp`: `ld b,3` → `ld b,2` — the NAME matches, the TYPE does not | 🎯 **`n.xtype`, `n.strnx` ONLY** — K-FV1's set minus `n.prefix`, which is the proof that byte 3 is the TYPE and bytes 1-2 are the name | the other 27 |
| **K-FV3** | `vnk_dollar`: `ld a,DEFTBL_STR` → `ld a,8` — §4.2 reverted | 🎯 **`f.str`, `n.strnx`, `x.numstr`** — the three things §4.2 claims to buy, and nothing else | the other 26, **`f.defstr` included** (its type comes from `deftbl_lookup`, not from `vnk_dollar` — which is what makes K-FV3 and K-FV4 separable) |
| **K-FV4** | `ex_for`: `jp z,type_mismatch_error` → 3 × `nop` | 🎯 **`f.str`, `f.defstr` ONLY** | the other 28, **`x.numstr` included** — it never reaches `ex_for` |
| **K-FV5** | `for_set`: `ld a,(FOR_CUR+2)` → `ld a,8` + `nop` — the loop variable is always stored as DOUBLE | **`f.pct`, `f.bang`, `f.twopct`, `f.coll`, `f.defint`** — every row whose variable is not the DEFtbl double | `f.hash` and all the unsuffixed rows, whose type IS 8 — 🎯 the coincidence is stated up front, not discovered |
| **K-FV6** | `FOR_STK_END`: `FOR_DEPTH*FOR_FRAME` → `7*FOR_FRAME` | 🎯 **`f.dep8` ONLY** (→ `Out of memory`) | the other 29 — 🎯 the one-row knife for the row that only exists because the frame grew |
| **K-FV7** | `for_name`: `ld (FOR_CUR+2),a` → 3 × `nop` — the type never reaches the frame at all | **broader than K-FV5 and predicted so**: every row whose type differs from the byte the previous statement left there. Reported as a SET, not as "exactly N" | — |
| **K-FV8** | `nx_have`: `pop hl` (the stepped value) → `nop` + a stack leak, **NOT byte-neutral** — ❌ **NOT TAKEN.** A cut that unbalances the stack tests the emulator, not the rule | — | — |
| **K-FV9** | `nx_top`: `ld (FOR_CUR),a` → 3 × `nop` — a bare `NEXT` re-uses whatever key the last `for_name`/`ldir` left | 🎯 **`n.mixnx` ONLY** — a LONE bare `NEXT` re-reads the key `ex_for` itself just wrote and matches its own frame by accident | the other 29, **`c.for`/`f.two`/`f.coll` included**, and that is the point |
| **K-FV10** | `CONTROL_WANT["c.for"]` made unmatchable (probe-only), against **`--sides vg8020,zb`** | exit **2**, 0 scored, `NOT MEASURED`, and the ROMs must **NOT** move | — (proves the probe fails closed) |

**Six cuts redden exactly the rows that exist for them**; K-FV6 and K-FV9 redden
exactly **one** each.

🔴 **K-FV9, `n.mixnx` AND K-FV6, `f.dep8` EXIST BECAUSE THE CUTS WERE DRAFTED
FIRST.** Asking *"which row moves?"* of two planned changes answered **none**
([[draft-the-knives-before-freezing-the-row-set]]):

* **the bare-`NEXT` sentinel** (§4.3) — against every row in the obvious set, the
  scratch cell already holds the right key when a bare `NEXT` reads it, because
  `ex_for` wrote it one statement earlier. Only a bare `NEXT` that follows a
  **named** one can tell. `n.mixnx` is that program.
* **the frame width** (§4.1) — no row in the obvious set nests more than twice,
  so 8 × 11 versus 8 × 9 is invisible and a fix that silently dropped to
  `FOR_DEPTH 6` would score a clean sweep. `f.dep8` is the row, and it is a
  **green-before, green-after** row, which is the only kind that can catch it.

⚠️ **K-FV10 IS SITED AGAINST `--sides vg8020,zb`, NOT `--sides zb`.** The
control check skips a lone `zb` by construction — only a REFERENCE can say the
apparatus is broken — so the narrowed invocation the other nine cuts use would
make this path structurally unreachable and score a false rc 0, which is exactly
what D-LRVAR's K-LV10 did.

---

## 9. Denominator

Scored by `forvar-acceptance`: **(NAME FORM: 1-char / 2-char / 3+-char /
letter+digit) × (TYPE SUFFIX: none / `%` / `!` / `#` / `$`) × (NEXT FORM: bare /
named-matching / named-mismatching)**, plus whether `NEXT` matches on the TYPE,
plus nesting, a named `NEXT` that CLOSES an inner frame, and a bare `NEXT` that
FOLLOWS a named one, plus the nesting DEPTH, plus the `A`/`A%`/`A$` identity,
plus the DEFtbl default, plus `STEP`, plus three positive controls and one
negative control, plus the two rows §4.2 forces outside `FOR` entirely.

**Not covered, and named rather than implied:** the multi-variable `NEXT` (§3 —
measured, divergent, DEFERRED with its own separating row and its own residual;
✅ **closed 2026-08-08 by D-NXLIST**, and this gate is **33/33** since); a
float-valued loop (`STEP .5`, D-D); `NEXT A(1)` (📏 measured by D-NXLIST and a
THIRD rule — §3); a loop variable modified
inside its own body; a loop variable that is also a `DEF FN` parameter; `NEXT`
reached inside a `GOSUB` called from the loop body; a space between a name and
its type suffix (`FOR A $=1`, unmeasured on either reference); and nesting
deeper than 8, where zerobas's fixed 8-frame stack and the references'
stack-bounded limit are different mechanisms and neither is measured against the
other.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `79f6bdb`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/program.asm`](../basic/program.asm) | new `for_name` (shared by both verbs); `ex_for` parses a whole reference and guards on the resolved type; `ex_next` gains no error path; `nx_top` writes a `name0 = 0` sentinel; `nx_scan` becomes a 3-byte compare with `nx_cmp`/`nx_miss`; `nx_have` keeps the stepped value on the stack; every frame offset shifted |
| [`basic/vars.asm`](../basic/vars.asm) | `vnk_dollar` writes `DEFTBL_STR` instead of 8; `var_get`/`var_set` → `for_get`/`for_set`, keyed on the frame instead of on a letter |
| [`basic/arrays.asm`](../basic/arrays.asm) | `deftbl_num_type` **deleted** (no callers left) and `dnt_check` folded into `check_vartype_num` |
| [`basic/sysvars.inc`](../basic/sysvars.inc) | `FOR_FRAME` = 11; `FOR_CUR` 9 → 11 B; `FOR_NEW` **deleted**; `FOR_STK` `$E070` → `$EA3A`; the stale "`$EA39..$EAFF` free" comment corrected |
| [`tests/test_vars.py`](../tests/test_vars.py) | Case 8 rewritten for the new contract, **plus four new cases**: `for_name`'s byte order, a `$` name resolving to `DEFTBL_STR`, `AB` vs `A` as distinct loop variables, and `A%` vs `A#` |
| [`tests/test_control_flow.py`](../tests/test_control_flow.py), [`tests/test_statements.py`](../tests/test_statements.py) | their `var()` read-back helpers take a key, and read the type from `DEFTBL` rather than hardcoding 8 |
| [`probes/basic/basic_probe_forvar.py`](../probes/basic/basic_probe_forvar.py) | **new**, 33 rows, 3 positive + 1 negative control, 2 deferred |
| [`probes/basic/basic_probe_arylv.py`](../probes/basic/basic_probe_arylv.py) | `DEFERRED` is now **empty** — `f.two`/`f.pct` were deferred *for this slice* |
| [`probes/basic/basic_probe_direct_ctrl.py`](../probes/basic/basic_probe_direct_ctrl.py) | the docstring's `FSP`-after-`RUN` value, the only place the old `FOR_STK` address was written down |
| [`Makefile`](../Makefile) | `forvar-characterize` + `forvar-acceptance`, both `.PHONY` |

### 10.2 The walls, measured from clean — **all five exact**

| wall | at `79f6bdb` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 6 B | ≈5 B (+1) | **5 B** | ✅ |
| **main low region** | 6 B | ≈11 B (−5) | **11 B** | ✅ |
| sub page 0 | 3604 B | unchanged | **3604 B** | ✅ |
| sub page 1 | 1483 B | unchanged | **1483 B** | ✅ |
| RAM | — | −72 B in `$E0xx`, +88 B at `$EA3A` | as designed | ✅ |

🎯 **AND ALL TWENTY PREDICTED SPANS LANDED TO THE BYTE** — `for_name` 14,
`ex_for` 63, `ex_next` 14, `nx_top` 4, `nx_scan`+`nx_cmp`+`nx_miss` 45,
`nx_have` 42, `nx_neg` 11, `for_get` 10, `for_set` 15, `check_vartype_num` 9,
and the ten unchanged bodies unchanged. The reason is §6.2: the counter was
calibrated **18/18** against the `.sym` before it was quoted for code that did
not exist ([[calibrate-a-hand-counter-before-quoting-it]]). Third slice running.

### 10.3 The ROM hashes — **all four predicted before the build**

| ROM | at `79f6bdb` | §6.4 predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `60419f46…` | MOVES | **`cc7e3cbf…`** ✅ |
| `sub.rom` | `accce5a1…` | 🎯 **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `963246fa…` | MOVES | **`0de562e4…`** ✅ |

🎯 **`sub.rom` HOLDING IS THE ONE THAT WAS WORTH PREDICTING.**
`sub/basic-resident-abi.inc` is regenerated from main's `.sym` on every build and
D-ARYLV recorded `sub.rom` moving while its walls held — so "a low-region edit
leaves the sub-ROM alone" is not the default. It holds here because
`deftbl_num_type` at `$3FEC` is the **last code in the low region** and all 11
exported addresses (`$3279`…`$3DAD`) lie below it
([[a-wall-is-a-size-a-hash-is-an-identity]]).

### 10.4 The gates — every counter on its predicted value

| gate | before | predicted | measured |
|---|---|---|---|
| **`forvar-acceptance`** | 8/30 | 30/30 | **31/31 agree, 0 diverge, 2 deferred** ✅ (§10.5(c)) — ✅ **33/33, 0 deferred since D-NXLIST** |
| **`arylv-acceptance`** | 16/16 + 2 def | **18/18** | **18/18, 0 deferred** ✅ |
| `unit-test` | 59 | 59 | **59** ✅ (§10.5(d)) |
| `audit-citations` swept / basic | 748 / 195 | 751 / 196 | **751 / 196** ✅ |
| `injector-check` | 342 | 343 | **343** ✅ |
| `rowshape-check` | 183/36/12/12/0 | 184/37/13/13/0 | **184/37/13/13/0** ✅ |
| `preflight-check` | 181/86/95/95/0 | unchanged | **181/86/95/95/0** ✅ |
| `latch-check` | 16/16 | unchanged | **16/16** ✅ |
| sub page-0 closure | 733 + 15, 14 tenants | unchanged | **733 + 15, 14** ✅ |
| sub page-1 closure | 585 + 43 | unchanged | **585 + 43** ✅ |
| resident ABI closure | 122 + 4 | unchanged | **122 + 4** ✅ |
| `deadcode` main / sub | 0 / 0 (+1) | unchanged | **0 / 0 (+1)** ✅ |

### 10.5 🔴 Four things went differently, and each is a finding

**(a) THE GATE FOUND A DEFECT IN THIS SLICE'S OWN FIRST DRAFT, AND ONLY THREE
ROWS COULD SEE IT.** `LD (nn),BC` writes **C** to `(nn)` and `var_name_key`
returns **B = name0**, so the frame's byte 0 is **name1** — and name1 is **0**
for every single-character name. §4.3's bare-`NEXT` sentinel (`name0 = 0`) sat on
that byte, so `NEXT A`, `NEXT A%` and `NEXT A$` all read as **bare** and took the
top frame whatever its name. The first gate run scored **27/30**, red on exactly
`n.xtype`, `n.prefix` and `n.strnx` — the only three rows where the wrongly
matched frame is a *different* frame. Every other row passed, `c.next` included.
Fixed byte-neutrally by keying the sentinel on `FOR_CUR+1`; the walls and both
holding hashes were unchanged by the fix, which is its own control.
🎯 **The three rows that caught it are the three §1 named as the ones no measured
row had ever asked.** The row set was not sized for this defect and caught it
anyway, because it was sized for the *rule*.

**(b) K-FV1's PREDICTED RED SET WAS DERIVED FROM THE BYTE ORDER THE DRAFT GOT
WRONG — the knife inherited the code's own error.** §8 predicted `ld b,1` would
redden `{n.prefix, n.xtype, n.strnx}`; it reddened `{n.xtype, n.strnx}`, because
a one-byte compare compares **name1**, and `FOR AB` / `NEXT A` differs there
already. 🔴 **And K-FV1 and K-FV2 then reddened the IDENTICAL set, which is a
MISSING ROW, not a bad cut**: every mismatching row in the battery differed in
`name1`, so nothing said whether `name0` was compared at all. **`n.samen1`**
(`FOR AB=1 TO 3` / `NEXT CB` → `NEXT without FOR`, both references) was added and
measured, and K-FV1/K-FV2 re-run against it separate cleanly — K-FV1 reddens it,
K-FV2 does not. That row exists only because the cuts were drafted first
([[draft-the-knives-before-freezing-the-row-set]]).

**(c) SO THE GATE IS 31/31, NOT THE PREDICTED 30/30**, and the extra row is
`n.samen1`. ⚠️ Recorded as a **scope change with a cause**, not as a better
number: §7's 30 was the scope before a knife proved the denominator was one row
short ([[a-prediction-copied-into-the-result-column]]).

**(d) `unit-test` WENT RED, AND IT WAS RIGHT TO.** Three host tests called
`var_get`/`var_set` by name with the single-letter contract this slice retires —
`test_vars.py` directly, and `test_control_flow.py` / `test_statements.py`
through their `var()` read-back helpers. Updated to the key-based contract, with
the type read from `DEFTBL` rather than hardcoded to 8 (the retired shim looked
it up, and a hardcoded 8 would make the helper lie under `DEFINT`). **59/59.**
🎯 Four cases were **added** rather than merely repaired, and one of them is
§4.2's mechanism pinned where no screen row can reach it: `for_name "a$"` must
resolve to `DEFTBL_STR` and **not** 8.

### 10.6 Knives — 9 cuts × 2 rounds, **7 EXACT, both rounds identical**

Runner: throwaway in the scratchpad, never committed. Subject = the probe invoked
directly, `--sides zb` (the reference columns are constants). Snapshot restore in
a `finally`; `rm -rf build` + full rebuild + repack before every run including
each baseline; ROM-hash guard per cut; rows via `probe_report.parse()` compared as
`{label → zb value}` with a row-count refusal. **No flakiness on any cut.**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-FV1** | `nx_cmp`: `ld b,3` → `ld b,1` | `n.prefix`, `n.xtype`, `n.strnx` | 🔴 `n.xtype`, `n.strnx` — then `n.samen1` too, once that row existed | ❌ ×2, see §10.5(b) |
| **K-FV2** | `nx_cmp`: `ld b,3` → `ld b,2` | 🎯 `n.xtype`, `n.strnx` ONLY | **exactly those two**, and `n.samen1` stays GREEN | ✅ ×2 |
| **K-FV3** | `vnk_dollar`: `ld a,DEFTBL_STR` → `ld a,8` | 🎯 `f.str`, `n.strnx`, `x.numstr` | **exactly those three**, `f.defstr` GREEN as predicted | ✅ ×2 |
| **K-FV4** | `ex_for`: `jp z,type_mismatch_error` → 3 × `nop` | 🎯 `f.str`, `f.defstr` ONLY | **exactly those two**, `x.numstr` GREEN | ✅ ×2 |
| **K-FV5** | `for_set`: `ld a,(FOR_CUR+2)` → `ld a,8` + `nop` | `f.pct`, `f.bang`, `f.twopct`, `f.coll`, `f.defint` | **those five plus `n.pct`** — a prediction one row short, see (i) | ❌ ×2 |
| **K-FV6** | `FOR_STK_END`: `FOR_DEPTH*FOR_FRAME` → `7*FOR_FRAME` | 🎯 **`f.dep8` ONLY** | **`f.dep8` ONLY**, `OK` → `Out of memory` | ✅ ×2 |
| **K-FV7** | `for_name`: `ld (FOR_CUR+2),a` → 3 × `nop` | broad, reported as a SET | **24 rows**, `c.for` among them → probe rc **2** | ✅ ×2, see (ii) |
| **K-FV9** | `nx_top`: `ld (FOR_CUR+1),a` → 3 × `nop` | 🎯 **`n.mixnx` ONLY** | **`n.mixnx` ONLY**, ` 3  3 ` → `NEXT without FOR` | ✅ ×2 |
| **K-FV10** | `CONTROL_WANT["c.for"]` unmatchable, `--sides vg8020,zb` | rc **2**, `NOT MEASURED`, ROMs unmoved | **rc 2 + banner, ROMs held** | ✅ ×2 |

*(K-FV8 was drafted and **not taken**: a cut that unbalances the stack tests the
emulator, not the rule. Recorded rather than silently dropped.)*

🔴 **(i) K-FV5 REDDENED ONE MORE ROW THAN PREDICTED, AND IT ALSO FAILED LOUDER
THAN PREDICTED.** `n.pct` (`FOR A%=1 TO 3` / `NEXT A%`) is an int-typed loop like
`f.pct` and simply belonged in the list — a prediction oversight, not a design
one. What was *not* foreseen is the shape: every one of the six reads
`<NO OUTPUT>`, not a wrong number. Storing an int16 into an entry allocated at the
wrong width takes the program down rather than mis-typing it, which is the same
lesson `DEFTBL_STR`'s own header records about namespace P → C crossings.

⚠️ **(ii) K-FV7 EXERCISED THE PROBE'S FAIL-CLOSED PATH WITH A REAL CUT, NOT A
SYNTHETIC ONE.** Dropping the type from the frame reddens `c.for` — a positive
control — so the probe exited **2** and printed its complete not-scored report
shape, which the runner parsed through `probe_report.parse()` without a hiccup.
K-FV10 proves the guard deliberately; K-FV7 proves it under an ordinary code cut,
and the rowshape contract is what makes both readable
([[a-gate-that-delegates-inherits-a-blind-spot]]).

### 10.7 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **28 targets, all rc=0**: `unit-test` 59 · `audit-citations` CLEAN
(751 swept) · `preflight-check` 181/86/95/95/0 · `injector-check` 343 ·
`rowshape-check` 184/37/13/13/0 · `latch-check` 16/16 · `deadcode` 0/0 ·
`lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance` ·
`logicops-acceptance` · `float-acceptance` · `linemax-acceptance` 60/60 ·
`dexp5-pin` · `editverb-acceptance` 61/61 · `lptverb-acceptance` 44/44 ·
`dskmsg-acceptance` 5/5 · `diskbasic-acceptance` 34/34 verbs ·
`fat-error-acceptance` · `runtail-acceptance` 9/9 · `castail-acceptance` 31/31 ·
`cassave-acceptance` 20/20 · `readvar-acceptance` 24/24 ·
**`arylv-acceptance` 18/18** · `inputary-acceptance` 7/7 ·
`lvfix-acceptance` 18/18 · `fldary-acceptance` 13/13 · `lrvar-acceptance`
21/21 · **`forvar-acceptance` 31/31**.

⚠️ `latch-check` still has **no `repack-machine` prerequisite**, so the script
builds explicitly before the loop rather than letting the first target do it.

### 10.8 The fix, as a program

Both columns are readings from the runs above.

```basic
10 FOR INDEX=1 TO 3
20 NEXT
30 PRINT "[";INDEX;"]"
```

| | screen after `RUN` |
|---|---|
| Philips VG-8020 / National CF-3300 | `[ 4 ]` |
| zerobas **before** | `Syntax error in 10` |
| zerobas **after** | `[ 4 ]` |

🎯 **The type is the half of the rule the filed residual could not see**, and
`NEXT` is where it shows:

```basic
10 FOR A%=1 TO 3
20 NEXT A
30 PRINT "[";A%;"]"
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **after** | `NEXT without FOR in 20` — `A` is not `A%` |
| zerobas **before** | `Syntax error in 10` |
| under **K-FV2** (the type dropped from the match) | `[ 4 ]` — the loop closes on the wrong variable |

And the row a knife demanded, which says `NEXT` reads **both** name characters:

```basic
10 FOR AB=1 TO 3
20 NEXT CB
30 PRINT "[OK]"
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **after** | `NEXT without FOR in 20` |
| under **K-FV1** (one byte of the key compared) | `[OK]` — 🔴 `CB` closed `AB` |

Finally, the defect the characterization found rather than went looking for —
not a `FOR` program at all:

```basic
10 A$="X"
20 B=1+A$
30 PRINT "[";B;"]"
```

| | screen after `RUN` |
|---|---|
| both references | `Type mismatch in 20` |
| zerobas **before** | `[ 1 ]` — 🔴 `A$` read as the numeric `A` = 0, and the program **ran on** |
| zerobas **after** | `Type mismatch in 20` |
