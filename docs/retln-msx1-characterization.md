<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-RETLN — `RETURN <line>`, measured: it is a POP **and** a GOTO, the empty-stack check comes FIRST, and it is **not** an error-handler exit

Measured 2026-08-01 against `6efafed` on **both** references — `Philips_VG_8020`
and `National_CF-3300` — with `--repeat 2` (two independent boots per side; a row
whose two readings differ is fatal, not averaged) and with every payload passed
through the echo guard on all three sides *before* any reading was read.

Instrument: the `lnrt` battery in
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
say mode. Each row runs a program and then reads `PRINT"[";A;ERR;"]"`, so one
bracket span carries both **where control went** (A) and **whether it aborted**
(ERR).

```bash
python3 probes/basic/basic_probe_lnblank.py --say --repeat 2 --sides vg8020,cf3300,zb --only lnrt-
```

---

## 0. The headline

Both references agree on **every** row of the walk — 25 rows, no reference
disagreement anywhere. Five rules, and only the first was in the filed item:

| | rule | rows |
|---|---|---|
| **R-T1** | The **empty-stack check runs first**, before the argument is parsed *or* resolved. An empty GOSUB stack is `ERR 3` no matter what the argument says. | `lnrt-nogos` `lnrt-nogosbad` `lnrt-nogosund` `lnrt-onerr` `lnrt-retrap` `lnrt-dir` |
| **R-T2** | `RETURN <line>` pops **exactly one** frame and then **branches**, instead of resuming at that frame's saved resume point. Statements after it on the same line do not run. | `lnrt-line` `lnrt-back` `lnrt-pop` `lnrt-depth` `lnrt-trail` `lnrt-blank` |
| **R-T3** | A line that does not exist → `ERR 8`, and the frame **is already gone** when it fires. `RETURN 0` is an ordinary lookup that fails the same way. | `lnrt-undef` `lnrt-undefp` `lnrt-zero` |
| **R-T4** | An argument that is neither a `$0E` line reference nor a statement terminator (`<EOL>` / `:`) → `ERR 2`. `RETURN` does **not** ignore trailing junk. | `lnrt-var` `lnrt-varp` `lnrt-bcolon` |
| **R-T5** | Every error above is filed against the **`RETURN`'s own line**, not the caller's. | `lnrt-erlund` `lnrt-erlvar` (`lnrt-erlctl` = control) |

---

## 1. 🔴 What the walk REFUTED

**MS-BASIC documents `RETURN <line>` as the way to leave an `ON ERROR` handler.
On MSX it is nothing of the kind.** I designed the first draft of this battery
around that lore, including a row (`lnrt-retrap`) asking whether leaving a handler
by `RETURN <line>` re-arms error trapping the way `RESUME` does.

It does not, because it never gets that far. A handler is entered **without**
pushing a GOSUB frame, so R-T1 fires and the statement is simply "RETURN without
GOSUB":

```
10 ON ERROR GOTO 50 : 20 ERROR 7 : 30 A=A+3:END
50 A=A+50:RETURN 70 : 70 A=A+70:END
                       both references -> A =  50, ERR 3
   ...the same program with RESUME 70  -> A = 120, ERR 0   (lnrt-onerrctl)
```

`lnrt-onerrctl` is the control that makes this a difference rather than a number:
the identical program with `RESUME 70` reaches line 70 and reads ` 120  0 `, so
the instrument demonstrably *can* read "the handler exited to line 70". It is
`RETURN 70` that cannot get there. The re-arm question never arises, and an
implementation built on the documented-elsewhere behaviour would have been wrong
in a way no row about *branching* would have caught.

⚠️ zerobas already agrees on all three of these rows, and agrees for the right
reason (its own empty-stack check fires first). They are **MUST-NOT-MOVE
controls** for the change, not merely rows that happen to pass.

---

## 2. 🔴 Two rows of the first walk AGREED FOR THE WRONG REASON

Recorded because both were written as decisive rows, both came back green on all
three sides, and neither was measuring anything.

### 2.1 `lnrt-back` was vacuous — the program ended before it began

The row was to prove the branch searches *backwards*, to a line before the
`GOSUB`. As first written it opened with the target line itself:

```
5 A=A+5:END : 10 GOSUB 40 : 20 A=A+20:END : 40 RETURN 5
```

`RUN` enters at line **5**, hits `END` immediately, and the program stops before
it ever reaches the `GOSUB`. All three sides read ` 5  0 ` — agreeing because
nothing under test had run. This is [[vacuous-gate-row-steers-not-just-misses]]
exactly: it does not merely miss, it *steers*, because ` 5  0 ` reads as "the
backwards branch works on zerobas too".

Fixed by making line 5 reachable **only** by the branch:

```
1 GOTO 10 : 5 A=A+5:END : 10 GOSUB 40 : 20 A=A+20:END : 40 RETURN 5
        both references ->  5  0        zerobas ->  20  0
```

### 2.2 `lnrt-depth` had two candidate causes and measured neither

The row was to ask whether the branch pops **one** frame or **all** of them. As
first written, line 40 was a bare `GOSUB 60`:

```
10 GOSUB 40 : 20 A=A+20:END : 30 A=A+30:RETURN : 40 GOSUB 60 : 50 A=A+50:END : 60 RETURN 30
```

"popped one frame and branched to 30, then `RETURN`ed through the outer frame to
line 20" gives ` 50  0 `. So does "never branched at all, resumed after `GOSUB
60`, and **fell through** into line 50". Both references and zerobas all read
` 50  0 ` — for opposite histories ([[row-with-two-candidate-causes]]).

Fixed by giving the not-branched history its own arithmetic and its own
terminator, so no two paths share a number:

```
10 GOSUB 40 : 20 A=A+20:END : 30 A=A+30:RETURN : 40 GOSUB 60:A=A+7:END : 60 RETURN 30
        both references ->  50  0        zerobas ->  7  0
```

| history | reading |
|---|---|
| pops ONE, branches to 30, `RETURN`s through the outer frame to line 20 | ` 50  0 ` ← both references |
| pops ALL, branches to 30, `RETURN`s on an empty stack | ` 30  3 ` |
| never branches, resumes on line 40 | ` 7  0 ` ← zerobas today |

Both fixes are in the probe with the reasoning attached, so the shape cannot come
back silently.

---

## 3. The readings

`A` is where control got to, `ERR` is what (if anything) aborted. Both references
identical on every row; the `zb` column is zerobas at `6efafed`.

### 3.1 Controls — each reads a value a subject row must CHANGE

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `lnrt-ctl` | `10 GOSUB 40 : 20 A=A+20:END : 30 A=A+30:END : 40 RETURN` | ` 20  0 ` | ` 20  0 ` | ` 20  0 ` |
| `lnrt-nogosctl` | `10 RETURN : 20 A=A+20:END` | ` 0  3 ` | ` 0  3 ` | ` 0  3 ` |
| `lnrt-undctl` | `10 GOSUB 99 : 20 A=A+20:END` | ` 0  8 ` | ` 0  8 ` | ` 0  8 ` |
| `lnrt-erlctl` | `…20 GOSUB 40 : 40 ERROR 7 : 50 A=ERL:END` | ` 40  7 ` | ` 40  7 ` | ` 40  7 ` |
| `lnrt-onerrctl` | `…50 A=A+50:RESUME 70 : 70 A=A+70:END` | ` 120  0 ` | ` 120  0 ` | ` 120  0 ` |

Each can move its own subject: break bare `RETURN` and `lnrt-ctl` goes red; break
the empty-stack check and `lnrt-nogosctl` goes red; break `find_line_bc` and
`lnrt-undctl` goes red; break `CURLINE` at error time and `lnrt-erlctl` goes red.

### 3.2 R-T2 — the branch happens, and it pops exactly one frame

| row | program | refs | zb |
|---|---|---|---|
| `lnrt-line` | `10 GOSUB 40 : 20 A=A+20:END : 30 A=A+30:END : 40 RETURN 30` | ` 30  0 ` | ` 20  0 ` |
| `lnrt-back` | `1 GOTO 10 : 5 A=A+5:END : 10 GOSUB 40 : 20 A=A+20:END : 40 RETURN 5` | ` 5  0 ` | ` 20  0 ` |
| `lnrt-blank` | `… 40 RETURN 3 0` | ` 30  0 ` | ` 20  0 ` |
| `lnrt-trail` | `… 40 RETURN 30:A=A+7` | ` 30  0 ` | ` 20  0 ` |
| `lnrt-pop` | `… 30 A=A+30:RETURN : 40 RETURN 30` | ` 30  3 ` | ` 20  0 ` |
| `lnrt-depth` | `… 40 GOSUB 60:A=A+7:END : 60 RETURN 30` | ` 50  0 ` | ` 7  0 ` |

* `lnrt-pop` is the one that says the frame is **gone**: control reaches line 30
  (`A = 30`) and the bare `RETURN` there finds an empty stack (`ERR 3`). If the
  frame had survived it would have read ` 50  0 `.
* `lnrt-trail` says the branch is a **branch**: `A=A+7` after it never runs.
* `lnrt-blank` is free confirmation that D-LNREF's crunch is already right —
  `RETURN 3 0` reaches line 30, so the blank inside the line number is skipped
  (R-N1) and the `$0E` arrives intact.

### 3.3 R-T1 — the empty-stack check beats **both** other errors

`lnrt-nogos` alone cannot say this: its line 30 exists and its argument is well
formed, so "check the stack first" and "parse the argument first" both end at
`ERR 3`. The two rows that separate them:

| row | program | refs | zb | what it rules out |
|---|---|---|---|---|
| `lnrt-nogos` | `10 RETURN 30 : … : 30 A=A+30:END` | ` 0  3 ` | ` 0  3 ` | — |
| `lnrt-nogosbad` | `10 B=1:RETURN B : 20 A=A+20:END` | ` 0  3 ` | ` 0  3 ` | not `ERR 2` → the argument is not parsed first |
| `lnrt-nogosund` | `10 RETURN 99 : 20 A=A+20:END` | ` 0  3 ` | ` 0  3 ` | not `ERR 8` → the line is not resolved first |

This fixes the implementation's **order**, not just its outcome, and zerobas
already agrees on all three — so all three are MUST-NOT-MOVE controls.

### 3.4 R-T3 — a failed branch has already popped

| row | program | refs | zb |
|---|---|---|---|
| `lnrt-undef` | `10 GOSUB 40 : 20 A=A+20:END : 40 RETURN 99` | ` 0  8 ` | ` 20  0 ` |
| `lnrt-zero` | `10 GOSUB 40 : 20 A=A+20:END : 40 RETURN 0` | ` 0  8 ` | ` 20  0 ` |
| `lnrt-undefp` | `10 ON ERROR GOTO 50 : 20 GOSUB 40 : 30 A=A+3:END : 40 RETURN 99 : 50 A=A+50:RETURN` | ` 50  3 ` | ` 3  0 ` |

`lnrt-undefp` is the one that reads the *stack* rather than the outcome. The
handler is entered without a frame of its own, so its bare `RETURN` reports on
whatever `RETURN 99` left behind: `ERR 3` means the frame was **already popped**
when the undefined-line error fired. Had it survived, the handler would have
returned to line 30 and read ` 53  8 `.

`lnrt-zero` settles a question `RESUME` answers the other way: `RESUME 0` means
"re-run the erroring statement", but `RETURN 0` is an ordinary line lookup that
fails with `ERR 8`. There is no zero special case.

### 3.5 R-T4 — trailing junk is a syntax error, `:` is not

| row | program | refs | zb |
|---|---|---|---|
| `lnrt-bcolon` | `10 GOSUB 40 : 20 A=A+20:END : 40 RETURN:A=A+7` | ` 20  0 ` | ` 20  0 ` |
| `lnrt-var` | `… 40 B=30:RETURN B` | ` 0  2 ` | ` 20  0 ` |
| `lnrt-varp` | `…40 B=1:RETURN B : 50 A=A+50:RETURN` | *(§3.7)* | |

`lnrt-bcolon` is what stops R-T4 from being over-read: `:` after a bare `RETURN`
is a **terminator**, not an argument — control still returns to the caller
(` 20  0 `, and the `A=A+7` after it does not run). So the accepted argument
alphabet is exactly `{ <EOL>, ':', $0E }` and everything else is `ERR 2`.

### 3.6 R-T5 — the error is filed against the `RETURN`'s own line

| row | program | refs | zb |
|---|---|---|---|
| `lnrt-erlctl` | `… 20 GOSUB 40 : 40 ERROR 7 : 50 A=ERL:END` | ` 40  7 ` | ` 40  7 ` |
| `lnrt-erlund` | `… 20 GOSUB 40 : 40 RETURN 99 : 50 A=ERL:END` | ` 40  8 ` | ` 0  0 ` |
| `lnrt-erlvar` | `… 20 GOSUB 40 : 40 B=1:RETURN B : 50 A=ERL:END` | ` 40  2 ` | ` 0  0 ` |

🎯 **These two rows are a constraint on the implementation, not on the outcome,
and they are the reason the cheapest shape is wrong.** The obvious way to write
the branch is to reuse the existing pop — which writes `CURLINE := the CALLER's
line` — and then resolve the target. Under that shape the `ERR 8` above would be
filed against line **10**, and both references say **40**. A row reading only `A`
and `ERR` would have passed a build that reports the wrong line number to the
user in every `RETURN <line>` failure.

`lnrt-erlctl` pins that the instrument reads ` 40  7 ` for an ordinary error on
that same line 40, so ` 40  8 ` is a *difference* and not a number floating on
its own. zerobas reads ` 0  0 ` on both subject rows because it raises no error
at all: `RETURN` ignores its argument, control resumes at line 20 and falls into
line 30's `END`, so `A=ERL` never runs.

### 3.7 Does the **syntax** error pop as well? Yes — identically

| row | program | refs | zb |
|---|---|---|---|
| `lnrt-undefp` | `… 40 RETURN 99 : 50 A=A+50:RETURN` | ` 50  3 ` | ` 3  0 ` |
| `lnrt-varp` | `… 40 B=1:RETURN B : 50 A=A+50:RETURN` | ` 50  3 ` | ` 3  0 ` |

🎯 **This row was written to decide between two implementations, and it picked
the cheaper one — which is not the outcome to expect and is exactly why it was
measured.** Two shapes reproduce R-T4's ` 0  2 ` equally well:

* pop the frame, then hand the cursor to `GOTO`'s own parser, which branches on
  `$0E` and raises `ERR 2` on anything else — **pops on both errors**;
* check for `$0E` first and only pop on the branch — **pops on neither**.

The references read ` 50  3 `: the handler's bare `RETURN` finds an empty stack,
so `RETURN B` **had already popped** before it raised `ERR 2`. Had the frame
survived, the handler would have returned to line 30 and read ` 53  2 `. So the
syntax error and the undefined-line error behave identically, and the reference's
own structure is "pop, *then* parse the argument as a branch target".

That is one measurement standing between a faithful implementation and a
plausible one that happens to be 5 bytes more expensive.

---

## 4. What zerobas does today

`ex_return` ([`basic/program.asm:1369`](../basic/program.asm:1369)) pops the
frame and never advances `HL` past the `RETURN` token at all, so **every**
argument is invisible to it. That single fact explains all twelve divergent rows:
the branch never happens (` 20  0 ` where the reference branches), no error is
ever raised (` 0  0 ` on the `ERL` rows), and the frame is always consumed the
one way.

The crunch is **not** the problem and has not been since D-LNREF: `40 RETURN 30`
stores `<8E> <0E><1E><00>` byte-identically on all three sides
([`docs/lnref-msx1-characterization.md`](lnref-msx1-characterization.md) §1).
The `$0E` is sitting in the token stream, correct, unread.

---

## 5. 🔴 A byproduct: `RETURN` and an open `FOR` — and the first attribution was wrong

Found while testing something else entirely, and recorded here because the way it
was *mis*-diagnosed is the reusable part.

`lnrt-leak` exists to test the implementation's own justification (§4 of the
spec): `ex_return` pushes the token cursor before the empty-stack check and does
**not** pop it on the `ERR 3` arm, on the argument that `raise_error` resets `SP`
from `SAVSTK`. Two stray bytes are invisible; 200 of them are 400 bytes of stack.
The first version drove those 200 traps from a `FOR` loop:

```
10 ON ERROR GOTO 50 : 20 FOR I=1 TO 200:RETURN:NEXT : 30 A=A+3:END : 50 A=A+1:RESUME NEXT
        both references ->  5  0        zerobas ->  203  0
```

**I read that as a stack finding and it is not one.** Reading the screen rather
than the reading — [[read-the-screen-when-a-probe-fails]] — showed `I = 1` on the
reference: the loop never reached its second iteration, so the divergence is
about the `FOR` frame, not about `SP`. The row measured two things at once and
could report on neither.

I then filed the cause as *"an error trap destroys the reference's FOR frame"* —
MS-BASIC keeps FOR frames on the Z80 stack, which a trap unwinds — and wrote that
sentence into the probe. **Its own control refuted it within the hour.**
`lnrt-forerr` is the identical program with **one** variable changed, `ERROR 7`
in place of `RETURN`:

| row | line 20 | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `lnrt-forerr` | `FOR I=1 TO 3:ERROR 7:NEXT` | ` 103  0  4 ` | ` 103  0  4 ` | ` 103  0  4 ` |
| `lnrt-forret` | `FOR I=1 TO 3:RETURN:NEXT` | ` 102  0  1 ` | ` 102  0  1 ` | ` 103  0  4 ` |

An ordinary trap leaves the loop entirely intact on all three sides — three
iterations, `I = 4`. The variable is **`RETURN` itself**: MS-BASIC's `RETURN`
discards the `FOR` entries it walks past looking for a GOSUB frame, and with no
GOSUB frame at all that means the open `FOR`. zerobas keeps FOR and GOSUB on
**separate RAM stacks**, so nothing is walked past.

Architectural, nothing to do with `RETURN <line>`, out of scope, filed in
`TODO.md` and **pinned** (`lnrt-forret` → ` 103  0  4 `) with `lnrt-forerr`
standing next to it as the green control that did the refuting.

⚠️ **And the rebuilt `lnrt-leak` then answered its own question cleanly.** Driven
by a counter and a branch instead of a loop — 200 `RETURN`-without-`GOSUB` traps,
no `FOR` anywhere — it reads ` 204  0 ` on **all three sides**. The stray push is
harmless, measured rather than argued.
