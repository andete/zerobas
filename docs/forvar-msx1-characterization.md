# D-FORVAR — what a `FOR`/`NEXT` loop variable may BE

*Measured 2026-08-08 at `79f6bdb` (D-LRVAR), `make forvar-characterize`,
`probes/basic/basic_probe_forvar.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack.*

🎯 **BOTH REFERENCES AGREE ON ALL 33 ROWS.** `FOR`/`NEXT` is core BASIC, present
on every MSX1, so every row here has **two** independent oracles — a stronger
footing than the whole lvalue/FIELD arc, which rested on the CF-3300 alone.

⚠️ **32 of the 33 were measured BEFORE the fix; `n.samen1` was added AFTER it**,
because a knife proved the denominator was one row short (§5). Its zerobas
column below is therefore the post-fix reading only, marked as such — a value
nobody measured is not a value this document may print.

---

## 1. The readings

| row | program (one statement per line) | both references | zerobas at `79f6bdb` |
|---|---|---|---|
| `c.for` | `FOR I=1 TO 3` / `NEXT` / `PRINT I` | ` 4 ` | ` 4 ` 🟢 **control** |
| `c.next` | `FOR I=1 TO 3` / `NEXT I` / `PRINT I` | ` 4 ` | ` 4 ` 🟢 **control** |
| `c.let` | `AB=7` / `PRINT AB` | ` 7 ` | ` 7 ` 🟢 **control** |
| `f.two` | `FOR AB=1 TO 3` / `NEXT` / `PRINT AB` | ` 4 ` | **Syntax error** 🔴 |
| `f.long` | `FOR INDEX=1 TO 3` / `NEXT` / `PRINT INDEX` | ` 4 ` | **Syntax error** |
| `f.dig` | `FOR A1=1 TO 3` / `NEXT` / `PRINT A1` | ` 4 ` | **Syntax error** |
| `f.alias` | `FOR ABC=1 TO 3` / `NEXT` / `PRINT AB` | ` 4 ` | **Syntax error** |
| `f.pct` | `FOR A%=1 TO 3` / `NEXT` / `PRINT A%` | ` 4 ` | **Syntax error** |
| `f.bang` | `FOR A!=1 TO 3` / `NEXT` / `PRINT A!` | ` 4 ` | **Syntax error** |
| `f.hash` | `FOR A#=1 TO 3` / `NEXT` / `PRINT A#` | ` 4 ` | **Syntax error** |
| `f.twopct` | `FOR AB%=1 TO 3` / `NEXT` / `PRINT AB%` | ` 4 ` | **Syntax error** |
| `f.str` | `FOR A$=1 TO 3` / `NEXT` / `PRINT"[OK]"` | **Type mismatch** | **Type mismatch** ✅ |
| `n.xtype` | `FOR A%=1 TO 3` / `NEXT A` / `PRINT A%` | **NEXT without FOR** | **Syntax error** |
| `n.two` | `FOR AB=1 TO 3` / `NEXT AB` / `PRINT AB` | ` 4 ` | **Syntax error** |
| `n.pct` | `FOR A%=1 TO 3` / `NEXT A%` / `PRINT A%` | ` 4 ` | **Syntax error** |
| `n.prefix` | `FOR AB=1 TO 3` / `NEXT A` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `n.wrong` | `FOR AB=1 TO 3` / `NEXT CD` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `n.samen1` | `FOR AB=1 TO 3` / `NEXT CB` / `PRINT"[OK]"` | **NEXT without FOR** | *(added post-fix, §5)* **NEXT without FOR** ✅ |
| `n.strnx` | `FOR A=1 TO 3` / `NEXT A$` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `n.multi` | `FOR AB=1 TO 2` / `FOR CD=1 TO 2` / `NEXT CD,AB` / `PRINT AB;CD` | ` 3  3 ` | **Syntax error** ⏸ **DEFERRED** |
| `n.multi1` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A` / `PRINT A;B` | ` 3  3 ` | **Syntax error** ⏸ **DEFERRED** |
| `n.nest` | `FOR AB=1 TO 2` / `FOR CD=1 TO 2` / `NEXT CD` / `NEXT AB` / `PRINT AB;CD` | ` 3  3 ` | **Syntax error** |
| `n.close` | `FOR AB=1 TO 2` / `FOR CD=1 TO 2` / `NEXT AB` / `PRINT AB;CD` | ` 3  1 ` | **Syntax error** |
| `n.mixnx` | `FOR AB=1 TO 2` / `FOR CD=1 TO 2` / `NEXT CD` / `NEXT` / `PRINT AB;CD` | ` 3  3 ` | **Syntax error** |
| `f.dep8` | 8 nested `FOR`/`NEXT` pairs, single letters | `OK` | `OK` ✅ |
| `f.coll` | `A=9` / `FOR A%=1 TO 3` / `NEXT` / `PRINT A;A%` | ` 9  4 ` | **Syntax error** |
| `f.colls` | `A$="X"` / `FOR A=1 TO 3` / `NEXT` / `PRINT A;A$` | ` 4 X` | ` 4 X` ✅ |
| `f.defint` | `DEFINT A` / `FOR AB=1 TO 3` / `NEXT` / `PRINT AB` | ` 4 ` | **Syntax error** |
| `f.defstr` | `DEFSTR A` / `FOR AB=1 TO 3` / `NEXT` / `PRINT"[OK]"` | **Type mismatch** | **Syntax error** |
| `f.step` | `FOR AB=10 TO 1 STEP -3` / `NEXT` / `PRINT AB` | `-2 ` | **Syntax error** |
| `f.ary` | `DIM A(3)` / `FOR A(1)=1 TO 3` / `NEXT` / `PRINT"[OK]"` | **Syntax error** | **Syntax error** ✅ 🔴 **negative control** |
| `x.numstr` | `A$="X"` / `B=1+A$` / `PRINT B` | **Type mismatch** | **` 1 `** 🔴 |
| `x.strtop` | `A$="X"` / `B=A$` / `PRINT B` | **Type mismatch** | **Type mismatch** ✅ |

**8 of the 30 scored rows agreed** at `79f6bdb` (2 rows deferred, see §3).
After D-FORVAR the battery is **31/31** — 33 cases, 2 deferred.

---

## 2. The rule, stated from the readings and from nothing else

> A `FOR` loop variable is an **ordinary scalar variable REFERENCE** — any name
> (2 significant characters), any explicit type suffix, the DEFtbl default when
> there is none — exactly what `LET` and `READ` and `INPUT` accept. It is **not**
> an array element. `NEXT` matches a frame on the **whole identity**: both name
> characters **and the resolved TYPE**. A `$` name is a `Type mismatch` as a
> `FOR` variable and simply **matches nothing** as a `NEXT` variable.

Four of those clauses are readings the filed residual could not have predicted,
and each one decides a byte of the design:

* 🎯 **`n.xtype` — THE TYPE IS PART OF THE MATCH KEY.** `FOR A%=1 TO 3` / `NEXT A`
  is **NEXT without FOR**, not a match. So the frame cannot hold a name alone:
  it has to hold `(name0, name1, type)`, and the compare is **three** bytes. No
  measured row before this one asked, and the obvious two-byte key is wrong.
* 🎯 **`n.prefix` — a ONE-character match is wrong in the OTHER direction too.**
  `FOR AB=1 TO 3` / `NEXT A` is **NEXT without FOR**. The shipped single-letter
  shim answers "match" here, so this row is red for a reason opposite to every
  other red row: the old code is not too strict, it is too loose.
* 🎯 **`n.strnx` — `NEXT A$` is NOT a type error.** It is **NEXT without FOR** —
  the reference does not reject the name, it simply fails to find a frame for it.
  A `jp c,type_mismatch_error` on `NEXT`'s parse (the obvious symmetry with
  `FOR`) would answer the wrong error. §4.2 of the spec is built on this row.
* 🎯 **`f.defstr` — a DEFSTR'd unsuffixed name is `Type mismatch` as a loop
  variable**, the same face as an explicit `A$`. So the guard belongs on the
  *resolved* type, not on the `$` character.

And two more the row set was widened to ask:

* **`f.dep8`** — 8 nested loops run on all three sides. A wider frame in a
  fixed-size stack is fewer frames unless the stack moves, so this row is what
  says a fix did not quietly buy its key with a nesting level.
* **`f.coll` / `f.colls`** — `A`, `A%` and `A$` are three distinct variables, and
  a loop over one leaves the others alone.

---

## 3. ⏸ The two DEFERRED rows are a DIFFERENT rule, and `n.multi1` is the proof

`NEXT CD,AB` reads ` 3  3 ` on both references and `Syntax error` here. That is
a divergence — but the row cannot say **which** defect causes it, because the
program also contains the two-character names this document is about.

**`n.multi1` is the same comma with the single-letter names `ex_for` already
parses**, and it is **still `Syntax error`**. So the multi-variable `NEXT` is an
independent defect: `ex_next`'s `nx_end` runs `jp exec_stmt` once its frame is
closed, and the `,` then arrives in statement position. Fixing the NAME cannot
turn either row green.

Both rows were **measured, printed and never scored**, in either direction — a
deferred row that started agreeing would itself be a finding. Filed in `TODO.md`
as its own residual ([[one-row-cannot-separate-two-rules]]).

✅ **CLOSED 2026-08-08 by D-NXLIST** ([`spec-basic-nxlist.md`](spec-basic-nxlist.md),
measured in [`nxlist-msx1-characterization.md`](nxlist-msx1-characterization.md)
at 28 rows on three sides). Both rows are **scored again** and
`forvar-acceptance` reads **33/33 with an empty `DEFERRED`**. 🎯 The separation
`n.multi1` bought was real: the fix is entirely in `nx_end`/`ex_next`'s comma
path and touches no part of the NAME rule this document is about. ⚠️ And it took
**three** measurement rounds — a trailing comma is not a bare `NEXT`, `NEXT B,1`
is `Syntax error` where `NEXT B,` is `NEXT without FOR`, and `NEXT A(1)` turned
out to be a THIRD rule (the reference evaluates the subscript) which D-NXLIST
declined with a price.

---

## 4. 🔴 `x.numstr` is a defect this document FOUND, not one it went looking for

`A$="X"` / `B=1+A$` reads **Type mismatch** on both references and **` 1 `**
here: zerobas resolves `A$` in a numeric factor to the *numeric* variable `A`,
reads it as an unset 0, and computes `1+0`. **The program runs on with a wrong
answer** — the worst shape a divergence can take.

`x.strtop` (`B=A$`, the same name at the TOP of the operand) is `Type mismatch`
on all three, which locates the defect exactly: `ev_rel`'s `str_eval` probe
catches a string operand only when it is the whole operand.

🎯 **This is D-DEFSTR's own class, in the form D-DEFSTR did not cover.**
[`spec-basic-deftbl-strcode.md`](spec-basic-deftbl-strcode.md) §3.1 records the
identical pair for a *DEFSTR-defaulted* name — *"`B=S` errored and `B=1+S`
silently read 0"* — and fixed it by having `ev_f_var` check the **resolved type**
through `check_vartype_num`. The check works; the *input* lies. `var_name_key`'s
`vnk_dollar` hardcodes `(VARTYPE)=8` for a `$` suffix, which is indistinguishable
from a default-double `A`, so the guard passes.

The rows are in this battery because [`spec-basic-forvar.md`](spec-basic-forvar.md)
§4.2's design has to change that cell to make `NEXT A$` miss, and **a side effect
that is measured is a finding; one that is not is a regression**.

---

## 5. 🔴 `n.samen1` — the row a KNIFE demanded, not the row set

Every mismatching `NEXT` row above differs from its frame in **`name1`**:
`n.wrong` moves both characters, `n.prefix` drops the second, `n.xtype` and
`n.strnx` move the type. So **nothing in the battery said whether `name0` is
compared at all** — and the knives said so out loud: K-FV1 (match on one byte)
and K-FV2 (match on two) reddened the **identical** set.

*A cut with no row of its own is a missing row, not a bad cut.* `n.samen1` holds
`name1` fixed at `B` and moves only `name0`; both references answer **NEXT
without FOR**, and re-running the two cuts against it separates them cleanly —
K-FV1 reddens it, K-FV2 does not
([[draft-the-knives-before-freezing-the-row-set]]).

---

## 6. Denominator

**(NAME FORM: 1-char / 2-char / 3+-char / letter+digit) × (TYPE SUFFIX: none /
`%` / `!` / `#` / `$`) × (NEXT FORM: bare / named-matching / named-mismatching /
multi-variable)**, plus whether `NEXT` matches on the TYPE, plus nesting and a
named `NEXT` that CLOSES an inner frame, plus a bare `NEXT` that FOLLOWS a named
one, plus the nesting DEPTH a wider frame could silently buy its key with, plus
the `A` / `A%` / `A$` identity, plus the DEFtbl that supplies the type when there
is no suffix, plus the array form both references REFUSE, plus the two rows §4's
design forces.

**Not covered, and named rather than implied:** a FLOAT-valued loop (`FOR A=1 TO
2 STEP .5` — the loop MATH is int16 in this tree by D-D and is not this slice's
to change); `FOR` with the loop variable modified inside the body; a loop
variable that is also a `FN` parameter; `NEXT` inside a `GOSUB` called from the
loop body; and the multi-variable `NEXT` of §3.
