# D-ONERR0 — `ON ERROR GOTO 0` inside an active handler RE-RAISES

*Landed 2026-08-09 on `0123dff`. Measured in
[`onerr0-msx1-characterization.md`](onerr0-msx1-characterization.md), 24 rows,
three sides, both references agreeing on every one.*

---

## 1. The reading, taken before anything was designed

```basic
10 ON ERROR GOTO 40
20 ERROR 7
30 PRINT"[NO]"
40 ON ERROR GOTO 0
50 PRINT"[RANON]"
```

| side | before this slice |
|---|---|
| VG-8020 | `Out of memory in 20` |
| CF-3300 | `Out of memory in 20` |
| zerobas | `[RANON]` |

The reference never reaches line 50. zerobas disarmed and ran on — an untrapped
error that never surfaced, the same shape as a swallowed one.

## 2. What is wrong, in one sentence

`ex_on_error`'s `oe_disable` arm treated `ON ERROR GOTO 0` as a pure state
write (`ONELIN := 0`, `ONEFLG := 0`) and continued the line, so an error that
had entered a handler could be discarded by disarming.

## 3. Scope

### 3.1 The rule is about `GOTO 0`, and that is MEASURED

`r.rearm` executes `ON ERROR GOTO 70` from *inside* a handler and reads
`[REARM]|[DONE]` on all three sides: it **re-arms and runs on**. So the
re-raise belongs to the disable arm alone, not to `ON ERROR` as a statement.
This is the single fact that keeps the fix at one branch in code that already
exists, and it is a reading rather than an assumption — it is also carried as a
standing **negative control**, because a fix keyed on `ON ERROR` would redden it.

### 3.2 What the slice does NOT touch

* **A second error inside a handler.** Already a forced abort with the INNER
  message on all three sides (`r.nested`), via `raise_error_hl`'s `ONEFLG != 0`
  arm. Unchanged, and carried as the other negative control.
* **`RESUME` in any form.** `res_same`'s behaviour is byte-identical; only its
  *packaging* changes (§4.2).
* **`No RESUME` (ERR 21).** Measured here (`e.trap`: `ERR` = 21) but already
  correct; D-ERR21 owns it.
* **`ERRLIN` / `ERR` semantics.** The re-raise deliberately does not re-record
  them (§4.3).

## 4. Design

### 4.1 🔴 THE CHEAP DESIGN WAS REFUTED BY A ROW WRITTEN TO REFUTE IT

Two mechanisms reproduce the whole of §1:

* **(a) restore-and-abort** — put `CURLINE`/`SAVTXT` back from `ERRRESUME` and
  abort;
* **(b) disarm-and-RESUME** — hand the erroring statement back to the run loop
  with the handler disarmed, so it raises again by itself.

💰 **(b) costs +7 B and (a) costs +16 B**, and (b) additionally answers the two
direct-mode rows (a) has to defer, because returning through `rp_exec` re-derives
`DIRECTF` for free. On price alone it wins outright.

🔴 **It is wrong.** (b) re-executes the failing statement, so a statement that
outputs *before* it fails outputs twice. `r.reexec` puts
`PRINT"[X]";ASC("")` under a disarming handler and both references print `[X]`
**once**. The reference restores context and aborts; it does not re-run.

⚠️ **Every other row in the battery answers (a) and (b) identically** — all six
clauses of the rule, both negative controls, all four `ERR`/`ERL` rows and the
`CONT` row. The row that decides it exists only because the cheap design was
drafted first and asked what its observable signature would be
([[a-priced-decline-is-a-claim-about-a-design]]).

### 4.2 🎯 `res_ctx` — a routine that was shared, was inlined, and is shared again

`basic/interp.asm` carried this comment at `res_same`:

> *"Formerly a shared `res_ctx` (called from here AND the `RESUME <line>` arm);
> inlined now that this is the only remaining site that needs `CURLINE`
> restored."*

This slice is the site that makes that false. The re-raise needs the identical
restore — `ONEFLG := 0`, `CURLINE :=` the erroring statement's line, `HL :=` its
text pointer — because the reference reports the **erroring** line (`r.line`:
handler at 30, error at 50, message `in 50`) and a later `CONT` resumes at the
**erroring** statement (`k.cont`). Re-extracting it costs +4 B and saves 6 B at
the new caller, a net −2 B against inlining, and it is what let the fix land
inside the wall at all.

⚠️ The `RESUME <line>` arm still does **not** come here: it needs `ONEFLG := 0`
and nothing else (`rp_goto` sets `CURLINE` from `GOTOTGT`), so it keeps its own
4-byte pair rather than paying for a restore it would discard.

### 4.3 `rerr_msg` — a label, zero bytes

The re-raise enters `raise_error` **past** two things:

* the `ld (ERRFLG),a` store — the code is already the one being re-raised;
* `call record_errline` — which would rewrite `ERRLIN` and `DOT` from the line
  the re-raise is *in*.

`e.reraise` measures `ERR`/`ERL` after the re-raise as the original `7 / 20`, so
skipping the record is **the behaviour**, not an optimisation.

🔴 That row was **green on zerobas before the fix, while the tree got the rule
completely wrong** — `ERRFLG`/`ERRLIN` were written at the original raise and
nothing reset them, so `ERR` read 7 and `ERL` read 20 on a run that swallowed
the error entirely. Only the error-text half of the row could see the defect.

### 4.4 The abort falls out

With `ONELIN` already 0 (written two instructions earlier) and `ONEFLG` cleared
by `res_ctx`, `raise_error_hl` **cannot** take the trap: both of its conditions
fail, so it goes to `ra_abort` with no new test. `fre_abort_low` then clears
`ONEFLG` on the way out (D-ONEFLG site A) and resets `SP` from `SAVSTK`, which
is why `r.depth` — the disarm inside a `GOSUB` called by the handler — needs
nothing of its own.

### 4.5 RAM

None. Every cell used (`ERRRESUME`, `CURLINE`, `SAVTXT`, `ONELIN`, `ONEFLG`,
`ERRFLG`) already exists and already holds what the fix reads.

## 5. Forced constraints

### 5.1 The `ONELIN := 0` store must stay AHEAD of the test

`raise_error_hl` decides trap-vs-abort from `ONELIN` **and** `ONEFLG`. If the
re-raise ran with `ONELIN` still armed it would re-enter the same handler, which
would disarm again — an infinite loop, not a divergence.

### 5.2 The old `ld (ONEFLG),a` on the disarm arm is DEAD, and deleting it is the carve

On the fall-through arm `ONEFLG` was already 0 — that is *why* control got
there. The store was writing 0 over 0. It could only be seen once the two states
were split; the single old path had to clear the flag because it served both.
**−3 B, and it pays for the test that exposed it.**

### 5.3 Region

`ex_on_error` and `res_ctx`/`rerr_msg` are all main page 1, so every new
reference is an intra-page `call`/`jp`. No low-region byte, no sub-ROM byte, no
new tenant.

## 6. The cost — measured, not estimated

| part | Δ |
|---|---|
| `res_ctx` re-extracted (+14 B routine, `res_same` 13 B → 3 B) | **+4** |
| `oe_disable`: read + test `ONEFLG`, minus the dead store (§5.2) | **+3** |
| `oe_reraise`: `call res_ctx` / `ld (SAVTXT),hl` / `jp rerr_msg` | **+9** |
| `rerr_msg` label | 0 |
| **total** | **+16** |

**Main page 1: 16 B → 0 B.** The hand count and the wall agree exactly.

🔴 **THIS LEAVES THE BINDING WALL AT ZERO.** The next slice to touch main page 1
must carve before it can add a byte. The nearest funded relief is the **−29 B
`loc_next` carve** ([`spec-basic-evalchk.md`](spec-basic-evalchk.md) §6.6),
which has its own denominator to build and was deliberately **not** ridden along
here.

## 7. 💰 DEFERRED with a price: the two direct-mode rows

> ✅ **BOTH LANDED 2026-08-09 IN D-LOCARG**
> ([`spec-basic-locarg.md`](spec-basic-locarg.md)), at **exactly the +7 B priced
> below**, funded by the −29 B `loc_next` carve. `make onerr0-acceptance` is now
> **24 rows / 24 scored / 0 deferred** and its `DEFERRED` dict is empty — emptied
> by fixing the rows, not by rescoring them. Knife **K-LA4** cuts the new
> `call derive_directf` out of `oe_reraise` and reddens **exactly these two rows
> and nothing else**, both rounds; **K-LA3** forces the constant this section
> says cannot serve and reddens **exactly one**, `d.dirtrap`.

| row | zerobas | both references |
|---|---|---|
| `d.instop` | `Out of memory` | `Out of memory in 20` |
| `d.dirtrap` | `Out of memory in 0` | `Out of memory` |

Both are one missing piece: `DIRECTF`. The fix aborts through `rerr_msg`, which
never passes `rp_exec` — the only place that **derives** `DIRECTF` from
`CURLINE`'s high byte — so the mode cell keeps whatever the *re-raising*
statement had.

🎯 **They fail in OPPOSITE directions, which is what says the answer is a DERIVE
and not a constant.** Forcing `DIRECTF := 0` fixes `d.instop` and breaks
`d.dirtrap`; forcing 1 does the reverse. Both readings were **predicted before
the fix was measured and both landed exactly** (§10.5).

💰 **Price: +7 B** — extract `rp_exec`'s six-instruction derive as a shared
`derive_directf` (+14 B routine, −13 B inlined, +3 B call back = net +4) and
`call` it from `oe_reraise` (+3). Against **0 B free**, it does not fit. Filed
in `TODO.md` with this price.

## 8. Knives

Four cuts, each byte-neutral, each run **twice**, on `--sides zb` only (a cut in
zerobas can only move zerobas; the references are constants). Predictions in
§10.6 were written before the runner was started.

| knife | cut | predicts |
|---|---|---|
| K-O1 | `or a` → `xor a` at `oe_disable` (never branch) | the 10 pre-slice divergences all move; nothing else |
| K-O2 | `ld (SAVTXT),hl` → 3 × `nop` in `oe_reraise` | **`k.cont` alone** moves |
| K-O3 | `res_ctx`: `ld (CURLINE),hl` → `ld (ERRRESUME),hl` | a positive control FAILS → probe exits **2** |
| K-O4 | `jr nz,oe_reraise` → `jr z,...` (polarity) | controls `c.disarm` + `c.never` FAIL → exits **2** |

K-O1/K-O2 score the normal report; K-O3/K-O4 score the exit-2 report — two
shapes, deliberately, because a runner that only knows the green one is the
recurring fault (`dev-workflow.md` §Knives). K-O2 is the sharp one: it predicts
a RED set of **size one**.

### 8.1 🔴 K-O3 REDDENED NOTHING, TWICE, AND THAT WAS A MISSING ROW

Round set A predicted K-O3 would fail `c.resume`. It came back `rc=0`, no
control failed, in **both** rounds.

🎯 **`RESUME NEXT` DOES NOT USE `res_ctx`.** `res_next` marshals to a sub-ROM
tenant (`SUBROM_IDX_SCANSTMT`) that does the identical prep *sub-side*, reading
`ERRRESUME` itself. So `c.resume` — the battery's only `RESUME` row — never
touched the routine this slice re-extracts, and **a shared engine was being
refactored with no row over its other caller**
([[a-shared-engine-fix-must-measure-its-other-callers]]). A cut with no row of
its own is a missing row, not a bad cut.

`c.resume0` is that row: bare `RESUME`, which *does* go through `res_ctx`. It
has to fix the failing condition first, because bare `RESUME` re-executes the
statement that failed — `A$` starts empty, `ASC(A$)` is ERR 5, the handler sets
`A$="Z"` and resumes. All three sides read `[DONE]`.

🔴 **AND THE RUNNER HAD ITS OWN BLIND SPOT IN THE SAME PLACE.** For an
EXIT2-predicted knife it logged only the failed-control list, so when K-O3 came
back `rc=0` it recorded `MISS` **and nothing else** — a knife that measured
nothing at the exact moment it had something to say. The cut *had* moved ten
rows; the runner never looked. Fixed to report the moved set on **both**
branches ([[a-shadowed-guard-has-no-knife]]).

⚠️ Growing the row set 23 → 24 invalidates every prediction written against the
old one, so all four knives were re-run in full as round set B rather than just
K-O3.

## 9. Denominator

See [`onerr0-msx1-characterization.md`](onerr0-msx1-characterization.md) §6.
24 rows, 6 positive controls, 2 negative controls, both references agreeing on
all 24.

## 10. As-built

### 10.1 What landed

* `basic/program.asm` — `oe_disable` gains the `ONEFLG` test and loses its dead
  store; new `oe_reraise` arm.
* `basic/interp.asm` — `res_ctx` re-extracted from `res_same`; `rerr_msg` label.
* `probes/basic/basic_probe_onerr0.py` — the 24-row battery.
* `make onerr0-characterize` / `make onerr0-acceptance`.

### 10.2 The walls

| wall | before | after |
|---|---|---|
| main page 1 | 16 B | **0 B** |
| page-0 low | 11 B | 11 B |
| sub page 0 | 3604 B | 3604 B |
| sub page 1 | 1483 B | 1483 B |

### 10.3 ROM hashes

`sub.rom` **unchanged** at `accce5a1` (no sub-side byte moved), `disk.rom`
`2c630d3d`, `basic-reloc` `06a235e1` → `d11dfd4a`.

### 10.4 Gates

`ROWS: 24 printed, 22 scored — 22 agree, 0 diverge, 2 deferred` — every scored
row green on all three sides, the two deferred ones printed with their price
(§7). Before the fix the same battery ran 13 agreeing of 23.

### 10.5 🔴 What went differently

1. **A positive control failed on all three sides** — the fixture, not the tree
   (characterization §3).
2. **The readout was blind on the side under test** and failed by making
   everything diverge (characterization §3.1).
3. **The cheap design was refuted by the row written to test it**, and it was
   the design that would have closed *more* rows for *less* money (§4.1).
4. **Every prediction about the two deferred rows landed exactly**, including
   the `in 0` that comes from the direct line's own uninitialised lineno field.
5. **The `+16 B` hand count matched the wall exactly**, which is what makes §7's
   `+7 B` quotable rather than a guess.

### 10.6 Knives — two full round sets, 16 runs

**Round set A** (23 rows, before `c.resume0`): **6 of 8 EXACT**, and the two
misses were both K-O3, reproducible across rounds. §8.1 is what they found.

**Round set B** (24 rows, after `c.resume0` and the runner fix): **8 of 8
EXACT, and round 2 is identical to round 1 on every knife.**

| knife | rc | verdict (both rounds) |
|---|---|---|
| K-O1 | 0 | **EXACT** — moved exactly the 10 pre-slice divergences, `extra=[]`, `unmoved=[]` |
| K-O2 | 0 | **EXACT** — moved `['k.cont']` and nothing else |
| K-O3 | 2 | **EXACT** — controls failed `['c.resume0']`, 10 rows moved |
| K-O4 | 2 | **EXACT** — controls failed `['c.disarm', 'c.never']`, 15 rows moved |

🎯 **K-O2 is the one worth reading.** A three-`nop` cut of `ld (SAVTXT),hl`
moved **one** row out of 24, and it was the predicted one. That is the whole
argument for spending 6 of the 16 bytes on the `SAVTXT` restore: exactly one
measured behaviour depends on it, and it is `k.cont`.

🎯 **K-O4 is why the controls are not decoration.** Inverting the test makes
`ON ERROR GOTO 0` re-raise *outside* a handler, and the two rows that catch it
are `c.disarm` and `c.never` — both positive controls, both of which look like
boilerplate until something reaches them.

Every cut was byte-neutral, every cut build was preceded by `rm -rf build`, and
every one was hash-checked against the baseline ROMs before scoring
(`assert_cut_reached`). No knife scored DID-NOT-HAPPEN and none aborted.
