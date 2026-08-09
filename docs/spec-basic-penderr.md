# D-PENDERR — first-error-wins is a property of the WRITE

`38becce` (D-TMFP) filed this slice unpriced:

> collapse `TMISMATCH` and `FPERR` into ONE set-if-empty `PENDERR` code cell, so
> first-error-wins is a property of the WRITE instead of a rule ~18 readers each
> re-implement

with the belief that it *saves* bytes, and instructions to decline with numbers
if it does not. It saves **48 bytes**. It is also **not the tidy-up it looks
like**, and §3.2 is the reason.

---

## 1. The claim, which was already three-quarters proved in the tree

`FPERR` (`$F069`) is not a boolean. It is a **code** — 1 overflow, 2 division by
zero, 3/8 illegal function call, 4 deferred syntax error, 5 subscript, 6 out of
memory, 7 redimensioned, 9 string formula too complex, 10 type mismatch, 11 out
of string space — mapped to an MSX ERR code by `fperr_to_err` (`basic/interp.asm`).

`TMISMATCH` (`$E3E5`) was a 1-byte boolean that fourteen readers tested *ahead*
of `FPERR`. It was never a second concept:

* `sfr_argok` (`basic/str-engine.asm`) already **promoted it by hand**, with
  `ld a,10` / `ld (FPERR),a` and a comment naming the value's meaning;
* `fperr_to_err` entry 10 is **ERR 13**, the same code and the same
  `err_msgtab` entry `type_mismatch_error` raises directly;
* `ev_mc_arg_checked`'s own header called it *"the OTHER deferred flag"*.

D-TMFP then supplied the invariant that makes the merge legal: `type_mismatch_set`
is the flag's only writer, it refuses to arm when `FPERR` is already non-zero, and
`exec_stmt` clears both cells together at every statement boundary. One lifetime,
one statement, one meaning — so `TMISMATCH` set ⟺ `FPERR := 10, if empty`.

## 2. What that buys, before it costs anything

Fourteen readers stop asking two questions. Three of them were **hand-rolled
copies of the same six-instruction ordering**, and two of those three are
copies a fix to `check_expr_errors` could never have reached — which is half of
why D-TMFP's briefed reorder was the wrong shape (`spec-basic-tmfp.md` §3):

| site | file | what collapses |
|---|---|---|
| `check_expr_errors` | interp.asm | becomes literally the same routine as `check_fperr_only` |
| `check_expr_errors_popbc` | interp.asm | the 2nd copy; its type-abort tail dies |
| `ex_let_arr` | arrays.asm | the 3rd copy; `ela_abort_tm` (vars.asm) dies |
| `ev_mc_arg_checked` | expr.asm | two tests become one |
| `sfr_argok` | str-engine.asm | the promotion *is* the merge, written out at one caller — deleted outright |
| `ev_f_defer` | expr.asm | its hand-rolled first-error-wins guard becomes the writer's contract |
| `eval_chan`, `fch_check`, `ev_ff_ckpdl` | float-arith / files / expr | branch on presence instead of kind (§5.3) |

## 3. The part the brief did not anticipate

### 3.1 The two cells' SEPARATENESS was load-bearing

`FPERR` had **twenty-one main-ROM writers and three in the sub-ROM**, and all but
two were a bare `ld (FPERR),a` — i.e. **last-error-wins**. The type fault was
safe from every one of them only because it lived somewhere else and every reader
looked there first.

### 3.2 The naive merge is unsound — but 🔴 MY REASON WAS WRONG, AND K-PE2 REFUTED IT

The design argument written before the work was:

> Merge the cells and leave the writers alone, and `WIDTH (A$<5)+0*(1/0)` does
> this: `(A$<5)` sets the cell to 10, then `0*(1/0)` hits `fp_div`'s
> `ld a,2` / `ld (FPERR),a` and **clobbers** it, and the boundary reports ERR 11
> where both references say 13. That row is `dfe-tmfp`, it ships green in
> `make width-acceptance`, and it is the row that refuted D-TMFP's briefed
> design.

**That is not what happens.** K-PE2 (§9) deletes set-if-empty outright — every
writer stores unconditionally, i.e. exactly the "naive merge" above — and
`o.tm.tmfp` (`WIDTH (Q$<5)+0*(1/0)`) **stays at ERR 13**. So do
`o.tm.tmov`, `o.tm.let`, `o.tm.ary` and `u.tm.tmfp`. Six predicted-red rows,
none of them moved.

🎯 **THE MEASUREMENT THAT EXPLAINS IT IS A PAIR ALREADY IN THE GATE.** Same
second operand, different first:

| row | program | K-PE2 |
|---|---|---|
| `o.nn.dzov` | `WIDTH 0*(1/0)+0*(1E38*1E38)` | ` 11 ` → ` 6 ` — **moved** |
| `o.tm.tmov` | `WIDTH (Q$<5)+0*(1E38*1E38)` | ` 13 ` → ` 13 ` — **did not** |

After a **numeric** first fault the second operand faults and writes. After a
**type** first fault it does not. So there was never a second writer to clobber
the type code, and the type/numeric rows are insensitive to the write rule
altogether. The screen cannot distinguish "the tail was not evaluated" from "it
was evaluated and did not fault", and this slice does not claim to know which —
but D-TMFP §8's independently-established **defect 1** (after a string-compare
mismatch the cursor does not land on the closing `)`) predicts the first, and
`r.hex.tm`'s behaviour under both K-PE2 and K-PE4 (13 → 2, i.e. the parser
lands on `str_arg_empty`) is consistent with it.

**THE DESIGN IS UNCHANGED; ONLY ITS JUSTIFICATION MOVED.** Set-if-empty is
required — by **17 measured rows** (`docs/penderr-msx1-characterization.md` §7.3)
— but they are the **numeric-vs-numeric** pairs, the two **sub-ROM**-first pairs,
the **`r.hex` family**, the **parse-time** rows and the three **widened readers**.
Not the rows I built the argument on.

⚠️ Recorded rather than quietly corrected, because the failure mode is the one
this project keeps re-deriving: a claim that is right about the conclusion and
wrong about the evidence looks identical to a claim that is right, until
something deletes the code and asks. It is also why the slice is not "delete a
cell": it is "make the cell first-write-wins at all twenty-four stores, which
then makes the collapse free" — and pricing only the deletion would have shipped
a 17-row regression while every type row stayed green.

### 3.3 That was the house rule already, implemented at 2 sites out of 24

`sfr_argok`: *"first-error-wins: an inner error keeps its own (more specific)
message"*. `ev_f_defer`: *"the reference reports the first error, not the later
reject"*. Both correct, both hand-rolled, both local. The rule was stated in the
tree four times and enforced twice.

## 4. Design — one writer, byte-neutral at every site

```
penderr_set:                    ; in: A = code. FPERR := A iff FPERR == 0.
                push    af      ; [the code + the CALLER's flags]
                ld      a,(FPERR)
                or      a
                jr      nz,pes_pending
                pop     af      ; A = the code again, F = the caller's
                ld      (FPERR),a
                ret
pes_pending:
                pop     af
                ret
```

**14 B, once.** Each writer's `ld (FPERR),a` (3 B) becomes `call penderr_set`
(3 B): **zero marginal cost.** Of the twenty-four pre-slice writers, one —
`sfr_argok`'s promotion — is deleted outright and the remaining **twenty-three**
are converted; `type_mismatch_set` then becomes the twenty-fourth, storing
direct on a cell it has just proved empty (§4.1).

🎯 **THE `push af` / `pop af` PAIR IS WHY THE SITE COST IS ZERO.** `pop af`
restores the flags *pushed on entry*, not the `or a` the routine performs, so the
routine clobbers **nothing** — register or flag — and is a true drop-in. Two
sites depend on that and would otherwise have needed guards of their own:
`arrays.asm`'s `ary_engine_call` tail argues **in prose** that its `NZ` survives
the store, and `str-engine.asm`'s `sct_ae_set` does `scf` immediately after.

### 4.1 The one store that stays direct
`exec_stmt`'s per-statement **clear**. A set-if-empty writer by contract refuses
to write when a code is pending, so it cannot perform a clear. It is now the only
bare `ld (FPERR),a` in the tree, which makes the invariant greppable.

`type_mismatch_set`'s own store also stays direct, because D-TMFP's guard has
*already* proved the cell empty two instructions earlier, and because that
routine publishes **different register contracts on its two paths** (`A = 1` on
the non-arming exit, `A = $DD` on the arming one — `spec-basic-tmfp.md` §4.3).
Delegating costs the same 3 bytes and would have made both exits identical, which
is a change nobody measured. Left alone deliberately.

### 4.2 The sub-ROM tenants reach the same writer
`sub/fp_pow.asm` (×2) and `sub/fp_exp.asm` raise into the cell from **page-1
tenant code**. Page-1 tenants may call main **low-region** routines by absolute
address, which is exactly what `tools/gen_resident_abi.py` exists to keep
current, so `penderr_set` was added to `REQUIRED` (12 symbols now). Without it,
first-error-wins would hold everywhere **except `x^y` and `EXP(x)`** — a
partial fix that every row outside `o.sub.*` would have scored green.

### 4.3 💰 The symbol is NOT renamed to `PENDERR`, deliberately
The brief names the merged cell `PENDERR`, and conceptually that is what it is.
`FPERR` keeps the name: 90+ references, `fperr_to_err`, `FPERR_STROOM`, and the
whole `fp_runtime_error` vocabulary are built on it, and a rename is a large diff
with a real regression surface and **zero byte value**. The concept is carried by
the *writer's* name (`penderr_set`) and by `FPERR_TYPEMM`, the new equate for the
value that used to be a flag. Named here so the divergence from the brief is a
decision, not a drift.

## 5. Forced constraints

### 5.1 `check_expr_errors` and `check_fperr_only` become the same instructions
Both names are kept. They are not redundant documentation: entering at
`check_fperr_only` was a caller's assertion that *"a type fault cannot be pending
here, and aborting on one would be a behaviour change"* — `program.asm`'s READ
site and `input.asm`'s each say so. The assertion is still worth reading; it is
now free.

### 5.2 A type fault with no numeric fault pending must not move
Thirteen negative controls, one per reader, all single-fault. This is what K-PE1
cuts.

### 5.3 The three kind-branching readers are WIDENED, not merely translated
`eval_chan`, `fch_check` and `ev_ff_ckpdl` asked *"is a TYPE fault pending"* and
now ask *"is anything pending"*. Each was byte-for-byte the same size either way,
and the widening is the correct reading of each site's own stated reason:

* `eval_chan` skipped its coercion so that a **hard-zeroed** expression would not
  fault spuriously. A pending div0 hard-zeroes identically.
* `fch_check` tested the type fault so a hard-zeroed channel would not be read as
  **channel 0** and answered ERR 59. Same argument, one fault class over.
* `ev_ff_ckpdl` kept PDL's ERR-5 domain check from preempting a fault that
  already happened. Same.

Rows `w.*` measure all three. §7 reports what actually moved.

## 6. The cost — measured, hand count EXACT on both walls

| wall | `38becce` | as built | Δ | hand count |
|---|---|---|---|---|
| main low region | 6 B | **14 B** | −8 | −8 ✓ |
| main page 1 | 22 B | **62 B** | −40 | −40 ✓ |
| sub page 0 | 3604 B | 3604 B | 0 | 0 ✓ |
| sub page 1 | 1483 B | 1483 B | 0 | 0 ✓ |

Low: `penderr_set` **+14**, `type_mismatch_set` 19→21 **+2**, `sfr_argok`'s
promotion **−17**, `ex_let_arr`'s copy **−7**.
Page 1: `exec_stmt`'s second clear **−3**, `check_expr_errors` **−10**,
`check_expr_errors_popbc` **−11**, `ela_abort_tm` **−5**, `ev_mc_arg_checked`
**−5**, `ev_f_defer` **−6**.

**Net −48 B.** 🟢 The low region — the tight wall since D-TMFP — more than
doubles, 6 → 14 B.

⚠️ `sub.rom`'s hash moves (`071347df` → `5d7c837a`) on what is nearly a main-only
change, and its walls do not: `gen_resident_abi.py` rewrites sub's call-target
immediates on every low-region shift. Here there is also one real sub change (the
three writers), but the hash would have moved regardless.

## 7. Results

`make penderr-acceptance` — **61 rows, 4 positive controls, 13 negative
controls, 61 scored, 61 agree, 0 diverge, 0 deferred**, on `vg8020` + `cf3300`
+ `zb`.

🔴 **A GATE THAT IS GREEN EVERYWHERE ON ITS FIRST RUN IS EXACTLY THE ONE TO
DISTRUST**, so the `zb` column was also measured on the **pre-slice tree** — the
sources reverted, rebuilt clean, and verified by reproducing `38becce`'s four ROM
hashes exactly before a row was read, then restored and re-verified byte-identical
to the slice build.

**44 of 61 already agreed. 17 moved. All 17 moved from a wrong answer to the
reference's. None moved the other way.** The gate was **44/61** before this slice.
Itemised in `docs/penderr-msx1-characterization.md` §7.3; the headline classes are
numeric-vs-numeric order (7 rows), a tenant-raised overflow losing to a later
div-by-zero (2), `str_arg_empty`'s clobber (4), and `LOF`/`EOF` answering
`File not open` where the reference reports the pending fault (3).

The three gates that hold this rule from outside, re-run on the shipped ROM:

| gate | before | after |
|---|---|---|
| `make tmfp-acceptance` | 49 scored + 1 deferred | **50 scored, 50 agree, deferred dict EMPTY** |
| `make width-acceptance` | 94/94 | **94/94** (holds `dfe-tmfp`) |
| `make locarg-acceptance` | 45/45 | **45/45** |

## 8. `r.hex`: D-TMFP's deferred row, closed — and what that does NOT mean

`Q2$=HEX$(0*(1/0)+(Q$<5))` reads ` 11 ` on both references. It read ` 13 ` before
D-TMFP, ` 2 ` after, and reads **` 11 `** now. D-TMFP priced the fix at **+6 B**
for a standalone guard on `str_arg_empty`'s clobber and declined it, the low
region having had exactly 6 B free. Routing that store through `penderr_set` cost
**zero marginal bytes**. `make tmfp-acceptance` goes **49 scored + 1 deferred →
50 scored, 50 agree, deferred dict empty**, and `r.oct` / `r.str` / `PRINT HEX$(…)`
agree too.

🔴 **DEFECT 1 IS STILL THERE, AND THE GREEN ROW IS NOT EVIDENCE OTHERWISE.**
D-TMFP §8 named two defects. Defect 2 (the unconditional `ld a,4`) is fixed.
Defect 1 — after a string-compare mismatch the cursor does not land on the
closing `)`, so `str_fn_radix` takes the `str_arg_empty` exit at all — is
**untouched**. HEX$ still bails; what changed is that bailing no longer
**rewrites** the pending code, so the division by zero that happened first
survives to the boundary and is what gets reported.

Closing defect 2 made defect 1 **unobservable through the error code**. That is
not the same as fixing it, and it stays filed in `TODO.md` as a cursor question.
Written down here because a green row is exactly how a masked defect gets
forgotten twice.

## 9. Knives

Four cuts, each run **twice**, each byte-neutral, each scored against a predicted
RED set **and** a predicted GREEN set, on `zb` only. All four ROMs hashed after
every cut build; every cut moved at least one ROM, so none is a DID-NOT-HAPPEN.
Both rounds were **identical for all four**.

| knife | cut | tests |
|---|---|---|
| K-PE1 | `jr nz,pes_pending` → `jr z,pes_pending` | the guard's polarity: nothing is ever recorded |
| K-PE2 | `ld a,(FPERR)` → `xor a` + 2 `nop` | **the slice itself**: the test always says "empty", i.e. LAST-error-wins at every writer |
| K-PE3 | the three SUB-ROM writers back to `ld (FPERR),a` | whether the resident-ABI half is load-bearing |
| K-PE4 | `str_arg_empty`'s writer back to `ld (FPERR),a` | D-TMFP §8's defect 2, restored |

⚠️ **K-PE2 IS SITED ON THE LOAD, NOT ON THE BRANCH,** and that is not cosmetic.
Replacing the `jr nz` with two `nop`s would orphan `pes_pending`, and the build
would be refused by `check_dead_code.py` — a knife aimed at the write rule killed
by the dead-code gate (D-MOUNTROW §6.3). Forcing the guard's *input* to zero
tests the identical claim, keeps the label referenced, and is byte-neutral.

### 9.1 Results

| knife | round 1 | round 2 | RED predicted | RED observed | GREEN held |
|---|---|---|---|---|---|
| K-PE1 | MISS | MISS | 43 | 40 (+1 unpredicted) | 17/18 |
| K-PE2 | **MISS** | **MISS** | 23 | **17** | 20/20 |
| K-PE3 | **EXACT** (predicted miss) | **EXACT** | 0 | 0 | 8/8 |
| K-PE4 | MISS | MISS | 6 | 5 | 8/8 |

**K-PE2 is the knife that matters, and its miss is §3.2.** Deleting set-if-empty
reddens exactly seventeen rows — the numeric-vs-numeric pairs, both
sub-ROM-first pairs, the two parse-time rows, and the whole `r.hex` family — and
reddens **none** of the six type/numeric rows the design argument was built on.
That is the measurement that corrected the justification. Its twenty predicted
greens all held, including `o.nn.dz5` and `o.tm.fptm`, whose answers happen to be
the last write anyway.

**K-PE3 reddened nothing, as predicted and for the stated reason.** `sub.rom`'s
hash moved (`1857b9bc` vs `5d7c837a`) while the three main ROMs stayed identical,
so the cut reached the artifact: this is a genuine "reddened nothing", not a
DID-NOT-HAPPEN. 🎯 **THE FINDING IS THAT THE SUB-SIDE CONVERSION IS DEFENSIVE,
NOT MEASURED.** Every path into the two tenants already refuses to run with a
code pending — `EXP` via `ev_mc_arg_checked`'s `ret nz`, `^` via `fp_pow`'s own
`ld a,(FPERR)` / `ret nz` prologue — which the pre-slice column corroborates
independently (`o.sub.dzex`, `o.sub.dzpw`, `o.sub.5ex` were already green at
`38becce`). The conversion and its resident-ABI symbol are kept anyway: both
guards exist for *other* reasons (not clobbering FAC; not running a function
body), so a future change to either would silently reintroduce last-error-wins in
exactly two places. This is `[[rule-gated-structurally-has-no-knife]]`, and it is
stated here rather than left as an unexercised symbol nobody can account for.

**K-PE4 missed by one row**, `o.pt.left` (`Q2$=LEFT$(0*(1/0)+1)`). Predicted to
take the `str_arg_empty` exit for its missing second argument; it does not —
`str_fn_left` reaches its error another way. A narrow, well-scoped prediction
error about one call site, not about the rule. Its five red rows are the whole
`r.hex` family and nothing else, which is the direct evidence that D-TMFP §8's
defect 2 is what those rows were failing on.

🔴 **K-PE1 IS THE BLUNT ONE AND ITS MISS IS PARTLY UNEXPLAINED.** It fails a
positive control (nothing can raise a deferred code any more, so `n.dz.w` prints
` 0 `), so the probe correctly exits **2** and prints its complete report in the
same grammar — which the runner parses, per D-ROWSHAPE. 40 of 43 predicted rows
moved. The four that did not (`o.nn.5dz`, `o.nn.5ov`, `o.sub.5ex`, `u.nn.5dz`)
all have `0*SQR(-1)` as their **first** operand and keep answering ERR 5 even
though no `penderr_set` write can succeed; `n.5.w`, which has the same first
operand and nothing after it, *did* move. Something raises ERR 5 on those rows by
a route that does not pass through the writer, and this slice does not know what
it is. It is a property of a **cut** tree, not of the shipped one, so it does not
bear on correctness — filed, not absorbed. The one unpredicted red, `r.hex.tm`
(13 → 2), is explained: with no code recordable, `str_arg_empty`'s
`jp str_eval_no` falls through to the LET-string driver's *direct* `stmt_error`
instead of a deferred 4.

## 10. As-built

### 10.1 What landed
One new 14 B routine (`penderr_set`, `basic/str-engine.asm`, low region); every
one of the twenty-four `ld (FPERR),a` stores except `exec_stmt`'s clear and
`type_mismatch_set`'s proven-empty one routed through it; the `TMISMATCH` cell
retired (its RAM byte deliberately left unclaimed so `MIDS_DEST` does not move);
fourteen readers collapsed to one test; three of them widened from "is a type
fault pending" to "is anything pending"; `penderr_set` added to the sub-ROM
resident ABI (12 symbols). **−48 B.**

### 10.2 The walls — the hand count was EXACT on both

| wall | `38becce` | as built | Δ |
|---|---|---|---|
| main low region | 6 B | **14 B** | −8 |
| main page 1 | 22 B | **62 B** | −40 |
| sub page 0 | 3604 B | **3604 B** | 0 |
| sub page 1 | 1483 B | **1483 B** | 0 |

ROMs: `basic-reloc 5dbec1dd`, `sub 5d7c837a`, `disk 2c630d3d`,
`zerobas-main-eu 350e9a69`.

### 10.3 Host tests
`make unit-test` **59/59**. Two files named the retired cell and were updated:
`tests/test_str_compare.py` now asserts `FPERR == 10` where it asserted
`TMISMATCH == 1`, which makes it the **host-side proof of the mapping the whole
slice rests on**; `tests/test_str_fn.py`'s statement-boundary stand-in clears one
cell instead of two.

### 10.4 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **40 targets, 24 min wall**: D-TMFP §10.4's 39 plus
**`penderr-acceptance` (new)**. All rc=0.

`unit-test` **59** · `audit-citations` CLEAN (**781** swept, +3 on D-TMFP's 778
— two new docs and one new probe) · `preflight-check` **95 guarded / 0
unguarded** · `injector-check` **352** files (+1) · `rowshape-check` **23**
probes (+1) · `latch-check` **16/16** · `deadcode` **0/0 (+1)** ·
`lnblank-acceptance REPEAT=2` **539/539** · `lnblank-say-acceptance` **204/204** ·
`logicops-acceptance` **193/193** · `clearpool-acceptance` **52/52** ·
`namspc-acceptance` **58/58** · `fldwidth-acceptance` **40/40 (+2 deferred)** ·
`onerr0-acceptance` **24/24** · `missing-acceptance` OK ·
`float-acceptance` · `linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` ·
`lptverb-acceptance` · `dskmsg-acceptance` · `diskbasic-acceptance` ·
`fat-error-acceptance` · `runtail-acceptance` · `castail-acceptance` ·
`cassave-acceptance` · `readvar-acceptance` · `arylv-acceptance` ·
`inputary-acceptance` · `lvfix-acceptance` · `fldary-acceptance` ·
`lrvar-acceptance` · `forvar-acceptance` · `nxlist-acceptance` ·
`nxary-acceptance` · `tgtspc-acceptance` — **plus the three gates that hold this
rule**: `width-acceptance` **94/94**, `locarg-acceptance` **45/45**, and
`tmfp-acceptance` **50/50 with its deferred dict emptied** (was 49 + 1).

🔴 **`latch-check` EXITED 2 IN THE CORPUS RUN, AND IT WAS THE DRIVER'S FAULT, NOT
THE TREE'S.** The corpus script does `rm -rf build` and then runs the six
emulator-free targets first; `latch-check` has no `repack-machine` prerequisite,
so it booted a machine config pointing at three ROMs that did not exist yet.
`omsx_preflight` refused rather than measured — *"a probe booted against this
machine would report the absence of the ROM as the absence of the FEATURE"* — and
that is precisely the failure it was built to catch, reproduced by the apparatus
that was supposed to be checking for it. Re-run with the ROMs present:
**16/16, rc=0.** Recorded because a corpus line reading `rc=2` is worth exactly
nothing until someone says which side broke.

⚠️ `rowshape-check` 22 → 23, `injector-check` 351 → 352 and `audit-citations`
778 → 781 all grow with the corpus, so last slice's figure is a prediction, not a
baseline. These were scored, not assumed.

🔴 **`badfnum-acceptance` (not a corpus target) exited 2 on ONE oracle drift:
`FIELD #-1,10 AS A$` captured nothing on `vg8020` while `cf3300` and the recorded
oracle both said `IFC`.** A `None` on a REFERENCE side is a broken fixture, not a
regression — and the row is a negative channel, which reaches `fchk_ifc` without
ever consulting the pending-error cell, so this slice cannot have moved it. Not
re-run; flagged here rather than folded in.

### 10.5 What went differently
1. 🔴 **The design's stated justification was refuted by its own knife** (§3.2).
   The merge does need set-if-empty; it needs it for seventeen rows that are not
   the ones the argument named, and the type/numeric rows it *was* built on turn
   out to be insensitive to the write rule entirely.
2. 🎯 **The deferred row closed for zero marginal bytes.** D-TMFP priced
   `r.hex`'s fix at +6 B against a 6 B budget and declined. Making the cell
   set-if-empty everywhere is byte-neutral at each site, so the guard came free —
   and `r.oct`, `r.str` and `PRINT HEX$(…)` came with it. The lesson is D-NAMSPC's
   again: **a price quoted per-site can be wrong by the whole slice when the fix
   is a shared writer** (`[[the-existing-split-is-cheaper-than-a-new-guard]]`).
3. 🔴 **A green row is not a fixed defect** (§8). `r.hex` is correct with defect 1
   still present; closing defect 2 made defect 1 unobservable through the error
   code. Written down because that is exactly how a masked defect gets forgotten
   a second time.
4. 🔴 **One knife proved a symbol is not load-bearing** (K-PE3) and the symbol was
   kept anyway, with the reason recorded. An unexercised resident-ABI entry that
   nobody can account for is worse than one that says why it is there.
5. 🔴 **A brief-supplied prediction was too pessimistic and the measurement said
   so.** The brief expected the write-side fix to close "half" of `r.hex` and
   warned it might move to a third wrong answer. It closed the row.
