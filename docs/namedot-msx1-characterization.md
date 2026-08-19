# `.` IN AN IDENTIFIER — MSX1 characterization (D-NAMDOT)

*Measured 2026-08-01 on **two** reference machines that agree on **all 23 rows**:
`Philips_VG_8020` (MSX1, cassette BASIC) and `National_CF-3300` (MSX1, Disk
BASIC). Probe: [`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
`dot` + `dotd` batteries. Spec: [`docs/spec-basic-namedot.md`](spec-basic-namedot.md).*

Byte readout is `("stored_line", TXTTAB)` — the stored line's **own bytes**, gloss
`printable ASCII verbatim, everything else as <XX>`; the 2-byte link is dropped
(an absolute address, and the CF-3300's text base is not the VG-8020's).

**Every byte payload passed the echo guard on both references before it was read,
and every reference pass ran at `--repeat 2` on independent boots.** No row came
back `UNSTABLE`. The `--repeat 2` is not ceremony: in the oracle-lock direction a
dropped keystroke is a false PASS *forever* ([[lineno-blank-echo-guard]]).

---

## 0. Why this battery exists

D-NAMBLANK filed this defect and deliberately did **not** fix it
([`docs/nameblank-msx1-characterization.md`](nameblank-msx1-characterization.md) §3).
Its evidence was two rows, and the second was written to be the *control* of the
first:

```
nam-dot    20 A=B .5   ref -> A<EF>B .5   zb -> A<EF>B <1D>@P<00><00>
nam-dot0   20 A=B.5    ref -> A<EF>B.5    zb -> A<EF>B<1D>@P<00><00>   NO BLANK
```

Two rows are a **sample**, not a surface — the trap D-NOTOPEN2 hit, where 3 of 7
rows gave a different answer than all 7. This battery is the denominator.

---

## 1. The rules

> **R-D1 — a `.` behind a LIVE name state CONTINUES the identifier.** It is
> copied verbatim and the in-a-name state survives it, exactly as a digit does.
>
> **R-D2 — a `.` with NO live name state begins a numeric constant, AND THE
> DIGIT IS OPTIONAL.** A bare `.` is the single-precision literal `0`.
>
> **R-D3 — the RUN-TIME variable scanner does NOT accept `.`.** A crunched
> `B.5` is name bytes that the executor then **refuses**: `Syntax error`.

R-D1 and R-D2 are one dispatch arm. R-D3 is the one that says which *other* code
does not change, and it is the reason this slice never touches the main ROM.

zerobas today is **rule F**: `tk_loop` looks exactly one character past a `.`,
at every position, and hands it to `tk_float` on a digit
([`basic/tokenise.inc:94`](../basic/tokenise.inc:94)) — a decision taken without
consulting the name state, and one that also *requires* the digit.

---

## 2. The rows that separate the rules

| label | typed | both references | zerobas | |
|---|---|---|---|---|
| `nam-dot0` | `20 A=B.5` | `A<EF>B.5` | `A<EF>B<1D>@P<00><00>` | ★ the filed row |
| `nam-dot` | `20 A=B .5` | `A<EF>B .5` | `A<EF>B <1D>@P<00><00>` | ★ its blanked twin |
| `dot-two` | `20 A=B..5` | `A<EF>B..5` | `A<EF>B.<1D>@P<00><00>` | **two** dots in one name |
| `dot-dig` | `20 A=B1.5` | `A<EF>B1.5` | `A<EF>B1<1D>@P<00><00>` | a **digit**-set state carries it too |
| `dot-blk2` | `20 A=B . 5` | `A<EF>B . 5` | `A<EF>B <1D>@P<00><00>` | a blank on **both** sides (R-N1) |
| `dot-lval` | `20 B.5=7` | `B.5<EF><18>` | `B<1D>@P<00><00><EF><18>` | LVALUE position |
| `dot-print` | `20 PRINT B.5` | `<91> B.5` | `<91> B<1D>@P<00><00>` | after a **keyword token** |
| `dot-op` | `20 A=B.5+1` | `A<EF>B.5<F1><12>` | `A<EF>B<1D>@P<00><00><F1><12>` | an operator still **breaks** it |
| `dot-start` ^ | `20 A=.B` | `A<EF><1D><00><00><00><00>B` | `A<EF>.B` | 🔴 §3 — **a control, and it refuted me** |
| `dot-lead` | `20 .A=1` | `<1D><00><00><00><00>A<EF><12>` | `.A<EF><12>` | 🔴 §3 |

`^` = written as a two-sided control.

**Eight rows carry R-D1. Two carry R-D2, and both were written to be CONTROLS.**

---

## 3. 🔴 The two controls that refuted their own prediction

`dot-start` and `dot-lead` were filed in this battery as **predicted-green
two-sided controls**: a `.` with a non-digit behind it, which under rule F and
under R-D1 alike is copied verbatim. Both references say otherwise.

```
20 A=.B   ->  A<EF><1D><00><00><00><00>B      the '.' is the LITERAL 0, then the name B
20 .A=1   ->  <1D><00><00><00><00>A<EF><12>   same, in statement position
```

**A `.`-led literal does not need its digit.** That is a rule about the *entry*
to the literal scan, not about the name state, and nothing in the filed pair
could have reached it — `nam-dot`/`nam-dot0` both have a digit behind the dot.

This is the same shape as [[knife-that-refutes-its-own-control]]: a
predicted-GREEN control going red is a finding about the **spec**, corrected in
place rather than dropped. It is also why `dot-lead` answers the question the
byte gloss was supposed to leave open — *can a name begin with a `.`?* **No.**
The `.` is a number, and the name starts after it.

### 3.1 The two cells R-D2 makes reachable, asked before it was implemented

Both round-1 rows put a **letter** behind the bare `.`. That is a sample of the
literal-scan entry, not its surface, so the two shapes with nothing and with an
**exponent marker** behind the dot were oracle-locked before any code was
written — a rule may not ship one row wider than its denominator.

| label | typed | both references | zerobas |
|---|---|---|---|
| `dot-eol` | `20 A=.` | `A<EF><1D><00><00><00><00>` | `A<EF>.` |
| `dot-exp` | `20 A=.E5` | `A<EF><1D><00><00><00><00>` | `A<EF>.E5` |

`dot-exp` stores **nothing after the token**: the reference consumed `E5` into
the literal as a well-formed exponent (`0E5` = 0), rather than leaving it as
name bytes. Both rows read the same value as a bare dot, and both are red today.

---

## 4. 🔴 R-D3 — the crunch accepts `.`, the EXECUTOR refuses it

The first cut of the `dotd` battery asked `B.5=7` then `PRINT"[";B.5;"]"`, and
**both references read `<none>`** — a value that compares EQUAL on every side and
would have been reported as *agrees*. That is precisely the trap filed in this
session ([[say-row-without-brackets]]). Reading the **screen** instead of the
extracted value ([[read-the-screen-when-a-probe-fails]]) showed why:

```
  B.5=7                ->  Syntax error
  PRINT"[";B.5;"]"     ->  `[ 0` then Syntax error      (no ']', hence no span)
```

PRINT emitted `[`, evaluated `B` as **0**, printed it, and then choked on the
leftover `.5`. So the reference's run-time variable scan **stops at the `.`**.

Re-asked through `ERR`, which prints its brackets whether or not the statement
under test aborts:

| label | typed | both references | zerobas | |
|---|---|---|---|---|
| `dotd-var` | `B.5=7` → `PRINT"[";ERR;"]"` | ` 2 ` | ` 2 ` | assigning: **Syntax error** |
| `dotd-ctl` ^ | `B5=7` → `PRINT"[";ERR;"]"` | ` 0 ` | ` 0 ` | CONTROL: same shape, no dot |
| `dotd-rd` | `A=B.5` → `PRINT"[";ERR;"]"` | ` 2 ` | ` 2 ` | reading: **Syntax error** too |
| `dotd-b5` | `B.5=7` → `PRINT"[";B5;"]"` | ` 0 ` | ` 0 ` | nothing was assigned to `B5` |
| `dotd-lead` | `.A=1` → `PRINT"[";.A;"]"` | ` 0  0 ` | `<none>` | `.` and `A` are **two items** |

🔴 **THIS INVERTS THE FILED PRESCRIPTION.** `TODO.md` and
[`nameblank-msx1-characterization.md`](nameblank-msx1-characterization.md) §3
both say, in as many words, that the run-time scan
([`basic/vars.asm`](../basic/vars.asm) `is_ident_cont`) *"has to accept `.` as
well, or the executor would look up a different variable than the one the
tokeniser stored"*. **The reference does exactly what that warning forbids** — it
stores name bytes it will not resolve — and the two ERR rows measure it, against
a control that reads 0. `basic/vars.asm` must **not** change, and `DEFINT`/
`DEFSNG`/`DEFSTR`, `VARPTR`, `FOR` variables, `DIM`/array names and `INPUT`/
`READ` targets are untouched *because they all reach the same unchanged scanner*.

⚠️ **`dotd-var`/`dotd-rd` AGREE TODAY, AND FOR THE WRONG REASON** — zerobas
reaches ERR=2 by crunching a float token and choking on *that*. After the fix it
must reach the same 2 by the reference's route. A cell pinned because it agrees
is what caught the regression D-BADFNUM's signed-off design shipped
([[badfnum-channel-class-slice]]), and these three are pinned for that reason.

---

## 5. The rows that BOUND the rule — where a `.` must still lead a literal

These agree on all three sides **today** and pin the cells the fix must not move.
They are the difference between R-D1 and *"a `.` is an identifier character
wherever it appears"*, and **neither filed row can tell those apart**.

| label | typed | all three sides | what it pins |
|---|---|---|---|
| `dot-sfx` | `20 A=B$.5` | `A<EF>B$<1D>@P<00><00>` | a type **suffix** ends the identifier |
| `dot-paren` | `20 A=B(.5)` | `A<EF>B(<1D>@P<00><00>)` | `(` clears the state |
| `dot-kw` | `20 A=B AND .5` | `A<EF>B <F6> <1D>@P<00><00>` | a **keyword** clears the state |
| `dot-many` ^ | `20 A=B.C.D` | `A<EF>B.C.D` | already green: dots with no digit behind |
| `dot-ctl` ^ | `20 A=B.` | `A<EF>B.` | a dot at EOL, inside a name |
| `dot-let` ^ | `20 A=B.C` | `A<EF>B.C` | a dot then a letter |
| `dot-str` ^ | `20 A$="B.5"` | `A$<EF>"B.5"` | inside a **string literal** |
| `dot-rem` ^ | `20 REM B.5` | `<8F> B.5` | a REM tail is **verbatim** |
| `dot-data` ^ | `20 DATA B.5` | `<84> B.5` | a DATA body is **verbatim** |

Plus the whole `dec-dot*` cohort D-DECBLANK already owns — `dec-dotlead0`
(`20 A=.5`), `dec-dotlead` (`20 A=. 5`), `dec-dotpre`, `dec-dotpost`, `dec-dotx`,
`dec-dotx0` — and `lit-float` (`20 A=1 . 5`). `ONLY=dot` selects every one of
them in the same run, which is not an accident to be worked around: a knife on
this rule wants the must-not-move cells for free.

---

## 6. ⚠️ `dot-goto` — a THIRD defect, measured here and NOT fixed here

```
20 GOTO 1.5   ref -> <89> <0E><01><00>.<0E><05><00>
              zb  -> <89> <0E><01><00><1D>@P<00><00>
```

The reference emits `$0E,0001`, copies the `.` **verbatim**, and then crunches
the `5` as a **second** `$0E` line-number reference. That is
[`branch_lineno`](../basic/tokenise.inc:587)'s list-continuation loop treating a
`.` as a separator that does not end the list — the same family as the empty-slot
and blank-before-comma bugs already recorded in `bl_num`'s own comment, and
**different code from the `tk_loop` dispatch this slice changes**.

Neither R-D1 nor R-D2 predicts this row: there is no name state after a
line-number reference, so R-D2 makes the `.` a literal `0` and the `5` an
ordinary integer — still not what the reference does. It is filed in `TODO.md`
with its exact post-fix bytes and pinned as `KNOWN_DIVERGE`. Closing it here
would be the D-MFDOM trap ([[maxfiles-domain-slice]]).

---

## 7. What was NOT measured

* `20 A=.E5` / `20 A=.` at end of line — a bare `.` immediately followed by an
  exponent marker, or by nothing. R-D2 makes both reachable for the first time;
  neither is asked, and neither is predicted by anything above.
* Only `$20` is measured as "a blank" (as in every battery in this probe).
* Whether `.` is significant in a name the executor *would* accept is
  **dissolved, not answered**: §4 shows no such name exists, so MSX-BASIC's
  two-significant-character key never sees a `.`.
