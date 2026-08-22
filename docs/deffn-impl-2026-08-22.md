# D-DEFFN — the verb, written and measured: **450 B**, and 100 are free

Status: **IMPLEMENTED, MEASURED GREEN, NOT SHIPPED.** 2026-08-22, from `b1a01be`.
Branch [`deffn-draft`](#7-where-the-code-is) carries the whole implementation;
`main` is byte-identical to `b1a01be` (`834c45b5` / `b91622a9`).

The design round refused to name a total, and said why:

> **No total is claimed.** … A size derived from counting the remaining
> instructions in my head is not a measurement and is not recorded here.
> — [`deffn-design-2026-08-22.md`](deffn-design-2026-08-22.md) §7

This file is that measurement. The verb was written, assembled, and run against
its own 85-row differential until every row agreed. It costs **450 B of main
ROM**; a clean tree at `b1a01be` has **100** (page 1 54 B + page-0 low 46 B).

---

## 1. The numbers

**Walls at `b1a01be`, clean, from `make basic-reloc` (which prints all four):**

| region | free |
|---|---|
| main page 1 | **54 B** |
| main page-0 low | **46 B** |
| sub page 0 | 3075 B |
| sub page 1 | 1624 B |

**With DEF FN in, the same build:** `__MEAS_PAGE1_END` = **`$818C`**, i.e. the
image runs **396 B past the `$8000` ceiling**, and `__MEAS_LOW_END` is unmoved at
`$3FD2`. So every byte lands in page 1 and the verb costs

> ### 396 + 54 = **450 B of main ROM. The gap is 350 B.**

`basic/deffn.asm` is **419 B** of that; the other **31 B** are six in-place arms.

| piece | B | what it is |
|---|---|---|
| `ex_deffn` | 52 | the statement: direct-mode refusal, name, record, skip |
| `ev_fn` | 21 | the numeric factor entry + its `$`-function refusal |
| `str_ev_fn` | 22 | the string-operand entry + its numeric-function DECLINE |
| `fn_call` head | 83 | `fn_enter` (frame save) + name → definition + list open |
| bind loop + delimiters | 45 | the two lists walked together |
| `fn_body` + result coercion | 75 | body eval, coercion to the FN's own type |
| `fn_leave` | 19 | the frame restore |
| `fn_bind_one` | 52 | one actual: evaluate, type-check both ways, store |
| `fn_slot` | 34 | open a shadow slot; the 9-formal ceiling |
| error tails | 16 | ERR 18 / 13, and `jp`s to ERR 5 / 7 / 2 |
| — `basic/deffn.asm` | **419** | |
| `ex_def` FN arm (`basic/usr.asm`) | 5 | |
| `clear_usrtab` cold-boot FN_FEND reset | 5 | |
| `ev_f` FN arm (`basic/expr.asm`) | 5 | |
| `str_eval_one` FN arm (`basic/strvar.asm`) | 5 | |
| PRINT item-classification arm (`basic/print.asm`) | 5 | |
| `raise_error` FN-frame reset (`basic/interp.asm`) | 5 | |
| `if_skip_to_else` → `tok_skip_to` (terminator in C) | 1 | |
| — in-place | **31** | |
| **total** | **450** | |

🎯 **THE SUB-ROM HALF COSTS THE MAIN ROM NOTHING, AND THAT IS WHERE THE FIRST
64 B WENT.** The shadow lookup — "is this name a formal of the FN call in
progress?" — is a `call fn_shadow_find` at the top of `sub/arrays.asm`'s
`scv_find`. Sited there it is reached by **all four** scalar accessors at once:
`var_find_typed` and `var_alloc_or_find` (ARY_OP 4/5) and, since slice-4c
unified string scalars into the same chain at type 1, `str_get_key` and
`str_set_key` too. Four preludes in `basic/vars.asm` would have been ~64 B of the
main ROM; this is **40 B** of a sub page 0 with 3 KB spare, riding a CALSLT
every scalar reference already pays.

**The sub-ROM side, measured the same way:** page 0 free **3075 → 3024 B**
(−51: `fn_shadow_find` 40, its `call`/`ret c` prelude in `scv_find` 4, the
`FN` keyword row 5, and up to 3 of alignment pad — see §4.5). Sub page 1 is
**unchanged at 1624 B**.

---

## 2. What the verb actually does — 69 of 69, 8 of 8, 3 of 3

`make deffn-acceptance` on the scaffolded machine (§3), boot-per-case:

    ROWS: 85 printed, 80 scored — 0 of 69 DEF FN rows still divergent;
                                  0 of 8 controls failed
    PASS claim:o.sameaddr  VARPTR(formal) differs from VARPTR(variable)
    PASS claim:z.addr2     the shadow cell does not move with nesting
    PASS claim:z.addr      the shadow is not the variable's own cell

Every subject row matches the banked two-reference reading, including the ones
the design round called out as the hard ones:

| row | program | both refs | zerobas |
|---|---|---|---|
| `o.nestsame` | `DEF FNA(X)=X : DEF FNB(X)=FNA(X+1)+X` → `FNB(3)` | `7` | `7` |
| `o.dynself` | `X=5 : DEF FNB(Y)=X : DEF FNA(X)=FNB(0)+X*100` | `205` | `205` |
| `o.realcell` | `X=5 : P=VARPTR(X) : DEF FNA(X)=PEEK(P)` | `5` | `5` |
| `o.fnpct` | `DEF FNA%(X)=X/2` → `FNA%(5)` | `2` | `2` |
| `o.p9` / `o.p10` | 9 formals / 10 formals | `1` / ERR 5 | `1` / ERR 5 |
| `b.recurse` | `DEF FNA(X)=FNA(X)` | ERR 7 | ERR 7 |
| `d.defonly` | `DEF FNA(X)=X+1` typed at the prompt | `Illegal direct` | `Illegal direct` |
| `o.clearwipe3` | …then `CLEAR` | `Undefined user function` | `Undefined user function` |
| `b.str` | `DEF FNA$(X$)=X$+"!"` → `FNA$("hi")` | `hi!` | `hi!` |
| `o.quotedcolon` | `DEF FNA$(X$)=X$+":Q"` → `FNA$("a")` | `a:Q` | `a:Q` |
| `b.undef` | `FNZ(1)` | ERR 18 | ERR 18 |

🎯 **THE SIX SILENT WRONG ANSWERS ARE GONE.** `FNZ(1)`, a forward `DEF`,
`FNZ(1,2)`, an unexecuted `IF 0 THEN DEF`, and both direct-mode rows all read a
plain `0` before this work — an undefined `FN<name>(…)` parsed as an ordinary
subscripted array reference. All six now refuse, with the reference's own code.

🟢 **AND THE ADDRESS ROWS BEHAVE.** `z.addr` reads `-5480` = `$EA98`, which is
`FN_PAREA + 3` — the shadow slot's own value field — against `-32679` for an
ordinary variable, and `z.addr2` = `z.addr2i` one nesting level apart. Those are
zerobas's own addresses, not the reference's `$F6EB`; what is gated is the
layout-independent claim, and all three hold.

---

## 3. 🔴 The scaffold — what it is, and what it does NOT prove

The verb does not fit, so it cannot be run on the machine it would ship on.
**It was run on a DIFFERENT machine, and that is stated rather than hidden.**

The scaffold is three existing feature switches turned off in
`basic/sysvars.inc`: `G6_RESIDENT` / `G7_RESIDENT` / `G8_RESIDENT` (DRAW's
resident half, `SPRITE$`, `VDP()`/`BASE()`'s G8 half). They are the tree's own
conditional-compilation mechanism and they were **already there**; nothing was
invented to make room. Turning the three off frees **652 B of main page 1**, so
the DEF FN build has 269 B of headroom instead of −396.

**Why this is honest for THIS measurement, in one line each:**

* Not one of the 85 rows contains a graphics statement. The fixtures use `CLS`,
  `PRINT`, `DEF`, `VARPTR`, `PEEK`, `DIM`, `CLEAR`, `GOTO`, `RUN`, `ON ERROR`.
* **All eight positive controls PASS on the scaffold**, which is what says the
  apparatus is measuring at all.
* The scaffold changes **no** line of the DEF FN implementation, no RAM address
  and no token — only which unrelated features are assembled.

**What it does NOT prove, and this is the honest half:**

* 🔴 **The shipping build has never been run**, because it cannot be built. Any
  defect that depends on the ROM's final layout — a `jr` reach, a page-crossing
  table, an address a probe hardcodes — is UNMEASURED.
* 🔴 **The full battery set was not run.** `graphics-acceptance`,
  `graphics-floor-acceptance` and `lineerr-acceptance` fail on the scaffold **by
  construction** (their subjects are the switched-off features), so running them
  would have measured the scaffold, not the verb. `unit-test`,
  `namspc-acceptance`, `strparen-acceptance` and `fldwidth-acceptance` WERE run
  on it — see §6 — because their subjects are the shared paths this work edits.
* 🔴 **No knives were cut.** A knife suite is a claim about a shipping build.

---

## 4. What the battery found — four defects, and every one read as a number

Three of the four were found by the differential, not by reading, and **all
three produced plausible values rather than damage**.

### 4.1 🔴 A scratch register that was the caller's VALUE — 26 rows

`fn_slot` stashed the formal's type in `E` while it wrote the slot header. `E` is
half of `DE`, and `DE` **is** the value whenever `FACTYP` is 2 — `var_store_fac`
takes the live RHS there and `fac_to_int_strict` is literally `cp 2 / ret z`.
So every numeric formal bound to its own **type byte**:

    DEF FNA(X)=X+1 : FNA(2)   ->  9   (X bound to 8, the type code for double)
    DEF FNA(A,B,C)=A : ...    ->  8
    Y=3 : DEF FNA(X)=X+Y      ->  11
    DEF FNA(X)=X/2 : FNA(5)   ->  4

🎯 **NOT ONE OF THOSE LOOKS LIKE A BUG.** They are small integers of the right
magnitude in the right places. It took the reference column to say `3`, `1`, `5`
and `2.5`. The fix is `push af`/`pop af` instead of `E`, +2 B.

### 4.2 🔴 The mirror of the same class, in the RESTORE — six rows, one constant

`fn_leave` restores the outer frame with an `ldir`, which needs `DE` — and then
took the return cursor off the stack **into `DE`**. An int-typed factor returns
its value in `DE` (FAC is not written for `FACTYP`=2), so every FN whose own type
was 2 returned a leftover stack address:

    DEFINT A-Z : DEF FNA(X)=7 : PRINT FNA(2)   ->  -3392   ($F2C0)

🎯 **THE CONSTANT IS WHAT NAMED IT.** Six rows, six different bodies, one
identical answer — a value that does not depend on the body is not the body's.
A float result lives in FAC, which is RAM, so it survived: the defect was
reachable ONLY through `DEFINT A-Z` or a `%` on the function's own name, and it
read as a wrong number rather than as a crash. `scratchpad/deffn_int_probe.py`
is the nine-row split that separated "the coercion" from "the body" in one run:
`DEFINT A-Z : DEF FNA(X)=7` → `-3392` while the identical program without
`DEFINT` → `7`.

### 4.3 🔴 A classification the verb does not own — three rows

`PRINT FNA$("hi")` was `Type mismatch`. Nothing was wrong with DEF FN: PRINT's
item loop classifies an item by **peeking at its first byte**, `$DE` was not in
that chain, so the item fell to `is_letter` → `exp_num` → the numeric factor —
whose own guard correctly refuses a `$` function. The fix belongs beside `(`, not
beside `INKEY$`: `FNA$("hi")` and `FNA(2)` share a token, so a peek cannot
classify them any more than it can classify `(A$)` versus `(A+1)`. The string
path is TRIED and `str_ev_fn` declines a numeric FN by restoring HL and returning
CF clear — exactly the contract `jr nc,exps_fallback` already relies on
(D-STRPAREN). +5 B.

⚠️ **AND THE FALSE READING POINTED AT THE WRONG FILE.** `ERR 13` from a `$`
function is the face a *DEF FN* defect would produce too.

### 4.4 The one found by reading: a save that saved the wrong three bytes

`fn_enter` saves only the LIVE prefix of the frame — 3 bytes at top level rather
than 102, which is what keeps a plain `FNA(2)` off a Z80 stack this machine has a
few hundred bytes of. That is one `ldir`, so the three control cells and the live
prefix must be **contiguous from a fixed base**. The draft put the cells ABOVE
the area, so the copy ran from `FN_PAREA` for `used + 3` bytes and took the first
three bytes of **slot 0** instead: `FN_FEND`/`FN_SLOTP`/`FN_RTYPE` were never
restored at all. Cells first, area second, one base address. ⚠️ It was still
worth measuring: `scratchpad/deffn_int_probe.py`'s `i.after` row read
`PEEK(&HEAF5)` = 157 = `$9D` after a completed call — the un-restored cell, in a
byte.

### 4.5 And a fifth, in a file this work only pushed sideways

`sub/deftype.asm`'s `edt_codes` is a 4-byte table indexed with an 8-bit
`add a,l`, guarded by `IF (high edt_codes) != (high (edt_codes+3))`. Adding
`fn_shadow_find` to `sub/arrays.asm` — included AHEAD of it — shifted those four
bytes onto a page boundary and **the build stopped**, which is the guard working
exactly as written. 🎯 **What the guard could not do was say what to do about
it**, and *"never let an unrelated sub-ROM edit relocate this table"* is not a
rule anyone can keep. So the alignment is now ENFORCED rather than asserted: at
most 3 bytes of page-0 pad (which has 3 KB), and the assert stays below it as a
proof that can no longer fire. **That fix is on `main`**, not on the draft
branch — it is correct on its own and costs the main ROM nothing.

---

## 5. The implementation, in six facts

* **RAM.** `$EA92`, the 110-byte window `deffn-ramhunt-2026-08-22.md` walked and
  then measured empirically (14/14 rows, 0 bytes changed under a FULL FOR stack
  *and* a ninth frame, GOSUB, the crunch, PAINT, DRAW, PLAY's ISR, strings, a
  disk write round trip, FILES). Layout: `FN_FEND`, `FN_SLOTP`, `FN_RTYPE`, then
  9 × 11 B of slots — `FN_BASE + 3 + 99` = `$EAF8`, 8 B spare below `LINEBUF`.
  ✅ **The `IF FN_BASE + FN_BLK > LINEBUF` and page-crossing asserts shipped IN
  the draft**, as `deffn-ramhunt` §6 required.
* 🎯 **The ceiling is a division and nothing spells 9.**
  `FN_AREA = ((LINEBUF - FN_PAREA)/11)*11`, `FN_MAXP = FN_AREA/11`. Same
  arithmetic that predicts the reference's own nine from its 100-byte block.
* **The slot IS a scalar chain entry** — `[name0][name1][type][value]`, 11 B —
  which is what lets `scv_find` hand one back to `var_load_fac`,
  `var_store_fac`, `str_get_key` and `str_set_key` completely unchanged.
* **The definition is an ordinary variable** keyed with bit 7 of `name0` set. So
  `CLEAR` erases it for free (`o.clearwipe3`) and `A` and `FNA` coexist
  (`o.namespace`), with no new table and no new eraser.
* **A nested call saves the outer frame and restores it**, on the Z80 stack,
  live-prefix only, with a page-granularity floor (`FN_STK_FLOOR $F200`) that
  turns runaway recursion into the reference's own ERR 7 (`b.recurse`).
* **A fault inside a body resets `FN_FEND`** in `raise_error` — 5 B, free of
  register cost because `record_errline` clobbers A anyway. Nothing unwinds
  `fn_leave` (the trap path resets SP outright), and a stale frame would make
  every later reference to a formal's NAME read a dead slot. `o.errrestore`
  (`X` = 5, `ERR` = 11 after a body that divided by zero) is the row.

---

## 6. Regression: what the shared-path edits did to everything else

Six of the seven in-place arms sit in code every program touches — PRINT's item
classifier, `ev_f`, `str_eval_one`, `raise_error`, `if_skip_to_else`. Run on the
scaffolded machine:

| gate | result |
|---|---|
| `make namspc-acceptance` | **102/102** — the same tally as `b1a01be` |
| `make strparen-acceptance` | **16/16** |
| `make fldwidth-acceptance` | **47/47** |
| `make deffn-selftest` | **18/18** (no emulator; the gate's own mutation battery) |
| `make unit-test` | **58 of 59 files PASS**, see below |

🎯 **THE ONE UNIT FAILURE IS THE SCAFFOLD ANNOUNCING ITSELF, AND THAT IS WORTH
MORE THAN A CLEAN RUN.** `test_stmt_dispatch.py` reports *"80 table entries, 80
dispatch OK"* and then four MISSING rows — `DRAW_TOKEN`, `SPRITE_TOKEN`,
`VDP_TOKEN`, `BASE_TOKEN`. Those are exactly, and only, the four statements
G6/G7/G8 gate. A scaffold that removes features and produces a completely green
suite would be a scaffold nothing checks; this one names its own three switches
in a gate that had no idea it was being used as a control.

⚠️ **These are scaffold readings.** They say the edits do not break the shared
paths; they do not say the shipping image is right, because there is no shipping
image.

---

## 7. Where the code is, and what it would take to ship it

The whole implementation is the branch **`deffn-draft`**:

    git diff main..deffn-draft

🔴 **THAT BRANCH DOES NOT BUILD ON ITS OWN TERMS** — `make basic-reloc` stops at
`BASIC_IMAGE_OVERRAN_8000_CEILING__TRIM_IT_OR_EVICT_TO_SUBROM`, which is the
assert doing its job. It is a measurement, not a candidate to merge.

**The 350 B has to come from two places, and both are measured, not guessed:**

1. **Carve.** `scratchpad/dupspan_sweep.py` at `b1a01be` reports **53 duplicate
   groups, 403 B recoverable IF every collapse is position-independent** —
   which the tool says out loud it cannot decide. Reading the groups by hand
   (terminator, internal `jr` reach, fallthrough entry) puts the SAFE subset at
   roughly **200 B**; `tools/clone_scout.py --min 6` independently estimates
   136 B over 14 groups, overlapping. 🔴 **Both figures are estimates and rot:
   RE-RUN THEM.** D-DUPSPAN spent the two ERR-code families out of this same
   list for a measured +50 B, so the remainder is what is left, not the whole.
2. **Evict the parsing.** `fn_call`'s name resolve (36 B), its list open (15 B),
   the bind loop's parse + delimiters (45 B), `fn_slot` (34 B) and the whole of
   `ex_deffn` (52 B) are pure token walking over page-3 RAM with no `eval` in
   them — **page-0-tenant legal**, in a sub page 0 that has 3046 B free after
   this work. Main would keep only the four call-outs it cannot delegate
   (`eval`, `str_eval`, `var_store_fac`, `str_set_key`), the frame save/restore
   and the result coercion. Estimated **~110 B** back, against ~46 B of new
   tenant glue. ⚠️ **ESTIMATED. It needs the same treatment this file gave the
   first draft: build it and read the wall.**

⚠️ **AND IT IS STILL TIGHT.** 100 + 200 + 110 = 410 against 450. The remaining
~40 B has to come from a third source or from shaving the draft, and pretending
otherwise is how a slice starts and does not finish.

---

## 8. What is NOT claimed

* **Nothing about the shipping build.** §3.
* **No knives.** The four predecessor suites (`dupspan`, `paintbord`, `paintmc`,
  `paints2seed`) were not run: they measure a shipping ROM against pinned
  hashes, and both images here are either byte-identical to `b1a01be` (`main`)
  or unbuildable (`deffn-draft`).
* **Nothing about aliasing between two formals of one call.** `FNA(P,Q)` called
  as `FNA(X, X*2)` from inside another FN whose own formal is `X` writes slot 0
  before the second actual reads it. The reference's behaviour is UNMEASURED and
  the row set does not contain a case that separates it. Filed.
* **Nothing about the string heap.** A string formal's shadow slot holds a
  descriptor that `strheap_gc` does not enumerate as a root. No measured row
  provokes a collection inside an FN call. Filed.
* **Nothing about `DEF FN` with `RESUME`, `CONT`, `TRON`, arrays as actuals, or a
  definition whose program line is later edited** — the design's own §9 list,
  unchanged.
