<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Spec — Error handling arc (`ON ERROR`, `RESUME`, `ERR`/`ERL`, `ERROR n`)

Status: **S1 COMPLETE 2026-07-18 — D-1 (untrapped-error abort) + D-2 (`in <line>`)
BOTH LANDED.** S2 (trapping) is the next slice, its own spec. User go-ahead this
session. Two scoping decisions locked: the arc is sliced
**S1 foundation → S2 trapping** (§2), and the printed-message wording stays
**house-style plus an `in <line>` suffix**, with `ERR` codes reference-exact (§4,
§5.4). The four §9 open questions are resolved with their recommended defaults. The
empirical findings in §1/§3 are black-box observations on the reference oracle
(Philips VG-8020) — an allowed source. **Implementation is split within S1 for
risk-staging: D-1 first (the correctness fix), D-2 (message text) as a follow-up
(broader test-expectation blast radius).**

**D-1 landed (2026-07-18).** `fre_abort_low` (basic/arrays.asm) is now the single
abort funnel: it sets `ENDFLAG`, so the run loop's post-`call exec` check unwinds to
the REPL. All run-mode error sites `jp fre_abort_low` — aliased to `print_string` in
the lean build (interp.asm), so lean stays byte-identical. Self-funded: reusing
`print_crlf` for the fresh-line reclaimed more than the `ENDFLAG` cost (repack low
region 3→8 B free). Gate `error-acceptance` Family A **10/10 green** (all ten error
types abort, matching the reference); `unit-test` 46/46 (`test_str_compare` updated —
it had asserted the *old buggy* continue-after-error); float/math/string/input
ALL PASS; `array-acceptance` **150/150**. Notable: the `gc.bugB.phantom` GC
regression test's re-tune (Fable) revealed it was **already stale/vacuous** pre-D-1
— slice-4c dissolved the `$E240..$E268` STRTAB pool it seeded into, so it had been
seeding dead RAM; it now seeds the real next-descriptor slot via `VARPTR(A$)+6` and
is empirically non-vacuous.

Related specs: [`spec-basic-empty-expr-syntax-error.md`](spec-basic-empty-expr-syntax-error.md)
(the `check_expr_errors` deferred-error discipline this arc generalises),
[`spec-basic-float-core.md`](spec-basic-float-core.md) §10.2 (`fp_runtime_error`,
FPERR D-F2-1), [`spec-basic-arrays.md`](spec-basic-arrays.md) §4.1/§9.5 (the array
error surface + FPERR internal-code table this arc must reconcile).

**D-2 landed (2026-07-18) as a self-funding bolt-on riding D-1's single funnel —
the central `raise_error` dispatcher of §5.1–5.3 is DEFERRED to S2.** Because D-1
already funnels every run-mode error site through `fre_abort_low`, the suffix logic
went in that ONE place, not a 15-site refactor. New RAM `DIRECTF` ($E1C2, §5.5) =
1 direct / 0 run, written by `run_prog`/`ex_cont` (0) and `dispatch_line` (1) before
any statement runs (no cold-boot init; every run-loop entry traced). `fre_abort_low`
branches on it: direct → `jp print_string` (unchanged); run → `print_string_stopcr`
(message body up to the baked CR) + `print_in_lineno` (" in " + `CURLINE+2` line no.
via `ln_div_entry` + CRLF). `do_break`'s "break in <N>" tail is refactored (repack)
to share `print_in_lineno`; lean keeps its exact inline tail (byte-identical). This
was self-funded on the byte-full page 1 by sharing duplicate message strings in the
repack build via `equ` aliases (lean keeps its own, byte-identical): `"out of
memory"` ×3→×1 (~32 B) and `"illegal function call"` ×2→×1 (24 B, in the low region
where `fre_abort_low` needed it), plus `do_break`'s factored tail. Final free: page-1
2 B, low region 22 B; lean `basic.rom` byte-identical. Gates: `error-acceptance`
Family B (the `in <line>` structure) now green on zerobas (was RED by design);
`unit-test` 46/46 (`test_str_compare`'s 5 stored-mode `type mismatch` → `type
mismatch in 20`); array/string/float/math/input ALL PASS; `diskbasic-repack` 33/34
(the lone PRINT#-USING failure is the pre-existing harness injection flake). Empirical
VG-8020 differential: suffix + correct line across 9 error types, direct-mode no
suffix, multi-statement (`division by zero in 25`), and STOP/CONT (`break in 15` +
mid-line resume). **S2 reuses `print_in_lineno` unchanged and adds the `raise_error`
dispatcher (SAVSTK stack-reset, ERR/ERL, ON ERROR trap) — the §5.1–5.3 design, now
scheduled where trapping actually needs it.**

---

## 1. The finding that reframes the arc

Before any `ON ERROR` work, a differential probe (scratch `err_probe.py`, this
session) turned up a **foundational divergence**: an untrapped runtime error does
**not abort a running program** in zerobas — it prints the message and falls through
to the next line. Real MSX aborts the RUN and returns to the prompt.

Program (fatal error at line 20/25, marker `PRINT` at line 30), `RUN`:

| Program | Reference (Philips VG-8020) | zerobas repack today |
|---|---|---|
| `20 B=SQR(-1)` | `MARKA` → `Illegal function call in 20` → **`Ok`** (stops) | `MARKA` → `illegal function call` → **`MARKC`** (continues!) |
| `20 DIM Q(2):25 Q(9)=1` | `Subscript out of range in 25` → stops | continues to line 30 |
| `20 NEXT` (no FOR) | `NEXT without FOR in 20` → stops | continues |
| `20 RETURN` (no GOSUB) | `RETURN without GOSUB in 20` → stops | continues |

Two divergences:

* **D-1 (severe, correctness).** Untrapped errors don't abort the RUN. **Root
  cause** (static trace, confirmed): zerobas's error handlers (`stmt_error`,
  `fp_runtime_error`, `type_mismatch_error`, the `program.asm` family) print the
  message and `ret`. In *direct* mode that `ret` unwinds through `dispatch_line`
  back to the REPL — correct. In *run* mode the erroring statement handler was
  reached by a tail `jp` from `exec_stmt`, and `exec` itself was entered by
  `call exec` at `rp_exec` (`program.asm:246`); the deferred-error discipline
  (§5.3) means the `jp <error>` fires at the statement boundary with a shallow
  stack, so the handler's `ret` lands back at `program.asm:247`. The run loop then
  finds `ENDFLAG` clear and **advances to the next line**. Nothing sets `ENDFLAG`
  on error. So the program runs on.

* **D-2 (faithfulness, cosmetic).** No `in <line>` suffix; wording is house-lowercase
  (a deliberate earlier divergence — "don't copy MSX's verbatim text"). The
  reference appends `in <line>` **only in run mode** (direct-mode errors omit it —
  §3).

D-1 is a prerequisite for the whole arc: `ON ERROR` traps an error at the moment
the flow aborts — but zerobas has no such moment in run mode. S1 builds it.

---

## 2. Scope & slicing (locked)

**S1 — foundation (this spec, detailed; the sign-off target).** A single central
error dispatcher every error site funnels into with a numeric MSX error code; a
stack-reset (`SAVSTK`) so an error from any call depth unwinds cleanly to one
decision point; correct **untrapped-error abort** in run mode (fixes D-1); and
run-mode `in <line>` reporting (fixes D-2). **No new user-facing statements.** The
dispatcher records `ERR`/`ERL` state and checks the (still always-zero in S1)
`ON ERROR` vector, so S2 is a thin layer, not another refactor.

**S2 — trapping (this spec, §7 outline; its own detailed spec + sign-off later).**
`ON ERROR GOTO <line>` / `ON ERROR GOTO 0`; `RESUME` / `RESUME NEXT` /
`RESUME <line>`; the `ERR` and `ERL` functions; the `ERROR n` statement. All read
or drive the S1 dispatcher state.

Rationale for the split: S1 is a wide, invasive refactor (every error site) with a
sharply testable success criterion (does the run abort?) and real standalone value
(programs that hit an error now stop, faithfully). S2 is narrow and additive on top.
Risk-staging a wide refactor away from new language surface is the standing pattern
(cf. the arrays arc's slice-4b/4c split).

---

## 3. Target behaviour (black-box oracle, VG-8020)

All observed this session (`err_probe.py`, `err_probe2.py`), all black-box:

```
direct: PRINT SQR(-1)         -> "Illegal function call"           (NO "in N")
run:    10 PRINT SQR(-1):RUN  -> "Illegal function call in 10"     (WITH "in N")
```

`ON ERROR` end-to-end (S2, for reference — the S2 acceptance oracle):

```
10 ON ERROR GOTO 100
20 A=SQR(-1)
30 PRINT"AFTER"
40 END
100 PRINT"TRAP";ERR;ERL
110 RESUME NEXT
RUN
-> TRAP 5  20        (ERR=5 Illegal function call, ERL=20)
   AFTER             (RESUME NEXT resumed at line 30)
   Ok
```

Confirmed facts this pins:

* `in <line>` appears **iff** a program line is executing (run mode); direct mode
  omits it. The "current line" is the line the erroring **statement** is on
  (`Subscript out of range in 25` for the `25 Q(9)=1` case, not the `20 DIM`).
* The reference prints no leading `?` on the VG-8020 (so house-style "no `?`" is
  *already* reference-consistent here); wording otherwise stays house-style per the
  locked decision.
* `ERR` = 5 for Illegal function call, `ERL` = the erroring line's number; both are
  ordinary numeric values (PRINT renders ` 5 ` / ` 20 ` with sign-space).
* `RESUME NEXT` resumes at the statement **after** the one that erred.
* Any `RESUME` (all four forms: bare / `0` / `NEXT` / `<line>`) **resets `ERR` to 0
  but KEEPS `ERL`** — empirically pinned on the VG-8020 (a read after RESUME gives
  `0 / 20`, not `0 / 0`; ERL holds the last erroring line until the next error).
  Implemented as a 1-byte `ERRCODE` clear at `ex_resume`'s trap-active head (landed
  2026-07-19; see the S2b packet's ERR-reset follow-up). This corrected the S2b-
  deferred note's premise, which had guessed both cells reset.

---

## 4. The MSX error-code table

Source: the published **MSX-BASIC language reference** (allowed-sources.md line 110,
grade B — the user-visible language contract: keywords, functions, **errors**), and
**black-box-verified** per code in S2 via `ON ERROR GOTO h : <trigger> : h PRINT ERR`
on the reference (never by reading the reference ROM). The standard Microsoft/MSX
numbering, with the zerobas string + site each code funnels from today:

| ERR | MSX name | zerobas string (today) | Raised at (site) |
|----:|---|---|---|
| 1 | NEXT without FOR | `next without for` | `program.asm` `err_nofor` |
| 2 | Syntax error | `syntax error` | `stmt_error` / FPERR=4 |
| 3 | RETURN without GOSUB | `return without gosub` | `program.asm` `err_noret` |
| 4 | Out of DATA | `out of data` | `program.asm` `err_data` |
| 5 | Illegal function call | `illegal function call` | FPERR=3/8, `subromcall.asm` |
| 6 | Overflow | `overflow` | FPERR=1 (`err_overflow`) |
| 7 | Out of memory | `out of memory` / `Out of memory` | FPERR=6, `err_mem`/`err_stack` |
| 8 | Undefined line number | `undefined line` | GOTO/GOSUB target resolve |
| 9 | Subscript out of range | `Subscript out of range` | FPERR=5 |
| 10 | Redimensioned array | `Redimensioned array` | FPERR=7 |
| 11 | Division by zero | `division by zero` | FPERR=2 |
| 12 | Illegal direct | *(none yet)* | — (S2: statement illegal in direct mode) |
| 13 | Type mismatch | `type mismatch` | FPERR=10 / `type_mismatch_error` |
| 14 | Out of string space | *(none yet)* | — |
| 15 | String too long | *(none yet)* | — |
| 16 | String formula too complex | `String formula too complex` | str-engine temp overflow (FPERR=9) |
| 17 | Can't continue | `can't continue` | `program.asm` `err_cont` |
| 18 | Undefined user function | *(none yet)* | — |
| 19 | Device I/O error | (`load error` family) | tape/disk load |
| 20 | Verify error | `Verify error` | `cload.asm` `err_verify` |
| 21 | No RESUME | — | S2 (RESUME machinery) |
| 22 | RESUME without error | — | S2 (RESUME machinery) |
| 23 | Unprintable error | — | S2 (`ERROR n` with n outside the table) |

Codes ≥ 50 (`FIELD overflow`, `Bad file number`, disk errors …) are out of S1/S2
scope; the dispatcher's code domain is a full byte so they slot in later without
rework.

**Note — the existing FPERR internal codes are NOT the MSX ERR codes.** The
float/array deferred-error mechanism uses its own 1..10 numbering (float-core §10.2,
arrays §4.1: 1=overflow, 2=divzero, 3=illegal-fn, 4=syntax, 5=subscript, 6=oom,
7=redim, 8=illegal-fn-arr, 9=too-complex, 10=type-mismatch). S1 introduces a small
**FPERR→ERR map** at the single funnel point (§5.3); FPERR itself is untouched, so no
float/array/string code changes.

---

## 5. S1 design

### 5.1 The central dispatcher `raise_error`

New single entry point (working name `raise_error`), replacing the scattered
`jp stmt_error` / `jp fp_runtime_error` / direct-print sites. Contract:

```
raise_error:   ; in: A = MSX error code (1..23). Never returns to its caller.
  1. ld sp,(SAVSTK)      ; unwind any depth to the run/direct anchor (§5.2)
  2. ld (ERRCODE),a      ; ERR (read by S2; recorded now so S1 needs no second path)
  3. record ERRLINE      ; from CURLINE+2 if run mode, else the "direct" sentinel
  4. IF ONELIN != 0 AND not already in a handler:   ; S2 — always false in S1
        -> take the trap (jump to the ON ERROR line)
     ELSE:
        -> abort: print "<message>[ in <line>]" + CRLF, jp to the prompt anchor
```

In **S1** step 4's trap branch does not exist (`ONELIN` is always 0 — no statement
sets it yet); the code is structured so S2 adds only the trap branch + the
`ONELIN`/`ONEFLG` writers, not another refactor. The dispatcher is the *only* place
that reads the vector, resets the stack, and reports — the property that makes `ON
ERROR` a small addition.

### 5.2 `SAVSTK` — the stack anchor (fixes D-1)

The reason D-1 exists is that error handlers `ret` into whatever called them. The
real-MSX fix is a saved stack pointer: capture SP at the two flow anchors, and have
`raise_error` restore it so control returns to a **known** point regardless of call
depth.

* **Run anchor.** `run_prog` (`program.asm:189`) saves `ld (SAVSTK),sp` at entry
  (before the run loop). On abort, `raise_error` does `ld sp,(SAVSTK)` then jumps to
  a small tail that prints the message and returns to the REPL (equivalently: sets
  `ENDFLAG` and returns into the run loop's `ret nz`, which unwinds to `dispatch_line`
  → REPL). Either way the run stops — D-1 fixed.
* **Direct anchor.** `dispatch_line` (or `exec`'s direct entry) saves SP likewise, so
  a direct-mode error resets to the same clean point. Direct mode is already correct
  today; the anchor just makes the *one* dispatcher work identically for both.

`SAVSTK` must be re-saved on entry to each RUN and each direct line (cheap: one
`ld (SAVSTK),sp`). This is strictly more robust than today's implicit "the deferred
discipline keeps the stack shallow" invariant, and it is what lets an error raised
from *any* depth (e.g. a future non-deferred site) unwind correctly.

### 5.3 Funnelling the existing sites

Every current error site is rewritten to `ld a,<code>` + `jp raise_error` (or a
`call`-free tail). Two families:

* **Deferred (FPERR/TMISMATCH) sites** — `fp_runtime_error`, `type_mismatch_error`,
  `check_expr_errors`/`check_fperr_only` (interp.asm). These already realise the
  error at the statement boundary. `fp_runtime_error` today indexes `fre_msgtab` by
  FPERR; S1 replaces its tail with: map FPERR→ERR (small 10-entry table), then
  `jp raise_error`. The message text still comes from the current strings (house-style
  kept); `raise_error` selects the message from an **ERR-indexed** table (superset of
  `fre_msgtab`, reusing the same string bytes — no new strings, same low-region homes).
* **Direct-print sites** — `stmt_error`, and the `program.asm` family (`err_nofor`,
  `err_noret`, `err_data`, `err_cont`, `err_mem`, `err_stack`, `err_overflow`),
  `cload.asm` `err_verify`, GOTO/GOSUB undefined-line. Each currently does
  `ld hl,<str>` + `print_string` + `ret`. S1 rewrites each to `ld a,<code>` +
  `jp raise_error`. This is the bulk of S1's mechanical surface (~15 sites).

`ERRMARK` (the landmark byte at $E010) keeps its current meaning (tape/BLOAD markers
$EE, $DD) — orthogonal to `ERRCODE`; not touched.

### 5.4 Message table & `in <line>`

`raise_error` prints, in run mode: `<message>` then ` in ` then `CURLINE+2` as bare
unsigned decimal (reuse `ln_div_entry`, exactly as `do_break` prints "break in N"
— `program.asm:302`), then CRLF. In direct mode: `<message>` + CRLF only. The
message strings are the **existing** ones (locked decision: house-style, no churn of
current capitalization); S1 only re-homes the *dispatch* (an ERR-indexed pointer
table) and appends the suffix. The column-0 fresh-line rule (`fre_abort_low`,
arrays.asm — CRLF first if the cursor is mid-line) is preserved and applied uniformly.

### 5.5 RAM state (new)

Natural home: the **freed `VARTAB`/`STRTAB` window** — in the repack build the old
fixed pools are gone, leaving the VARTAB slot region `$E1C2..$E240` and the old
`STRTAB` window `$E240..$E268` free (~160 B, freed by arrays slices 4b/4c), *below*
the live 2-byte `ARYTAB` cell at `$E1C0` and clear of the still-live string scratch
`RVDESC`/`STRSCR` at `$E26A+`. Exact addresses pinned at impl time; the state is tiny:

| Cell | Size | Meaning | Set by |
|---|---|---|---|
| `SAVSTK` | 2 | stack anchor for `raise_error` unwind | run_prog / dispatch_line entry |
| `ERRCODE` | 1 | last error's MSX code (S2 `ERR`) | `raise_error` |
| `ERRLINE` | 2 | last error's line number, 0 = direct/none (S2 `ERL`) | `raise_error` |
| `ONELIN` | 2 | `ON ERROR` handler line addr, 0 = none (S2) | S2 `ON ERROR`; declared 0 in S1 |
| `ONEFLG` | 1 | 1 = inside a handler (S2 nested-error → forced abort) | S2 |
| `ERRRESUME` | 2+ | resume context (erroring CURLINE + stmt ptr) for `RESUME` (S2) | S2 |

S1 allocates/zeros `SAVSTK`, `ERRCODE`, `ERRLINE`, and reserves `ONELIN`/`ONEFLG`
(always 0 in S1) so the dispatcher's step-4 check compiles now. Cold boot + `clear_vars`
zero them.

### 5.6 Explicitly NOT in S1

`ON ERROR`, `RESUME`, `ERR`, `ERL`, `ERROR n` (all S2). `load_error` (the disk/tape
device-load path, ERR 19) keeps its own `ret`-based semantics for S1 — it is already
direct-mode-anchored and its "nested reject returns CF" contract (load-error-is-not-
abort memory) is delicate; folding it into `raise_error` is a deliberate S2-or-later
call, flagged in §9. `check_expr_errors`' existing behaviour is preserved (it already
routes to `fp_runtime_error`, which now tails into `raise_error`).

### 5.7 Empirical re-verification of commit 8c1b4a8 (2026-07-18, post-D-1)

Re-running the `INPUT#` mid-statement FP-error work (commit 8c1b4a8) against the
VG-8020 oracle post-D-1 (scratchpad `err_input.py` / `err_input_screen.py`, observable-
variable + screen capture) **confirms the fix is correct and non-vacuous after D-1**:
`INPUT#1+0*(1/0),B$` now raises `division by zero` and **aborts** (`A`=1, matching the
reference), where pre-D-1 it continued. The fix governs *ordering within the statement*
(the FP error is caught right after the channel-`eval`, before the field read),
orthogonal to D-1's *whole-RUN* abort — both are needed and both hold. This resolves the
task that re-verified 8c1b4a8 and corrected the stale "div-by-zero/overflow non-fatal"
wording in [TODO.md](../TODO.md) (that claim was a misread of the very D-1 bug).

The same differential surfaced **two adjacent gaps** (real divergences, but **not**
D-1 escapes — zerobas printed *no* error message in either, so nothing was *raised* for
D-1 to abort; both then fell through to the deliberately-deferred non-fatal `load_error`
of §5.6, which is why they continued). **BOTH FIXED + LANDED 2026-07-18:**

| case | reference | zerobas (pre-fix) | root cause | fix |
|---|---|---|---|---|
| `INPUT#99999*99999,B$` | `Overflow in N`, abort | `load error`, continues | channel-number **float→int coercion doesn't raise Overflow** — the channel `eval` used the bare `eval`, never coercing to the int domain | `eval_chan`: coerce a numeric channel via `fac_to_int_addr` (out-of-domain → FPERR=1) |
| `PRINT#1+0*(1/0),"x"` | `Division by zero in N`, abort | `load error`, continues | **PRINT#'s channel `eval` has no FPERR check** — the sibling of 8c1b4a8's INPUT# `check_fperr_only`, absent on the PRINT# path | `eval_chan`: `check_fperr_only` surfaces the deferred divzero |

**As landed:** both fold into one shared helper `eval_chan` (basic/float-arith.asm,
low region) = `eval` + (numeric-channel-only) `fac_to_int_addr` int coercion +
`check_fperr_only`, used by INPUT#/LINE INPUT# (basic/files.asm) and PRINT#
(basic/print.asm). A numeric channel now raises **Overflow** when out of int range
(gap 1) and surfaces a deferred **Division-by-zero** (gap 2); both then abort via the
D-1 funnel with the D-2 ` in <line>` suffix (verified: `overflow in 20` /
`division by zero in 20`, observable-var `A`=1). A **TMISMATCH** channel (`INPUT#A$`)
skips the coercion (guarded on `TMISMATCH`, since `type_mismatch_set` leaves `FACTYP`
untouched and a blind coerce on the hard-zeroed state could spuriously fault) and still
derails to `load error` — verified unchanged. This is a *targeted channel-eval*
coercion, not the broad D-F2-2 general-coercion change (that stays its own future item).
Byte budget: `eval_chan` is +17 B low region, but folding INPUT#'s `eval`+`check_fperr_
only` into one call *freed* 3 B on page-1 (net page-1 2→5 B free, low 20→3 B); lean
16 KB `basic.rom` byte-identical (all repack-only). Gates: unit 46/46, input / error /
string / float / math acceptance, array 150, diskbasic 34 (lean) + 34 (repack) all green.

---

## 6. S1 acceptance & gates

New probe `basic_probe_error_acceptance.py` (repack machine + VG-8020 differential),
asserting **abort semantics** and **`in N` reporting** — not verbatim wording (D-2:
differential asserts behaviour, house-style text differs by design). Cases:

* **Abort (uniform)**: for **all ten** error types reachable today (illegal-fn 5 /
  subscript 9 / next-without-for 1 / return-without-gosub 3 / redim 10 / type-mismatch
  13 / out-of-data 4 / undefined-line 8 / division-by-zero 11 / overflow 6) — the
  **observable-variable** design (line 10 `A=1`, error at line 20, line 30 `A=2`; after
  RUN a direct `PRINT A`): assert `A`=1 on **both** machines (the run aborted, line 30
  never ran). Robust (no marker-vs-echo disambiguation) and already locked green on the
  reference (all ten `A`=1) and red on zerobas today (all ten `A`=2 — the D-1 bug).
* **`in N`**: run-mode error carries ` in <lineno>` with the correct line (the
  *statement's* line, e.g. `in 25`); direct-mode error carries no suffix.
* **Multi-statement**: error mid-`:`-line reports the right line and aborts the line.

Standing gates that must stay green (S1 touches the shared error tails): `unit-test`,
`array-acceptance` (150), `input-acceptance` (16), `string-acceptance`,
`float-acceptance`, `math-acceptance`, `diskbasic-acceptance` (34), the tape battery,
`repack-boot`, and **lean `basic.rom` byte-identity** (the lean build must stay pinned;
if S1 needs new code that doesn't fit the lean 16 KB, the mechanism lives repack-only
like the arrays/float/string engines — see §8).

---

## 7. S2 outline (trapping)

> **Detailed S2 spec drafted (sign-off pending):**
> [spec-basic-error-handling-s2.md](spec-basic-error-handling-s2.md). The outline
> below is superseded by it; kept here for the at-a-glance summary.

* **`ON ERROR GOTO <line>`** — resolve `<line>` to an addr, store in `ONELIN`;
  `GOTO 0` clears it (`ONELIN`=0). `raise_error` step 4: if `ONELIN`≠0 and `ONEFLG`=0,
  set `ONEFLG`=1, save resume context, and branch to `ONELIN` (through the same
  `SAVSTK` reset). An error while `ONEFLG`=1 (error inside a handler with no RESUME)
  forces the abort path (real-MSX behaviour).
* **`RESUME` / `RESUME 0`** — retry the erroring statement; **`RESUME NEXT`** — the
  statement after it; **`RESUME <line>`** — a given line. Clears `ONEFLG`. Needs the
  §5.5 `ERRRESUME` context (the erroring `CURLINE` + statement pointer); the run loop's
  existing `RESUMEPTR`/`RESUMEFLAG` mid-line-resume machinery (program.asm:858) is the
  reuse vehicle. `RESUME` with `ONEFLG`=0 → `RESUME without error` (ERR 22).
* **`ERR` / `ERL`** — numeric functions returning `ERRCODE` / `ERRLINE` (expr.asm
  function tokens). Trivial once S1 records them.
* **`ERROR n`** — statement: evaluate the argument, then raise it. **Faithful domain
  = 1..255** (empirically pinned VG-8020): `ERROR 0`, `ERROR 256`, and any out-of-range
  value within int16 raise **ERR 5** (illegal function call); `1..255` raise that code
  verbatim (a code with no message string still prints `unprintable error`/ERR 23 but ERR
  = n, e.g. `ERROR 200`). `ex_error` rejects the full evaluated value (`D<>0` or `E==0`),
  not just the low byte (arg-validation landed 2026-07-19). *Boundary:* `|n|` overflowing
  int16 hits the separate D-F2-2 int-coercion seam (ref ERR 6 Overflow vs zb ERR 5).

S2 oracle = §3's `ON ERROR` transcript, extended per statement.

---

## 8. Space budget & the tenant question

The repack page-1 is **byte-full (0 B free)** after the arrays arc's last commit
(memory: `INPUT# mid-statement FP-error ordering`). S1 is net-additive (a new
dispatcher + ~15 rewritten sites + a map table). The rewritten sites mostly *shrink*
(each `ld hl,<str>` + `call print_string` + `ret`, ~7 B, becomes `ld a,n` +
`jp raise_error`, ~4 B — a ~3 B/site saving × ~15 ≈ 45 B reclaimed), which may fund
the dispatcher body. **Measure first** (the standing discipline; estimates run ~1.4×).
If it doesn't self-fund, the signed-off strategy applies: this is repack-only, and the
dispatcher body can live as a **sub-ROM page-0/1 tenant** (subrom-tenant-playbook.md),
exactly like the arrays/math engines — the glue (`ld a,n` + `jp`/`call`) stays in main,
the leaf goes to the tenant. The lean 16 KB build stays byte-identical (error handling
is repack-only Phase-3 surface, like every Phase-3 feature since the string engine).

**S1 does not decide the tenant question up front** — it is a measured outcome. The
spec's position: attempt self-funding in main first (the site-shrink likely covers it);
fall back to the tenant only if the byte count demands it.

---

## 9. Resolved decisions (were open questions; recommended defaults adopted)

1. **`load_error` unification (ERR 19) — DEFERRED to S2/later.** The disk/tape
   device-load error path keeps its own `ret`-based semantics in S1; its nested-reject
   CF contract (load-error-is-not-abort memory) is delicate, and it is already
   direct-mode-anchored. S1 does not touch it.
2. **Overflow/divzero are FATAL — uniform abort model (CORRECTED 2026-07-18).** An
   earlier note (and this spec's first draft) claimed the reference treats
   Overflow/Division-by-zero as *non-fatal* (RUN continues). **A definitive
   differential (`err_lock.py`, this session) falsifies that:** on the VG-8020 ALL ten
   reachable error types — including `B=1/0` (`Division by zero in 20`) and `C%=99999`
   (`Overflow in 20`) — **abort the run** (observable `A` stays 1; the run returns to
   `Ok`). The "continues" behaviour that was mistaken for a reference quirk was in fact
   **zerobas's own D-1 bug** (all ten continue on zerobas today, `A`=2). So there is
   **no non-fatal-error special case**: `raise_error` aborts (or traps) for every code
   uniformly. This simplifies S1. (Float overflow that stays *in* MSX's BCD range —
   e.g. `1E30*1E30`=1E60, representable — raises no error at all and is not an error
   case; only genuinely out-of-range/int-overflow raises `Overflow`.) See the §6 probe
   and the caveat in §9a below re: the `INPUT#` FP-ordering fix's premise.
3. **`ERRLINE` in direct mode — S1 records 0; exact sentinel pinned in S2.** The
   reference `ERL` after a direct-mode error is a large sentinel (commonly 65535); its
   exact value only matters once `ERL` is readable (S2), pinned black-box then.
4. **Message home — CONSOLIDATE behind one ERR-indexed table.** S1 rebuilds error-
   message dispatch as a single ERR-indexed pointer table (superset of `fre_msgtab`),
   reusing the existing string bytes at their current low-region homes. This is what
   makes `ERROR n` + message reuse clean in S2.

---

## 9a. Caveat — the `INPUT#` FP-ordering fix's stated premise was wrong

The last arrays-arc commit (`8c1b4a8`, `INPUT# mid-statement FP-error ordering`) is
documented (TODO.md + memory) as resting on "real MSX BASIC's own quirk that
Division-by-zero/Overflow are non-fatal (the RUN continues to the next statement)."
§9.2's differential shows that premise is **false** — those errors abort. The
behaviour that looked non-fatal was zerobas's D-1 bug. The *fix itself* (abort the
channel-number FP error before the field read) is plausibly still correct or a no-op
once S1 lands (S1 makes the whole statement abort the RUN, which subsumes "abort
before the field read"). **Action:** when S1 makes all errors fatal, re-run
`diskbasic-acceptance` (the `INPUT#` cases) and re-examine `8c1b4a8`'s behaviour
against the reference; correct its TODO/PROVENANCE wording. Flagged as a separate
follow-up (not S1-blocking); logged to the review queue / a background task.

## 10. Provenance

Clean-room throughout. Error-code numbering: published MSX-BASIC language reference
(allowed-sources.md line 110, grade B) + black-box `PRINT ERR` verification per code
(S2) on the reference machine — never reference-ROM disassembly. All behaviour in
§1/§3 is black-box observed (VG-8020 oracle, allowed-sources "black-box oracle",
grade A iff black-box). Message wording is zerobas's own house-style (kept; the
`in <line>` suffix + abort semantics are the only S1 output changes). To record in
`basic/PROVENANCE.md` on landing: "Phase 3: error handling S1 — central dispatcher +
untrapped-error abort + `in <line>`".
