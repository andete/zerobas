# D-DELIVER — a case whose program was never stored may not report a value

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— probe infrastructure only, so no sign-off gate applies. Written up as a slice
anyway, with predicted RED/GREEN sets fixed before the change and knives that
prove the guard both *fires* and *does something*.

Closes the item D-PREFLIGHT filed but did not fix
([`docs/spec-probe-preflight.md`](spec-probe-preflight.md) §8.5): the two
standing red rows in `make graphics-acceptance`, and the fact that
`graphics-acceptance` was in **no spec's corpus list**.

Companion: [`docs/graphics-delivery-characterization.md`](graphics-delivery-characterization.md).

---

## 1. The filed failure

`make graphics-acceptance`, 290 rows, red since an unknown date:

```
FAIL  put_pat64_16   ref='ZE 5'      zb=None
FAIL  rd_base_s0     ref='ZK 6144'   zb='ZE 5'
```

D-PREFLIGHT attributed them away from itself twice — byte-identical under
`ZEROBAS_PREFLIGHT=off`, and byte-identical on the stashed pre-slice tree — and
filed two hunches:

> `rd_base_s0` reading `'ZE 5'` (the neighbouring row's answer) rather than a
> value of its own suggests the readout, not the ROM; `put_pat64_16`'s `zb=None`
> is a no-capture. Diagnose before assuming either.

Both hunches were right about the *side* and wrong about the *mechanism*, and
the mechanism is the thing worth having. Neither row is about sprites or about
`BASE(n)`.

---

## 2. What was measured

Full detail in the characterisation doc; the load-bearing readings:

### 2.1 Neither row survives isolation

Boot-per-case, both machines:

| case | ref | zb | batched verdict |
|---|---|---|---|
| `SCREEN2,2:PUT SPRITE 0,(10,20),4,64` | `ZE 5` | **`ZE 5`** | FAIL (`zb=None`) |
| `SCREEN0:A=BASE(10)` | `ZK 6144` | **`ZK 6144`** | FAIL (`zb='ZE 5'`) |

So the ROM answers exactly what the reference answers. The divergence is
manufactured by the **batched** delivery path.

### 2.2 The stored program is missing a line

Reading the line-link chain from `TXTTAB` immediately before each case's `RUN`,
across the same batches that produce the two reds:

| batch | case | typed | **stored** |
|---|---|---|---|
| phase O | `put_pat64_16` | 10, 20, 30, 40 | **20, 30, 40** |
| phase Q2 | `rd_base_s0` | 10, 20, 30, 40 | **10, 20, 40** |
| phase Q2 | `wr_v255fr` | 10, 20, 30, 40 | **20, 30, 40** |
| phase M | `SCREEN2:DRAW"B"` | 10, 20, 30, 40 | **20, 30, 40** |
| — every other case in those batches — | 10, 20, 30, 40 | 10, 20, 30, 40 |
| — every case, `Philips_VG_8020` — | 10, 20, 30, 40 | 10, 20, 30, 40 |

(The phase-M row was found by the guard itself, after the fact — §7.3.)

That is the whole defect. Each phase-O/Q2 case is

```
10 ON ERROR GOTO 40
20 <the statement under test>
30 SCREEN0:PRINT"ZK"[;A]:END
40 SCREEN0:PRINT"ZE";ERR:END
```

* `put_pat64_16` loses **line 10**. Its ERR 5 is then *untrapped*: the RUN
  aborts with the machine still in SCREEN 2, so the probe's SCREEN-0 name-table
  scrape reads VRAM `$0000` — which in SCREEN 2 is the zeroed pattern generator
  table. Measured: **960 bytes of `$00`**, every one of them rendered as a blank.
  `_outcome` finds no tag → `None`.
* `rd_base_s0` loses **line 30**. Line 20 then falls straight through into the
  handler, which prints `"ZE";ERR` — and `ERR` still holds **5** from the
  preceding case, `rd_baseneg` (`SCREEN2:A=BASE(-1)`). The filed hunch that
  `'ZE 5'` "is the neighbouring row's answer" is *literally true*, by a route
  nobody guessed.
* `wr_v255fr` loses **line 10** and **passes anyway** — it never raises, so the
  handler it lost is never reached. A row currently passing for no reason at
  all; see §9.2.

### 2.3 It is an alignment race, and both hypotheses about the injector are wrong

* **Not positional alone.** Eleven harmless filler cases in front of a
  slice that passes reproduce the loss; a prefix of *only* fillers, same index,
  does not. Position and predecessor content both shift it.
* **Not a step-length problem in the ordinary sense**, though `step=5.0` clears
  it. At `step=0.7` the zerobas machine mis-delivers 1 case in 30 and the
  reference 0 in 30; at `step=1.2` both are clean. Raising `step` moves the
  alignment, it does not remove the class.
* 🔴 **The injector is not at fault the way the module docstring warns.**
  `omsx_repl`'s docstring records that "each `__key` call resets GETPNT/PUTPNT,
  so lines delivered mid-operation collapse into one". Instrumented **in the
  same run that reproduced the fault**: KEYBUF was *drained* (`GETPNT ==
  PUTPNT`) before **every** injection, and `GETPNT` was exactly `KEYBUF` after
  **every** injection. All 20 characters of `10 ON ERROR GOTO 40` were written,
  the pointers were correct, and the openMSX `after time` callback is atomic
  with respect to the emulated CPU. Nothing was lost *in* the injector.
* What the screen says: 0.02 s after that injection the screen already reads
  ```
   ZBN ERROR GOTO 40
   Syntax error
  ```
  The machine consumed the first **four** characters (`10 O`) without echoing
  them, the screen editor read back `N ERROR GOTO 40`, and BASIC rejected it. The
  line was never stored. Four is also the length of the preceding injection
  (`CLS`+CR), which is suggestive and is **not** established as the cause.

⚠️ **What is NOT established:** the exact ROM/BIOS path that swallows those four
characters. A deliberate type-ahead differential — inject a line *while* a
program is printing, and again while it spins silently — comes back clean on
**both** machines (the typed line survives and executes). So zerobas does not
systematically drop type-ahead; this is a narrow race, and this slice does not
claim to have found its floor. What the slice does claim is that **the class is
now impossible to misread as semantics**, which is the part that left two rows
red for an unknown length of time with no way to interpret them.

---

## 3. Design

### 3.1 The rule

> A batched case whose program the machine did not store as typed has produced
> **no reading**. It may not be compared, and it may not be reported as a value.

### 3.2 Detection — ask the machine what it stored

`_tcl` already schedules one capture per case. For `mode == "stored"` it now also
schedules, **`min(0.4, step/5)` seconds before the `RUN` injection**, a walk of
the line-link chain from `TXTTAB` (`$F676`), emitted as `prog.<idx>=<n1,n2,…>`.
Before `RUN`, so a case whose own program calls `NEW`/`CLEAR` cannot erase the
evidence.

The expected chain is `10, 20, …, 10*len(lines)` — exactly what `_tcl` typed.
`direct`-mode cases emit nothing and are **not** covered; that is a stated
coverage limit, not an oversight (§9.3).

### 3.3 Repair — re-run the case on the delivery path that is immune

`run_cases(batch=True)` compares the delivered chain against the typed one. Any
mismatch is **announced on stderr**, naming the case index, the typed chain and
the stored chain, and that case alone is re-run with `batch=False`. Boot-per-case
is the path §2.1 measured immune, and it is the escape hatch `run_batch`'s own
docstring already names.

Announcing is not decoration. A matrix that genuinely depends on batch context
would get a different answer from the repair path, and the operator has to be
able to see that it happened.

### 3.4 A repair that also mis-delivers is an APPARATUS FAILURE

`run_batch` verifies too, and raises
`SystemExit("omsx_repl: APPARATUS FAILURE …")` when a case it delivered on its
own — the boot-per-case path, including every `run_case` caller — comes back
mangled. There is no third fallback, and a guard that cannot judge must say so
rather than hand back a value ([[guard-that-cannot-judge-must-say-so]]).

**There is deliberately no retry.** A retry would be a code path the slice never
exercised, and boot-per-case measured immune in every run here (including the
four repairs the clean gate run performed). If that ever stops being true the
gate says so loudly, which is the outcome a retry would hide.

`verify_delivery=False` exists as an explicit opt-out for a probe that
deliberately drives line entry to refusal. **No probe needs it today** — measured:
of the 8 probe files using `mode="stored"`, none expects a line to be rejected;
the `("stored_line", …)` refusal probes (`linemax`, `crunch`, `kwsweep`,
`lnblank`, `pin_errtokens`, `time`, `math_conv`) all type in `direct` mode.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline, measured on the unchanged tree at `4243343`: `make graphics-acceptance`
= **290 rows, 2 FAIL**, 3 m 20 s.

### 4.1 Predicted GREEN after the change

| row | predicted ref | predicted zb |
|---|---|---|
| `put_pat64_16` | `ZE 5` | **`ZE 5`** |
| `rd_base_s0` | `ZK 6144` | **`ZK 6144`** |
| `wr_v255fr` | `ZK 255` | `ZK 255` (unchanged verdict, now for a reason) |
| the other 287 rows | unchanged | unchanged |

`make graphics-acceptance` → **290/290, exit 0**, with a stderr notice naming
the mis-delivered cases and the re-runs.

Corpus, unchanged: unit 56/56 · deadcode 0/0 · msgexact 55/55 · preflight-check
0 unguarded · lnblank 536/536 at `REPEAT=2` · logicops 193/193 · array 151/151 ·
diskbasic 34/34 · linemax 60/60 · direct-ctrl 40/40 · float / string / error /
error-trap / abort / stop-trap / arrdim / clearpool / input / time ALL PASS.
**No ROM is rebuilt by this slice; the merged ROM must hash identical
throughout.**

### 4.2 Predicted RED — the knives

| knife | cut | predicted RED | predicted GREEN control |
|---|---|---|---|
| **K1** | delete the `prog.N=` emission in `_tcl` (nothing to compare) | `put_pat64_16` = `ZE 5`/`None`, `rd_base_s0` = `ZK 6144`/`ZE 5` — **byte-identical to the filed reading** | the other 288 rows green |
| **K2** | keep the emission and the call, make the comparison always answer "delivered" | **the same two rows, same values** — coverage is not efficacy [[coverage-gate-cannot-see-a-gutted-guard]] | the other 288 rows green |
| **K3** | keep detection, make the repair a no-op (report, do not re-run) | the same two rows RED — but **refused**, not mis-valued: a `MIS-DELIVERED` line on stderr for exactly cases 22 (phase O) and 12 (phase Q2) | the other 288 rows green |
| **K4** | positive control: force the class with `step=0.7` on a 30-case filler batch | the guard **fires and repairs**; batch verdicts identical to a `step=2.5` run | the same batch at `step=1.2` fires **zero** times |
| **K5** | zero-RED prediction: run the **reference** machine's half of both phases with the guard armed | **zero** fires — `Philips_VG_8020` mis-delivered nothing in any measurement | the zb half fires exactly twice |

K5 is written as a zero-RED knife deliberately
([[knife-that-reddens-nothing-is-the-finding]]): if the reference *did* fire, the
guard would be measuring something other than the class §2.2 identified.

---

## 5. Corpus decision — `graphics-acceptance` joins the standing list

**Yes.** It is added to the standing corpus list this repo keeps in each slice
spec's "Gates" section, and to
[`docs/spec-basic-dotgaps.md`](spec-basic-dotgaps.md) §9.2's table.

The argument is not that these two rows mattered — they were an artefact. It is
that a 290-row VG-8020 differential covering PSET/PRESET/POINT, LINE, CIRCLE,
PAINT, DRAW, sprites, `VDP(n)` and `BASE(n)` sat outside every corpus list and
went red at a date nobody can name — it took D-PREFLIGHT running it as an
unrelated blast-radius check to notice at all — *a gate nobody runs is not a
gate*
([[expkw-marker-not-marker-slice]]). Cost: **3 m 20 s**, sequential, on the same
`repack-machine` prerequisite every other emulator gate already needs.

⚠️ It is the **only** corpus member that was ever red at admission, so its
admission is conditional on §4.1 coming back 290/290.

---

## 7. What landed, and what it measured

`probes/lib/omsx_repl.py` only. **No `basic/`, `sub/`, `disk/` or `tape/` source
touched; no ROM rebuilt.**

* `_tcl` emits `prog.<idx>=<chain>` for every stored-mode case, via a new
  `__lines` Tcl proc that walks the line-link chain from `TXTTAB`.
* `_run_batch` is the raw engine and returns `(captures, delivered)`.
* `run_batch` verifies and **raises** `APPARATUS FAILURE` — it *is* the
  boot-per-case path, so it has nothing to fall back on.
* `run_cases(batch=True)` verifies, announces, and re-runs the affected case
  boot-per-case.
* `expected_lines` / `mis_delivered` / `verify_delivery=False` are the seams.

### 7.1 Predicted GREEN — hit exactly

`make graphics-acceptance` → **290/290, exit 0**, 2 m 58 s (was 290 rows / 2 FAIL
/ 3 m 20 s). A row-by-row diff of the whole gate against the baseline moves
**exactly two rows**, to exactly the values §4.1 predicted, and nothing else.
Two independent full runs announce the **same four** mis-deliveries — openMSX is
deterministic, so the race is too, which is why it read as semantics rather than
as flake [[deterministic-mangle-is-still-a-mangle]].

Corpus, run sequentially, all exit 0: unit **56/56** · deadcode **0/0** ·
preflight-check **0 unguarded** · msgexact **55/55** · logicops **193/193** ·
array **151/151** · linemax **60/60** · direct-ctrl **40/40** · diskbasic
**34/34** · bdos **12/12** · lnblank **536/536 at `REPEAT=2`, allowlist empty** ·
missing · width · string · error · error-trap · abort · stop-trap · arrdim ·
clearpool · float · input · input-devices · time · intarg · sound · play · beep ·
math. No `basic/`, `sub/`, `disk/` or `tape/` source touched;
`make -q build/zerobas-main-eu.rom` exit 0 throughout, so no ROM was rebuilt.

### 7.2 Predicted RED — the knives, all five

K1 and K2 both returned the filed reading **byte-identical**; K3 turned it into
an attributed refusal; K4 fired and repaired with every verdict unchanged; K5
came back zero on the reference. Full table in the characterisation doc §9.

### 7.3 🔴 The guard found two rows the gate could not

The clean run announced **four** mis-deliveries, not two. `wr_v255fr` (phase Q2)
and the phase-M `SCREEN2:DRAW"B"` row had each lost their `ON ERROR GOTO 40` and
**passed anyway** — they are value rows that never raise, so the handler they
lost was never reached. Two green rows that were green for no reason, invisible
to a gate that only compares outcomes.

### 7.4 🔴 The rate at the DEFAULT step

Thirty identical, harmless cases, `step=2.5` — the default every batched probe in
this repo uses — mis-deliver **one** on the zerobas machine and **zero** on the
reference. This is not a graphics-probe curiosity. It is a property of the
batched delivery path that has been running under every suite in the corpus, and
the reason the corpus is green is that `mode="stored"` is used by only 8 probe
files and the lost line usually lands somewhere that does not change a verdict
(§7.3 is what that looks like when you can see it).

---

## 8. Findings

### 8.1 🔴 Both stories about the injector were wrong, and the module's own docstring told the first one

`omsx_repl`'s docstring has recorded since D-DOTGAPS that "each `__key` call
resets GETPNT/PUTPNT, so lines delivered mid-operation collapse into one". That
is a real hazard and it is **not** this one. Instrumented in the run that
reproduced the fault: KEYBUF was drained before all 490 injections and `GETPNT`
was exactly `KEYBUF` after all 490. The second story — that writing `GETPNT`
before `PUTPNT` leaves a transient non-empty buffer the CPU can eat from — dies
on the same reading, because the openMSX `after time` callback is atomic with
respect to the emulated CPU.

⚠️ **The first two instrumented runs proved nothing**, because I did not check
that the fault had reproduced in them. A clean instrument on a run where the
subject never occurred reads exactly like an exoneration
[[knife-runner-false-negatives]]. Both were re-run with a reproduction check in
the same run before their result was used.

### 8.2 🔴 A right conclusion from a wrong model still has to be re-derived

D-PREFLIGHT filed the hunch that `rd_base_s0`'s `'ZE 5'` was "the neighbouring
row's answer … suggests the readout, not the ROM". It is *exactly* the
neighbouring row's answer: `ERR` still held 5 from `rd_baseneg`. But the route
was a lost `PRINT"ZK"` line and a fall-through into the handler — not a
mis-scrape. Implementing against the hunch would have produced a fix aimed at
the readout that could not have touched the cause, and it would have looked like
it worked, because the symptom would have moved.

### 8.3 🔴 A blank screen is two different machine states

`zb=None` came from a capture of **960 bytes of `$00`**. In SCREEN 0 a cleared
name table is `$20`. `$00` at VRAM `$0000` is SCREEN 2's zeroed pattern
generator table — so the reading was "the machine is still in a graphics mode",
which the decoded string cannot express, because both bytes render as a blank.
`_outcome`'s abort guard is blind for the same reason: in SCREEN 2 the echo and
the error message are at `$1800` and the scrape reads `$0000`
[[readout-blind-to-its-own-subject]].

### 8.4 The class is positional, but not only positional

Three of the four mis-deliveries in a clean gate run are at batch index **22**,
in three unrelated phases. Yet a prefix of twenty-two *identical* filler cases,
target at index 22, delivers clean. Position and predecessor content both move
the alignment; neither is the cause on its own. `step=5.0` clears the graphics
case and `step=1.2` clears the filler batch — which is a reason **not** to
"fix" this with a bigger step. A number that moves a race is not a guard
[[deterministic-mangle-is-still-a-mangle]].

---

## 9. What this does not fix

### 9.1 The floor of the race

§2.3 and §8.1. The four swallowed characters are characterised, not explained. The guard
converts the class from "a wrong value" to "a re-run, announced" — which is the
outcome that matters — but a future slice that finds the ROM path is still worth
having, and the characterisation doc records everything measured so far.

### 9.2 `wr_v255fr` was passing vacuously

Phase Q2's `wr_v255fr` lost its `ON ERROR GOTO 40` and passed regardless, because
it is a value row that never raises. After this slice it is delivered intact, so
it passes for its own reason — but the general point stands: **a row whose
handler is never exercised cannot tell you its handler arrived**
([[gate-can-be-green-while-measuring-nothing]]). Not enumerated here.

### 9.3 `direct`-mode delivery is still unguarded

There is no stored program to interrogate, so the same race in a `direct`-mode
matrix still reads as a value. The existing echo guards
([[decblank-echo-guard-blind]], [[lineno-blank-echo-guard]]) are the instrument
there, and they are per-probe rather than harness-wide. Filed.

🎯 **CLOSED 2026-08-03 BY D-ECHO** ([`docs/spec-probe-echo.md`](spec-probe-echo.md)).
Every injected line is now checked against what the machine echoed, so both modes
are covered by one oracle — the race is in the DELIVERY path, not the store path
(phase O re-expressed in `direct` mode, byte-identical injections on
byte-identical slots, mangles the same case on the same line). The stored-program
oracle above **stays**, as a second opinion: each is blind exactly where the
other sees. Six standing corpus suites turned out to be mis-delivering a case on
every run, all `direct`-mode, all green.

D-ECHO also settled §9.1's loose end in part: the swallow count is **exactly the
length of the preceding injection including its CR** (six measurements, three of
them predicted in advance). The *trigger* is still open.

🎯 **§9.1 CLOSED IN FULL 2026-08-04 BY D-LATCH**
([`docs/spec-probe-latch.md`](spec-probe-latch.md)). The trigger is the one
instruction boundary at `$1197` — between C-BIOS `chget`'s `ld hl,(GETPNT)` and
`ld de,(PUTPNT)` — where this module's injector moved `GETPNT` **backwards**
under a CPU that had already latched it. §8.1's readings stand exactly as
recorded and were never wrong: nothing *was* lost in the injector, and `GETPNT`
*was* `KEYBUF` after every injection. The pointer the machine used was in a
register. The injector now writes at the current `GETPNT` and never moves it, so
the class no longer occurs; both oracles stay armed, and `make latch-check`
forces the race so they keep a live subject.
