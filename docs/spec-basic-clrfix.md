<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-CLRFIX — CLEAR's memory-ceiling slot had no guard at all, and the fix was a carve

Status: **✅ SHIPPED. −4 B of main page 1** (free **1 → 5 B**), on `7b87126`.
`basic-reloc.rom` `59f0a082 → f1e743c2`, merged `5ea13c71 → 5293b7c7`,
`sub.rom` unchanged `490ffc49`.

Two open `TODO.md` items went in. **Four defects came out, plus three vacuous
rows in a characterization document and two false claims in the source** — and
the whole thing costs negative bytes.

---

## 1. What was filed, and what was actually there

Filed by [D-CLRTRAP](spec-basic-clrtrap.md) §3: `CLEAR 200,` raises the right
error but loses the `ON ERROR` trap and writes `HIMEM = 0`; `CLEAR ,200`
completes silently where both references answer `Syntax error`.

The baseline sweep (`scratchpad/clrfix_before.out`,
`scratchpad/clrfix_char_before.out`, `scratchpad/clrfix_himem_before2.out`)
found **the memory-ceiling slot has no guard of any kind**:

| row | statement | refs | zerobas BEFORE | |
|---|---|---|---|---|
| `q.trail`  | `CLEAR 200,`       | `24 0` | `UNTRAPPED Missing operand in 30`   | filed |
| `q.kcolon` | `CLEAR 200,:A=1`   | `24 0` | `UNTRAPPED Missing operand in 30`   | filed |
| `q.comma`  | `CLEAR ,200`       | `2 0`  | `0 0`                               | filed |
| `q.conly`  | `CLEAR ,`          | `2 0`  | `UNTRAPPED Missing operand in 30`   | 🔴 new |
| `q.commak` | `CLEAR ,200:A=1`   | `2 0`  | `UNTRAPPED **Out of memory** in 30` | 🔴 new |
| `q.div`    | `CLEAR 200,1/0`    | `11 0` | `UNTRAPPED Division by zero in 30`  | 🔴 new |
| `q.str`    | `CLEAR 200,"x"`    | `13 0` | `UNTRAPPED Type mismatch in 30`     | 🔴 new |
| `q.ovf`    | `CLEAR 200,70000`  | `6 0`  | `0 0`                               | 🔴 new |
| `z.hd000`  | `CLEAR ,&HD000`    | `2 0`  | `0 0`                               | 🔴 new |
| `z.seq`    | `CLEAR 500:CLEAR ,&HD000` | `UNTRAPPED Syntax error in 30` | `0 0` | 🔴 new |
| `z.neg`    | `CLEAR 200,-1`     | `5 0`  | `0 0`                               | 🔴 new, **NOT FIXED** |

**11 divergent rows where 3 were filed.** And every one of them wrote:

| row | statement | refs | zerobas BEFORE |
|---|---|---|---|
| `h.trail` | `CLEAR 200,`       | `SAME` | `->0` |
| `h.comma` | `CLEAR ,200`       | `SAME` | `->200` |
| `h.div`   | `CLEAR 200,1/0`    | `SAME` | `->0` |
| `h.str`   | `CLEAR 200,"x"`    | `SAME` | `->0` |
| `h.ovf`   | `CLEAR 200,70000`  | `SAME` | `->0` |
| `h.hd000` | `CLEAR ,&HD000`    | `SAME` | `->53248` |
| `h.neg`   | `CLEAR 200,-1`     | `SAME` | `->65535`, **NOT FIXED** |

[D-MISSOP](spec-basic-missop.md)'s silent-memory-write class had **one** member
recorded here. It has seven.

## 2. ✅ As built — two changes, one of them negative

    ex_clear:   cp ',' / jr z,clr_himem          DELETED          -4 B
    clr_himem:  call eval -> call eval_int16_checked               0 B

💰 **NET −4 B. Main page 1 free 1 B → 5 B**, read from a clean
`make basic-reloc` on 2026-08-23.

**(a) The carve.** `CLEAR ,himem` is not MSX BASIC — both references answer
`Syntax error`. With the special case gone, a leading comma falls into the
**pool** argument's `eval_int16_checked`, whose own `check_expr_errors` raises
the deferred `ev_f_empty` syntax error at `ex_clear`'s depth — before `POOLSIZE`
is stored and before `clear_vars` can eat the trap. **The references' answer,
for free, out of machinery that was already there.**

**(b) The swap, at zero bytes.** `eval_int16_checked` *is*
`eval` + `check_expr_errors` + `get_int16_checked`, so one 3-byte call replacing
another buys three fixes: the deferred-fault guard (which closes the trap loss
*and* the write, because the raise happens before `ld (HIMEM),de`), the type
fault, and the `ERR 6` the references give on `70000`.

> 🔴 **CORRECTION, SAME DAY (D-HIMDOM, [`spec-basic-himdom.md`](spec-basic-himdom.md)):
> `eval_int16_checked` WAS THE WRONG LEAF AND THIS SHIPPED A REGRESSION.** Its
> `get_int16_checked` stage rejects `|x| > 32767`, and **both references ACCEPT
> `CLEAR 200,50000`** (HIMEM = 50000). The coercion is the MSX **address**
> domain, −32768..65535 — `eval_addr`, which `basic/poke.asm` already uses.
> 🎯 **`q.ovf` could not have caught it:** `70000` is rejected under the signed
> rule *and* under the address rule, so the row cannot separate them, and
> `&HD000` passed only because MSX BASIC reads a hex literal ≥ `&H8000` as
> NEGATIVE (−12288), landing inside `|x| <= 32767` by accident. **No row in the
> 26 held a decimal in [32768, 65535].** The guard, the type fault and the
> trap/write half of this slice are unaffected and still measured — only the
> coercion's WIDTH was wrong. Fixed at +3 B by `eval_addr` + an explicit
> `check_expr_errors` (that leaf defers, exactly as `do_poke` handles it).

⚠️ **The control this could have broken is `h.set`.** `&H9000` is **−28672** as
a signed int16, so `|x| <= 32767` and the accepted ceiling still passes:
`->36864` on all three machines, before and after. Knife K-CF3 is what proves
that row is a detector.
🔴 **And that paragraph is the whole mistake in miniature.** `h.set` passing
*because* `&H9000` reads as negative is the fact that should have prompted the
question **"then what does a POSITIVE 50000 do?"** — it is written down here, one
line above the defect, as reassurance rather than as a lead.

## 3. The measurement — 26 rows × 3 machines, boot-per-case

`scratchpad/clrfix_probe.py` (16 rows, `[ERR 0]` from an `ON ERROR` handler with
a `<A>` pre-marker) and `scratchpad/clrfix_himem.py` (10 rows, HIMEM read in
**direct mode** either side of the `RUN`).

**ERR: 11 DIFF → 1. HIMEM: 7 DIFF → 1.** Both survivors are `z.neg` / `h.neg`,
§5. Controls `q.ok` `q.both` `q.bare` `q.kbare` `t.notrap` `h.none` `h.ok`
`h.set` unmoved throughout.

🎯 **`z.seq` matches the references *including being untrapped*.** Both answer
`UNTRAPPED Syntax error in 30`, because the *first* `CLEAR` has already killed
the `ON ERROR` handler — [D-CLRTRAP](spec-basic-clrtrap.md) §3.1's `t.after`
finding firing again, this time as a want rather than a defect.

### 3.1 🔬 An apparatus fix that was free: the *before* value is not the question

D-CLRTRAP's HIMEM probe printed HIMEM before **and** after — which is what makes
the delta knowable — and then put **both** in the face. `h.set` therefore read
`62336->36864` on the VG-8020 and `56951->36864` on the CF-3300 and scored
**"THE REFERENCES DISAGREE"**: an unscoreable positive control. Dropping the
machine-specific half (`SAME` or `->after`) moved the set from 7 scored to 10 at
no extra boots. The absolute value was never the question.

## 4. 🔴 Two false claims in the source, and three vacuous rows in a document

* **`basic/clear.asm` said HIMEM was "record-only today" and that "no allocator
  consults HIMEM yet".** It is consulted, **by `CLEAR` itself**:
  `basic/str-engine.asm` `heap_reset` — called from `clear_vars`, which
  `clr_done` calls three lines later — computes `FRETOP := min(HIMEM,TXTMAX)`.
  Row `q.commak` is what caught it: `CLEAR ,200:A=1` answered **`Out of
  memory`**, because writing 200 into HIMEM and then wiping the variables leaves
  no heap for the very next assignment. 🎯 **A comment asserting that a store is
  inert is exactly the kind that stops anyone auditing the store.**
* **`heap_reset`'s design justification was about a statement that does not
  exist.** It said deriving the pool floor sub-side "still makes `CLEAR ,himem`
  keep its size (characterization §2.8)". `CLEAR ,himem` is a syntax error on
  both references. **The design is unaffected and still right for its own
  reason**; the benefit it claimed was to a form the language does not have.
* **`docs/clearpool-vg8020-characterization.md` §2.4 and §2.8 record REFERENCE
  readings for `CLEAR ,&HD000`.** Row `z.hd000` measures that statement: **ERR 2
  on both machines.** So §2.4's *"`CLEAR 500 : CLEAR ,&HD000` → 500"* reads 500
  because **the second statement never ran**, and §2.8's *"→ 200 (unchanged)"*
  is the boot default surviving a statement that did not execute.
  ⚠️ **The surrounding conclusions are untouched** — `NEW` and `RUN` really do
  keep the size, and §2.8's other two readings use legal statements. Only the
  `,himem`-only clause had nothing behind it.

All three are **inverted in place, not deleted**.

## 5. What this does NOT fix — `CLEAR 200,-1`, and why the obvious cure is wrong

`z.neg` / `h.neg`: **`CLEAR 200,-1` is `Illegal function call` on both
references** and completes here, writing `HIMEM = 65535`. Not closed, filed.

🔴 **The pool argument's own negative test would be WRONG here.** Two lines up,
`CLEAR`'s *string-space* argument rejects negatives with `bit 7,d / jp
nz,gb_illegal`. Applying that to HIMEM breaks the accepted case: **`&H9000` has
bit 15 set exactly as `-1` does**, and `CLEAR 200,&H9000` is accepted on all
three machines (`h.set`). So HIMEM's domain is **a range, not a sign** — its
edges are unmeasured, and guessing one would be the [D-CIRCDOM](spec-basic-circdom.md)
mistake of blessing a domain that never existed. It needs its own characterization
sweep against both references.

🎯 Knife **K-CF3** makes this concrete: narrowing the coercion to a byte turns
**both** surviving red rows green at once — `z.neg` → `5 0` and `h.neg` →
`SAME`, matching the references on the ERR *and* on the write — while breaking
`q.both` and `h.set`. *A case that agrees can agree for the wrong reason*,
demonstrated on exactly the rows the next slice has to fix. **A fix for this row
that does not keep `h.set` at `->36864` is not a fix.**

## 6. 🔬 Knives — 4 of 4 EXACT, and the two that missed in round 1 missed together

`scratchpad/clrfix_knives.py`, `scratchpad/clrfix_knives.out`; round 1 kept at
`scratchpad/clrfix_knives_round1.out`. Each knife runs BOTH probes, 26 rows.

| knife | cut | moved |
|---|---|---|
| K-CF1 | the SWAP reverted alone (`eval_int16_checked` → `eval`) | **9**, all trailing-comma |
| K-CF2 | the CARVE undone alone (leading-comma arm restored, +4 B) | **7**, all leading-comma |
| K-CF3 | the coercion narrowed to a byte | **4** |
| K-CF4 | `clr_himem`'s `inc hl` → `nop` | **9** |

🎯 **K-CF1 and K-CF2 move DISJOINT row sets, and that is the point.** The fix
has two halves that landed in one commit and turned every row green together, so
the differential cannot tell them apart. Reverting each alone shows the swap owns
the trailing-comma rows and the carve owns the leading-comma ones, with no
overlap. It also shows the carve's mechanism is real: under K-CF2, `q.conly`
(`CLEAR ,`) answers `24 0` rather than the reference's `2 0`, because the
restored arm sends it to the HIMEM slot where the guard now raises 24 — the
right error for the wrong slot.

🔴 **Round 1 scored 2/4, and BOTH misses were one omitted row — `h.neg`.**
K-CF3 and K-CF4 each stop `CLEAR 200,-1` reaching the store, so its write row
moves in step with its ERR row. Every other ERR row in the file is predicted
together with its HIMEM twin; the one row I omitted the twin for is the one row
this slice does not fix — the row filed as *"out of scope, ignore"*.
🎯 **Out of scope for the FIX is not out of scope for the DENOMINATOR.** A row
written off stops being carried in the bookkeeping while continuing to move.


## 7. 🔴 Gates — two RED, and neither was mine

a per-slice clrfix_gates.sh battery wrapper (`scratchpad/*.sh` is gitignored —
the drivers are per-session by design, so it is not in the repo). The 26-row
sweep in §3 went green and **two gates
written for other slices went red**: `unit-test` and `array-acceptance`. This is
the D-MISSOPFIX lesson again — a purpose-built probe's denominator is shaped by
the hypothesis that motivated it, and the blast radius of a deleted grammar arm
is exactly what that hypothesis does not describe.

**Both red gates, and four more consumers found by grepping for the form, were
asserting `CLEAR ,himem` — a statement neither reference accepts.**

| consumer | asserted | now |
|---|---|---|
| `tests/test_statements.py` | `CLEAR ,&HABCD` **sets** HIMEM | the legal 2-arg form sets it, **and** the refused form leaves it alone |
| `basic_probe_arrays.py` ×2 | squeezed RAM with `CLEAR,&H8050` | `CLEAR 200,&H8050` — same ceiling, legal statement |
| `basic_probe_clearpool.py` ×2 | 🔴 **vacuous**: passed because the statement never ran | anchored on the error tail — a real refusal differential |
| `basic_probe_clear.py` group 2c | acceptance, **and is wired to no make target** | the abort, sentinel pre-zeroed so "did not fire" is a reading |
| `basic/PROVENANCE.md` | "all **four** syntax forms parse without error"; HIMEM "record-only" | three forms; the record-only claim inverted, three new oracle-locked rows |

🎯 **The pattern across all six: an assertion about a statement that does not
exist cannot fail for the right reason.** `basic_probe_clear.py` held the claim
for the life of the tree with no target ever running it — **an oracle nothing
runs is a claim nothing checks** — and `PROVENANCE.md` cited it as evidence.

⚠️ **AND THE BATTERY'S OWN DENOMINATOR WAS SHORT.** The 34-target list inherited
from D-CIRCMISS contains **no gate that owns CLEAR**: `clearpool-acceptance` was
never in it, which is why the two vacuous rows were invisible to it. The gates
that *did* go red caught the change through FIXTURES, not through the verb's own
gate. `clearpool-acceptance` is added; the battery is now 36 targets.
**A battery's denominator is a scope claim** [[a-hand-listed-denominator-is-a-scope-claim]].

After the corrections: `unit-test` 59/59, `array-acceptance` **146/146**
(including `scalar.str.chain.oom`, which had been failing too),
`clearpool-acceptance` **62/62 gated rows agree**, with `dflt-comma` and
`hmem-only` now reading `'Syntax error'` on both machines.
