<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-CLRTRAP — the dangling comma at PAINT and CLEAR, and a deferred error that outlives its own trap

Status: **✅ SWEPT. Measurement only — no source file changed, no ROM byte
moved** (`abfefa7f` / `490ffc49` / `a8173c25` throughout), on `e23e350`.
This is the follow-through D-CIRCMISS §7 left owing: five of its nine sibling
rows scored **NOT MEASURED**, and NOT MEASURED is not green.

Three defects and one faithful behaviour came out of closing that hole. Two of
them were **invisible to the round-1 instrument**, and both for the same
reason — see §5.

---

## 1. What the round-1 sweep actually left open

`scratchpad/circmiss_siblings.out` measured 4 rows of 9. The five `<NO OUTPUT>`
rows were **not one problem**:

* **3 were the instrument.** 🔴 **PAINT's border defaults to the FILL colour**
  (`basic/graphics.asm` `ep_default_b`, *"no `,B` -> B = C"*). Round 1 drew its
  stop-box in 15 and filled with 5, so `B` was 5, nothing on screen was 5, and
  the fill never terminated. 🎯 **The row's failure mode was a CONSEQUENCE of
  the defect it was measuring** — zerobas paints (it has the defect) and hung;
  the references abort at ERR 24 before painting and read fine. **It looked like
  an apparatus fault on one side only, which is the most misleading shape
  available.** And `p.ok` failed on **all three**, the tell that the case and
  not the machine was wrong: in SCREEN 2 one 8×1 cell holds two colours, so
  writing 5 into a cell already holding border-15 + background-4 forces the
  third colour out, the border stops reading as 15, and the fill escapes
  everywhere. **Fix: fill with the SAME colour as the stop-box**, so `B == C ==`
  the box and no cell ever needs three. All 10 PAINT rows now fence.
* **2 were the finding** (§3).

## 2. 🔴 PAINT has CIRCLE's defect, at both slots and by both routes

`scratchpad/circmiss_sib2.py`, 16 rows × 3 machines, boot-per-case. `[ERR R]`,
`R = POINT(50,50)` — the seed: **4 = nothing filled, 15 = filled.**

| row | statement | refs | zb | |
|---|---|---|---|---|
| `p.colour` | `PAINT(50,50),` | `24 4` | `0 15` | 🔴 DIFF |
| `p.kcolour` | `PAINT(50,50),:A=1` | `24 4` | `0 15` | 🔴 DIFF |
| `p.b` | `PAINT(50,50),15,` | `24 4` | `0 15` | 🔴 DIFF |
| `p.kb` | `PAINT(50,50),15,:A=1` | `24 4` | `0 15` | 🔴 DIFF |
| `p.cc` | `PAINT(50,50),,` | `24 4` | `0 15` | 🔴 DIFF |
| `p.kcc` | `PAINT(50,50),,:A=1` | `24 4` | `0 15` | 🔴 DIFF |
| `p.none` | `PAINT(50,50)` | `0 15` | `0 15` | ✅ the trap |
| `p.omit` | `PAINT(50,50),,15` | `0 15` | `0 15` | ✅ the trap |
| `p.plain` | `PAINT(50,50),15` | `0 15` | `0 15` | ✅ control |
| `p.ok` | `PAINT(50,50),15,15` | `0 15` | `0 15` | ✅ control |

**Six divergent rows, four green trap rows.** The site is `ep_default_b`,
reached from the **C slot** (`:701`/`:703`) and the **B slot** (`:723`/`:725`) —
4 jump instructions — and `p.cc`/`p.kcc` prove the second slot is reached by
**both** its routes (`ep_c_empty` after `,,` as well as the comma that ends C).

💰 **AND UNLIKE CIRCLE THIS IS BYTE-BLOCKED.** PAINT's grammar is *main* page 1,
**4 B free on 2026-08-23**, where CIRCLE's tenant had 1617 B of sub page 1. A
`cpt_err24`-shaped raiser needs a carve or a promotion first.

⚠️ `p.cc` was flagged LOW CONFIDENCE before the run and came back `24`. It could
have been `2`: `ep_parse_b`'s own third arm sends a *third* comma to `ep_syntax`,
and D-LINERR measured LINE's box slot as ERR 2 one field past a slot that is 24.
**Slots do not inherit verdicts** — that is why all six were run.

## 3. 🔴 CLEAR — the two rows that were the finding, not the instrument

`CLEAR 200,` scored `<NO OUTPUT>` in round 1 and `TODO.md` filed it as *"zerobas
is UNMEASURED… an APPARATUS gap"*. **That filing is wrong.** The raw screen:

    <A>
    Missing operand in 30

**zerobas raises the RIGHT error at the RIGHT line — and `ON ERROR GOTO 900`
does not catch it**, so no fence ever printed. Both references trap it (`24 0`).
**The divergence is the trap, not the error.**

### 3.1 The mechanism, read from the source and confirmed by a control

    clr_himem:  inc  hl
                call skip_spaces
                call eval            ; D-MISSOPFIX: DEFERS ERR 24, returns DE = 0
                ld   (HIMEM),de      ; <-- stores the 0 ANYWAY: FPERR is never tested
    clr_done:   push hl
                call clear_vars      ; <-- THE WIPE, and it takes the ON ERROR trap
                call vars_reset
                pop  hl
                jp   exec_stmt       ; <-- the deferred error surfaces HERE

⚠️ **A SUCCESSFUL `CLEAR` KILLS THE `ON ERROR` TRAP ON ALL THREE MACHINES —
that part is FAITHFUL.** Row `t.after` (`ONERRORGOTO900` / `CLEAR 200` / `A=1/0`)
is `UNTRAPPED Division by zero in 40` on the VG-8020, the CF-3300 **and**
zerobas, and its control `t.notrap` — the same fault with no `CLEAR` in front of
it — is trapped `11 0` on all three. 🎯 **So the wipe is not the defect. The
ORDERING is:** the references raise while the trap is still live; zerobas defers
past `clear_vars` and raises into a machine that no longer has a handler.

### 3.2 🔴 AND IT WRITES. Measured, not argued.

`scratchpad/clrtrap_himem.py`, HIMEM (`$FC4A`) read in **direct mode** either
side of the RUN, because on zerobas the abort is untrapped and no program line
runs after it:

| row | statement | VG-8020 | CF-3300 | zerobas | |
|---|---|---|---|---|---|
| `h.none` | *(no CLEAR)* | `SAME` | `SAME` | `SAME` | control |
| `h.ok` | `CLEAR 200` | `SAME` | `SAME` | `SAME` | control |
| `h.set` | `CLEAR 200,&H9000` | `->36864` | `->36864` | `->36864` | ✅ all three land on `$9000` |
| `h.trail` | `CLEAR 200,` | `SAME` | `SAME` | **`62336->0`** | 🔴 **DIFF** |

**`CLEAR 200,` overwrites the memory ceiling with 0 and only then aborts.** That
is D-MISSOP's *silent memory write* class at a **17th** slot, and it survived
D-MISSOPFIX for the same reason the trap does: **the deferral lands after the
store.** `do_poke` tests `FPERR` before storing; `ex_clear` does not.
⚠️ `basic/clear.asm` calls HIMEM *"record-only today"*, so nothing reads the 0
yet — but the same header says a future string heap or variable mover would.

### 3.3 🔴 A third, unpredicted one: `CLEAR ,200` is Syntax error on the references

Row `q.comma`: **`2` on both references, `0` here.** `ex_clear`'s
`cp ',' / jr z,clr_himem` accepts a form neither reference has. Own design,
found by a row written as a *control*.

## 4. Predictions scored — 13 of 16, and both misses are instructive

Written before the run: `scratchpad/circmiss_sib2_predictions.md`.

* **10 of 10 PAINT rows EXACT**, including the pair flagged low-confidence.
* `q.trail` / `q.kcolon` **EXACT**, including the amended `UNTRAPPED` outcome.
* 🔴 **`q.comma` MISS.** I predicted `0` on the references and called the row a
  control for a *legal* form. It is **ERR 2**. The zerobas half was right and
  the reference half was invented — I had read `clr_himem`'s existence as
  evidence about the language.
* 🔴 **`t.after` MISS.** I predicted `CLEAR` would NOT kill the trap, citing
  `clear.asm`'s header (*"the argument expressions are evaluated first… then
  everything is wiped"*). **That sentence is about the ARGUMENT, not the trap**,
  and I used it to answer a question it does not address. It kills the trap on
  every machine.
* The HIMEM write was **claimed from the source before it was measured**, and
  held.

## 5. 🔴 The instrument lesson, and it fired TWICE in one afternoon

**AN UNNAMED OUTCOME READS AS NO OUTCOME.**

1. `q.trail` scored `<NO OUTPUT>` because `face()` knew only about a numeric
   fence. The machine had printed `Missing operand in 30` — a complete, correct
   reading — and the probe called it nothing. Naming the outcome
   (`UNTRAPPED <msg> in <line>`) turned the hole back into a measurement.
2. **And then the hole MOVED ONE MESSAGE ALONG.** With `UNTRAPPED` added,
   `t.after` scored `<NO OUTPUT>` **on all three machines** — because
   *"Division by zero"* was missing from the alternation. The fix for a
   too-narrow classifier was a *slightly less* narrow classifier, and it failed
   the same way within the hour.

🎯 Same family as [[a-probe-whose-answer-is-nothing-happened]]: when the
apparatus has a bucket meaning *"nothing"*, every unmodelled outcome falls into
it, and a row in that bucket is indistinguishable from a dead machine. **Ask what
the machine might legitimately DO that the readout has no name for** — and when
you add one name, ask what the next one is.

**A second, arithmetic version of the same thing:** round 1 of the HIMEM probe
printed ONE fence and 3 of its 4 rows died as *"THE REFERENCES DISAGREE"* —
correctly, because HIMEM boots at 62336 on the VG-8020 and 56951 on the CF-3300.
**The absolute value was never the question; the DELTA was.** Printing HIMEM
before *and* after took the same number of boots and moved the row set from
1 scored to 3.

## 6. What this does NOT establish

* **No fix was written and nothing was knifed.** §2's four PAINT jumps and §3's
  ordering are a diagnosis, not a build.
* **The `cp COLON` scan is a scope claim.** 63 sites, and the three candidates
  it surfaced are the ones whose jump target is not an error routine *and* whose
  statement is a BASIC-surface argument list. `basic/screen.asm`'s three
  `clr_apply` sites have the shape and are correct (`COLOR 15,` completes on all
  three — D-MISSOP §5), which is the reminder that the scan ranks candidates and
  does not judge them.
* **`h.set` is unscoreable across machines** and is kept as a positive control
  only: all three write `$9000`, so the read-back method is sound on each.
