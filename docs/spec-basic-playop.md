<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-PLAYOP — PLAY's missing operand, and the loop the filing did not count

Status: **✅ SHIPPED.** 2026-08-26, on `2258c6b`. **11 rows × 3 machines,
references unanimous on all 11, 4 DIFF → 0, +2 B.**
`scratchpad/playop_probe.py` (`playop_base.out`, `playop_after.out`).
Predictions pinned in `playop_predictions.md` before the probe ran once.

Closes `TODO.md`:1711, filed 2026-08-22 by D-DUPSPAN §6.3 — the last open member
of THE GENERIC ERROR-LAYER SEAM's missing-operand half.

---

## 1. The filed claims, run before anything was built

| claim | verdict |
|---|---|
| *"`PLAY` and `PLAY:PRINT 1` → ERR 24 on both"* | ✅ **CONFIRMED** — 24 / 24 / 2 |
| *"`PLAY ,"E"` → ERR 2 on both and here"* | ✅ **CONFIRMED** |
| *"TWO of `pl_syntax`'s four call sites move, not four"* | ✅ **CONFIRMED**, and see §2 |
| *"The fourth (a 4th voice string) is UNMEASURED — do not assume it into either half"* | ✅ measured **2 on both**, already correct |
| *"`pl_syntax`'s header cites the VG-8020 for the ERR-2 claim; that citation is right for one site and wrong for two"* | ✅ **CONFIRMED** |

🎯 **THIS IS THE FIRST FILING IN THIS RUN THAT SURVIVED ITS OWN RE-RUN INTACT.**
D-MISSOP3's justification was false, D-EVFERR's site count had rotted twice, and
the `KEY` item was misdiagnosed. This one was right on every point — **including
the one it explicitly refused to guess.** *"Do not assume it into either half"*
is the sentence that made the fourth site cheap to check and impossible to get
wrong by inheritance.

---

## 2. 🔴 THE FILING COUNTED INSTRUCTIONS, AND `pl_voice` IS A LOOP

`basic/play.asm:74` is `jr pl_voice`, so the three entry-side tests are
re-entered **after every comma**. Each has **two entry conditions** — the FIRST
voice and a SUBSEQUENT one — so *"two of four call sites"* is a claim about
instructions, and the rows are seven:

| site | test | first voice | subsequent voice |
|---|---|---|---|
| `:42` | `or a` | `PLAY` → **24** | `PLAY"A",` → **24** |
| `:44` | `cp COLON` | `PLAY:PRINT1` → **24** | `PLAY"A",:PRINT1` → **24** |
| `:46` | `cp ','` | `PLAY,"E"` → **2** | `PLAY"A",,"C"` → **2** |
| `:73` | `cp 3` | — | `PLAY"A","B","C","D"` → **2** |

**Both entry conditions answer the same way at every site**, so the filing's
conclusion holds — but that is a *result*, not something the instruction count
could have told anyone. D-ONLIST had the identical shape and came out the other
way: there, one instruction genuinely answered differently depending on how it
was reached. **The question has to be asked per site, every time.**

---

## 3. The rule, holding on a verb it was not derived from

D-MISSOP's partition (`docs/spec-basic-missop.md` §5), applied to PLAY:

> **A required slot that ENDS where a value was needed is `Missing operand`
> (24); an EMPTY operand terminated by `,` is `Syntax error` (2).**

All seven rows obey it, at both entry conditions, on both references. That is the
rule's first out-of-sample confirmation since D-MISSOP3 refined it — and PLAY was
one of the ten verbs D-MISSOP3 named as *"unmeasured, not green"*.

---

## 4. The fix — +2 B, and the arithmetic INVERTS D-PAINTMISS's

```
pl_voice:  or   a
           jr   z,pl_syntax   ->  jp z,loc_missing      +1 B
           cp   COLON
           jr   z,pl_syntax   ->  jp z,loc_missing      +1 B
           cp   ','
           jr   z,pl_syntax       (unchanged — measured 2 at both entries)
```

**Main page 1: 85 → 83 B**, read from clean; `basic-reloc.rom`
`24d8e393` → `53cb0bd9`, `sub.rom` unmoved.

🎯 **D-PAINTMISS REASONED THE OPPOSITE WAY AND WAS RIGHT FOR ITS OWN CASE.** It
recorded: *"A trampoline beats both alternatives because the sites are `jr`s: an
inline `ld a,24 / jp raise_error` is 5 B and four `jp z,loc_missing` is +4 B."*
With **four** sites, +4 B loses to a 3 B trampoline. With **two**, +2 B wins.
**The arithmetic inverts below four sites**, so the filed conclusion is a
function of the site count and not a rule — worth stating, because the next
slice to reach for it will have its own count.

`loc_missing` is `equ g8_missing` in the shipping build and a real body in the
`!G8_RESIDENT` arm, so both switch arms still assemble.

---

## 5. 🔬 Knives

`scratchpad/playop_knives.py` / `playop_knives.out`. Four cuts, two kinds:

* **K-PL1 / K-PL2** revert the two sites that moved. Each is predicted to move
  **two** rows, not one — the loop claim from §2, measured.
* **K-PL3 / K-PL4** point the two sites that must **not** move at the new target
  on purpose, reddening rows that are green today. Without them, *"two of four"*
  is a claim no row can falsify.

---

## 6. What this does NOT establish

* **Whether PLAY queues anything BEFORE raising is not measured.** The seam work
  found wrong ordering at SWAP (raised before its exchange) and PAINT (filled
  then raised); this probe reads the error code only, so a `PLAY"A",` that plays
  voice A and *then* raises is indistinguishable here from one that raises
  first. Named, not covered.
* The `PLAY(n)` **function** (background-queue query) remains unimplemented and
  is a separate open item.
* Voice counts beyond four are not swept; `:73` is `cp 3`, so a fifth behaves as
  the fourth by construction, not by measurement.
