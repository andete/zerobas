# D-STMTPEND — a fault that already happened outranks the rest of the statement

Settled contract. The measurement notebook is
[`stmtpend-msx1-characterization.md`](stmtpend-msx1-characterization.md); the
gate is `make stmtpend-acceptance`.

## 1. The rule

> **A pending error code outranks everything the statement does after it —
> including the statement simply finishing.**

zerobas defers expression faults: `penderr_set` records a code, the expression
yields a defined value, and a later reader turns the code into an error.
D-PENDERR made every *writer* set-if-empty, so the code that survives is the
FIRST fault. It did not make anything read the cell that was not already reading
it — and two places threw the recorded code away:

* **`exec_stmt`** cleared the cell unconditionally at the top of every statement.
  Since every driver ends in `jp exec_stmt`, that clear is where a fault raised
  by a driver which never calls `check_expr_errors` was silently discarded.
  `SCREEN 0*(1/0)`, `DEFUSR=0*(1/0)` and `FOR I=0*(1/0) TO 3` reported **nothing
  at all**; both references report `Division by zero`.
* **`stmt_error`** raised ERR 2 over a live code, so a statement whose own
  delimiter check failed reported `Syntax error` instead of the fault that had
  already happened — `FOR I=0*(1/0) STEP 2` on the numeric side, and every
  statement whose delimiter landed on a token a string-compare mismatch had
  stranded the cursor short of (`FOR I=(A$<5) TO 3`, `POKE (A$<5),0`).

## 2. How the slice got here, and why the brief's target is NOT the rule

The item worked was D-TMFP's **defect 1** (`TODO.md`): after a string-compare
mismatch the token cursor does not land on the closing `)`. D-PENDERR had already
made its only known symptom disappear, so the brief's own expectation was that
this would end in "unobservable, here is the denominator, close the item".

The cursor is real and is now **measured** rather than inferred — frozen at
`type_mismatch_set`, `IX` points at the RHS **operand**, not past it; frozen at
`penderr_set`, the first code written after `HEX$((A$<5)+0*(1/0))` is 4
(`str_arg_empty`) and never 2 (`fp_div`), which settles that the tail of the
expression is **never evaluated** — the question
[`spec-basic-penderr.md`](spec-basic-penderr.md) §3.2 explicitly declined to
answer. See the characterisation §2.

🎯 **BUT THE CURSOR IS A ROUTE, NOT THE RULE.** A stranded cursor makes a
well-formed statement look malformed; what happens then depends only on whether
that statement's driver reads the pending cell. Take the string out entirely and
the same two holes are still there: `SCREEN 0*(1/0)` needs no comparison to lose
a division by zero. **So the cursor is left exactly as it is** — straightening it
would need the mismatch path to consume an arbitrary trailing operand, which the
references never do either (they raise eagerly), and it would close none of the
`s.*` rows.

## 3. The design, and its price

Four stores, all in [`basic/interp.asm`](../basic/interp.asm). **+14 B of page 1
(62 -> 48), hand count EXACT**; the low region and both sub-ROM walls are
unchanged.

| site | change | B |
|---|---|---|
| `exec_stmt` | `ld a,(FPERR)` / `or a` / `jp nz,fp_runtime_error`, **replacing** the unconditional `ld (FPERR),a` | +4 |
| `record_errline` | `xor a` / `ld (FPERR),a` — CONSUME the code on the way out | +4 |
| `stmt_error` | `call check_expr_errors` before `ld a,2` | +3 |
| cold-boot hook | `ld (FPERR),a` (A already 0) | +3 |

🎯 **THE CLEAR IS FREE AT `exec_stmt`.** A is 0 on the fall-through exactly when
the cell already is, so the store the reader replaces was redundant — the reader
costs 4 bytes, not 7. The "cleared once per statement" invariant is unchanged; it
is now *proved* by the test rather than *imposed* by the store.

🔴 **AND THE CONSUME IS NOT OPTIONAL, WHICH IS THE PART THE FIRST SKETCH MISSED.**
With `exec_stmt` reading the cell, a TRAPPED error would re-raise: raise -> trap
-> handler line -> `exec_stmt` -> the same code is still there -> raise again,
now with `ONEFLG` set, i.e. forced abort, so the handler never runs. Putting the
clear in `record_errline` rather than in `raise_error` also covers
[`basic/arrays.asm`](../basic/arrays.asm)'s `e21_last` (`No RESUME`, ERR 21),
which reaches `record_errline` without going through `raise_error`. D-ONERR0's
re-raise entry `rerr_msg` deliberately skips `record_errline` and is correct to:
it is re-raising a code that was consumed the first time.

⚠️ **The cold-boot zero is load-bearing on hardware and invisible in emulation.**
`exec_stmt` used to clear the cell before anything read it; it now reads first, so
power-on RAM garbage would raise a bogus error out of the very first statement.
openMSX zero-fills RAM, so no emulator row can see this store — exactly like
`ld (DOT),hl` two lines away. Knife K-SP4 predicts **zero** red rows and says so
rather than letting a green run read as coverage.

## 4. What it measures

`make stmtpend-acceptance`, 58 rows x 3 sides (VG-8020, CF-3300, zerobas), the
two references agreeing with each other on **every** row.

| | scored | agreeing |
|---|---|---|
| before (`bf0dab5`, base ROM hashes reproduced first) | 58 | **36** |
| after | 56 (+2 deferred) | **56** |

**Twenty rows moved, every one wrong -> right**, and none of the 36 already-green
rows moved — including the whole `g.*` family (HEX$/OCT$, WIDTH, LOCATE, PRINT,
IF, DIM, an array lvalue, MID$, STRING$, OPEN, NEXT, SOUND, ON..GOTO, POKE),
which is what D-PENDERR shipped and what a fix in the wrong place would have
broken.

**Knives: 4 cuts x 2 rounds, all eight EXACT** (characterisation §5). K-SP3
(cutting the consume) reddens 24 rows, seven of them rows this slice did not
touch — the sharpest evidence that making the statement boundary a reader is not
a local change.

## 5. Deferred, with the reason

Two rows are measured and not scored.

* **`c.line.tm`** — `LINE (0,0)-((A$<5),1)` is ERR 5 here, ERR 13 on both
  references. It reaches neither of this slice's two writers: LINE raises its own
  `Illegal function call` eagerly from inside its coordinate parse. Closing it is
  a per-driver fix in `graphics.asm`.
* **`u.scr.dz`** — `SCREEN 0*(1/0)` untrapped. The trapped twin `s.scr.dz` now
  agrees (` 11 `), but the untrapped reading is unreadable on zerobas, and the
  reason is itself a finding: **the statement boundary reports the right code at
  the wrong TIME.** SCREEN has already run `CHGMOD` by the time `jp exec_stmt`
  raises, so the screen — including the `RUN` echo the reading anchors on — has
  been reinitialised. zerobas does print `Division by zero in 20`, measured
  directly off the name table; the references never apply the mode. An
  apply-then-reject ordering is a per-driver fix, and the statement boundary is
  by construction too late for it.

## 6. As-built

### 6.1 The walls — the hand count was EXACT

| wall | `bf0dab5` | as built | Δ |
|---|---|---|---|
| main low region | 14 B | **14 B** | 0 |
| main page 1 | 62 B | **48 B** | +14 |
| sub page 0 | 3604 B | **3604 B** | 0 |
| sub page 1 | 1483 B | **1483 B** | 0 |

ROMs: `basic-reloc d4bc0ca3`, `sub 5d7c837a`, `disk 2c630d3d`,
`zerobas-main-eu 192ffc9c`.

### 6.2 Corpus

Sequentially from clean (`rm -rf build`, **bash** — `zsh` does not word-split
`make $t`), **40 targets, all rc=0**: D-PENDERR §10.4's 39 plus
**`stmtpend-acceptance` (new)**.

`unit-test` **59/59** · `audit-citations` CLEAN · `preflight-check` **95
guarded / 0 unguarded** · `injector-check` **353** files (+1) ·
`rowshape-check` **24** probes (+1) · `latch-check` **16/16** · `deadcode`
**0/0 (+1 allowlisted)** · `penderr-acceptance` **61/61** ·
`tmfp-acceptance` **50/50** · `width-acceptance` **94/94** ·
`locarg-acceptance` **45/45** · `namspc-acceptance` **58/58** ·
`fldwidth-acceptance` **40/40 (+2 deferred)** · `onerr0-acceptance` **24/24** ·
`lnblank-acceptance REPEAT=2` **539/539** · `lnblank-say-acceptance`
**204/204** · `logicops-acceptance` **193/193** · `clearpool-acceptance`
**52/52** · plus the 20 remaining acceptance gates.

### 6.3 Comments this slice made stale, and did not leave standing

`exec_stmt`'s clear was cited as a FACT in five places, and two of them built a
falsifiability argument on it — `basic/field.asm`'s `tgt_parse_fld` and
`probes/basic/basic_probe_fldary.py` both say a cut is falsifiable *because*
"exec_stmt CLEARS FPERR ... so cutting this makes FIELD..A$(9) print OK". The
boundary is a reader now, so that reason no longer holds; the checks still earn
their place, because they raise BEFORE their driver's side effects, which the
boundary is by construction too late for (§5). All five were reworded.
🔴 **What has NOT been done is re-running K-FA5 to measure what the cut now
reads** — filed in `TODO.md` rather than predicted here.

## 7. Filed, not folded in

* `SCREEN (1<5)` (i.e. `SCREEN -1`) is `Syntax error` here and
  `Illegal function call` on the VG-8020 — `ex_screen`'s two range rejects
  `jp stmt_error` instead of raising ERR 5. Unrelated to pending codes; found
  while building the denominator.
* `FIELD #(A$<5),1 AS Z$` is `Type mismatch` here and `Illegal function call` on
  the VG-8020 — the reference classifies the CHANNEL before the expression.
* The cursor itself, deliberately unchanged (§2).
