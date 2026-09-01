# D-MISSOPBOUND — `Missing operand` is for an EMPTY slot, not a WRONG one

**2026-09-01.** D-UNCOLLECTED ran `cursor-acceptance`, which the battery did not
collect, and found three failing rows: `X=TAB(5)`, `X=SPC(5)` and
`IF TAB(5)=0` read `Missing operand` (ERR 24) here and `Syntax error` (ERR 2) on
both references.

**The three rows were a tenth of the defect.** Measured over 18 rows: **11
diverged**, across nine token classes.

## The source comment was the first thing falsified

`basic/print.asm` says, beside the PRINT-item dispatch:

> TAB( and SPC( are PRINT-ITEM dispatch, NOT $FF factors. Placing them here and
> NOWHERE in ev_f is what makes `X=TAB(5)` and `IF TAB(5)=0` a SYNTAX error
> (MEASURED) with no code at all.

The design is right and the consequence is wrong: falling off ev_f's chain does
not produce a syntax error, it produces `Missing operand`. **A justification
written beside the code, marked MEASURED, and never re-run.**
[[a-fix-falsifies-the-justification-beside-it]]

## Two rules fit every row either side had

`basic/expr.asm`'s `ev_f_var` requires a LETTER and sends everything else to
`ev_f_missop`. D-MISSOP measured that as correct **at 16 slots**, so the obvious
reading was "TAB(/SPC( are a special case worth 8 bytes". The alternative was a
boundary. Both fit every row in hand, so the probe was built to **separate**
them [[two-rules-that-coincide-on-every-row-you-have]]:

| typed | VG-8020 | CF-3300 | zerobas (before) |
|---|---|---|---|
| `X=` | ERR 24 | ERR 24 | ERR 24 |
| `X=:PRINT 1` | ERR 24 | ERR 24 | ERR 24 |
| `X=ELSE` | ERR 24 | ERR 24 | ERR 24 |
| `X=*5` | **ERR 2** | **ERR 2** | ERR 24 |
| `X=TAB(5)` · `X=SPC(5)` · `IF TAB(5)=0` | **ERR 2** | **ERR 2** | ERR 24 |
| `X=THEN` · `X=TO` · `X=STEP` · `X=GOTO` | **ERR 2** | **ERR 2** | ERR 24 |
| `X=PRINT` · `X=INPUT` · `X=USING` | **ERR 2** | **ERR 2** | ERR 24 |
| `X=,5` · `X=)` | ERR 2 | ERR 2 | ERR 2 (already) |

**The rule is a boundary:** a factor slot ended by **end of statement** (EOL or
`':'`) is `Missing operand`; **anything actually present** is `Syntax error`. Not
"is it a keyword" — `X=*5`, a bare operator, is ERR 2 too.

🟢 **`X=ELSE` IS THE ROW THAT PROVES IT, AND IT LOOKS LIKE A COUNTER-EXAMPLE.**
It reads ERR 24 on all three, which under "a keyword in a factor slot is a syntax
error" would be an exception needing its own story. It is not: MSX tokenises
`ELSE` as `:ELSE`, so the slot genuinely sees a colon. An agreeing row that
separates two rules is worth more than a diverging one that does not.

The old comment on `ev_f_missop` named the wrong set out loud — *"end of line,
':', or a stray operator"*. The first two belong; the third is exactly the case
that diverges.

## The fix

At `ev_f_missop` — reached from **one** site, with `A` still holding the
offending byte — default to `FPERR_MISSOP`, keep it for `0` and `':'`, and
otherwise defer **FPERR 4**, which `fperr_to_err` in `basic/interp.asm` maps to
ERR 2. The code is `4`, not `2`: FPERR is a dense table index, not a BASIC error
number, and writing the error number there would have been a
[[a-derived-constant-falsified-from-another-file]] in waiting.

**Page 1 free 358 → 349 B (−9).** 11 divergences → **0/18**.

Regression checks, all green and all necessary: `missing-acceptance` (D-MISSOP's
16 slots — the rule had to preserve every one), `lineerr-acceptance` (the suite
D-MISSOP's first draft broke), and `cursor-acceptance` itself.

## The stale exemption, retired

`cursor-acceptance` carried `KNOWN_RED`, 8 rows banner-documented as *"D-CUR-3 —
a mid-statement error does not abort the statement"*. **All 8 now agree**, and had
been agreeing for an unknown time — so the exemption suppressed nothing while the
suite was red for a reason its banner never named.

🔴 **AN EXEMPTION THAT NO LONGER FIRES IS NOT INERT.** It is a row set silently
ungated. Emptying it puts all 8 back under the verdict; they pass, 67 rows green.
The D-CUR-3 analysis is kept — inverting a conclusion beats deleting the
reasoning that reached it.

With the suite green and its only reason for exclusion gone,
**`cursor-acceptance` joins the battery**: 50 → **51 units**, 23 of 68
acceptance targets collected.
