# D-ONERR0 — what `ON ERROR GOTO 0` does INSIDE an active handler

*Measured 2026-08-09 at `0123dff`, `make onerr0-characterize`,
`probes/basic/basic_probe_onerr0.py`. Three sides: Philips VG-8020, National
CF-3300, zerobas repack.*

🎯 **BOTH REFERENCES AGREE ON ALL 24 ROWS.** Non-file rows throughout, so both
references are legitimate oracles everywhere — there is no one-reference
weakness in this battery.

⚠️ **Measured in FOUR rounds, and every round after the first came from
something other than the row set:** round 2 replaced a positive control that was
failing on all three sides (§3), round 3's `r.reexec` was demanded by a *design*
that had already been priced and looked like a bargain (§4), and round 4's
`c.resume0` was demanded by a *knife that reddened nothing* (§4.1).

---

## 1. The question, and why the filed row could not answer it

D-NXARY filed this rule on 2026-08-08 from **one** row that was measuring
something else ([`nxary-msx1-characterization.md`](nxary-msx1-characterization.md)
§3): its first `a.autodim` disarmed with `ON ERROR GOTO 0` before a `DIM`, both
references answered `NEXT without FOR`, zerobas answered `OK`, and the row read
as a clean three-side divergence while answering a question nobody asked.

🔴 **AND BY THE TIME ANYONE CAME BACK TO IT, THE ROW HAD ROTTED WITHOUT THE RULE
MOVING.** Re-measured in the 2026-08-09 staleness sweep
([`todo-staleness-sweep-2026-08.md`](todo-staleness-sweep-2026-08.md) §4.6) the
zerobas reading was no longer `OK` but `Redimensioned array in 60` — because
D-NXARY's *own* auto-DIM now creates `A(0..10)` at the `NEXT`, so the `DIM A(3)`
two lines later is a redimension. The swallow was intact; the row that reported
it was not.

**So every program in this battery is array-free.** The error is raised by
`ERROR n`, which no slice of the arrays arc can reach.

---

## 2. The rule, as measured

> **`ON ERROR GOTO 0` executed while a handler is ACTIVE disarms the handler and
> RE-RAISES the error that entered it, untrapped, immediately, reporting the
> ORIGINAL error's code and the ORIGINAL erroring line — without re-executing
> the statement that failed.**

Six clauses, and each one is a row that could have gone the other way:

| clause | the row that pins it | reading (both references) |
|---|---|---|
| it re-raises at all | `r.reraise` | `Out of memory in 20` |
| the ORIGINAL code, not a fixed one | `r.code` | `Subscript out of range in 20` |
| the ORIGINAL line, not the handler's | `r.line` | `Out of memory in 50` (handler is line 30) |
| immediately, not at end of statement | `r.mid` | `Out of memory in 20`, no `[AFTER]` |
| **without re-executing** the statement | `r.reexec` | `[X]` printed **once** |
| at any call depth | `r.depth` | `Out of memory in 20` from inside a `GOSUB` |

🎯 **AND THE SCOPE CLAUSE, WHICH IS THE ONE NOBODY HAD ASKED FOR.** `r.rearm`
arms a *different* line from inside the handler:

| row | program | all three sides |
|---|---|---|
| `r.rearm` | `40 ON ERROR GOTO 70` / `50 PRINT"[REARM]"` / `60 RESUME 80` / `70 PRINT"[RETRAP]"` / `80 PRINT"[DONE]"` | `[REARM]|[DONE]` |

**`ON ERROR GOTO <n>` inside a handler RE-ARMS and runs on.** So the rule is
about `GOTO 0` and *not* about `ON ERROR` — **disarming is special**. That is
what makes the fix a three-instruction test at the existing `oe_disable` arm
instead of a new branch in the `ON ERROR` parser, and it is a reading, not an
assumption.

### 2.1 What ends the handler state

Three rows say the rule is keyed on *being inside a handler* and not on *an
error having happened*, and all three are green on zerobas both before and
after the fix:

| row | shape | all three sides |
|---|---|---|
| `c.disarm` | `ON ERROR GOTO 0` **before** any error | `Out of memory in 30` (plain disarm) |
| `c.never` | `ON ERROR GOTO 0` with no handler ever armed | `[OK]` (a no-op) |
| `r.afterres` | `ON ERROR GOTO 0` **after** a `RESUME NEXT` left the handler | `[OK]` (plain disarm) |

### 2.2 `ERR` / `ERL` after the fact — and what `No RESUME` is

Read by typing `PRINT ERR;ERL` at the prompt the abort returns to.

| row | ending | `[ERR,ERL]` |
|---|---|---|
| `e.untrap` | ordinary untrapped abort at line 10 | `[ 7 , 10 ]` |
| `e.trap` | fell off the END of the handler | `[ 21 , 40 ]` |
| `e.reraise` | the re-raise | `[ 7 , 20 ]` |
| `e.disarm` | plain disarm, then an untrapped error | `[ 7 , 30 ]` |

🎯 **`No RESUME` IS AN ERROR, NOT A REPORT** — `e.trap` reads **21**, its own
code, and `ERL` moves to the handler's line. The brief asked this as an open
question; one row answers it.

🔴 **AND `e.reraise` AGREED FOR THE WRONG REASON BEFORE THE FIX.** zerobas read
`[ 7 , 20 ]` there *while swallowing the error entirely*, because `ERRFLG` and
`ERRLIN` were written at the original raise and nothing reset them. The `ERR`
half of the row was green on a tree that got the rule completely wrong; only the
error-text half (`[RANON]` vs `Out of memory in 20`) could see it. **A case that
agrees can agree for the wrong reason** — which is also, read forwards, the
proof that the re-raise must **not** re-record `ERRLIN`.

### 2.3 Direct mode

| row | shape | both references |
|---|---|---|
| `d.plain` | `ON ERROR GOTO 0` typed, no handler | no-op |
| `d.direrr` | a TYPED `ERROR 7` with a handler armed | **traps** into the handler |
| `d.instop` | handler SUSPENDED by `STOP`, then the disarm typed | `Out of memory in 20` |
| `d.dirtrap` | the ERRORING statement was itself typed | **bare** `Out of memory` |

🎯 `d.instop` is the only way to execute `ON ERROR GOTO 0` from inside a handler
in direct mode, and it shows **the rule holds there too**. `d.dirtrap` is its
mirror: when the erroring statement was the typed one, the re-raise names **no
line at all**. The two together are what say the reported mode is *derived from
the restored context*, not a constant — see §5.

---

## 3. 🔴 Round 2: a positive control that failed on all three sides

`c.resume` was drafted as `ON ERROR GOTO 40` / `ERROR 7` / `PRINT"[RESUMED]"` /
`RESUME NEXT` and read, identically on VG-8020, CF-3300 **and** zerobas:

```
[RESUMED]|RESUME without error in 40
```

`RESUME NEXT` lands on line 30, line 30 then **falls into** the handler, and a
second `RESUME` with no error active is ERR 22. Nothing about zerobas; the
fixture was wrong. **Classify a control failure by which side failed it** — red
on every side at once is a broken fixture, reported and scored as nothing
([[classify-a-control-failure-by-which-side-failed-it]]). Fixed by adding an
`END`, not by widening the expectation.

⚠️ It is the same two-sufficient-causes trap `basic/interp.asm`'s own D-DOTLINE
note records for `clp-trap` — same file, same idiom, re-derived because the
handler-falls-through shape is genuinely easy to write by accident.

### 3.1 🔴 And a readout that was blind on exactly the side under test

Every zerobas reading in the first full run carried its own later echoes:

```
zb='Out of memory in 10|ZBPRINT"[";ERR;",";ERL;"]"|[ 7 , 10 ] >> [ 7 , 10 ]'
```

`omsx_repl.screen_tail` ends its span at a row that **is** a prompt
(`PROMPTS = ("Ok", "ZB")`). On both references `Ok` sits alone on its line and
the span ends correctly. zerobas emits `ZB` with **no trailing newline**, so the
prompt and the next echoed line share one row, no row ever equals a prompt, and
the span ran to the bottom of the screen.

🎯 **So the readout was structurally blind on the one side it exists to
measure**, and it failed by making every row diverge — the loud direction, this
time. Clipped in the probe (`clip_at_prompt`) and not in `omsx_repl`: 24 gated
probes read that helper, and widening the shared span rule is its own slice with
its own denominator.

---

## 4. 🎯 Round 3: `r.reexec`, the row a REFUTED DESIGN demanded

Two mechanisms reproduce every reading in §2, and they are not the same
mechanism:

* **(a) restore-and-abort** — put `CURLINE`/`SAVTXT` back from `ERRRESUME` and
  jump into `raise_error` past `record_errline`;
* **(b) disarm-and-RESUME** — hand the erroring statement back to the run loop
  with the handler now disarmed, so it raises again *by itself*.

💰 **(b) IS 14 BYTES CHEAPER AND IT LOOKED LIKE A BARGAIN.** It gets `CURLINE`
and `SAVTXT` back for free by reusing `res_same`, the `CONT` point falls out
because the statement really did fail again, and — the part that made it look
decisive — **`DIRECTF` fixes itself**, because the run loop re-derives it at
`rp_exec`. It answers `d.instop` *and* `d.dirtrap`, which (a) cannot afford.
The whole fix would have been **+7 B**.

The only reading that can tell them apart is a statement that **outputs before
it fails**, because (b) runs it twice:

| row | program | both references | verdict |
|---|---|---|---|
| `r.reexec` | `20 PRINT"[X]";ASC("")` under a handler that disarms | `[X]\|Illegal function call in 20` | **`[X]` ONCE** |

🔴 **THE REFERENCE DOES NOT RE-EXECUTE THE STATEMENT IT RE-RAISES FROM.** Design
(b) is refuted, and it is refuted by a row that exists **only because the cheap
design was drafted first and its observable signature was asked for before it
was implemented**. Every other row in the battery answers (a) and (b)
identically — including all six clauses of §2, both negative controls and all
four `e.*` rows. Had the row set been frozen before the design, the cheap
design would have shipped and the battery would have been green.

---

## 4.1 🔴 Round 4: `c.resume0`, the row a KNIFE THAT REDDENED NOTHING demanded

The fix re-shares `res_ctx` with `RESUME` (spec §4.2), so a knife broke the
restore inside it and predicted the `c.resume` positive control would fail. It
reddened **nothing**, in both rounds.

🎯 **`RESUME NEXT` DOES NOT GO THROUGH `res_ctx`.** `res_next` marshals to a
sub-ROM tenant that does the identical prep sub-side. `c.resume` was the
battery's only `RESUME` row, so the shared routine this slice re-extracts had
**no coverage at all** ([[a-shared-engine-fix-must-measure-its-other-callers]]).

| row | program | all three sides |
|---|---|---|
| `c.resume0` | `10 ON ERROR GOTO 50` / `20 B=ASC(A$)` / `30 PRINT"[DONE]"` / `40 END` / `50 A$="Z":RESUME` | `[DONE]` |

Bare `RESUME` **re-executes the failing statement**, so the handler has to fix
the condition first or the program loops forever — which is the same fact
`r.reexec` measures from the other side, and it is why `RESUME` and the
re-raise cannot be the same mechanism.

## 5. Where zerobas stands

**Before the fix (`0123dff`): 13/23.** Ten rows diverged — `r.reraise`,
`r.code`, `r.line`, `r.mid`, `r.reexec`, `r.depth`, `e.reraise`, `k.cont`,
`d.instop`, `d.dirtrap`.

**After the fix: 24 rows, 22 scored, all 22 agreeing — and the 2 DEFERRED ones
printed with a price (§5.1).**

🔴 **`r.line` WAS AGREEING ON ITS ERROR TEXT FOR THE WRONG REASON, AND ONLY THE
PREFIX SAW IT.** Before the fix the row read:

```
vg8020='Out of memory in 50'   zb='[RANON]|Out of memory in 50'
```

The reference's `in 50` is the re-raise. zerobas's `in 50` is a *completely
fresh* error, raised when execution ran on past the disarm and re-entered line
50 with no handler armed. The message, the code and the line number all matched;
the only thing that separated them was the `[RANON]` the reference never prints.
A reading that had kept only the error text would have scored this row green
([[readout-blind-to-its-own-subject]]).

### 5.1 💰 The two deferred rows, priced

Both are the same missing piece, and they fail in **opposite directions**:

| row | zerobas after the fix | both references |
|---|---|---|
| `d.instop` | `Out of memory` | `Out of memory in 20` |
| `d.dirtrap` | `Out of memory in 0` | `Out of memory` |

The fix restores `CURLINE` and `SAVTXT` and aborts through `rerr_msg`, which
never passes `rp_exec` — and `rp_exec` is the **only** place that derives
`DIRECTF` from `CURLINE`'s high byte. So the mode cell keeps whatever the
*re-raising* statement had. 🎯 **That they fail in opposite directions is what
says the answer is a DERIVE and not a constant**: forcing `DIRECTF := 0` fixes
`d.instop` and breaks `d.dirtrap`; forcing 1 does the reverse.

💰 **Price: +7 B** — extract `rp_exec`'s six-instruction derive as a shared
`derive_directf` (+14 B routine, −13 B inlined, +3 B call back = net +4) and
`call` it from `oe_reraise` (+3). **Main page 1 has 0 B free after this slice**,
so it does not fit. Filed in `TODO.md` with this price. The −29 B `loc_next`
carve that would fund it belongs to its own slice
([`spec-basic-evalchk.md`](spec-basic-evalchk.md) §6.6) and is deliberately not
ridden along here.

---

## 6. The denominator

(WHICH error is re-raised: code 7 vs code 9) × (WHICH line it reports:
handler-before-error vs handler-after-error) × (WHEN: immediately vs end of
statement) × (WHICH `ON ERROR`: `GOTO 0` vs `GOTO n`, the disarm-is-special
discriminator) × (DEPTH: handler top level vs inside a `GOSUB` it called) ×
(HANDLER STATE: entered / left by `RESUME` / never entered / suspended by
`STOP`) × (MODE: stored vs direct, on both the disarm **and** the erroring
statement), plus `ERR`/`ERL` read at the prompt after four different endings —
which is also what says whether `No RESUME` is a report or an error — plus
`CONT` after the re-raise, plus the second-error-inside-a-handler rule that must
not move, plus the re-execution signature that separates the two candidate
designs.

**Six positive controls** (`c.untrap`, `c.trap`, `c.resume`, `c.resume0`,
`c.disarm`, `c.never`) and **two negative controls** (`r.nested`, `r.rearm`).

---

## 7. Provenance

Black-box only: BASIC typed into two reference machines and into zerobas, screen
output read back from VRAM. No reference ROM was disassembled or decoded; the
references are oracles — identical inputs in, observed outputs out. The rule in
§2 is stated from the readings above and from nothing else.
