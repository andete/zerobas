<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-MIDOP — the rule reaches a second verb, but not by the shape that fixed the first

Status: **✅ SHIPPED.** 2026-08-26, on `f595a8d`. **9 rows × 3 machines,
references unanimous on all 9, 4 DIFF → 0, +6 B of the page-0 LOW region**
(main page 1 untouched). `scratchpad/midop_probe.py`
(`midop_base.out`, `midop_after.out`). Predictions pinned in
`midop_predictions.md` before the probe ran once.

The last of the three string rows D-MISSOP filed, and the only one that survived
D-MISSOP3's re-measurement.

---

## 1. The same shared tail D-PUSING had just split

`ex_mid_stmt` ended with:

```
    call    str_eval
    jr      nc,ems_err_pop2     ; not a string operand   -> ERR 2
```

`str_eval` declines both for *"there is nothing here"* and for *"there is
something and it is not a string"* — the identical shape D-PUSING split in
`ex_print_using` an hour earlier. The references:

| row | statement | refs | before |
|---|---|---|---|
| `m.none` | `MID$(A$,2)=` | **24** | 2 |
| `m.colon` | `MID$(A$,2)=:PRINT1` | **24** | 2 |
| `m.num` | `MID$(A$,2)=5` | **13** | 2 |
| `m.plus` | `MID$(A$,2)=+` | **24** | 2 |

**So the rule does reach a second verb.** *A required operand that ENDS where a
value was needed is 24; one PRESENT but of the wrong type is 13.*

---

## 2. 🔴 BUT D-PUSING'S FIX SHAPE WOULD HAVE GOT `m.plus` WRONG

D-PUSING's cure is an EOL/`:` test ahead of `str_eval`. Applied here it answers
**13** for `MID$(A$,2)=+` — `+` is neither end-of-line nor `:`, so it falls
through to the type-mismatch arm — where both references say **24**.

🎯 **THE DISCRIMINATOR IS NOT "IS THERE A BYTE", IT IS "CAN A FACTOR START
HERE"** — which is `ev_f`'s question, not a peek's. Two verbs, the same rule, and
**the same fix does not serve both**. Had `m.plus` not been in the set, this
would have shipped as a copy of D-PUSING and been wrong in a row nobody had.

⚠️ `m.plus` was pinned as *"the weakest row"* in the predictions, because the
only evidence for it was `A$=+` → 24 — LET's RHS, a **third** grammatical
position. It is the row that decided the design.

---

## 3. The fix — ASK THE ROUTINE THAT ALREADY ANSWERS IT

`els_tc_common` (`basic/missing.asm`, D-MISS-1) is what already makes `A$=` and
`A$=+` read 24: it clears `ERRMARK`, evaluates the operand **numerically**, and
lets `check_expr_errors` decide — a deferred FPERR aborts with its own code (24,
via `ev_f_missop`), a clean parse means a real numeric RHS (13), and the `$DD`
landmark means nothing parsed (2).

`basic/files.asm`:724 already records that **a third entry point costs zero
bytes**: *"`els_typecheck` and `elas_typecheck` each pop their own saved word and
fall into it"*. MID$ is the fourth, popping `[n][m]`:

```
ems_typecheck:  pop de / pop de / jp els_tc_common      +5 B
    jr nc,ems_err_pop2  ->  jp nc,ems_typecheck         +1 B
```

**Page-0 low region: 45 → 39 B.** Main page 1 **unchanged at 89 B** —
`str-engine.asm` lives in the low region, so this slice does not touch the wall
everything else has been competing for.

⚠️ **`sub.rom` MOVES, AND THAT IS CORRECT.** A main **low-region** edit shifts the
addresses in the GENERATED `sub/basic-resident-abi.inc` — 11 of its 12 entries
moved by 6 B — so the sub image is rebuilt against new constants with its walls
unchanged (2464 / 1622). The operating rules record only the converse, *"only
`sub.rom` moves on a sub-tenant edit"*; asserting it unmoved here would have
failed every knife for the wrong reason.

---

## 4. 🔴 TWO RECORDS DISAGREE ON WHETHER THE POPS ARE NEEDED

`files.asm`:732 says `raise_error`'s own `ld sp,(SAVSTK)` discards whatever is
left, and the code agrees — the trap arm resets SP at `interp.asm`:1022, the
abort arm through `fre_abort_low` (`interp.asm`:1731, citing `4d35b6d` /
`docs/spec-basic-abort-depth.md`). The `abort-chain-returns-into-caller` note
says the opposite, and **predates that fix**.

**The shipped code pops anyway.** Popping is correct under *both* readings and
costs 2 B, so the fix did not bet a stack on which record is current.

🎯 **AND K-MD2 SETTLED IT: DELETING BOTH POPS MOVES NOTHING — 0 rows of 9.**
`raise_error` **does** reset SP from `SAVSTK` on both arms; `files.asm`:732 is
right and the `abort-chain-returns-into-caller` note is **stale on this point**
(it describes the tree before `4d35b6d`). That note has been corrected.

⚠️ **THE 2 B ARE THEREFORE A MEASURED CARVE, AND THEY ARE STILL IN THE TREE.**
They were written to be correct under an unresolved disagreement; the
disagreement is now resolved, but removing them makes the code *depend* on the
SAVSTK behaviour rather than merely survive it. `els_tc_common`'s own header says
*"every path out of here errors"*, so the dependency is sound — this is a 2 B
carve with its evidence attached, filed rather than taken at the end of a slice.
🔴 **A knife that moves NOTHING is usually a knife that failed. This one is the
opposite: moving nothing WAS the prediction, and it is only a result because the
row set is 9 rows that all reach the tail.**

---

## 5. 🔬 Knives — and TWO instrument faults found while writing them

`scratchpad/midop_knives.py` / `midop_knives.out`.

| knife | cut | claim |
|---|---|---|
| K-MD1 | the delegation reverted to the blanket ERR 2 | all four shapes go back |
| K-MD2 | **DELETE the two pops** | turns §4's documentation disagreement into a reading |
| K-MD3 | the missing-`=` check pointed at the delegation | the site that must STAY 2 |

### 5.1 🔴 I ASSERTED THE WRONG THING ABOUT `sub.rom`, TWICE

The operating rules say *"only `sub.rom` moves on a sub-tenant edit"*, which
invites asserting it **unmoved** for a `basic/` cut. But the fix itself moved it
(§3). So I asserted it **must move** — and K-MD1 failed: that cut is a
`jp`→`jp` retarget, **size-neutral**, so it shifts no addresses and the
generated ABI does not move.

🎯 **THE TRUE RULE IS NARROWER THAN EITHER: a main low-region edit moves
`sub.rom` IFF IT CHANGES SIZE**, because the coupling is the generated ABI's
*addresses* and nothing else. A runner cannot know a cut's size a priori, so it
now **reports** the fact and asserts only what must hold — that the main image
moved at all. ⚠️ **An assertion that is right for the FIX can be wrong for the
KNIVES**, because a knife is chosen for what it changes semantically, not for
what it changes in size.

### 5.2 🔴 THE RUNNER DID NOT RESTORE ON THE FAILURE PATH

The 5.1 assertion fired **after** the cut had been written, and the only restore
sat at the *end* of the loop body. So the run exited leaving
`basic/str-engine.asm` holding the K-MD1 cut — and the next invocation reported
**"anchor appears 0 times"**, which reads as a bad anchor and is really a
**dirty tree**.

`zerobas-gate-operating-rules` says *"RESTORE BY WRITING THE BYTES"* and says
nothing about **when**. An `atexit` handler registered beside the read now covers
the assert, the exception and the clean return alike. **A knife runner that can
exit between the write and the restore is one that can silently corrupt whatever
is measured next** — and every knife runner in `scratchpad/` shares this shape.
Filed.

---

## 6. What this does NOT establish

* `m.noclose` (`MID$(A$,2="Q"`) reads **13** on all three — I predicted 2. It
  agrees, so it is not a defect, but the *reason* is unmeasured: `2="Q"` parses
  as a comparison of a number to a string. **An agreeing row whose mechanism is
  a guess is still a guess.**
* The `n`/`m` argument domains are untouched here (D-MISS-2 owns them).
* `LSET`/`RSET`, which share `tgt_desc`/`MIDS_DEST`, have no rows in this slice.
