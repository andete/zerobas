# D-NXARY — a `NEXT` operand is a full variable REFERENCE

*Slice D-NXARY, 2026-08-08, on `main`, based on `5a50a04` (D-NXLIST).*

D-NXLIST measured three rows and **declined this with a price**
([`spec-basic-nxlist.md`](spec-basic-nxlist.md) §3.1): `NEXT A(1)` is
**NEXT without FOR** but `NEXT A(99)` is **Subscript out of range**, so the
reference EVALUATES the subscript before matching anything, and the cheap
8-byte *"a `(` makes the key unmatchable"* fix answers the wrong error.

🎯 **BOTH REFERENCES, EVERY ROW.** 21 rows, three sides, and **both references
agree on all 21**.

---

## 1. The rule — measured before it was designed, in two rounds

**21 rows measured 2026-08-08 BEFORE a byte was written** —
[`nxary-msx1-characterization.md`](nxary-msx1-characterization.md) is the table.

> A `NEXT` operand is an **ordinary variable REFERENCE**: name, type suffix,
> and — when a `(` follows — a full subscript list that is **EVALUATED**,
> **auto-DIMs** an as-yet-unreferenced array, and is **range- and rank-checked**
> (raising `Subscript out of range`). A resolved array ELEMENT then matches no
> `FOR` frame, so the answer is **NEXT without FOR** (ERR 1). This holds in every
> type namespace — unsuffixed, `%` and `$`.

🎯 **THE THREE READINGS THAT DECIDED THE DESIGN ARE ONES NO EARLIER ROW ASKED:**

| row | reading | what it forces |
|---|---|---|
| `a.autodim` — trap the error, then `DIM A(3)` | **Redimensioned array** | 🎯 the resolve **auto-DIMs**. The fix must use the *auto-dimming* resolve (`ary_op0_resolve` op=0), which is what `tgt_parse` already calls — a side effect on a row that ERRORS, invisible to every direct reading |
| `a.stroob` — `NEXT A$(99)` | **Subscript out of range** | 🎯 the `$` arm resolves too. `a.str` (`NEXT A$(1)`) is **already green** here, and for a reason that has nothing to do with arrays — D-FORVAR made a `$` name resolve to `DEFTBL_STR`, a type no frame can hold, so ERR 1 falls out *without the subscript being looked at*. **A case that agrees can agree for the wrong reason** |
| `a.rank` — `DIM A(3,3)` / `NEXT A(1)` | **Subscript out of range** | the rank is checked, so this is the real resolve and not a subscript skipper |

⚠️ **`a.errno` PINS THE ERROR AS A NUMBER, NOT A STRING.** Read through
`ON ERROR`, both references answer `ERR` = **1** where zerobas answers **2** —
so "NEXT without FOR" is the identity of the error, not a wording that happens
to match.

---

## 2. What is wrong, in one sentence

* **`ex_next`** ([`basic/program.asm`](../basic/program.asm)) — its parse is
  `for_name`, i.e. `var_name_key` + the frame key: a name and a type suffix and
  **never a subscript**, so a `(` is left in the cursor and reaches statement
  position as `Syntax error`.

---

## 3. Scope

**In:** the subscript surface at `NEXT` — literal / variable / expression,
1-D / 2-D / the WRONG rank, in range and out, DIMmed and unDIMmed; all three
type namespaces; whether the resolve auto-DIMs; the error NUMBER; and an array
element as an element of a D-NXLIST list. Plus — forced by §6.3's carve, not
chosen — **8 nested loops**.

**Out, and named rather than implied:**

* 🔴 **`ON ERROR GOTO 0` INSIDE A HANDLER MUST RE-RAISE, AND ZEROBAS DOES NOT.**
  Found by this slice's own first draft of `a.autodim` (§10.5(a)) and **filed as
  its own residual** in `TODO.md`: it belongs to the error-handling surface, not
  to `NEXT`. Measured, on both references, at the reading that exposed it.
* **`FOR A(1)=`** — `Syntax error` on both references, and it must **stay** so.
  Carried as the NEGATIVE control (`f.ary`), and it is load-bearing here in a way
  it was not before: this slice teaches `ex_next` to resolve a subscript, and the
  obvious tidy-up is to share that reach with `ex_for`. §5.2 prices why not.
* **A subscript that is itself an array element** (`NEXT A(B(1))`), and a
  `NEXT` operand whose subscript has a side effect (`NEXT A(FNX(1))`).

---

## 4. Design

### 4.1 🎯 THE PARSE BECOMES `tgt_parse`, WHICH IS THE LVALUE FAMILY'S OWN

`tgt_parse` ([`basic/vars.asm:242`](../basic/vars.asm)) already is the whole
rule: name + suffix + optional subscripts, `ary_op0_resolve` op=0 (**which
auto-dims on first reference — `a.autodim`**), `Z` = ok / `NZ` = resolve failed
with `FPERR` mapped, `BC` = the key, `(TGT_ADDR)` = the element address **or 0
for a scalar**. Six sites already call it; this becomes the seventh.

```
                call    var_str_type        ; A = mode (0 numeric / 1 string).
                                            ;   HL is NOT advanced -- a.str/a.stroob
                                            ;   need the $ arm to pick the STRING array
                call    tgt_parse           ; BC=key, (VARTYPE)=type, (TGT_ADDR)
                jp      nz,fp_runtime_error ; Subscript out of range -- a.oob/a.rank
                call    for_key             ; FOR_CUR[0..2] = (BC, VARTYPE)
                ld      a,(TGT_ADDR+1)      ; 0 iff scalar: an element lives in RAM
                or      a                   ;   above $8000, so its high byte is never 0
                jr      z,nx_find           ; a scalar keeps its real key
                ld      (FOR_CUR+1),a       ; 🎯 an ELEMENT matches NO frame, and A is
                                            ;   already >= $80 -- no name0 can be
```

🎯 **THE UNMATCHABLE KEY IS FREE, AND IT IS THE SAME TRICK TWICE OVER.**
D-FORVAR made `NEXT A$` miss by giving it a type no frame holds; D-NXLIST made
`NEXT B,` miss by parking a `name0` no name has. Here `A` already holds the
element address's **high byte** — necessarily ≥ `$80`, because arrays live in
RAM — and `name0` is `is_letter`-gated to `$41..$5A`. So the value that answered
*"is this an element?"* **is** the value that makes it unmatchable, and the store
is 3 bytes with no constant to load.

### 4.2 `for_name` splits, and the split costs nothing

`ex_for` still must **not** resolve subscripts (§5.2), so it keeps
`var_name_key`. The half both verbs share is the frame-key store:

```
for_name:       call    var_name_key        ; ex_for's entry
for_key:        ld      (FOR_CUR),bc        ; ex_next's entry, after tgt_parse
                ld      a,(VARTYPE)
                ld      (FOR_CUR+2),a
                ret
```

`for_name` falls into `for_key`, so the second entry point is **0 bytes**.

### 4.3 Funding carve — `ex_for`'s overflow bound stops destroying `HL`

`ef_havestep` computes the FOR-stack bound with `sbc hl,de`, which destroys
`HL`, and then reloads `(FSP)` into `DE` for the `ldir`. One `add` answers both:

```
                ld      de,(FSP)            ; 4  the ldir destination, loaded ONCE
                ld      hl,-FOR_STK_END     ; 3
                add     hl,de               ; 1  CF set iff FSP >= FOR_STK_END
                jr      c,ef_over           ; 2  too many nested FORs
                ld      hl,FOR_CUR          ; 3  (DE still = FSP)
```

**18 → 13, −5.** ⚠️ This is the SENSE of a comparison, the edit most likely to
pass every row that never reaches it — hence `a.dep8` (§5.3) and **K-NA4**.

And `ef_havestep`'s resume pointer is stored and then re-loaded three
instructions later across a `ldir` that does not touch the stack:
`ld hl,(FOR_CUR+9)` → `push hl` / `pop hl`, **−1**.

### 4.4 RAM

**Nothing.** No cell is added, moved or retired.

---

## 5. Forced constraints

### 5.1 🔴 THE RESOLVE MUST BE THE AUTO-DIMMING ONE, AND ONLY `a.autodim` SAYS SO

A resolve that refused an unreferenced array would answer `a.lit`
(`FOR A=1 TO 2` / `NEXT A(1)`, no `DIM`) with the *right* error for the *wrong*
reason — ERR 1 either way. `a.autodim` traps the error and then `DIM A(3)`s:
both references answer **Redimensioned array**, so the array **was created**.
`tgt_parse`'s `ary_op0_resolve` op=0 already does this; the constraint is that
nothing may be "tightened" to avoid the side effect.

### 5.2 🔴 `ex_for` MUST NOT SHARE THE REACH — AND THE COST IS AN INVISIBLE SIDE EFFECT

The tidy move is to give `ex_for` the same `tgt_parse` head and reject an
element after the fact — `f.ary`'s `Syntax error` face is even reachable that
way. **It is wrong, and not because of the face:** `tgt_parse` would *resolve*
`A(1)` first, auto-DIMming an array the reference never creates. `FOR A(1)=`
would then leave `A(0..10)` behind on a statement both references refuse. The
face would match and the machine would differ, on a row nothing in this battery
reads. `ex_for` keeps `var_name_key`.

### 5.3 The carve rewrites a comparison's SENSE, so it needs a row that reaches it

`a.dep8` — 8 nested `FOR`/`NEXT` pairs, `OK` on all three sides, green **before
and after**. It is the only row in this battery that reaches `ef_havestep`'s
bound at all, and it fails the moment the bound is one frame tight (**K-NA4**).
⚠️ The *other* direction — a bound too LOOSE — has no oracle: zerobas's fixed
8-frame stack and the references' stack-bounded limit are different mechanisms
(D-FORVAR §9). Named, not covered.

---

## 6. The carve scout

Off `build/basic-reloc.sym` from a clean build at `5a50a04`: low **11 B**, page 1
**15 B**, sub p0 **3604 B**, sub p1 **1483 B**; `basic-reloc.rom 2cce96c3…`,
`sub.rom accce5a1…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 38668085…`.

### 6.1 Region — asked before anything is priced

| symbol | address | region | note |
|---|---|---|---|
| `ex_next`, `for_name`, `ex_for`, `ef_havestep` | `$79xx`–`$7Axx` | **page 1** | every byte this slice writes |
| `tgt_parse` | `$473E` | page 1 | reused, unchanged |
| `var_str_type` | `$470A` | page 1 | reused, unchanged |
| `fp_runtime_error` | `$426F` | page 1 | reused, unchanged |
| `ary_op0_resolve` | `$3F96` | **LOW** | reached *through* `tgt_parse`, as `ex_read` already does from page 1 |

🎯 **THE EXPENSIVE PART IS ALREADY BUILT AND ALREADY REACHED FROM PAGE 1.**
`ex_read` (page 1) has called `tgt_parse` since D-ARYLV, so the page-1 → low hop
through `ary_op0_resolve` is a path this tree already runs; this slice adds a
caller, not a mechanism.

### 6.2 The estimator, calibrated before it is used

Hand-counted from source and checked against the `.sym` **first**
([[calibrate-a-hand-counter-before-quoting-it]]): `for_name` **14**, `ex_for`
**63**, `ef_step` **4**, `ef_havestep` **48**, `ef_over` **10**, `ex_next` **3**,
`nx_comma` **2**, `nx_head` **17**, `nx_notletter` **8**, `nx_find` **6**,
`nx_miss` **4**, `nx_bound` **13**, `nx_scan` **12**, `nx_cmp` **9**, `nx_have`
**33**, `nx_neg` **2**, `nx_limit` **10**, `nx_again` **20**, `nx_end` **16**,
`nx_nofor` **11**. **20/20 exact.**

### 6.3 The cost — a BOUND, with the twin named for every part

| body | region | before | after | Δ |
|---|---|---|---|---|
| `nx_head` — `call for_name` + `jr nx_find` (5) → `var_str_type` 3 + `tgt_parse` 3 + `jp nz` 3 + `for_key` 3 + `ld a,(TGT_ADDR+1)` 3 + `or a` 1 + `jr z` 2 + `ld (FOR_CUR+1),a` 3 = 21 | p1 | 17 | **33** | **+16** |
| `for_name` → `for_name` + `for_key` (fallthrough entry) | p1 | 14 | **14** | **0** |
| `ef_havestep` — the bound test keeps `HL` (−5) and the resume pointer rides the stack (−1) | p1 | 48 | **42** | **−6** |
| low / sub p0 / sub p1 / RAM | — | | | **0** |
| **main page-1 total** | | | | **+10** |

### 6.4 The bottom line

| region | free at `5a50a04` | slice | free after |
|---|---|---|---|
| **main page 1** | **15 B** | **+10** | **≈ 5 B** |
| main low | 11 B | 0 | **11 B** |
| sub page 0 / page 1 | 3604 / 1483 | 0 | **unchanged** |

⚠️ **THIS SPENDS D-NXLIST'S WHOLE SURPLUS AND PUTS THE WALL BACK AT 5 B.** That
is the honest reading and it is stated rather than buried: the residual was
declined at 15 B free *for being a different rule*, not for being unaffordable,
and it is affordable — but only just, and only because `ex_for`'s bound test was
still paying to destroy a register it then reloaded. **The next slice needs a
carve scout again** ([[which-wall-binds-is-a-history-question]]).

⚠️ **Predicted ROM hashes:** `basic-reloc.rom` **MOVES**; `zerobas-main-eu.rom`
**MOVES**; `disk.rom` **HOLDS at `2c630d3d…`**; 🎯 **`sub.rom` HOLDS at
`accce5a1…`** — no low-region byte is written and only low addresses are
exported to the sub-ROM.

### 6.5 ✅ VERDICT: **GO, self-funded at +10 into 15.** No eviction, no RAM, no sub-ROM byte — and the wall ends where D-FORVAR left it.

---

## 7. Predicted GREEN

`make nxary-characterize` must read, on all three sides:

| row | prediction | |
|---|---|---|
| `c.for` / `c.aryrd` / `c.nofor` | ` 4 ` / ` 7 ` / `NEXT without FOR` | 🟢 **controls** — green before **and** after |
| `a.lit` `a.spc` `a.dim` `a.var` `a.expr` `a.2d` `a.pct` | `NEXT without FOR` | the element that matches nothing |
| `a.oob` `a.dimoob` `a.rank` `a.stroob` `a.pctoob` | `Subscript out of range` | the resolve's own error faces |
| `a.str` | `NEXT without FOR` | green before and after — 🎯 and `a.stroob` is why that proved nothing |
| `a.errno` | ` 1 ` | the error as a NUMBER |
| `a.autodim` | `Redimensioned array` | 🎯 §5.1 — the resolve auto-DIMs |
| `a.list` | `NEXT without FOR` | composes with D-NXLIST |
| `a.dep8` | `OK` | 🔴 **the CARVE's row** — green before **and** after |
| `f.ary` | `Syntax error` | 🔴 **NEGATIVE control** — green before **and** after |

⇒ **`make nxary-acceptance` scores 21/21**, from **6/21** at `5a50a04`.

Static counters, each predicted by reading its own check's definition
([[a-count-is-predicted-by-reading-its-definition]]): `audit-citations` 754 →
**757** swept, basic 197 → **198**; `injector-check` 344 → **345**;
`rowshape-check` 14 → **15** probes; `preflight-check`
**181/86/95/95/0 unchanged**; `latch-check` **16/16 unchanged**; `deadcode`
**0/0 (+1) unchanged**; closures **585+43 / 733+15 / 122+4 unchanged**;
`unit-test` **59 unchanged**. ⚠️ **`forvar-acceptance` and `nxlist-acceptance`
must stay 33/33 and 25/25** — `ex_next`'s parse is what this slice replaces, so
both are regression surfaces, not bystanders.

---

## 8. Knives — drafted before the row set was frozen

Read [`dev-workflow.md`](dev-workflow.md) §"Knives" first. Subject = the probe
invoked directly, `--sides zb`, except K-NA5.

| # | cut (byte-neutral) | predicted RED | predicted GREEN |
|---|---|---|---|
| **K-NA1** | `nx_head`: `jp nz,fp_runtime_error` → 3 × `nop` — the resolve's FAILURE is ignored | 🎯 **`a.oob`, `a.dimoob`, `a.rank`, `a.stroob`, `a.pctoob`** — exactly the five out-of-range rows | the other 16 |
| **K-NA2** | `nx_head`: `ld a,(TGT_ADDR+1)` → `xor a` + 2 × `nop` — every reference looks like a SCALAR, so an element gets the real key and MATCHES | 🎯 **`a.lit`, `a.spc`, `a.dim`, `a.var`, `a.expr`, `a.2d`, `a.pct`, `a.errno`, `a.list`** (9) | the other 12 — **`a.str` included**, because its key is unmatchable on TYPE and never needed this test; **`a.autodim` included**, because the array is created by the resolve either way |
| **K-NA3** | `nx_head`: `call var_str_type` → `xor a` + 2 × `nop` — the mode is always "numeric" | **`a.stroob`** at least; reported as a SET, since a `$` name resolved in the numeric namespace may surface a different error face rather than the right one | the numeric rows |
| **K-NA4** | `ef_havestep`: `ld hl,-FOR_STK_END` → `ld hl,-(FOR_STK+7*FOR_FRAME)` | 🎯 **`a.dep8` ONLY** (→ `Out of memory`) | the other 20 |
| **K-NA5** | `CONTROL_WANT["c.aryrd"]` unmatchable (probe-only), `--sides vg8020,zb` | rc **2**, `NOT MEASURED`, ROMs **NOT** moved | — |

All five red sets are **pairwise distinct** (K-NA3 ⊂ K-NA1 but strictly
smaller), and K-NA4 reddens exactly **one** row.

🔴 **K-NA2 IS THE KNIFE FOR THE WHOLE POINT OF THE SLICE**, and `a.str` sitting
in its GREEN set is the measurement `a.stroob` was added to make: a row that is
already green can stay green under the cut that breaks the thing it appears to
test.

⚠️ **`a.autodim` has no cut of its own.** Its subject is a side effect the
*existing* resolve performs; removing code cannot expose it, and a design that
avoided it would be an addition. Named rather than left implied.

---

## 9. Denominator

**(SUBSCRIPT FORM: literal / variable / expression) × (RANK: 1-D / 2-D / the
WRONG rank) × (RANGE: in / out) × (DIMmed / unDIMmed)**, plus the three type
namespaces, plus the error NUMBER read through `ON ERROR`, plus whether the
resolve AUTO-DIMS, plus an array element as a LIST element, plus 8-deep nesting
for the carve, plus the `FOR A(1)=` form both references REFUSE.

**Not covered, and named rather than implied:** `ON ERROR GOTO 0`'s re-raise
inside a handler (§3 — measured, divergent, filed as its own residual); a
subscript that is itself an array element; a subscript with a side effect; a
`NEXT` operand resolved while a string GC is pending; and nesting deeper than 8,
where the two machines' limits are different mechanisms.

---

## 10. As-built

Implemented 2026-08-08 on `main`, based on `5a50a04`.

### 10.1 What landed

| file | change |
|---|---|
| [`basic/program.asm`](../basic/program.asm) | `ex_next`'s parse becomes `var_str_type` + `tgt_parse` + `for_key`, with an element made unmatchable by the very byte that identifies it; `for_name` gains the `for_key` fallthrough entry; `ef_havestep`'s bound test keeps `HL` and its resume pointer rides the stack; `ef_step`'s two arms stop needing a join |
| [`probes/basic/basic_probe_nxary.py`](../probes/basic/basic_probe_nxary.py) | **new**, 22 rows, 3 positive + 1 negative control, 1 deferred |
| [`Makefile`](../Makefile) | `nxary-characterize` + `nxary-acceptance`, both `.PHONY` |

### 10.2 The walls — **and §6.3's bound was 2 B LIGHT**

| wall | at `5a50a04` | §6.4 predicted | as built | |
|---|---|---|---|---|
| **main page 1** | 15 B | ≈5 B (+10) | **5 B** | ✅ *(after §10.5(a))* |
| main low / sub p0 / sub p1 / RAM | 11 / 3604 / 1483 | unchanged | **unchanged** | ✅ |

**19 of 20 spans landed to the byte.** The one that did not is `nx_head`:
predicted **33**, built **35**.

🔴 **§6.3 COUNTED A FALLTHROUGH THE LAYOUT FORBIDS.** §4.1's code block ends at
`ld (FOR_CUR+1),a` and the arithmetic assumed the array arm then *falls into*
`nx_find` — but `nx_notletter` sits between them, so the arm needs a `jr
nx_find`, which is exactly the missing 2. Same class as D-FORVAR §10.5(b): the
prediction inherited the sketch's layout error rather than re-deriving it from
where the labels actually are.

Recovered by a carve §6.3 had not priced: `ef_step`'s default step is now loaded
**before** the `STEP` test and overwritten by `eval`, so the two arms stop
needing a join (**−2 B**). Guarded in both directions by rows that already
exist — `f.step` (forvar) and `m.step` (nxlist) take the STEP arm; every other
loop row takes the default.

### 10.3 The ROM hashes — all four predicted

| ROM | at `5a50a04` | predicted | as built |
|---|---|---|---|
| `basic-reloc.rom` | `2cce96c3…` | MOVES | **`62a461c1…`** ✅ |
| `sub.rom` | `accce5a1…` | **HOLDS** | **`accce5a1…`** ✅ |
| `disk.rom` | `2c630d3d…` | **HOLDS** | **`2c630d3d…`** ✅ |
| `zerobas-main-eu.rom` | `38668085…` | MOVES | **`80a57733…`** ✅ |

### 10.4 The gates

| gate | before | predicted | measured |
|---|---|---|---|
| **`nxary-acceptance`** | 6/21 | 21/21 | **21/21 agree, 1 deferred** ✅ (§10.5(b)) |
| `forvar-acceptance` | 33/33 | unchanged | **33/33** ✅ |
| `nxlist-acceptance` | 25/25 | unchanged | **25/25** ✅ |
| `audit-citations` swept / basic | 754 / 197 | 757 / 198 | **757 / 198** ✅ |
| `injector-check` | 344 | 345 | **345** ✅ |
| `rowshape-check` | 14 | 15 probes | **15** ✅ |
| `unit-test` · `preflight` · `latch` · `deadcode` · closures | — | unchanged | **unchanged** ✅ |

### 10.5 🔴 Four things went differently

**(a) THE BYTE BOUND WAS 2 LIGHT, FOR A LAYOUT REASON AND NOT AN ARITHMETIC
ONE** — §10.2. The counter was calibrated 20/20 against the `.sym`; what it got
wrong was *where the label sits*, which no amount of instruction counting
catches.

**(b) `a.spc` WAS PREDICTED GREEN AND IS RED — AND D-NXLIST'S OWN DECLINE NOTE
HAD SAID SO.** `tgt_parse`'s `(` test is a bare `ld a,(hl)`, so `NEXT A (1)`
reads as the scalar `A`. `spec-basic-nxlist.md` §3.1 wrote *"`m.aryspc` adds
that the `(` is not even lexically contiguous, so the test would need
`skip_spaces` too"* — carried into this slice's characterization and **not into
its design**. 💰 Deferred rather than fixed, and **not for space**: the fix is 3
bytes with 5 free, but `tgt_parse` has **seven** call sites and the other six are
unmeasured ([[a-shared-engine-fix-must-measure-its-other-callers]]). Filed.
✅ **CLOSED 2026-08-08 by D-TGTSPC** ([`spec-basic-tgtspc.md`](spec-basic-tgtspc.md)),
and **both numbers in that sentence are wrong**: the fix is **2 B** (it replaces
a one-byte `ld a,(hl)`), and there are **EIGHT `call` sites from NINE statement
surfaces** — the hand list forgot to count `ex_next` itself. `a.spc` is now
scored and `nxary-acceptance` is **22/22**.

**(c) K-NA2 REDDENED `a.str`, WHICH §8 PREDICTED GREEN — AND THE PREDICTION'S
REASONING WAS WRONG ABOUT THE SHIPPED CODE.** §8 argued `a.str`'s key "is
unmatchable on TYPE and never needed this test". It is not: on the array path
`BC` and `(VARTYPE)` are whatever `ary_op0_resolve` left, so `for_key` stores a
key that is not the name's at all. The shipped code is correct **only** because
the element store overwrites `FOR_CUR+1` — which is precisely what K-NA2 cuts.
The code comment now says so.

**(d) K-NA3 REDDENED NOTHING, AND THAT WAS A MISSING ROW.** Forcing the MODE
argument to 0 (so the resolve is told the TYPE CODE) changed no reading across
21 rows, because the two namespaces coincide today
([[two-namespaces-sharing-a-value]]). **`a.strpick`** — `DIM A(50)` / `DIM A$(3)`
/ `NEXT A$(9)`, where 9 is in range in one array and out in the other — separates
them: both references answer `Subscript out of range`, and re-run against it
K-NA3 cuts exactly that one row. `var_str_type` is load-bearing, and the row that
proves it exists only because the cuts were run before the row set was called
finished ([[draft-the-knives-before-freezing-the-row-set]]).

### 10.6 Knives — 5 cuts × 2 rounds, **4 EXACT, both rounds identical**

| # | cut | predicted RED | measured | |
|---|---|---|---|---|
| **K-NA1** | `jp nz,fp_runtime_error` → 3 × `nop` | 🎯 the five out-of-range rows | **exactly those five**, all → `NEXT without FOR` | ✅ ×2 |
| **K-NA2** | `ld a,(TGT_ADDR+1)` → `xor a` + 2 × `nop` | 8 rows, `a.str` GREEN | **9 rows — `a.str` too**, see (c) | ❌ ×2 |
| **K-NA3** | `call var_str_type` → `xor a` + 2 × `nop` | `a.stroob` | **nothing** — then 🎯 **`a.strpick` ONLY**, once that row existed | ❌→✅ ×2, see (d) |
| **K-NA4** | `ef_havestep`: `ld hl,-FOR_STK_END` → one frame tight | 🎯 **`a.dep8` ONLY** | **`a.dep8` ONLY**, `OK` → `Out of memory` | ✅ ×2 |
| **K-NA5** | `CONTROL_WANT["c.aryrd"]` unmatchable, `--sides vg8020,zb` | rc 2, ROMs unmoved | **rc 2 + banner, ROMs held** | ✅ ×2 |

⚠️ **`a.autodim` has no cut of its own** — its subject is a side effect the
*existing* resolve performs, so removing code cannot expose it. Named rather
than left implied.

### 10.7 Corpus — **30 targets now, and the list had to grow**

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **all rc=0 in 15 min**: the 29 of
[`spec-basic-nxlist.md`](spec-basic-nxlist.md) §10.7 — `forvar-acceptance`
**33/33** and `nxlist-acceptance` **25/25** among them, the two regression
surfaces this slice's parse rewrite could have reached — **plus
`nxary-acceptance` 21/21**.

⚠️ **THE 30th WAS RUN SEPARATELY, BECAUSE THE RUNNER'S LIST WAS A SLICE STALE.**
The corpus script is a scratchpad throwaway rebuilt from the previous slice's
§10.7, so a gate added *by* the current slice is exactly the one it omits. Caught
here by reading the target list rather than the exit code — `fail=0` over 29
targets is not `fail=0` over the 30 that exist. **Copy the list forward from
THIS section, not from the last one.**

### 10.8 The fix, as a program

```basic
10 FOR A=1 TO 2
20 NEXT A(1)
30 PRINT "[OK]"
```

| | screen after `RUN` |
|---|---|
| VG-8020 / CF-3300 | `NEXT without FOR in 20` |
| zerobas **before** → **after** | `Syntax error in 20` → `NEXT without FOR in 20` |
| under **K-NA2** (the element test cut) | `[OK]` — 🔴 `A(1)` closed the loop over the scalar `A` |

And the subscript is really evaluated, which is the whole reason the cheap fix
was refused:

```basic
10 FOR A=1 TO 2
20 NEXT A(99)
```

| | screen after `RUN` |
|---|---|
| both references / zerobas **after** | `Subscript out of range in 20` |
| zerobas **before** | `Syntax error in 20` |
| under the 8-byte fix D-NXLIST priced | `NEXT without FOR` — the wrong error, which is why it was declined |
