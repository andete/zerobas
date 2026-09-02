# D-MIDOP — predictions, PINNED BEFORE THE PROBE RAN

2026-08-26, on `f595a8d`. Walls: main p0 low 45 B, **main p1 89 B**.

## 0. The filed row and the site

`MID$(A$,2)=` → refs **24**, zb **2** (D-MISSOP3; originally D-MISSOP's
`midd.val`). `basic/str-engine.asm`'s `ex_mid_stmt` ends with

    call    str_eval
    jr      nc,ems_err_pop2     ; not a string operand   -> ERR 2

🔴 **AND THAT IS THE SAME SHARED TAIL D-PUSING JUST SPLIT.** `str_eval` declines
both for *"there is nothing here"* and for *"there is something and it is not a
string"*, and D-PUSING measured the references answering **24** and **13** to
exactly that pair. If MID$ follows, the fix is the same two-instruction
prefix — and if it does not, that is worth more than the fix.

## 1. Readout `[ERR V]`

`A$="HELLO"` first; `V = ASC(MID$(A$,2,1))` after. **69 (`E`) = untouched,
81 (`Q`) = the assignment happened.** D-MISSOP's headline finding was that this
class can COMPLETE AND WRITE, so an ERR column alone would not be enough.

## 2. Row-by-row

| row | statement | refs | zb | what it asks |
|---|---|---|---|---|
| `m.none` | `MID$(A$,2)=` | **`24 69`** | `2 69` 🔴 | filed |
| `m.colon` | `MID$(A$,2)=:PRINT1` | **`24 69`** | `2 69` 🔴 | same site, `:` terminator |
| `m.num` | `MID$(A$,2)=5` | **`13 69`** | `2 69` 🔴 | **the OTHER meaning of the same instruction** |
| `m.plus` | `MID$(A$,2)=+` | `24 69` | `2 69` 🔴 | a stray operator, not a value |
| `m.nocomma` | `MID$(A$)="Q"` | `2 69` | `2 69` ✅ | a missing `,` is a separator, not a value |
| `m.noclose` | `MID$(A$,2="Q"` | `2 69` | `2 69` ✅ | a missing `)` |
| `m.noeq` | `MID$(A$,2)"Q"` | `2 69` | `2 69` ✅ | a missing `=` |
| `m.ok` | `MID$(A$,2)="Q"` | `0 81` | `0 81` ✅ | control — the write MUST still happen |
| `m.ok3` | `MID$(A$,2,1)="Q"` | `0 81` | `0 81` ✅ | control, explicit `m` |

**Predicted: 9 scored, 4 DIFF.**

## 3. The rule being predicted

D-PUSING's, carried to a second verb:

> **A required operand that ENDS where a value was needed is `Missing operand`
> (24); one that is PRESENT but of the wrong type is `Type mismatch` (13); a
> missing SEPARATOR or PUNCTUATION is `Syntax error` (2).**

`m.num` is the row that can break it. ⚠️ **AND I HAVE BEEN WRONG ABOUT EXACTLY
THIS BEFORE**: D-PUSING's `u.comma` was written down as a *control* and predicted
wrong twice, because I carried one grammatical position's answer into another.
MID$'s RHS is a string-assignment operand, not a function argument, and nothing
measured so far says those must agree.

⚠️ **`m.plus` = 24 IS THE WEAKEST ROW.** `A$=+` reads 24 (D-MISSOP3), but that is
LET's RHS, a third position again.
