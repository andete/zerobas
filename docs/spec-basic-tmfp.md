# D-TMFP — of two pending faults, the one that happened FIRST is reported

`887e78a` (D-LOCARG) filed `t.tmfp` as a deferred row with a priced fix:

> a pending numeric fault outranks TMISMATCH too; that order is
> `check_expr_errors`', with 4 other callers

and priced it as a REORDER — test `FPERR` ahead of `TMISMATCH`, +7..+9 B,
declined for want of a denominator.

🔴 **BOTH HALVES OF THAT ITEM ARE WRONG, AND THE FIRST ONE IS REFUTED BY A ROW
THAT ALREADY SHIPS GREEN.** The rule is not a rank between two flags, the
denominator is not four callers, and the fix is not in `check_expr_errors`.

---

## 1. The two rows that cannot both be satisfied by a rank

Both have BOTH deferred flags live at the statement boundary. Both references
agree with each other on both. They disagree with each other about which flag
wins:

| program | vg8020 | cf3300 | zerobas @ `887e78a` |
|---|---|---|---|
| `WIDTH (A$<5)+0*(1/0)` | ` 13 ` | ` 13 ` | ` 13 ` 🟢 |
| `LOCATE STR$(1/0),3` | ` 11 ` | ` 11 ` | ` 13 ` 🔴 |

The first is `dfe-tmfp`, and D-EVALCHK §5.1 froze `TMISMATCH`-first as a
**forced constraint** on the strength of it. The second is D-LOCARG's `t.tmfp`.
A reorder fixes the second and breaks the first. **There is no rank here.**

⚠️ The filed item says §5.1 was frozen on `PRINT #A$,"X"` — "a row with a type
fault and NO pending numeric one, i.e. a row that cannot discriminate". That is
a misreading of the doc. `PRINT #A$,"X"` is D-BADFNUM §6's row, about
`eval_chan`, and it is indeed non-discriminating; §5.1's row is
`WIDTH (A$<5)+0*(1/0)`, which discriminates perfectly. §5.1 was **right**, and
so was `t.tmfp`. They are about different things.

## 2. The axis that separates them is TIME

The two rows differ in exactly one respect: **which fault occurs first** while
the expression is being evaluated. Swapping the operands swaps the answer:

| program | fault order | vg8020 | cf3300 |
|---|---|---|---|
| `WIDTH (A$<5)+0*(1/0)` | type, then numeric | ` 13 ` | ` 13 ` |
| `WIDTH 0*(1/0)+(A$<5)` | numeric, then type | ` 11 ` | ` 11 ` |
| `WIDTH (A$<5)+0*SQR(-1)` | type, then numeric | ` 13 ` | ` 13 ` |
| `WIDTH 0*SQR(-1)+(A$<5)` | numeric, then type | ` 5 ` | ` 5 ` |

🎯 **THE `SQR(-1)` PAIR IS WHAT MAKES THIS A RULE ABOUT ORDER AND NOT ABOUT
DIVISION.** The winning code changes with the *operand* (11 vs 5), not with the
operator. A "division by zero is special" reading predicts 11 in both; a rank
reading predicts one constant answer for all four.

**The rule:** the reference raises **eagerly**. There is no ranking mechanism on
the reference at all — the first fault aborts the statement on the spot and the
second one never happens. Everything above follows from that single fact.

### 2.1 Why zerobas cannot simply do the same

`ev_rel` has no mid-expression unwind — that is the entire reason
`type_mismatch_set` (basic/str-engine.asm) exists, and it is documented as such
since pre-4a. zerobas therefore emulates eager errors with two **sticky flags**
read at the statement boundary, and a **static test order** in the readers. A
static order can only ever approximate a rule that is about time, and it
approximated it wrongly in one direction for every row where the numeric fault
came first.

## 3. Scope — the denominator, which is not the filed one

The filed item counts "four other callers of `check_expr_errors`". At `887e78a`
the tree has **twelve** `call`/`jp check_expr_errors` sites, plus **two further
hand-rolled copies of the same ordering that a fix to `check_expr_errors` would
not have moved at all**, plus **four readers of `TMISMATCH` that never consult
`FPERR`**:

| site | shape | both flags reachable? |
|---|---|---|
| `interp.asm` `ex_if` | `IF <expr> THEN` | yes |
| `print.asm` `exp_num` | `PRINT <num>` | yes |
| `print.asm` `exps_notrel` | `PRINT "A" IMP 1` | yes — and it was ALREADY right |
| `interp.asm` `eval_int16_checked` | WIDTH / CLEAR / LOCATE / FIELD | yes |
| `float-arith.asm` `eval_chan` | `PRINT #<n>,` | yes |
| `missing.asm` `els_tc_common` | `A$=<numeric>` | yes |
| `graphics.asm` `ex_draw`, `spr_assign` | DRAW / `SPRITE$(n)=` | string operands only |
| `play.asm` `pl_dispatch` | PLAY | string operands only |
| `files.asm`, `input.asm`, `program.asm` | INPUT# / LINE INPUT / READ | ✗ TM structurally 0 (each says so) |
| **`interp.asm` `check_expr_errors_popbc`** | `ex_let` | **a SECOND copy of the ordering** |
| **`arrays.asm` `ex_let_arr`** | `A(0)=<expr>` | **a THIRD copy of the ordering** |
| **`files.asm` `fch_check`** | the string-channel test, all 12 file verbs | **tests TM, never FPERR** |
| **`expr.asm` `ev_ff_ckpdl`** | `PDL(x)` | **tests TM, never FPERR** |
| **`expr.asm` `ev_mc_arg_checked`** | `RND(x)` etc. | tests both, FPERR first |
| **`str-engine.asm` `sfr_argok`** | `HEX$`/`OCT$` | tests TM, then FPERR |

🎯 **THE THREE BOLD ROWS ARE THE ONES THAT DECIDE THE DESIGN.** A reorder of
`check_expr_errors` would have left `ex_let`, `ex_let_arr` and all four
TM-only readers still answering by flag identity — i.e. it would have fixed
*some* of the 21 divergent rows and left the rest, while breaking §5.1's row.

## 4. Design — record the order where it is KNOWN

`TMISMATCH` has exactly **one** writer, `type_mismatch_set`, and `exec_stmt`
(basic/interp.asm) clears both flags **together** at every statement boundary.
Therefore, at the instant the type fault is marked, a non-zero `FPERR` means —
with no bookkeeping, no sequence counter and no new RAM cell — that the numeric
fault came first.

So the type fault simply **does not arm**:

```
type_mismatch_set:
                ld      de,0            ; the D-2 contract's hard 0, BOTH paths
                ld      a,(FPERR)
                or      a
                ld      a,1             ; A=1 on BOTH paths (§4.3); does not
                                        ; touch the flags
                ret     nz              ; a numeric fault is already pending: it
                                        ; happened FIRST and is what the reference
                                        ; reports -- leave TMISMATCH clear
                ld      (TMISMATCH),a   ; A is still 1
                ld      a,$DD
                ld      (ERRMARK),a
                ret
```

Every reader of `TMISMATCH` — all fourteen of them, including the two copies a
`check_expr_errors` fix could not reach and the four that never test `FPERR` —
then reports the fault that really did come first. **One site, +5 B.**

### 4.1 Why the hard 0 is hoisted above the guard
`ld de,0` is part of the routine's published contract on **both** paths, not
just the arming one: `field.asm` relies on "type_mismatch_set's hard 0 for a
STRING" and `eval_chan` on a type-mismatched expression yielding 0. Hoisting it
above the early `ret` keeps that true and costs nothing (nothing between the
hoist and the stores touches DE).

### 4.2 💰 The reorder, priced and DECLINED on evidence
Testing `FPERR` first inside `check_expr_errors` breaks the `check_fperr_only`
fall-in and needs the FPERR test written twice: **+6 B** in main page 1 in its
cheapest form (12 B for the two tests with a fall-through into the unchanged
`check_fperr_only`, vs 13 B today). Affordable at 22 B free. **It is declined
because it is wrong, not because it is dear:** it would turn `dfe-tmfp` red in
the shipped `width-acceptance` gate, and it would not move `ex_let`,
`ex_let_arr` or the four TM-only readers at all.

### 4.3 🔴 The first draft leaked a register the header did not document
The guard's first cut returned early **without restoring `A`**, so the early
exit published `A = FPERR`'s value where the routine had always published
`A = 1`. The header promised only "DE = 0; ret. Clobbers A" — but `str_cat`'s
`sct_err2` does `call type_mismatch_set` / `or a` / `ret` and names the value in
its own comment, `A=1 -> CF clear (malformed operand)`. `ld a,1` is therefore
hoisted **above** the `ret nz` (it does not touch the flags, so the `ret nz`
still tests `FPERR`), and both exits publish it. Cost unchanged at +5 B; the
header now states the contract.

⚠️ **AND THAT WAS NOT THE CAUSE OF THE ROW THAT PROMPTED IT.** Restoring `A`
was necessary and did **not** fix `r.hex` — see §8. A hypothesis that is right
about the contract can still be wrong about the symptom; it was worth building
only because it was measured immediately afterwards rather than assumed.

## 5. Forced constraints

### 5.1 A type fault with NO numeric fault pending must not move
Seven negative controls (`n.tm.*`) across every reader, plus `n.fp.*` for the
mirror. This is what K-TF2 (inverted polarity) cuts.

### 5.2 The hard 0 must survive on the non-arming path
§4.1. `eval_chan` performs its coercion when `TMISMATCH` is clear, so the value
it coerces must still be the contract's 0.

### 5.3 §5.1 of `spec-basic-evalchk.md` is CORRECTED, not deleted
Its row and its reading were right; its *generalisation* ("the `TMISMATCH` test
must stay AHEAD of the FPERR test") was one row wide. Restated there as a
consequence of this rule.

## 6. The cost — measured

| wall | before | after | Δ |
|---|---|---|---|
| main low region | 11 B | 6 B | **−5** |
| main page 1 | 22 B | 22 B | 0 |
| sub page 0 | 3604 B | 3604 B | 0 |
| sub page 1 | 1483 B | 1483 B | 0 |

Hand count: `ld de,0` (3) + `ld a,(FPERR)` (3) + `or a` (1) + `ret nz` (1) = 8 B
inserted; `ld de,0` (3) deleted from the tail. **Net +5 B, exact.**

⚠️ **`sub.rom`'s HASH MOVES ON A MAIN-ONLY CHANGE, AND ITS WALLS DO NOT.**
`tools/gen_resident_abi.py` regenerates sub's view of main's resident ABI from
`build/basic-reloc.sym` on every build, so a low-region shift rewrites sub's
call-target immediates without changing its size. A knife runner that hashes all
four ROMs sees this correctly; one that expected "main-only edit ⇒ sub
unchanged" would misread it as contamination.

## 7. Region
Every byte is main **low region** (`basic/str-engine.asm`, the string engine at
`$2812-$3FFF`). No page-1 byte, no sub-ROM byte, no new RAM cell.

---

## 8. 💰 DEFERRED with a price: `r.hex`

`Q2$=HEX$(0*(1/0)+(Q$<5))` reads ` 11 ` on both references. It read ` 13 `
before this slice and reads ` 2 ` after. **Say it plainly: the fix moved this
row from one wrong answer to another wrong answer.** It is 1 of 50, and it is
the only row of the fifty that does not agree.

🎯 **WHAT IT BOUGHT IS WORTH MORE THAN THE ROW.** Localized on zb
(`docs/tmfp-msx1-characterization.md` §5), the failure is:

* **not** specific to `HEX$` — `STR$` and `OCT$` do it too;
* **not** specific to the assignment driver — `PRINT HEX$(…)` shows it as well;
* dependent on **both** faults landing inside a string function's parentheses —
  either fault alone reads correctly (` 13 ` / ` 11 `).

The mechanism is **two pre-existing defects that `TMISMATCH` was masking**,
neither of them caused by this slice:

1. after a string-compare mismatch the cursor does not land on the closing `)`,
   so `str_fn_radix`'s `cp ')'` fails and takes the `str_arg_empty` exit;
2. `str_arg_empty` then does `ld a,4` / `ld (FPERR),a` — **overwriting** the
   pending Division-by-zero 11 with the deferred syntax-error 4, which is what
   prints as ERR 2.

🔴 **DEFECT 2 IS A FIRST-ERROR-WINS VIOLATION OF EXACTLY THE KIND THIS SLICE IS
ABOUT**, three hundred lines from the routine it fixed, in the same file — and
`sfr_argok`'s own comment fifteen lines away already states the rule it breaks
("an inner error keeps its own (more specific) message"). Before D-TMFP both
defects were invisible, because `TMISMATCH` was armed and `check_expr_errors`
reported 13 before the clobbered code could surface. **A masked defect is not a
fixed one, and the only reason this is legible now is that the mask came off.**

💰 **PRICED.** Guarding the clobber is **+6 B** (`ld a,(FPERR)` / `or a` /
`jr nz` around the two stores) and the main low region has **exactly 6 B free**
after this slice — the entire remaining budget, spent on a guard that fixes
defect 2 and leaves defect 1 (the cursor) unmeasured and unexplained. A row that
needs its own cursor characterisation is its own slice with its own denominator,
not a rider on this one. Filed in `TODO.md`.

## 9. Knives

See §9.1 for results. Three cuts, each run twice, scored against a predicted RED
set **and** a predicted GREEN set, on `zb` only (a cut in zerobas can only move
zerobas; the references are constants).

| knife | cut | tests |
|---|---|---|
| K-TF1 | `ret nz` → `nop` — the guard is computed and discarded | the whole rule: the pre-slice ordering returns |
| K-TF2 | `ret nz` → `ret z` — inverted polarity | that a type fault **alone** must still arm |
| K-TF3 | the `ERRMARK` store dropped | **which** of the two stores the readers consult |

All three cuts are byte-neutral (`ret nz` → `nop` / `ret z`; `ld (ERRMARK),a` →
three `nop`s), which is confirmed by `sub.rom`'s hash staying at `071347df`
across every cut — no main symbol moved, so the regenerated resident ABI did not
either (contrast §6's warning about a non-neutral change).

### 9.1 Results — both rounds identical for all three

| knife | round 1 | round 2 | RED rows |
|---|---|---|---|
| K-TF1 | **EXACT** | **EXACT** | 9 predicted, 9 observed |
| K-TF2 | **MISS** | **MISS** | 7 predicted, **16** observed |
| K-TF3 | **EXACT** (predicted miss) | **EXACT** | 0 predicted, 0 observed |

**K-TF1** moved exactly the nine FP-first rows, each from its correct code back
to ` 13 ` (`o.w.fp5` from ` 5 `, the rest from ` 11 `), with all nine green rows
held. That is the rule, deleted and restored.

🔴 **K-TF2'S PREDICTION WAS WRONG, AND THE ERROR WAS MINE, NOT THE TREE'S.** The
knife comment claimed its red set would be **disjoint** from K-TF1's — "the pair
is what makes the partition". It is not disjoint; it is the **union** (16 rows).
Inverting `ret nz` to `ret z` does two things, and the prediction only counted
one: with `FPERR` clear the routine returns early and the type fault never arms
(the 7 predicted rows), **and** with `FPERR` set it falls through and arms — i.e.
exactly the pre-slice behaviour, so all nine of K-TF1's rows move too. A single
inverted branch cannot produce a disjoint set; it produces the complement on one
side and the original defect on the other.

🎯 **THE MISS IS THE MOST INFORMATIVE PART OF THE RUN, BECAUSE OF *HOW* THE SEVEN
DEGRADE.** Each TM-only reader fails in its own way once the flag stops arming,
which is the direct evidence that §3's four extra readers are real, distinct, and
were never reachable from `check_expr_errors`:

| row | reader | ` 13 ` → |
|---|---|---|
| `n.tm.loc` | `eval_int16_checked` | ` 0 ` — **no error at all**, the string coerced silently |
| `n.tm.hex` | `sfr_argok` (HEX$) | ` 0 ` — no error at all |
| `n.tm.chan` | `fch_check` (files) | ` 59 ` — derails to a **file** error |
| `n.tm.pdl` | `ev_ff_ckpdl` | ` 5 ` — PDL's own domain check preempts |
| `n.tm.w` | `eval_int16_checked` | ` 5 ` |
| `o.w.tm` | `eval_int16_checked` | ` 5 ` |
| `o.if.tm` | `ex_if` | ` 2 ` — syntax error |

Five distinct wrong answers from one cut. `n.tm.chan` reproducing D-BADFNUM §6's
own "derail to a file error" failure mode is the sharpest of them: that is the
regression that slice was written to prevent, recovered here as a knife result.

**K-TF3** reddened **nothing**, as predicted and for the stated reason —
`ERRMARK`'s only reader is `els_tc_common`, which reads it *after*
`check_expr_errors`, and on every row here a fault is pending so that call aborts
first. The ROM hash moved (`d819a385` vs the baseline `af0a69ef`), so this is a
genuine "the cut reached the artifact and reddened nothing", not a
DID-NOT-HAPPEN. It narrows the claim: **the rule rides on the `TMISMATCH` store
alone**, and the `ERRMARK` store beside it is not load-bearing for any row here.

## 10. As-built

### 10.1 What landed
One guard in `type_mismatch_set` (`basic/str-engine.asm`), **+5 B**, main low
region. No page-1 byte, no sub-ROM byte, no new RAM cell, no change to
`check_expr_errors` or to any of its twelve callers.

### 10.2 The walls — the hand count was EXACT

| wall | `887e78a` | as built | Δ |
|---|---|---|---|
| main low region | 11 B | **6 B** | −5 |
| main page 1 | 22 B | **22 B** | 0 |
| sub page 0 | 3604 B | **3604 B** | 0 |
| sub page 1 | 1483 B | **1483 B** | 0 |

### 10.3 The gate

`make tmfp-acceptance` — 50 rows, 4 positive controls, 7 negative controls,
**49 scored and agreeing, 1 deferred** (§8), on `vg8020` + `cf3300` + `zb`.
Before the fix the same 50 rows scored **29 agree / 21 diverge**.

`make locarg-acceptance` goes **44/45 → 45/45 with its DEFERRED dict emptied**,
which was this slice's stated target.

### 10.4 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`, and this run re-derived that the hard way), **39 targets, all rc=0,
23 min 31 s wall**: D-LOCARG §10.6's 38 plus **`tmfp-acceptance` (new)**.

`unit-test` **59** · `audit-citations` CLEAN (**778** swept, +3 on D-LOCARG's
775 — two new docs and one new probe; **the sweep counts docs, not just code**) ·
`preflight-check` **95 guarded / 0 unguarded** · `injector-check` **351** files ·
`rowshape-check` **22** probes · `latch-check` **16/16** · `deadcode` main 1586 /
sub 1533 spans, **0/0 (+1)** · `lnblank-acceptance REPEAT=2` **539/539** ·
`lnblank-say-acceptance` **204/204** · `logicops-acceptance` **193/193** ·
`float-acceptance` · `linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` ·
`lptverb-acceptance` · `dskmsg-acceptance` · `diskbasic-acceptance` ·
`fat-error-acceptance` · `runtail-acceptance` · `castail-acceptance` ·
`cassave-acceptance` · `readvar-acceptance` · `arylv-acceptance` ·
`inputary-acceptance` · `lvfix-acceptance` · `fldary-acceptance` ·
`lrvar-acceptance` · `forvar-acceptance` · `nxlist-acceptance` ·
`nxary-acceptance` · `tgtspc-acceptance` · `namspc-acceptance` **58/58** ·
`fldwidth-acceptance` **40/40** · `clearpool-acceptance` **52/52** ·
`onerr0-acceptance` **24/24** — **plus the three gates this slice touches**:
**`width-acceptance` 94/94** (the gate holding `dfe-tmfp`, the row that refuted
the briefed design — this is the number that had to hold and did),
**`missing-acceptance` 214/214 as recorded**, and **`locarg-acceptance` 45/45
with 0 deferred** (was 44/45 + 1).

⚠️ **`rowshape-check` 21 → 22 and `injector-check` 350 → 351**, each +1 for the
new probe, and **`audit-citations` 775 → 778** for two docs plus one probe. All
three grow with the corpus, so last slice's figure is a prediction, not a
baseline — these were scored, not assumed.

🔴 **THE 50-ROW GATE WAS RE-RUN AGAINST THE SHIPPED ROM, AND THAT WAS NOT
CEREMONY.** The full three-side run in §10.3 was taken on the guard's FIRST
draft, before §4.3's `A = 1` hoist. 18 of the 50 rows were re-measured by the
knife baseline, leaving 32 carried across a rebuild. Re-run on the shipped
image: **50 printed, 49 scored, 49 agree, 0 diverge, 1 deferred**, rc=0. A
headline number measured on a superseded build is exactly the shape of
[[a-prediction-copied-into-the-result-column]], and it applies to one's own
figures first.

### 10.5 Three things went differently
1. 🔴 **The slice as briefed was refuted, by a row that already ships green.**
   The reorder would have traded `dfe-tmfp` for `t.tmfp`. The predicted refuter
   was `eval_chan` (D-BADFNUM's caller); the actual refuter was D-EVALCHK §5.1's
   own row, which the filed item had mis-described as non-discriminating.
2. 🔴 **The denominator was 4 in the filed item and 18 in the tree** — twelve
   `check_expr_errors` sites, two further hand-rolled copies of the ordering,
   and four readers that never test `FPERR`. The fix reaches all of them
   *because* it moved to the writer instead of the readers; the priced reorder
   would have reached six.
3. 🔴 **A hypothesis that was right about the contract was wrong about the
   symptom.** §4.3's `A = 1` leak is real, was worth fixing, and did **not** fix
   `r.hex` — measured immediately rather than assumed, which is the only reason
   §8's actual cause was found.
4. 🔴 **A knife prediction claimed a partition that a single inverted branch
   cannot produce** (§9.1). The miss is recorded rather than absorbed, and what
   it exposed — five distinct wrong answers from five distinct readers — is
   better evidence for §3's denominator than the prediction would have been.
