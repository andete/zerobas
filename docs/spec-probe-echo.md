# D-ECHO — a line the machine did not echo was not delivered

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— `probes/lib/omsx_repl.py` and its host unit test only, so no sign-off gate
applies. Written up as a slice anyway, with predicted RED/GREEN sets fixed before
the change and knives that prove the guard both *fires* and *does something*.

Closes the item D-DELIVER filed but did not fix
([`docs/spec-probe-delivery.md`](spec-probe-delivery.md) §9.3): `direct`-mode
delivery is unguarded, and `direct` is the majority — of the 53 probe files that
drive `omsx_repl`, **8** use `mode="stored"`.

Companion: [`docs/echo-delivery-characterization.md`](echo-delivery-characterization.md).

---

## 1. The filed failure

> There is no stored program to interrogate, so the same race in a `direct`-mode
> matrix still reads as a value. The existing echo guards are the instrument
> there, and they are per-probe rather than harness-wide.

D-DELIVER measured the class at **1 case in 30 at the default `step=2.5`** on the
zerobas machine and **0 in 30** on the reference, and proved it deterministic. A
`direct`-mode probe that hits it reports whatever the screen happened to say.

---

## 2. What was measured before designing

Full detail in the characterisation doc; the load-bearing readings.

### 2.1 🔴 The two machines do not share screen geometry

| | `Philips_VG_8020` | `C-BIOS_MSX1_EU_REPACK_DISK` |
|---|---|---|
| left margin of every row | **2** | **1** |
| `LINLEN` (`$F3B0`) | **37** | **39** |
| column a wrapped echo resumes at | 2 | 1 |
| prompt | `Ok`, on a row of its own | `ZB`, prefixing the echo row |

So a comparator with a hard-coded width or margin is wrong on one side or the
other — and wrong in the direction that reports the *zerobas* machine as mangled.
The margin is **measured per capture** (the narrowest indent on the screen, the
method [`basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py) arrived
at) and the width is **read from the machine** (`LINLEN`), never assumed.

### 2.2 The echo is a contiguous stream, and it survives the next injection

Rows are `[margin][LINLEN columns][pad]`; a line too long for the window resumes
at the margin of the next row. Concatenating `row[margin : margin+LINLEN]` over
all 24 rows therefore yields one contiguous text stream in which a wrapped echo
is a plain substring. Measured on both machines with a 43-character line (which
`_tcl` chunks into 38 + 5).

An echo also stays on screen across the following injections, so a dump taken at
`t + 0.8·step` — after the line has been consumed, before the next line is
written — sees it.

### 2.3 🔴 The race is in the DELIVERY path, not the store path

Phase O re-expressed in `direct` mode — the line numbers and the final `RUN`
written out by hand, so the injected bytes and every `after time` slot are
**identical** to the stored-mode run — mangles **the same case 22, the same
line**. `mode` selects only which branch of `_tcl` composes the text; it does not
touch what the race does to it. This is what makes one oracle able to cover both.

### 2.4 A `puts` costs no emulated time

D-DELIVER §8.1 established that the openMSX `after time` callback is atomic with
respect to the emulated CPU. A dump slot therefore does **not** move the
alignment — which is the whole reason the oracle may not be built by splitting an
injection into body-then-CR, however much easier that would make it. A number
that moves a race is not a guard [[deterministic-mangle-is-still-a-mangle]].

### 2.5 🔴 The swallow count is the length of the preceding injection

Measured *after* the design was drafted, and it changed the design. D-DELIVER
recorded four characters swallowed and noted four is also the length of the
preceding injection (`CLS`+CR) — *"suggestive and NOT established"*. Varying only
the reset's last line:

| preceding injection | length with CR | swallowed |
|---|---|---|
| `CLS` | 4 | **4** |
| `CLS:CLS` | 8 | **8** |
| `CLS:REM1` | 9 | **9** |
| `CLS:REM123456` | 14 | **14** |
| `CLS:CLS:CLS:CLS` | 16 | **16** |

The last three were stated as predictions before the run. A sixth confirmation
came unbidden from `time-acceptance`, whose mangled line follows
`20 SWAP TIME,A` — 15 bytes with its CR, and 15 swallowed.

So the race takes a **prefix**, and what the machine echoes is therefore a proper
**suffix** of what was typed. That is what §3.3 uses as positive evidence, and it
is why the guard is not a heuristic about screen shapes.

⚠️ A rule, not a mechanism — see the characterisation doc §5. And it says nothing
about the *floor*: why the race fires on one slot and not the next.

---

## 3. Design

### 3.1 The rule

> A line the machine did not echo was not delivered. A case containing one has
> produced **no reading**: it may not be compared, and it may not be reported as
> a value.

### 3.2 Detection — read the screen back after every injection

`_tcl` schedules, at `t + 0.8·step` after **every** `__inj`/`__key` slot, a dump
of `SCRMOD` (`$FCAF`), `LINLEN` (`$F3B0`) and the SCREEN-0 name table. Both
sysvars are published MSX2-TH contract; no ROM was disassembled. `_tcl` also
hands back one `(case_index, typed_text)` record per slot, so the comparison is
against what the harness *actually scheduled* rather than against a
reconstruction of it.

`@WAIT` pseudo-lines type nothing and never produce a slot
([`omsx_repl.is_wait`](../probes/lib/omsx_repl.py)), so they are structurally
absent here rather than special-cased.

### 3.3 A MANGLED verdict must carry its own control

"The typed text is not on the screen" is **not** sufficient. A payload that
clears the screen — `CLS`, `SCREEN n`, a `RUN` whose program does either — erases
its own echo, and that is indistinguishable from never having echoed one. So the
verdict is:

| verdict | condition |
|---|---|
| `OK` | the typed text is in the stream |
| `MANGLED` | it is not, the screen **lost nothing** since the previous slot, and a proper **suffix** of the typed text is on it |
| `BLIND/mode` | `SCRMOD != 0` — the SCREEN-0 scrape is not looking at the text plane |
| `BLIND/rewrote` | the screen lost content — cleared, or scrolled — or the previous slot was blind so there is no baseline |
| `BLIND/noecho` | nothing resembling a truncated echo is there |
| `BLIND/unprintable` | the payload holds a character the screen cannot spell back (a tab, which the ROM *renders*) |
| `NODUMP` | no dump arrived (apparatus) |

The paired control is the **suffix**, and it comes from §2.5's measured
mechanism, not from a guess about screen shapes: the race takes a prefix, so a
truncated echo is always a proper suffix of what was typed, and a *wiped* echo
never is. "Lost nothing" then rules out a clear or a scroll having removed the
real echo. Everything else refuses to judge
[[guard-that-cannot-judge-must-say-so]].

⚠️ §4bis.2 records the three weaker controls this replaced, each of which
survived inspection and was killed by the corpus — two of them after breaking a
green gate.

⚠️ **The exemptions are themselves blind spots, and they are named, not hidden**:
a mangle of `CLS`, of `SCREEN n`, of a `RUN` whose program clears, of any line on
a screen that scrolls, of a payload containing a control character, or one that
swallows a line *entire* (no suffix survives) is invisible to this oracle. §5 is
where that hole gets its second opinion. Measured cost on a real batch: of 245
phase-O slots, 169 `OK`, 68 `BLIND/rewrote`, 7 `BLIND/mode`, 1 `MANGLED` — about
**69 % of injections judged**.

### 3.4 Repair — as D-DELIVER, and for the same reason

`run_cases(batch=True)` announces on stderr and re-runs the affected case
`batch=False`; `run_batch` — which *is* the boot-per-case path — raises
`APPARATUS FAILURE`. No retry, for the reason D-DELIVER §3.4 gives.
`verify_delivery=False` opts a probe out of **both** oracles.

`ZEROBAS_ECHOGUARD=off` disables emission and judgement and prints a banner,
mirroring `ZEROBAS_PREFLIGHT=off` — an operator escape hatch that doubles as K1.

### 3.5 🔴 The two oracles check each other

The echo oracle is blind on the slots §3.3 lists; the stored oracle is blind to
`direct` mode and to `RUN` itself. They are **independent** — one reads the
screen, the other walks the line-link chain from `TXTTAB` — so where both can
see, they must agree. `run_cases` announces a `ORACLES DISAGREE` line when the
stored oracle flags a case the echo oracle judged clean, or vice versa.

This is the standing check with teeth, and it needs no frozen payload: a
self-contained batch of *identical* cases does **not** reproduce the race
(measured, §2 of the characterisation, and consistent with D-DELIVER §8.4 —
predecessor content moves the alignment), so a permanent emulator positive
control would have to freeze phase O's exact 35 payloads and would go silent the
day a ROM change moved the alignment. Cross-oracle agreement fires exactly when
the race does, whatever it takes to provoke it.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline, measured on the unchanged tree at `5c96a0a`: `make graphics-acceptance`
= **290/290, exit 0**, 4 mis-deliveries announced by the stored oracle.

### 4.1 Predicted GREEN after the change

| | predicted |
|---|---|
| `make graphics-acceptance` | **290/290, exit 0** — verdicts unchanged, row for row |
| its mis-delivery announcements | the **same four** cases, now each carrying an echo verdict |
| phase O, zb | echo flags exactly **case 22**, line `10 ON ERROR GOTO 40` |
| phase Q2, zb | echo flags exactly **case 12** (line `30 SCREEN0:PRINT"ZK";A:END`) and **case 22** (line `10 ON ERROR GOTO 40`) |
| phase O + Q2, `Philips_VG_8020` | **zero** echo flags, 490 slots |
| `ORACLES DISAGREE` | **not emitted** anywhere in the corpus |
| corpus false positives | **zero** MANGLED verdicts that are not a real mis-delivery |

Corpus, unchanged: unit **57/57** (one new file) · deadcode 0/0 · msgexact 55/55
· preflight-check 0 unguarded · lnblank 536/536 at `REPEAT=2` · logicops 193/193
· array 151/151 · linemax 60/60 · direct-ctrl 40/40 · diskbasic 34/34 · float /
string / error / error-trap / abort / stop-trap / arrdim / clearpool / input /
time ALL PASS. **No ROM is rebuilt; `make -q build/zerobas-main-eu.rom` exit 0
throughout.**

⚠️ **The repair is wired only if the corpus false-positive count is zero.** A
guard that re-runs healthy cases boot-per-case costs a full boot each and would
be paid on every gate forever. If the count is non-zero the guard lands
report-only and this spec records the number that stopped it.

### 4.2 Predicted RED — the knives

| knife | cut | predicted RED | predicted GREEN control |
|---|---|---|---|
| **K1** | `ZEROBAS_ECHOGUARD=off` — no emission, no judgement | the direct-mode phase-O reproduction reports **0 MANGLED** (armed: 1) | **the stored oracle still fires on case 22 in that same run** — proof the fault reproduced and the instrument, not the machine, went quiet [[knife-runner-false-negatives]] |
| **K2** | keep the emission **and** the call, gut `echo_verdicts` to `return []` | the same **0 MANGLED**, with `echo.0=` present in both the Tcl and the output file — coverage is not efficacy [[coverage-gate-cannot-see-a-gutted-guard]] | `graphics-acceptance` still **290/290**, because the *stored* oracle repairs it — which is exactly how this hole stayed open |
| **K3** | detection kept, repair replaced by `pass` | the direct reproduction still **announces** case 22 and does not repair it | the announcement text is byte-identical to the armed run |
| **K4** | positive control: the direct-mode phase-O batch, guard armed | fires **exactly once**: case 22, slot 156, `10 ON ERROR GOTO 40` | the stored-mode run of the same batch flags the same case |
| **K5** | zero-RED: both phases on `Philips_VG_8020` | **zero** fires | the zb half of the identical batch fires 1 and 2 |
| **K6** | hard-code the margin to `2` (the reference's) | the **zerobas** side (margin 1) reports MANGLED on essentially every judged slot | the **reference** side stays green — the asymmetry §2.1 measured is what the knife exposes |

K5 is a zero-RED knife on purpose [[knife-that-reddens-nothing-is-the-finding]].
K6 exists because §2.1 is the finding most likely to be "simplified" away later
by someone who assumes one MSX screen geometry.

**Scored:** K1–K5 hit exactly. 🔴 **K6's prediction was wrong** — the cut produces
**zero** fires, not a flood: a margin too large by one eats only the prompt, so
the margin is load-bearing only for a *wrapped* echo, and where it does bite the
suffix requirement makes it fail **blind** rather than loud (`MANGLED` 1 → 0,
three slots moved into `BLIND`). So the geometry has no emulator knife at all;
the host unit test is its only instrument, and under the same cut that test exits
1 on four rows. Detail in the characterisation doc §8.

---

## 4bis. What landed, and what it measured

`probes/lib/omsx_repl.py` plus a new `tests/test_echo_oracle.py`. **No `basic/`,
`sub/`, `disk/` or `tape/` source touched; `make -q build/zerobas-main-eu.rom`
exit 0 throughout, so no ROM was rebuilt.**

### 4bis.1 Predicted GREEN — hit, including the ones that mattered

`make graphics-acceptance` → **290/290, exit 0**, 2 m 55 s (was 2 m 58 s). The
**same four** mis-deliveries are announced, and **both oracles fired on all
four** — `ORACLES DISAGREE` was not emitted. Phase O and Q2 flagged exactly the
cases and exactly the lines §4.1 predicted, and the reference flagged **zero** in
490 slots. `make unit-test` **57/57**.

Corpus, run sequentially, all exit 0: unit **57/57** · deadcode **0/0** ·
preflight-check **0 unguarded** · msgexact **55/55** · lnblank **536/536 at
`REPEAT=2`, allowlist empty** · lnblank-echo · logicops · array · linemax
**60/60** · direct-ctrl **40/40** · diskbasic · bdos · kwsweep · sysvarsweep ·
string · missing · width · float · arrdim · clearpool · error · error-trap ·
abort · stop-trap · input · input-devices · time · intarg · math · sound · play ·
beep · cursor · binfre · str-domain · badfnum · lof · graphics-floor · subrom ·
interval/key/sprite/strig-trap.

### 4bis.2 🔴 The false-positive prediction was WRONG, four times over

§4.1 predicted zero corpus false positives and made the repair conditional on it.
The first three comparators all failed that condition — on the corpus, not on
inspection — and two of them broke a green gate:

| control | broken by | damage |
|---|---|---|
| "the typed text is absent" | every `CLS` reset erases its own echo | would fire on every case |
| "…and the screen GREW" | `linemax`'s `LIST` **scrolls** its echo away | 60/60 → **exit 2** |
| "…and the screen LOST NOTHING" | `missing`'s `WIDTH 40:CLS:PRINT…` clears *then* prints | **59 fires**, exit 2 |
| "…and a proper SUFFIX is present" | `lnblank`'s `2\t0 REMX` — the ROM renders the tab | 4 fires, **on the reference** |

The surviving rule takes its positive evidence from the mechanism (§2.5) rather
than from the shape of the screen, and the fourth was caught by the **zero-RED
control**: it fired on `Philips_VG_8020`, which mis-delivers nothing. Each is now
a row in `tests/test_echo_oracle.py`.

Only once all four were fixed did the condition hold — **zero false positives
across the corpus** — so the repair is wired as designed.

### 4bis.3 🔴 Six standing suites were mis-delivering a case, every run, and were green

`logicops`, `float`, `math`, `str-domain`, `time` and `error-trap` are all
`direct`-mode: nothing in the tree could see it. They were green because
`run_differential` self-heals any case where the two machines disagree — so the
outcome was usually rescued, at the price of an unattributable boot-per-case
pair, and with no protection at all where a mangle leaves a plausible value both
sides agree on. Full table in the characterisation doc §7.

### 4bis.4 🔴 The guard was wired in, and silent, and only the cross-oracle check knew

`$__f` is a global; inside a Tcl `proc` it does not resolve, so `__echo` errored
and openMSX dropped the callback without a word. The emission was present, the
call site was present, every slot was recorded — and the oracle reported nothing.
That is the **K2 shape occurring by accident**, on the first run, and the thing
that caught it was §3.5's `ORACLES DISAGREE` line, not any gate.

## 5. Does the stored-mode oracle stay?

**It stays, as a second opinion, and the pair is now load-bearing.**

Not sentiment — coverage. Each oracle is blind where the other sees:

| | stored oracle | echo oracle |
|---|---|---|
| `direct`-mode cases (45 of 53 probe files) | **blind** | covers |
| a mangled `RUN` | blind (it reads before `RUN`) | covers, when the screen grows |
| a mangled reset (`NEW`/`CLS`) | blind | covers `NEW`; **blind** on `CLS` |
| a case typed while `SCRMOD != 0` | covers | **blind** |
| a payload that wipes its own echo | covers | **blind** |
| a line stored but stored *wrong* | covers | covers |

The measured instance of the third row is real: phase O case 22 leaves the
machine in SCREEN 2, so all seven slots of case **23** are `BLIND/mode` — and the
stored oracle reads case 23's chain regardless. Replacing the stored oracle would
have swapped one hole for another.

Retiring it would also cost the only independent check the echo oracle has (§3.5).

---

## 6. Coverage limits, stated

* Probes with their own `build_tcl` — every `probes/disk/*` script and
  `basic_probe_printusing.py` — do not go through `omsx_repl._tcl` and are **not**
  covered. Not enumerated further here.
* A payload whose only distinguishing feature is a **trailing blank** is not
  distinguishable by a substring search, the same structural blindness
  [[decblank-echo-guard-blind]] records. The per-probe echo guards remain the
  instrument for that.
* The **floor** of the race is still not explained — D-DELIVER §9.1 stands
  unchanged. This slice makes the class unmissable in one more mode; it does not
  find the cause.

  🎯 **CLOSED 2026-08-04 BY D-LATCH** ([`docs/spec-probe-latch.md`](spec-probe-latch.md)).
  The trigger is the single instruction boundary at `$1197`, between C-BIOS
  `chget`'s `ld hl,(GETPNT)` and `ld de,(PUTPNT)`: the injector moved `GETPNT`
  **backwards** under a CPU that had already latched it into `HL`. 2039 slots
  across seven instrumented batches, 6 at `$1197`, 6 mis-deliveries, none
  anywhere else — and forcing the injection onto that address with a breakpoint
  reproduces it every time while the neighbouring boundaries deliver intact.
  §2.5's hypothesis was **inverted**: nothing saves or restores a pointer; what
  survives is a register copy. The injector now writes at the current `GETPNT`
  and never moves it, so the race cannot fire; `make latch-check` replaces the
  positive control §3.5 says these oracles would otherwise lose.

  ⚠️ **§2.5's "26-byte predecessor: the batch delivered clean" row was a PARTIAL
  READING** — taken from the echo oracle alone. It hits the trigger too; the
  swallow simply exceeds the payload, so the line arrives after garbage and the
  *stored* oracle flags a spurious line `0` (D-LATCH characterisation §4.1).
