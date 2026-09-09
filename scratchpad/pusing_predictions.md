# D-PUSING — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on `054a17f`. Walls: main p0 low 45 B, **main p1 83 B**.

## 0. The two rows D-MISSOP3 measured, and what is unknown around them

* `PRINT USING` → refs **24**, zb **2** 🔴
* `PRINT USING"##"` → refs **2**, zb **0** 🔴 — it COMPLETES SILENTLY

Two different defects in one verb, and neither site's neighbourhood is measured.

**Defect 1 is another shared tail.** `basic/printusing.asm:51` is
`jp nc,stmt_error`, reached when `str_eval` declines — which is BOTH *"there is
nothing here at all"* (`PRINT USING`) and *"there is something and it is not a
string"* (`PRINT USING 5`). One instruction, two meanings, exactly the shape
D-EVFERR / D-ONLIST / D-PLAYOP each had.

**Defect 2 is a silent completion**, the class D-MISSOP found could WRITE.
`PRINT USING"##"` reaches `pu_main`, sees end-of-line and takes
`jr z,pu_endlist`. The question is whether the reference distinguishes a format
that CONTAINS A FIELD (`"##"`, needs a value) from one that is pure literal
text (`"abc"`, complete on its own) — because zerobas already does, at
`pu_has_field`.

## 1. Readout `[ERR L]`

`L` is `CSRLIN` captured immediately after the statement, with the cursor parked
at row 5 first. **`L`=5 means nothing was printed; `L`=6 means one line was.**
An ERR code alone cannot tell a silent no-op from a silent *print*, and this
verb's whole job is printing.

## 2. Row-by-row

| row | statement | refs | zb | what it asks |
|---|---|---|---|---|
| `u.none` | `PRINT USING` | **`24 5`** | `2 5` 🔴 | filed |
| `u.colon` | `PRINT USING:PRINT1` | **`24 5`** | `2 5` 🔴 | the same site, terminated by `:` |
| `u.num` | `PRINT USING 5` | `13 5` | `2 5` 🔴 | **the OTHER meaning of the same instruction** |
| `u.numsemi` | `PRINT USING 5;1` | `13 5` | `2 5` 🔴 | ditto, with a value list present |
| `u.fmtonly` | `PRINT USING"##"` | **`2 5`** | `0 6` 🔴 | filed — and does zb PRINT before completing? |
| `u.fmtsemi` | `PRINT USING"##";` | `2 5` | `0 6` 🔴 | separator present, values absent |
| `u.lit` | `PRINT USING"abc"` | `0 6` | `0 6` ✅ | a field-less format is complete on its own |
| `u.litsemi` | `PRINT USING"abc";` | `0 6` | `0 6` ✅ | ditto with a separator |
| `u.ok` | `PRINT USING"##";5` | `0 6` | `0 6` ✅ | control |
| `u.ok2` | `PRINT USING"###";12` | `0 6` | `0 6` ✅ | control |

**Predicted: 10 scored, 6 DIFF.**

## 3. The rules being predicted, so a row can refute each

1. **The format operand obeys the D-MISSOP partition**: *ends where a value was
   needed* → **24**; *present but wrong type* → **13**. `u.num` is the row that
   separates them, and if it reads **2** on the references then the site is
   correct as one tail and only the missing-operand half moves.
2. **A format CONTAINING A FIELD requires a value list.** `u.lit` / `u.litsemi`
   are the rows that keep this narrow: if a field-less format also errored, the
   rule would be *"USING always needs values"* and `pu_has_field` would be the
   wrong discriminator to hang it on.

⚠️ **LOW CONFIDENCE ON `u.num` = 13.** I have no reference reading for a
non-string format at all; 13 is inference from `PLAY 5` → 13, and PLAY's operand
is a string in a different grammatical position. This is the row most likely to
be wrong and it is the one the fix's shape depends on.

⚠️ **`L` FOR THE zb SIDE OF `u.fmtonly` IS A GUESS.** `pu_endlist` may or may not
emit a CRLF; `0 6` vs `0 5` is not derivable from the filed row, which recorded
only the ERR.

---

# ROUND 1 SCORED — 6 of 10, and MY NARROWING ROWS REFUTED MY OWN RULE

| row | I predicted refs | refs ACTUALLY | |
|---|---|---|---|
| `u.none` `PRINT USING` | `24 5` | `24 5` | ✅ |
| `u.colon` | `24 5` | `24 5` | ✅ |
| `u.num` `PRINT USING 5` | `13 5` | `13 5` | ✅ **the low-confidence row was right** |
| `u.numsemi` | `13 5` | `13 5` | ✅ |
| `u.fmtonly` `PRINT USING"##"` | `2 5` | `2 5` | ✅ (incl. zb's `0 6`) |
| `u.fmtsemi` `PRINT USING"##";` | `2 5` | **`24 5`** | ❌ |
| `u.lit` `PRINT USING"abc"` | `0 6` | **`2 5`** | ❌ |
| `u.litsemi` `PRINT USING"abc";` | `0 6` | **`5 5`** | ❌ |

🔴 **ALL THREE MISSES ARE THE ROWS I ADDED TO KEEP THE FIX NARROW, AND THEY SAY
THE DEFECT IS WIDER.** This is D-ONLIST's lesson with the sign flipped: there the
references were **lazier** than I assumed and the narrowing rows stopped me
shipping three regressions; here they are **stricter**, and the same instinct
stopped me shipping a fix that would have closed 2 rows while leaving 6 and
calling the item done. **8 of 10 rows diverge.**

🎯 **`pu_has_field` IS NOT THE DISCRIMINATOR I THOUGHT.** The measured rule set:

| condition | reference |
|---|---|
| no format at all (EOL or `:`) | **24** |
| format present, not a string | **13** |
| format present, **no separator**, no values | **2** — *field-ness is irrelevant* |
| separator, no values, format **HAS** a field | **24** |
| separator, no values, format has **NO** field | **5** |

So there are FIVE answers where I had modelled two, and *"a field-less format is
complete on its own"* — which zerobas implements at `pu_literal_only` — is not a
thing either reference does.

## ROUND 2 — the row that decides whether a whole BLOCK is dead

`pu_literal_only` (`printusing.asm:139`) has **exactly one** incoming jump. If a
field-less format is an error in every case, that block, `pu_lo_skip` and
`pu_lo_end` become unreachable, `make deadcode` refuses the build, and the fix
is also a **carve**. One unmeasured row decides it.

| row | statement | refs | zb | what it decides |
|---|---|---|---|---|
| `u.litval` | `PRINT USING"abc";5` | **`5 5`** | `0 6` | 🎯 whether `pu_literal_only` is dead in EVERY case |
| `u.comma` | `PRINT USING"##",5` | `0 6` | `0 6` | is `,` a separator like `;` |
| `u.emptyonly` | `PRINT USING""` | `2 5` | `0 6` | the empty format, no separator |
| `u.emptysemi` | `PRINT USING"";5` | `5 5` | `0 6` | the empty format is field-less |
| `u.strfield` | `PRINT USING"!";"AB"` | `0 6` | `0 6` | control, a STRING field |
| `u.numnosemi` | `PRINT USING"##"5` | `2 5` | `0 6` | no separator, value present |

**Predicted: 6 scored, 5 DIFF.** ⚠️ `u.litval` = 5 is inference from
`u.litsemi` = 5, i.e. from ONE measured row. It is the row this round exists for
and the one most likely to be wrong.

---

# ROUND 2 SCORED — 5 of 6, and the decisive row landed

`u.litval` (`PRINT USING"abc";5`) is **`5 5`** as predicted, from a single
measured neighbour. **So a field-less format ALWAYS errors** — 2 without a
separator, 5 with one, values or not — and `pu_literal_only` implements
behaviour **neither reference has**. Its one incoming jump makes it, and
`pu_lo_skip`/`pu_lo_end`, dead under the fix: `make deadcode` will refuse the
build until they go. **The fix is also a carve.**

🔴 **MISS: `u.comma`.** I predicted `PRINT USING"##",5` → `0 6`; it is **`2 5`**
on both references. **`,` is NOT a valid separator between the format and the
values** — zerobas accepts it at `puf_sep`. One more divergence, found by a row
I had written down as a control.

**Running total: 13 DIFF of 16.**

## ROUND 3 — two rows that BOUND the fix, pinned before running

| row | statement | refs | zb | why it bounds the fix |
|---|---|---|---|---|
| `u.valcomma` | `PRINT USING"##";1,2` | `0 6` | `0 6` | `,` is rejected as the FORMAT separator; `pu_msep_chk` also accepts it between VALUES, a **different grammatical position**. 🔴 Do not carry one row's answer into the other — that is exactly how `u.comma` got predicted wrong. |
| `u.chan` | `OPEN"CRT:"…:PRINT#1,USING"##";5` | `0 6` | `0 6` | `ex_print_using` is shared by PRINT, LPRINT and PRINT#; the fix serves all three and only PRINT has rows. |

**Predicted: 2 scored, 0 DIFF.** Both are controls — if either diverges, the fix
has a second front and the slice is bigger than measured.
