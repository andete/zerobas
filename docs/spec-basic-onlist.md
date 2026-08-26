<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-ONLIST — `ON n GOTO` with no target list, and the wide rule that would have broken three green rows

Status: **✅ SHIPPED.** 2026-08-26, on `9644bf2`. **15 rows × 3 machines,
references unanimous on all 15, 3 DIFF → 0.** `scratchpad/onlist_probe.py`
(`onlist_base.out`, `onlist_sep.out`, `onlist_after.out`). Predictions pinned in
`onlist_predictions.md` before each round.

Opened by D-MISSOP3, which found `ON 1 GOTO` and `ON 1 GOSUB` completing
silently where both references say `Syntax error`.

---

## 1. The site set, enumerated as INSTRUCTIONS

`eon_seek_nth` (`basic/program.asm`) hands its verdict to two tails, and **seven
jump instructions reach them**:

| site | reached by | source comment | truth |
|---|---|---|---|
| `esn_p1` `cp $0E` | no list at all, **or** a comma then a non-lineno | *"list shorter than N"* | ⚠️ **true for one entry condition, false for the other** |
| `esn_p1` `cp ','` | no comma after an entry | *"list shorter than N"* | LEGAL |
| `esn_scan` `cp $0E` | N=0, no entries at all | *"no entries at all"* | LEGAL (measured) |
| `esn_scan_lp` `cp ','` | end of list | *"no more commas"* | LEGAL |
| `esn_scan_lp` `cp $0E` | comma then non-lineno | — | LEGAL (measured) |
| `esn_p2` `cp ','` | end of list | *"HL past the list"* | LEGAL |
| `esn_p2` `cp $0E` | comma then non-lineno | *"malformed: stop here"* | LEGAL (measured) |

🔴 **I read four of these seven as errors. The machines say ONE.**

---

## 2. 🔴 THE RULE I PREDICTED WAS TOO WIDE, AND THE REFUTATION IS THE SLICE

Round 1 predicted, as **one rule** so that one row could break it:

> *An `ON n GOTO/GOSUB` whose target list is EMPTY or MALFORMED is a
> `Syntax error` REGARDLESS of N.*

**Five of eleven rows refuted it, all on the reference side, all the same error —
I assumed the reference validates a list it never looks at.**

| row | statement | I predicted refs | refs ACTUALLY | |
|---|---|---|---|---|
| `o.zeronolist` | `ON 0 GOTO` | `2 0` | **`0 1`** | ❌ |
| `o.overnolist` | `ON 5 GOTO` | `2 0` | **`0 1`** | ❌ |
| `o.trail1` | `ON 1 GOTO 40,` | `2 0` | **`0 2`** | ❌ **zb already right** |
| `o.trail0` | `ON 0 GOTO 40,` | `2 0` | **`0 1`** | ❌ **zb already right** |
| `o.badafter` | `ON 1 GOTO 40,X` | `2 0` | **`0 2`** | ❌ **zb already right** |

🎯 **THREE OF THE FIVE ARE ROWS WHERE ZEROBAS WAS ALREADY CORRECT.** A fix built
on the wide rule — the one a careful reading of the source produces — would have
raised `Syntax error` at three sites the references leave silent, and shipped
**three regressions into green behaviour** while closing two real defects. The
rows that caught it are the ones added as *"legal, must not move"* and the
malformed tails I was most confident about. Same family as
[[two-rules-that-coincide-on-every-row-you-have]], except here the two rules did
**not** coincide and I simply had not run the rows that separate them.

---

## 3. 🎯 The rule the refutation leaves, and the row that pins it

`ON 1 GOTO` is **ERR 2** and `ON 5 GOTO` is **silent** — and in `eon_seek_nth`
those are the **same instruction**, `esn_p1`'s `cp LINENO_TOKEN` on its first
iteration. So the discriminator is not the list:

> **THE REFERENCE DEMANDS A LINE NUMBER ONLY AT THE POSITION IT IS ABOUT TO USE.
> `Syntax error` iff the Nth position is REACHED and what is there is not a line
> number. N=0 never looks; a list that ends before position N never looks.**

The separating pair, and neither row exists without the other:

| row | statement | refs | before | after |
|---|---|---|---|---|
| `o.n2trail` | `ON 2 GOTO 40,` | **`2 0`** | `0 1` 🔴 | `2 0` ✅ |
| `o.n5trail` | `ON 5 GOTO 40,` | `0 1` | `0 1` | `0 1` ✅ |

**The same consumed comma commits the reference to position 2 and commits
nothing at position 5.** In `eon_seek_nth` terms that is exactly `DE == 1` at
`esn_p1` — the entry about to be read is the one being sought — and nothing else.
Round 2 was **4 of 4 exact**.

---

## 4. The fix — 14 B, one site

```
esn_p1:   cp   LINENO_TOKEN
          jr   nz,esn_notlineno      ; 0 B, the same instruction
...
esn_notlineno:
          dec  de                    ; DE==1 -> this IS the sought position
          ld   a,d
          or   e
          jr   nz,esn_nocf           ; still counting -> the list simply ENDS: LEGAL
          or   $FF                   ; sought position, no lineno -> CF clear + NZ
          ret
esn_nocf: xor  a                     ; CF clear + Z  (was `or a`; same 1 byte,
          ret                        ; and now the Z flag carries the verdict)

eon_goto / eon_gosub:  jp nc,exec_stmt -> jp nc,eon_notfound      0 B each
eon_notfound:
          jp   nz,stmt_error         ; malformed -> ERR 2 (trappable)
          jp   exec_stmt             ; legal -> fall through, as before
```

**Main page 1: 99 → 85 B**, read from clean, and `basic-reloc.rom`
`fa720d6a` → `24d8e393` with `sub.rom` unmoved.

⚠️ **THE RAISE IS AT THE CALLER, NOT INSIDE `eon_seek_nth`, AND THAT IS LOAD-
BEARING.** The abort chain prints and `ret`s **without resetting SP**, so it is
only correct at the statement handler's own stack depth
([[abort-chain-returns-into-caller]]). `eon_seek_nth` is one `call` deeper: a
`jp stmt_error` from inside it would land control back in `eon_seek_nth`'s
caller, which is the measured `LOCATE`-errors-twice / `WIDTH 300`-continues-with-
the-error-code-as-data failure shape. The verdict is carried out in the Z flag
and raised at handler depth instead.

---

## 5. 🔬 Knives — 4 of 4 EXACT, on the SECOND attempt, and the first attempt is the finding

`scratchpad/onlist_knives.py`, `onlist_knives.out` (round 1) and
`onlist_knives2.out` (round 2). Three of the four exist to make the **refuted
wide rule** falsifiable rather than merely regretted: each re-creates one
specific regression it would have shipped, and each must redden rows that are
green today.

| knife | cut | round 1 | round 2 |
|---|---|---|---|
| K-OL1 | delete the discriminator | ✅ 3 rows revert | ✅ same |
| K-OL2 | force the discriminator always-true | 🔴 5 moved, 4 to the wrong value | ✅ `o.overnolist`, `o.n5trail` → `2 0` |
| K-OL3 | `esn_ok`'s *"malformed: stop here"* → the raiser | 🔴 1 of 2 | ✅ `o.trail1`, `o.badafter` → `2 0` |
| K-OL4 | `esn_scan`'s *"no entries at all"* → the raiser | 🔴 **moved NOTHING** | ✅ `o.zeronolist` → `2 0` |

### 5.1 🔴 THREE OF THE FOUR FIRST-ATTEMPT KNIVES WERE WRONG, AND ALL FOR ONE REASON

`esn_notlineno` **opens with `dec de`**. At `esn_p1` that is the discriminator;
from anywhere else DE is already 0, so it wraps to `$FFFF`, tests NZ, and lands
back on the LEGAL exit. **Pointing another site at it does not re-create the
wide rule — it re-creates silence**, which is why K-OL4 reddened nothing and
K-OL3 moved its row to the wrong value.

🎯 **A KNIFE THAT REDDENS NOTHING IS A CLAIM ABOUT THE KNIFE BEFORE IT IS ONE
ABOUT THE CODE** ([[apparatus-is-part-of-the-measurement]]). The repair was to
name the raise point — **`esn_bad`, a label, 0 B, ROM byte-identical at
`24d8e393`** — so a site can ask for the verdict *past* the test. The shipped
comment there now says it is a label and not a reusable raiser, because its own
knives are the evidence.

⚠️ **AND K-OL2 DID NOT DO WHAT ITS DESCRIPTION SAID.** `jr nz` → `jr z` INVERTS
a test; it does not remove one. It moved five rows and scored nothing, because a
knife whose cut and whose description disagree cannot test its claim however
much it perturbs. Round 2 cuts a VALUE instead (`or e` → `xor a`).

⚠️ **The K-OL2 anchor was also non-unique (`or e` appears 6 times; even with two
lines of context, 2 times — `esn_p1`'s own countdown test is byte-identical).
The runner's `assert n == 1` caught it before anything built.** That duplicate
is filed as its own item: `dupspan_indep.py` does **not** see it — measured,
`scratchpad/onlist_dupspan.out` — because the identical part is a 4-instruction
PREFIX and the tool's model is spans-with-terminators.

---

## 6. What this does NOT establish

* `ON ERROR GOTO`, `ON STOP`, `ON KEY`, `ON SPRITE`, `ON STRIG` and
  `ON INTERVAL` all leave `ex_on` before `ex_on_expr` and are **untouched and
  unmeasured** here.
* The rule is pinned by `o.n2trail` / `o.n5trail`; **positions beyond 2 are
  interpolated**, not measured.
* `ON n GOSUB` shares `eon_seek_nth` and is covered by two rows
  (`o.nolistsub`, `o.gosubok`), not by the full grid.
