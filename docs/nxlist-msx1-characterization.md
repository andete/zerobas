# D-NXLIST — `NEXT` takes a LIST of loop variables

*Measured 2026-08-08 at `e966c0b` (D-FORVAR), `make nxlist-characterize`,
`probes/basic/basic_probe_nxlist.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack.*

🎯 **BOTH REFERENCES AGREE ON ALL 28 ROWS.** `FOR`/`NEXT` is core BASIC, present
on every MSX1, so every row here has **two** independent oracles.

⚠️ **The 28 were measured in THREE rounds, and rounds 2 and 3 each REFUTED a
design that round 1 had already made look finished.** That is recorded in §3 and
§4 rather than smoothed away: a row set frozen after round 1 would have shipped
a wrong rule, and a row set frozen after round 2 would have shipped an
8-byte fix for a row whose real answer is a different error.

---

## 1. The readings

| row | program (one statement per line) | both references | zerobas at `e966c0b` |
|---|---|---|---|
| `c.for` | `FOR I=1 TO 3` / `NEXT` / `PRINT I` | ` 4 ` | ` 4 ` 🟢 **control** |
| `c.next` | `FOR I=1 TO 3` / `NEXT I` / `PRINT I` | ` 4 ` | ` 4 ` 🟢 **control** |
| `c.nest` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B` / `NEXT A` / `PRINT A;B` | ` 3  3 ` | ` 3  3 ` 🟢 **control** |
| `m.two` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A` / `PRINT A;B` | ` 3  3 ` | **Syntax error** 🔴 |
| `m.name` | `FOR AB=1 TO 2` / `FOR CD=1 TO 2` / `NEXT CD,AB` / `PRINT AB;CD` | ` 3  3 ` | **Syntax error** |
| `m.three` | three nested / `NEXT C,B,A` / `PRINT A;B;C` | ` 3  3  3 ` | **Syntax error** |
| `m.inner` | `FOR A=1 TO 3` / `FOR B=1 TO 2` / `NEXT B,A` / `PRINT A;B` | ` 4  3 ` | **Syntax error** |
| `m.count` | `N=0` / `FOR A=1 TO 3` / `FOR B=1 TO 2` / `N=N+1` / `NEXT B,A` / `PRINT N` | ` 6 ` | **Syntax error** |
| `m.type` | `FOR A%=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A%` / `PRINT A%;B` | ` 3  3 ` | **Syntax error** |
| `m.typex` | `FOR A%=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `m.wrong` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,C` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `m.deep` | `FOR A` / `FOR B` / `FOR C` / `NEXT B,A` / `PRINT A;B;C` | ` 3  3  1 ` | **Syntax error** |
| `m.step` | `FOR A=3 TO 1 STEP -1` / `FOR B=1 TO 2` / `NEXT B,A` / `PRINT A;B` | ` 0  3 ` | **Syntax error** |
| `m.trail` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,` / `PRINT A;B` | **NEXT without FOR** | **Syntax error** |
| `m.trail1` | `FOR B=1 TO 2` / `NEXT B,` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `m.trailnum` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,1` / `PRINT"[OK]"` | **Syntax error** | **Syntax error** ✅ |
| `m.trailc` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,:PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `m.trail2` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A,` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** |
| `m.lead` | `FOR B=1 TO 2` / `NEXT ,B` / `PRINT"[OK]"` | **Syntax error** | **Syntax error** ✅ |
| `m.space` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B , A` / `PRINT A;B` | ` 3  3 ` | **Syntax error** |
| `m.after` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B,A:PRINT A;B` | ` 3  3 ` | **Syntax error** |
| `m.colon` | `FOR A=1 TO 2` / `FOR B=1 TO 2` / `NEXT B:NEXT A` / `PRINT A;B` | ` 3  3 ` | ` 3  3 ` ✅ |
| `m.ary` | `FOR A=1 TO 2` / `NEXT A(1)` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** ⏸ **DEFERRED** |
| `m.ary9` | `FOR A=1 TO 2` / `NEXT A(99)` / `PRINT"[OK]"` | **Subscript out of range** | **Syntax error** ⏸ **DEFERRED** |
| `m.aryspc` | `FOR A=1 TO 2` / `NEXT A (1)` / `PRINT"[OK]"` | **NEXT without FOR** | **Syntax error** ⏸ **DEFERRED** |
| `n.nofor` | `NEXT A` / `PRINT"[OK]"` | **NEXT without FOR** | **NEXT without FOR** ✅ |
| `n.barenofor` | `NEXT` / `PRINT"[OK]"` | **NEXT without FOR** | **NEXT without FOR** ✅ |
| `n.num` | `FOR A=1 TO 2` / `NEXT 1` / `PRINT"[OK]"` | **Syntax error** | **Syntax error** ✅ 🔴 **negative control** |

**9 of the 25 scored rows agreed** at `e966c0b` (3 rows deferred, see §4).
After D-NXLIST the battery is **25/25** — 28 cases, 3 deferred.

---

## 2. The rule, stated from the readings and from nothing else

> `NEXT` takes a **comma-separated list** of loop variables, and `NEXT B,A` is
> exactly `NEXT B : NEXT A`. Each element obeys `NEXT`'s own matching rule
> whole — both name characters **and** the resolved type — and closes any inner
> frames above the one it matches. The comma is read **only on the path where a
> frame CLOSES**: while a loop is still running, execution resumes at that
> loop's body and the rest of the list is never seen. After a comma a variable
> is **required**: a comma followed by the end of the statement is **NEXT
> without FOR**, and a comma followed by anything else that is not a name is
> **Syntax error**.

Four of those clauses are readings neither filed row could have predicted, and
each one decides a byte of the design:

* 🎯 **`m.count` — THE CONTINUES PATH NEVER SEES THE COMMA.** ` 6 ` is 3 × 2
  inner-body executions. A fix that tested for the comma before the
  loop-continue fork would read ` 3 ` here and *nothing else in the battery
  would move* — `m.two` would still be ` 3  3 `. This is the row for the path a
  fix is most likely to break, and it is a NUMBER, not an error face.
* 🎯 **`m.trail` — A TRAILING COMMA IS NOT A BARE `NEXT`.** With an OUTER frame
  standing, a bare `NEXT` would have closed it and the program would have
  finished; both references answer **NEXT without FOR** instead. See §3.
* 🎯 **`m.trailnum` — AND IT IS NOT A BLANKET ERROR EITHER.** `NEXT B,1` is
  **Syntax error**, the same face as `NEXT 1` alone. So the two error faces are
  BOTH live after a comma and which one fires depends on whether what follows
  is a statement TERMINATOR or merely not a name.
* 🎯 **`m.ary9` — A `NEXT` OPERAND IS A FULL VARIABLE REFERENCE, SUBSCRIPT AND
  ALL.** `NEXT A(99)` is **Subscript out of range**, so the reference EVALUATES
  the subscript before it matches anything. See §4.

And three the row set was widened to ask:

* **`m.deep`** — ` 3  3  1 `. A list element closes inner frames on its way, and
  the discarded frame's variable is **not** stepped: `C` reads 1, the value its
  own `FOR` last assigned.
* **`m.colon`** — the same nesting closed by a `:` instead of a `,` is green
  **before and after**, which is the only row that can tell "the comma re-enters
  `NEXT`" from "any separator re-enters `NEXT`".
* **`n.nofor` / `n.barenofor`** — a `NEXT` with no `FOR` **at all**. §5.

---

## 3. 🔴 Round 2: `m.trail` refuted the rule round 1 had already made obvious

After round 1 the natural reading of `NEXT B,` was *"a comma with nothing after
it is a bare `NEXT`"* — it costs no bytes, it re-uses the machinery that is
already there, and it explains `m.trail1` (`FOR B` / `NEXT B,` → **NEXT without
FOR**) perfectly: the frame stack is empty by then, so a bare `NEXT` has nothing
to match.

**`m.trail` is the same program with an OUTER frame standing**, and under that
reading it would close the outer loop and run to completion — ` 3  3 `. Both
references answer **NEXT without FOR**.

🎯 **`m.trail1` ALONE COULD NOT HAVE SAID THIS**, because its stack is empty at
exactly the moment the two readings differ, so both predict the same answer. One
row cannot separate two rules ([[one-row-cannot-separate-two-rules]]) — and the
knife that would have caught it late is **K-NL4**, which reddens `m.trail` and
`m.trailc` and leaves `m.trail1` and `m.trail2` GREEN for that same reason
(`spec-basic-nxlist.md` §8).

`m.trailnum` then fixed the *other* end of the same question. *"A comma demands a
variable"* is not enough: **which error?** `NEXT B,1` reads `Syntax error` and
`NEXT B,` reads `NEXT without FOR`, so the split is between "a statement
terminator follows" and "something that is not a name follows" — which is the
split `ex_next`'s own no-variable path already makes, and §4.2 of the spec spends
**one byte** on it rather than a guard.

---

## 4. ⏸ Round 3: `NEXT A(1)` is a DIFFERENT rule, and `m.ary9` is what says so

`m.ary` (`NEXT A(1)` → **NEXT without FOR**) looks like a free ride on this
slice: an array element is a different variable from the scalar `A`, so it
matches no frame, and the cheapest way to say that is to make the parsed key
unmatchable when a `(` follows the name — **8 bytes**, the same trick D-FORVAR
used for `NEXT A$` ([`spec-basic-forvar.md`](spec-basic-forvar.md) §4.2).

**`m.ary9` refutes it.** `NEXT A(99)` — 99 is outside an auto-DIMmed `0..10` —
reads **Subscript out of range** on both references. So a `NEXT` operand is
parsed as a *complete variable reference*: the subscript is EVALUATED and
range-checked **before** anything is matched. The 8-byte fix answers `NEXT
without FOR` there and would have traded one red row for another
([[a-priced-decline-is-a-claim-about-a-design]]).

`m.aryspc` (`NEXT A (1)`) adds that the space is skipped too, so it is not even
a lexically contiguous suffix test.

⇒ All three rows are **measured, printed and never scored**. The faithful fix is
an array-element *reference* parse in `ex_next` — the D-ARYLV / lvalue family,
not the LIST family — and it is filed in `TODO.md` as its own residual with these
three readings. A deferred row that started agreeing would itself be a finding,
which is why they still print.

---

## 5. 🔴 `n.nofor` / `n.barenofor` — the rows the CARVE demanded

This slice is funded by merging `nx_find`'s *"the FOR stack is empty"* test with
`nx_miss`'s *"the walk ran out of frames"* test into one `nx_bound`
([`spec-basic-nxlist.md`](spec-basic-nxlist.md) §6.3).

**No row in the D-FORVAR battery enters through `nx_find`'s test.** Every
mismatching row there (`n.wrong`, `n.prefix`, `n.samen1`, `n.xtype`, `n.strnx`)
runs with exactly one frame on the stack, so `nx_find`'s test passes and the
error is raised from `nx_miss` after that frame is popped. A `NEXT` with no `FOR`
**at all** is the only program that takes the other entry — and it existed
nowhere.

Both forms are here (`NEXT A` and a bare `NEXT`) because the two entries reach
`nx_scan` with different keys, and both are green **before and after**: they are
the kind of row that can only catch a carve, never a fix.

---

## 6. Denominator

**(LIST LENGTH: 1 / 2 / 3) × (ELEMENT: matching name / mismatching name /
mismatching TYPE / two-char name / array form) × (DEGENERATE: trailing comma
with an outer frame / trailing comma with none / trailing comma after a full
list / trailing comma before a `:` / leading comma / a non-name after the comma /
spaces around the comma)**, plus the CONTINUES path measured as an inner-body
COUNT, plus a list element that closes inner frames on its way, plus a NEGATIVE
step inside a list, plus termination by `:` after the list and by a `:` used
INSTEAD of the comma, plus a `NEXT` with no `FOR` at all through **both** of the
frame-stack guard's entries, plus the numeric form both references REFUSE.

**Not covered, and named rather than implied:** `NEXT A(1)` and its subscript
evaluation (§4 — measured, divergent, DEFERRED with its own residual); a list
element that is a `$` name (`NEXT B,A$` — D-FORVAR `n.strnx` says a `$` `NEXT`
name misses, and inside a list that composes, but it is not measured here); a
list spanning a line boundary; a `NEXT` list reached inside a `GOSUB` called from
the loop body; a list longer than three; and nesting deeper than 8, where
zerobas's fixed 8-frame stack and the references' stack-bounded limit are
different mechanisms and neither is measured against the other.
