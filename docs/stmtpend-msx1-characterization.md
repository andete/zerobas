# D-STMTPEND — where a pending error code goes to die

MSX1 characterisation, 2026-08-09. Sides: Philips VG-8020 (`vg8020`), National
CF-3300 (`cf3300`), zerobas repack (`zb`). Gate: `make stmtpend-acceptance`
([`probes/basic/basic_probe_stmtpend.py`](../probes/basic/basic_probe_stmtpend.py),
58 rows x 3 sides).

This is the notebook. The settled contract is
[`spec-basic-stmtpend.md`](spec-basic-stmtpend.md).

## 1. What was asked, and what it turned into

The item worked was D-TMFP's **defect 1**, restated by D-PENDERR
([`spec-basic-penderr.md`](spec-basic-penderr.md) §8): in
`Q2$=HEX$(0*(1/0)+(Q$<5))` a string-compare mismatch leaves the token cursor
short of the closing `)`, so `str_fn_radix`'s `cp ')'` fails and the function
bails through `str_arg_empty` without computing anything.

The trap attached to it was explicit: D-PENDERR had fixed the *other* defect, so
`r.hex`, `r.oct`, `r.str` and `PRINT HEX$(...)` are green on three sides **while
the cursor is still wrong**, and the expected honest outcome was "not observable,
here is the denominator, close the item".

**It is observable — 22 of 58 rows, on both references — and what makes those
rows divergent is not the cursor.**

## 2. The cursor, measured

No screen row can witness a token cursor. These readings come from freezing
zerobas at a ROM breakpoint and reading the machine.

### 2.1 Where the cursor lands

Breakpoint at `type_mismatch_set`; direct line `Q2$=HEX$(0*(1/0)+(Q$<5))` with
`Q$` already holding a string; dump `IX` and 64 bytes of `TOKBUF` ($EC00):

```
TOKBUF   51 32 24 ef  ff9b 28 11 f3 28 12 f4 11 29 f1 28 51 24 f0 16 29 29 00
         Q  2  $  =   HEX$ (  0  *  (  1  /  0  )  +  (  Q  $  <  5  )  )  .
offset    0  1  2  3   4 5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22

IX = $EC13 = TOKBUF+19  ->  $16, the digit token for `5`
```

The comparator has consumed the LHS `Q$` and the relop `<` and **stopped on the
RHS operand**. The coherent landing place is offset 20, the inner `)`.

The routine that leaves it there is `ers_rhs_mismatch`
([`basic/str-engine.asm`](../basic/str-engine.asm)): it restores the cursor
pushed at `ers_rhs`, and that push happened *before* `str_eval` was asked to read
the RHS — `str_eval` failing being precisely the condition on this path.
`evr_mismatch` ([`basic/expr.asm`](../basic/expr.asm), the symmetric `5 < A$`
form) restores the identical position for the identical reason.

⚠️ **The bare-LHS form is unaffected, and that is the control.** `HEX$(Q$)`
enters `ers_mismatch` directly, where IX is still the cursor from the relop
probe — on the `)` — and the function parses normally.

### 2.2 The tail is NEVER EVALUATED — the question §3.2 declined to answer

[`spec-basic-penderr.md`](spec-basic-penderr.md) §3.2 measured that after a
**type** first fault the second operand does not write a code, and said plainly
that the screen cannot separate *"the tail was not evaluated"* from *"it was
evaluated and did not fault"*. A breakpoint can. `penderr_set` is the single
writer; break there and read **A** on the FIRST hit:

| subject | first `penderr_set` call | reading |
|---|---|---|
| `Q2$=HEX$((Q$<5)+0*(1/0))` | **A = 4**, `str_arg_empty` | the division never ran |
| `Q2$=HEX$(1+0*(1/0))` (control) | **A = 2**, `fp_div` | it runs when nothing is stranded |
| `WIDTH (Q$<5)+0*(1/0)` | **never called at all** | the division never ran |
| `WIDTH 1+0*(1/0)` (control) | **A = 2**, `fp_div` | it runs when nothing is stranded |

**After a deferred type fault the rest of the expression is not evaluated.** The
stranded cursor is why: every layer of the precedence ladder above the comparator
finds a token that is not its operator and returns, and the enclosing `(` handler
finds a digit where it wants `)`.

### 2.3 ...and by itself it changes no reported code

Which is the trap the brief named. The references raise the type mismatch
**eagerly**, so they do not evaluate the tail either; `penderr_set` has been
set-if-empty since D-PENDERR, so whichever fault happened first is reported
whatever the cursor does. Across the whole `g.*` family — HEX$/OCT$, WIDTH,
LOCATE, PRINT, IF, DIM, an array lvalue, MID$, STRING$, OPEN, NEXT, SOUND,
ON..GOTO, POKE — all three sides agree, and agreed before this slice.

## 3. Where it IS observable — and the hole underneath it

A stranded cursor makes a well-formed statement look malformed. What happens next
depends only on whether that statement's driver ever reads the pending cell, and
**two places threw the code away**.

### 3.1 Mechanism E — `stmt_error` outranks a live code

Breakpoint at `stmt_error`, reading `FPERR` ($F069) and `ERRMARK` ($E010):

| row | statement | FPERR at `stmt_error` |
|---|---|---|
| `c.for.tm` | `FOR I=(Q$<5) TO 3:NEXT` | **$0A** (10, type) — live |
| `c.for.mt` | `FOR I=(5<Q$) TO 3:NEXT` | **$0A** — live |
| `c.poke.tm` | `POKE (Q$<5),0` | **$0A** — live |
| `c.forlim` | `FOR I=1 TO (Q$<5) STEP 1` | $00 |
| `c.scr.tm` | `SCREEN (Q$<5)` | $00 |
| `c.usr.tm` | `DEFUSR=(Q$<5)` | $00 |
| control | `FOR I=(1<5) TO 3:NEXT` | never reaches it |

The first three arrive with the fault still recorded, and `stmt_error` raises
ERR 2 straight over the top of it.

🔴 **AND THE FIRST ATTEMPT AT THIS READING WAS AN ARTEFACT OF THE INSTRUMENT.**
openMSX breakpoints are **address-only**. `stmt_error` lives at $4259, and the
disk ROM mapped at the same address during the boot slot scan fired every one of
them: all seven rows returned an identical capture with `FPERR` and `ERRMARK`
both $FF — read through a slot that was not RAM yet. Scheduling `debug set_bp`
at an emulated time *after* the program had been typed made the seven readings
distinct. The tell was the identity of seven captures that had no reason to
agree. §2's page-0 breakpoints (`type_mismatch_set` $2E86, `penderr_set` $2834)
are not ambiguous in this machine's slot layout, which is why those readings were
sound; the arming fix was applied to them anyway and reproduced them.

### 3.2 Mechanism S — `exec_stmt` DROPS the code, and needs no string at all

The other rows never reach `stmt_error` with anything live because `exec_stmt`
cleared the cell first. `exec_stmt` is where **every** driver ends
(`jp exec_stmt`), and its first act was an unconditional `ld (FPERR),a`. So a
driver that never calls `check_expr_errors` simply forgets:

| statement | zb (before) | vg8020 | cf3300 |
|---|---|---|---|
| `FOR I=0*(1/0) TO 3:NEXT` | ` 0 ` — **no error, loop runs** | ` 11 ` | ` 11 ` |
| `FOR I=0*(1E38*1E38) TO 3:NEXT` | ` 0 ` | ` 6 ` | ` 6 ` |
| `FOR I=0*SQR(-1) TO 3:NEXT` | ` 0 ` | ` 5 ` | ` 5 ` |
| `FOR I=1 TO 0*(1/0):NEXT` | ` 0 ` | ` 11 ` | ` 11 ` |
| `SCREEN 0*(1/0)` | ` 0 ` | ` 11 ` | ` 11 ` |
| `DEFUSR=0*(1/0)` | ` 0 ` | ` 11 ` | ` 11 ` |
| `DEFUSR=0*(1E38*1E38)` | ` 0 ` | ` 6 ` | ` 6 ` |

🔴 **Not one of these contains a string.** The cursor was the route that led
here; the hole is a plain missing read. Untrapped, `FOR I=0*(1/0) TO 3:NEXT`
printed no message at all and the program ran on to the next line — the
`u.for.dz` row read `[RANON]` where both references read
`Division by zero in 20`.

## 4. The measurement

**The before column was taken against the untouched tree at `bf0dab5`, with the
four base ROM hashes reproduced first** — a gate that is green on its first run
is the shape most likely to be blind (D-PENDERR §6).

| | scored | agreeing |
|---|---|---|
| before (`bf0dab5`) | 58 | **36** |
| after | 56 (+2 deferred) | **56** |

**Twenty rows moved, every one wrong -> right**, and none of the 36 already-green
rows moved. The two references agree with each other on **all 58**, so every row
has an oracle.

## 5. The knives — 4 cuts x 2 rounds, all eight EXACT

28-row subset (both predicted sets), zerobas-only column, byte-neutral cuts, four
ROM hashes asserted moved after every cut build.

| knife | cuts | predicted RED | result |
|---|---|---|---|
| K-SP1 | `exec_stmt`'s reader (restores the unconditional clear) | 11 | **EXACT** both rounds; the `s.*` rows fall to ` 0 ` and the `c.*` rows the boundary owns fall to ` 2 ` |
| K-SP2 | `stmt_error`'s check | 6 | **EXACT** both rounds; `e.*` and the three `c.*` rows that reach `stmt_error` live fall to ` 2 ` |
| K-SP3 | `record_errline`'s CONSUME | 24 | **EXACT** both rounds |
| K-SP4 | the cold-boot zero | **0 — a PREDICTED MISS** | 0 moved, hashes confirmed changed |

🎯 **K-SP3 IS THE ONE WORTH READING.** It reddens twenty-four rows, and
**`g.hex`, `g.hex.tm`, `g.wid`, `g.loc`, `n.dz.w`, `n.tm.loc` and `n.trap.res`
are among them — rows this slice did not touch and whose drivers were already
checking before it existed.** Without the consume, a trapped error re-raises at
the handler's own first statement with `ONEFLG` set, i.e. forced abort, and the
handler never runs: every trapped fault row in the gate returns `<NO CAPTURE>`.
That is the sharpest evidence that making the statement boundary a reader is not
a local change, and it is why the consume is part of the design rather than a
follow-up.

⚠️ **K-SP4's miss is stated in advance, not discovered.** openMSX zero-fills RAM,
so no emulator row can see the cold-boot store; the runner's four-ROM hash check
is what separates *"the cut reached the artifact and reddened nothing"* from
*"the cut never reached the artifact"*, and it reported the former.

## 6. Deferred, and filed

**Deferred (measured, not scored) — see [`spec-basic-stmtpend.md`](spec-basic-stmtpend.md) §5:**

* `c.line.tm` — `LINE (0,0)-((A$<5),1)`, ERR 5 here vs 13 on both references;
  reaches neither writer.
* `u.scr.dz` — `SCREEN 0*(1/0)` untrapped. zerobas prints the RIGHT message
  (`Division by zero in 20`, read directly off the name table) but `CHGMOD` has
  already run by the time the boundary raises, so the screen — including the
  `RUN` echo the reading anchors on — is reinitialised. **The statement boundary
  reports the right code at the wrong TIME.** The references never apply the
  mode.

**Filed, not folded in** (found while building the denominator, unrelated to
pending codes):

* `SCREEN (1<5)` (i.e. `SCREEN -1`) is `Syntax error` here and
  `Illegal function call` on the VG-8020 — SCREEN's range rejects go to
  `stmt_error` instead of raising ERR 5.
* `FIELD #(A$<5),1 AS Z$` is `Type mismatch` here and `Illegal function call`
  on the VG-8020.
* The cursor itself, deliberately unchanged — see
  [`spec-basic-stmtpend.md`](spec-basic-stmtpend.md) §2.
