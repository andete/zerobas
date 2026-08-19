<!-- Copyright (c) 2026 Joost Yervante Damad -->
<!-- SPDX-License-Identifier: 0BSD -->

# T-RUNAWAY — sweep `tests/` for rows that read RAM **after a runaway**

Status: **SIGNED OFF 2026-07-31** — §6 answered: harden the harness, invariant
**unconditional** (no escape hatch), **R3 included**. Item: [`TODO.md`](../TODO.md) ~line 2665,
filed 2026-07-30 by D-CONTR ([`docs/spec-basic-cont-record.md`](spec-basic-cont-record.md) §5.5).
Touches `tests/` only — **0 ROM bytes**, no `basic/` or `sub/` source, so the
walls (low 23 B, page 1 26 B free) are not in play.

---

## 1. The class, as filed

Any `msxtest` row that

* **(a)** calls a routine which can reach `ld sp,(SAVSTK)` — anything reaching
  `fre_abort_low`, `raise_error`'s abort arm, or the run loop — with `SAVSTK`
  unset in the zeroed host harness, so the funnel's tail `ret` pops from
  `$0000` and the CPU **runs away**; and
* **(b)** reads state **after** the call rather than at a trap; and especially
* **(c)** wraps the call in `try: … except: pass`, which converts *"the CPU ran
  away for 2,000,000 steps"* into *"the row passed"*.

One member was found — `test_poke.py`'s ERRMARK row — and fixed there
2026-07-30 by trapping `fre_abort_low` and sampling at the moment the row is
actually about. It had agreed **for the wrong reason for its whole life**; an
unrelated 19-byte page-1 shift moved where the runaway landed and it went red.

---

## 2. What was MEASURED this session — the DENOMINATOR

> 🔴 The filed recipe was a **grep** (`grep -n "except" tests/*.py`). A grep
> cannot measure this class, because **a runaway does not have to raise**: if it
> wanders into `PC=$FFFF` it hits `msxtest`'s sentinel and `call()` *returns
> normally*, with no exception to swallow and no `except` to grep for. The
> denominator therefore needs an instrument, not a pattern match.

### 2.1 The instrument

Measurement-only, never committed (scratchpad `sitecustomize.py`, auto-imported
via `PYTHONPATH`, patches nothing in the repo). It wraps `Z80.step` and
`msxtest.Machine.call` and records, for **every** `call()` the suite performs:
entry point, step count, **minimum and maximum SP reached during the run**, SP
at exit, and any exception. Nested frames (the sub-ROM bridge calls `call()`
recursively) each get their own min/max and propagate into the parent, so an
inner excursion cannot be lost by a reset.

Two detectors:

* **SP-lost** — `min_sp < $8000` (SP below the RAM base ⇒ SP was loaded from
  uninitialized memory: the `ld sp,(SAVSTK)`-with-`SAVSTK`=0 signature) or
  `max_sp > $F380` (SP popped past the harness's own frame).
* **unbalanced return** — `call()` returned but `exit_sp ≠ $F380`.

### 2.2 Coverage of the instrument — total, and checked

`grep -n "\.step(\|cpu\.pc *=" tests/test_*.py` → **0 code sites** (one comment
in `test_usr.py`). No test drives the CPU itself; **every** instruction the
suite executes runs inside `Machine.call`, so wrapping `call()` sees everything.

### 2.3 The numbers — AS-RUN, whole suite, 2026-07-31

| quantity | measured |
| --- | --- |
| test files | **54** (all green) |
| files that execute Z80 at all | **53** (`test_msgenc.py` is a pure ROM-table reader — 0 calls) |
| `Machine.call()` invocations | **5606** |
| **SP-lost** | **0 / 5606** |
| **unbalanced return** | **0 / 5606** |
| exceptions out of `call()` | **0 / 5606** |
| lowest SP any call reached | **`$F326`** — a 90-byte excursion below the harness stack base `$F380` |
| highest SP any call reached | **`$F380`** (exactly the base; never past it) |
| distinct `exit_sp` values | **`$F380`, and only that** |

The `except` first pass, for the record: **3** textual `except` in 54 files, of
which **0 swallow a call** — `test_msgenc.py:98` is `except ValueError` around
a symbol-file parse; `test_stmt_dispatch.py:342` catches `RuntimeError` and
**reports it as a failure** (the correct pattern); `test_poke.py:118` is a
comment. Exactly **one** test traps an abort funnel: the repaired poke row.

**Conclusion: the class is EMPTY today — 0 of 5606 calls, 0 of 54 files.** The
poke row was the only member, and it is fixed.

### 2.4 🔴 A detector whose green state is "found nothing" is a claim — CANARY RUN

Per [[apparatus-is-part-of-the-measurement]] and [[deadcode-gate]], the zero
above is worthless until the detector is shown to **cut**. Falsified by
reconstructing a synthetic member of the class (scratchpad `canary.py`: the
pre-fix poke row verbatim in shape — `do_poke` with a comma-less stream,
exception swallowed, `ERRMARK` read after):

```
canary: swallowed RuntimeError: runaway: 2000001 steps, PC=0xe1c6
canary: ERRMARK read AFTER the call = 0xdd (the row asserted $DD); final SP=0x09bc
instrument: {"entry": "do_poke", "min_sp": 0, "exit_sp": 2492,
             "raised": "RuntimeError: runaway: 2000001 steps, PC=0xe1c6"}
```

`min_sp = 0` — the detector sees the class in its purest form. And note the
canary's own reading: **`ERRMARK` = `$DD`, the value the old row asserted.**
Alone on the D-CONTR build the same read gave `$3A`, after the four preceding
POKE cases `$DB`. The wrong apparatus still reproduces the "right" answer some
of the time — [[err21-no-resume-slice]]'s F3 lesson, in the test layer.

---

## 3. What this session should therefore DELIVER

The sweep's product **cannot** be "fixed N rows" — N is 0. Reporting "swept,
nothing found" and closing the item would leave the situation that produced the
defect completely intact: the harness still lets SP go to `$0000` and then burns
2,000,000 steps before saying anything, and what it finally says
(`runaway: 2000001 steps, PC=0xe1c6`) **names the symptom, not the cause** — a
future reader gets the arbitrary landing address, not `ld sp,(SAVSTK)`. That is
precisely how the poke row survived: the guard fired every single run and the
message was uninformative enough to be worth swallowing.

So: turn the one-off detector into a **permanent harness invariant**, so that a
new member of the class is impossible to write silently.

### 3.1 `tests/msxtest.py` — SP-band invariant inside `call()`

In `call()`'s existing step loop, after each `cpu.step()` (and after the
trap-path `cpu.pop()`), assert SP is inside the band the harness owns:

```
$8000  ≤  SP  ≤  sp0          sp0 = the SP call() itself established
                              ($F380, or the caller's SP when keep_sp=True)
```

Measured headroom (§2.3): the whole suite lives in `$F326…$F380`, so the floor
is 29 KB clear of the deepest real use — it cannot fire on legitimate nesting.
Violation raises `StackLost`, a **subclass of `RuntimeError`** so that
`test_stmt_dispatch.py:342`'s existing handler keeps turning it into a reported
failure rather than an unhandled traceback. The message names the cause, the
call, the PC, and the fix:

```
StackLost: SP left the harness band [0x8000,0xf380]: SP=0x0000 at PC=0x76a4,
step 3129 of call('do_poke'). The routine loaded SP from uninitialized RAM --
almost always `ld sp,(SAVSTK)` with SAVSTK=0 in this zeroed harness (the abort
funnel). Anything this row reads AFTER the call measures a RUNAWAY, not the
routine: trap the funnel (fre_abort_low / raise_error) and sample THERE.
See docs/spec-tests-runaway-sweep.md.
```

Cost per step: one range compare, no extra function call. Timing is a gate
row (§5), not an assumption — baseline `make unit-test` = **18.2 s** as measured
this session.

**No escape hatch — the invariant is unconditional** (signed off 2026-07-31).
A future test that legitimately models a real `SAVSTK` unwind has to edit the
harness, which is maximally visible; 0 tests need it today. An `sp_guard=False`
keyword was rejected as an off-switch that could be reached for instead of
understood — a defaulted knob is exactly how 18 of 54 files came to test the
lean cart ([[lean-retire-s3-gates]]). Note that a test setting `SAVSTK` to a
*plausible* stack (≥ `$8000`, ≤ `sp0`) passes the band naturally, so honest
modelling is not blocked in the first place.

### 3.2 `tests/test_harness_guard.py` — NEW, the canary that keeps the guard honest

An invariant whose green state is "nothing found" rots
([[deadcode-gate]]: *an allowlist that must keep matching is a control; one that
only suppresses is rot*). Three rows, so the guard cannot be weakened silently:

* **R1 — the knife.** Poke 4 bytes of Z80 into RAM: `ld sp,($F000)` (`ED 7B 00
  F0`) with `$F000` holding `$0000`, then `ret`. `call()` **must** raise
  `StackLost`, and must raise it **early** — the row asserts the step count is
  ≪ 2,000,000, i.e. the failure comes from the new invariant and not from the
  old runaway guard. ROM-independent: it tests the *harness*, which is the
  subject.
* **R2 — the GREEN control.** A poked `ret` (and one real routine call) must
  pass, returning with `exit_sp == $F380`. Without R2, R1 alone is satisfied by
  a guard that fires on everything.
* **R3 — the class member in situ.** `do_poke` with a comma-less stream and the
  funnel **not** trapped — the exact D-CONTR case — must now raise `StackLost`
  instead of running away. This is the row that would catch someone deleting
  `test_poke.py`'s `fre_abort_low` trap. Knowingly coupled to `poke.asm`'s error
  path; if that path stops reaching the funnel the row fails loudly, which is
  the correct outcome for a characterization row.

### 3.3 Explicitly NOT in this slice

* No change to the 2,000,000-step guard's threshold. It stays as the backstop
  for genuine infinite loops that keep SP sane.
* No ROM source change; no `probes/` change. The probe layer boots a real
  machine where `SAVSTK` is initialized — the class does not exist there.
* Not chasing the subtler cousin *"trap fires, RETs, execution continues, row
  samples later"*: measured at exactly **one** funnel-trapping test (§2.3), and
  in that one the trap is reached by `jp` with no intervening frame, so the RET
  goes straight to the sentinel. Nothing to sweep.

---

## 4. Falsification — AS-RUN 2026-07-31, each a real edit to the code under test

| # | knife | prediction | **AS-RUN** |
| --- | --- | --- | --- |
| **F1** | Delete both band checks from `call()` | R1 + R3 RED, R2 green | ✅ **as predicted.** R1 `got plain RuntimeError instead: runaway: 2000001 steps, PC=0x1fd5`; R3 `only the 2M runaway guard fired … PC=0xe1c6` — *the filed landing address, reproduced*. R2 green on the same build |
| **F2** | Restore the checks, drop the floor to `$0000` | R1 + R3 RED — the *floor* is load-bearing | ✅ RED, **but not by the predicted mechanism for R3**: see §4.1 |
| **F3** | Restore the floor, raise the ceiling to `$FFFF` | R1/R3 stay GREEN — the ceiling is not what catches this class | ✅ all four rows green, 325 steps / `SP=$0000` unchanged. The **floor** is what catches it |
| **F4** | `StackLost(Exception)` instead of `StackLost(RuntimeError)` | `test_stmt_dispatch.py` stops reporting it as a failure | ✅ measured, and the answer is **narrower than the prediction**: see §4.2 |
| **F5** | Restore everything | all 55 files green | ✅ `make unit-test` **ALL 55 TEST FILE(S) PASSED**, 17.8 s |

Every red row was taken with the R2 green control on the same build, per
[[apparatus-is-part-of-the-measurement]] (*a red falsification reads as SUCCESS —
pair it with a GREEN control*).

### 4.1 🔴 F2: the ceiling caught R3 twelve steps later — and only an ORACLE-LOCKED row could tell

With the floor at `$0000`, R3 did go red, but the exception was
`StackLost SP=0xFFFE at PC=0x775f, 337 steps`, not `SP=$0000` at 325. The
runaway had continued past the lost `ld sp,(SAVSTK)` and **pushed at `SP=0`,
wrapping to `$FFFE`**, which tripped the *ceiling*. So the two halves are not
floor-catches-everything + dead ceiling: the ceiling is a real backstop, twelve
steps behind the floor.

**The lesson is about the row, not the band.** R3 asserts `e.sp == 0x0000` — the
*cause*. Had it asserted only *"`StackLost` was raised"*, **F2 would have read
GREEN and scored the floor as unnecessary**, and the invariant would have shipped
catching this class 12 steps late, by a wrapped stack pointer, with a message
pointing at the wrong address. That is [[err21-no-resume-slice]]'s F6 —
*a green falsification is a claim about the PATCH first* — and
[[vacuous-gate-row-steers-not-just-misses]]'s `want=`, both landing in the test
layer: **the oracle-lock is what made the knife visible.**

### 4.2 F4: the `RuntimeError` base is not what makes it LOUD

Measured on a reproduction of `test_stmt_dispatch.py:342`'s handler shape
(`except RuntimeError as e: fails.append(…); continue`) over three cases:

* `StackLost(RuntimeError)` → `reported=['case 0: StackLost', 'case 1: …', 'case 2: …'] cases_reached=3/3`
* `StackLost(Exception)` → uncaught traceback on case 0, exit 1, **cases 1–2 never ran**

Both go red, so the prediction *"no longer reports it as a failure"* is right in
letter but the base class is **not** load-bearing for loudness — `run.py` sees a
nonzero exit either way. What it is load-bearing for: the rest of the file keeps
measuring, and the failure is reported in the test's own vocabulary instead of a
traceback. Kept, on that narrower ground.

---

## 5. Gates — AS-RUN 2026-07-31

* **`make unit-test` → `ALL 55 TEST FILE(S) PASSED`** (54 existing +
  `test_harness_guard.py`). Per-file breakdown diffed against the baseline run:
  **identical, with `test_harness_guard.py` inserted** — checked by name, not by
  count.
* **Timing**: **18.30 s** vs the **18.16 s** baseline measured this session
  (and 17.80 s on the F5 re-run — inside the noise). The per-step range compare
  is free, and that figure *includes* the new file's own `pasmo` run. No hoist
  needed.
* **§2 instrument re-run on the patched harness**: **5610 calls** (5606 + the new
  file's 4), SP band and `exit_sp` unchanged, and the **only** detections are the
  two deliberate ones in `test_harness_guard.py` (R1 at step 1, R3 at step 325,
  both `SP=$0000`, both `StackLost`). The pre-existing 5606 calls are untouched:
  the invariant changed no test's behaviour.
* **No ROM source changed** — `git status` is exactly
  [`docs/spec-tests-runaway-sweep.md`](spec-tests-runaway-sweep.md),
  [`tests/msxtest.py`](../tests/msxtest.py),
  [`tests/test_harness_guard.py`](../tests/test_harness_guard.py). Nothing was
  rebuilt (the unit layer assembles to `/tmp`), so `build/basic.rom` and
  `build/sub.rom` are untouched and **no ROM gate is due**: the acceptance set
  (error-trap 126/126, abort 49/49, diskbasic 34/34, …) measures nothing that can
  have moved. **0 ROM bytes; the 23 B / 26 B walls are unmoved.**

---

## 6. Sign-off — ANSWERED 2026-07-31, before implementation

1. **Is "the class is empty, so harden the harness" the right product?** —
   **YES, harden.** 0 members is a fact about today's tests, not about the
   harness that permitted the defect.
2. **`sp_guard=False` escape hatch?** — **NO.** Unconditional. An off-switch can
   be reached for instead of understood; a test that legitimately models a real
   `SAVSTK` unwind passes the band as it stands (§3.1).
3. **R3's coupling to `poke.asm`?** — **INCLUDE R3.** It preserves the D-CONTR
   case from the other side and would catch the removal of `test_poke.py`'s
   `fre_abort_low` trap.

---

## 7. What this slice is worth — and what it is not

**Not** "3 rows fixed": zero rows needed fixing. What changed is that the class
can no longer be *written* silently. Concretely, on the one real path that
reaches it (R3), the failure moved from

* `runaway: 2000001 steps, PC=0xe1c6` — arbitrary, 2,000,001 steps late, naming
  a symptom, and *worth swallowing*, to
* `SP left the harness stack band [0x8000,0xf380]: SP=0x0000 at PC=0x3d4a, step
  325 of call('do_poke')` + the cause + the fix — **6,154× earlier**, at the
  `ld sp,(SAVSTK)` itself.

The first message is why the poke row's `except: pass` looked reasonable for
years. The second one is not swallowable with a straight face.

Two things this slice did **not** change and deliberately leaves standing: the
2,000,000-step guard (still the backstop for honest infinite loops that keep SP
sane), and `test_stmt_dispatch.py:342`'s `except RuntimeError` — which is the
*correct* pattern, because it reports rather than swallows.
