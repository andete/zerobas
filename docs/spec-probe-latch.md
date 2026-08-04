# D-LATCH — the trigger is one instruction wide

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— `probes/lib/omsx_repl.py` and its host unit test only, so no sign-off gate
applies. Written up as a slice anyway, with predicted RED/GREEN sets fixed before
the change and knives that prove the mechanism both *fires* and *is the cause*.

Closes the item D-DELIVER filed and D-ECHO halved
([`docs/spec-probe-delivery.md`](spec-probe-delivery.md) §9.1,
[`docs/spec-probe-echo.md`](spec-probe-echo.md) §6):

> The **floor** of the race is still not explained. §2.5 gives the *size* of the
> bite, not the trigger.

Companion: [`docs/latch-trigger-characterization.md`](latch-trigger-characterization.md).

---

## 1. The filed failure

D-ECHO established the **law**: a batched injection can have its head swallowed,
and the number of characters swallowed is **exactly the length of the preceding
injection, its CR included** — six measurements, three of them stated as
predictions before the run. What it could not say is why the race fires on one
slot and not the next. Position alone does not explain it (22 identical fillers
with the target at index 22 deliver clean); predecessor content alone does not
either (a 26-byte predecessor shifts the alignment and nothing mangles).

The hypothesis on file was that *"the ROM saves a `GETPNT` past the previous line
and later restores it"*. That hypothesis is **wrong in its mechanism and right in
its consequence**, and §2 says exactly how.

---

## 2. What was measured before designing

Full detail in the characterisation doc; the load-bearing readings.

### 2.1 The instrument: the CPU's registers at the moment of injection

`__key` is the only place the harness writes KEYBUF/GETPNT/PUTPNT. An openMSX
`after time` callback is atomic with respect to the emulated CPU (D-DELIVER
§8.1), so at the **top** of `__key`, before a single byte is written, the machine
is in exactly the state the injection is about to interrupt. Reading `reg pc`,
`reg hl`, `reg de`, `reg sp` and the two pointers there costs **zero emulated
time** and therefore cannot move the alignment it is measuring
([[apparatus-is-part-of-the-measurement]]).

### 2.2 🔴 The mangled slot is the only slot in 245 whose PC is `$1197`

The phase-O batch (`SPRITE_BEHAV`, reset `("NEW","CLS")`), 245 injection slots,
one mangle — case 22, slot 156, `10 ON ERROR GOTO 40` → `N ERROR GOTO 40`:

| slot | PC | opcode at PC | HL | DE | GETPNT | PUTPNT |
|---|---|---|---|---|---|---|
| 154 | `$11A0` | `$18` | `$FBF4` | `$FBF4` | `$FBF4` | `$FBF4` |
| 155 | `$11A0` | `$18` | `$FBF4` | `$FBF4` | `$FBF4` | `$FBF4` |
| **156** | **`$1197`** | **`$ED`** | **`$FBF4`** | `$FBF4` | `$FBF4` | `$FBF4` |
| 157 | `$11A0` | `$18` | `$FC04` | `$FC04` | `$FC04` | `$FC04` |

230 of 245 slots sit at `$11A0`; fifteen sit elsewhere; **exactly one** sits at
`$1197`, and it is the mangled one.

### 2.3 The address map, from the published entry point and C-BIOS's own source

`$009F` (`CHGET`, published MSX BIOS jump table) holds `C3 8F 11`. Reading 24
bytes from `$118F` on the subject machine gives a byte stream that matches, one
for one, the `chget` routine in C-BIOS's **source** — which this repo already
carries patches against (`cbios-repack/`, pinned `v0.29-3-gb5ad9cb`). No
reference ROM was disassembled; C-BIOS is BSD-2 source we build ourselves, and
the *reference* machine is used below only as a zero-RED outcome control
([[no-reference-rom-disasm]]).

```
$118F  chget        CD C2 FD      call H_CHGE
$1192               E5            push hl
$1193               D5            push de
$1194  chget_wait   2A FA F3      ld hl,(GETPNT)
$1197               ED 5B F8 F3   ld de,(PUTPNT)     <-- THE BOUNDARY
$119B               E7            rst $20            (DCOMPR: HL vs DE)
$119C               20 04         jr nz,chget_char
$119E               FB            ei
$119F               76            halt
$11A0               18 F2         jr chget_wait
$11A2  chget_char   7E            ld a,(hl)
```

`$11A0` is where openMSX parks PC while the CPU is halted (the instruction after
`halt`), which is why 230 slots read it.

### 2.4 🔴 The trigger, stated exactly

> The injection callback must land on the **single instruction boundary at
> `$1197`** — after `ld hl,(GETPNT)`, before `ld de,(PUTPNT)`.

At that boundary `HL` holds the **pre-injection** `GETPNT`. The buffer was
drained, so that value is `KEYBUF + len(previous injection incl. CR)`. The
harness then writes the new line at `KEYBUF`, sets `GETPNT = KEYBUF` and
`PUTPNT = KEYBUF + n`. The CPU resumes at `$1197`:

* `ld de,(PUTPNT)` reads the **new** `PUTPNT`;
* `rst $20` compares the **stale** `HL` against it — unequal, so "a key is
  waiting";
* `ld a,(hl)` reads `KEYBUF + N`, **not** `KEYBUF`.

Every other boundary in that loop is safe, and for a reason:

| PC at injection | why it is harmless |
|---|---|
| `$1194` | `HL` is loaded *after* the write — fresh |
| `$119B`, `$119C`, `$119E` | both `HL` and `DE` are stale and **equal**, so `rst $20` says Z → `halt` → `jr` → both reloaded |
| `$119F`, `$11A0` | halted / about to re-enter the loop — both reloaded |
| anywhere else | the CPU is not in `chget`; it reaches `chget_wait` after the write |

So the hypothesis on file was inverted: **nothing restores a saved `GETPNT`.**
C-BIOS writes `GETPNT` in exactly three places (init, `chget`'s post-read
increment, and never in `kilbuf`, which writes `PUTPNT`). What survives the
injection is not a saved pointer in memory but a **latched copy in HL**, one
instruction ahead of the compare that would have invalidated it.

This explains, at once:

* **the law** — `N` is whatever `GETPNT` held, which is where the drained
  predecessor left it;
* **the floor** — one boundary out of a whole `step` is rare, and *which*
  boundary the callback lands on is a pure alignment question, which is why
  position and predecessor content both move it and neither explains it;
* **why `step=5.0` "fixes" one case and `step=1.2` another** — a different number
  lands the callback on a different boundary. A number that moves a race is not a
  guard [[deterministic-mangle-is-still-a-mangle]];
* **why the reference never fires** — its `chget` is not this code.

### 2.5 A second, unobserved window — named, not hidden

If the buffer is **not** drained the CPU can be inside `chget_char`
(`$11A2`–`$119D`), holding a stale `HL` it is about to write back to `GETPNT`.
That window is ~7 instructions wide and produces a swallow of `HL - KEYBUF + 1`.
It has never been observed, because the buffer was measured drained before
**490/490** injections (D-DELIVER §8.1) — the `step` is three orders of magnitude
longer than a line takes to consume. It is a real hole in the rule below and it
is stated, not assumed away.

---

## 3. Design

### 3.1 The rule

> The harness may not move `GETPNT` **backwards**. A CPU that has already latched
> it into `HL` cannot see the move, and will read the fresh buffer from the old
> offset.

### 3.2 The fix — write where the machine is already looking

`__key` currently writes the payload at `KEYBUF` and sets
`GETPNT = KEYBUF`, `PUTPNT = KEYBUF + n`. It will instead write the payload
**starting at the current `GETPNT`**, wrapping at `KEYBUF + 40`, and set
`PUTPNT = GETPNT + n` (wrapped). **`GETPNT` is not written at all.**

This is race-free *by construction*, not by alignment:

* `GETPNT` is only ever stale-latched into `HL` **while it still equals its
  in-memory value** (C-BIOS writes it one instruction after the read that would
  have used it), so a latched `HL` points exactly at the first byte of the new
  payload.
* The discard semantics are unchanged: anything pending is overwritten and
  `PUTPNT` is moved to the end of the new payload, exactly as today.
* The size limit is unchanged: a 40-byte circular buffer holds 39 bytes
  unambiguously, and `MAX_DIRECT` (38) + CR is 39.

⚠️ It does **not** close §2.5's window. Both delivery oracles stay armed; that is
what they are for.

### 3.3 What does NOT change

Both oracles, the repair path, `ZEROBAS_ECHOGUARD=off`, `verify_delivery=False`.
A fix that removes the race does not remove the need to detect it — the guards
are the instrument that would notice if this analysis is incomplete, and §2.5
says it is.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline, on the unchanged tree at `121b05b`, `make repack-machine` run first.
Reference `Philips_VG_8020`, subject `C-BIOS_MSX1_EU_REPACK_DISK`.

### 4.1 The biconditional — predicted before running any of these

Phase O is the discovery run (§2.2) and is **not** counted as a prediction.
Everything below was written down first.

| # | run | predicted |
|---|---|---|
| **P1** | phase Q2 (`G8_BEHAV`), zb, reset `("NEW","CLS")` | **exactly 2** slots at PC `$1197`, and they are exactly the two D-ECHO named — case 12 (`30 SCREEN0:PRINT"ZK";A:END`) and case 22 (`10 ON ERROR GOTO 40`). No other slot at `$1197` |
| **P2** | phase O, zb, reset `("NEW","CLS:CLS")` | **exactly 1** slot at `$1197`; it is the mangled one; `HL = $FBF8` (`KEYBUF+8`) and the swallow is 8 |
| **P3** | phase O, zb, reset `("NEW","CLS:REM123456")` | **exactly 1** at `$1197`; `HL = $FBFE` (`KEYBUF+14`); swallow 14 |
| **P4** | phase O, zb, reset `("NEW","CLS:REM123456789012345678")` — the reset D-ECHO measured **clean** | 🎯 **ZERO** slots at `$1197`, and zero mangles. This is the direction that makes it a biconditional and not a coincidence |
| **P5** | phase O + Q2, `Philips_VG_8020` | zero mangles from either oracle (zero-RED control). Its PCs are recorded and **not interpreted** |
| **P6** | every slot in every run above | `GETPNT == PUTPNT` (drained), and at a `$1197` slot `HL == GETPNT` and the swallow `== GETPNT - KEYBUF` |

### 4.2 Predicted RED — the knives

The instrument for K1–K4 is a **CPU breakpoint that performs the injection**:
`debug set_bp <addr> {} { … }` fires at that address, so the callback lands on
that boundary **by construction** instead of by luck. That converts a 1-in-245
race into a deterministic experiment, which is the only honest way to claim
causation from a single observation.

| knife | cut | predicted RED | predicted GREEN control |
|---|---|---|---|
| **K1** | inject from a breakpoint at **`$1197`** | the line is mangled **every time**, swallow `== GETPNT - KEYBUF` exactly | the same batch, injected on the normal `after time` schedule, mangles nothing |
| **K2** | inject from a breakpoint at **`$1194`** — one instruction earlier | **zero** mangles | K1 in the same session mangles |
| **K3** | inject from a breakpoint at **`$119B`** (after `ld de`, before the compare) | **zero** mangles | as K2 |
| **K4** | inject from a breakpoint at **`$11A0`** (halted) | **zero** mangles | as K2 |
| **K5** | the fix in place, K1's breakpoint injection repeated | 🎯 **zero** mangles — 100 % → 0 % on the one experiment that reproduces at will | reverting `__key` to the old body brings K1 back to 100 % |
| **K6** | the fix in place, `__key` writing at `KEYBUF` but *not* writing `GETPNT` (half the change) | K1 mangles again — proving **both** halves are load-bearing, not just the pointer | K5 stays zero |
| **K7** | zero-RED: the fix in place, `Philips_VG_8020`, phases O and Q2 | zero mangles (it never had any) — a fix that reddens the reference is not a fix | the zb half goes from 3 announcements to 0 |

### 4.3 Predicted GREEN after the change

| | predicted |
|---|---|
| phase O, zb | **0** mis-deliveries (was 1), verdicts unchanged |
| phase Q2, zb | **0** (was 2), verdicts unchanged |
| `make graphics-acceptance` | **290/290, exit 0**, and **zero** mis-delivery announcements (was four) |
| the six `direct`-mode suites D-ECHO found | **zero** echo announcements (was one each) |
| `ORACLES DISAGREE` | not emitted |
| `make unit-test` | 57/57 plus the new rows |

Corpus, unchanged and all exit 0: unit · deadcode 0/0 · preflight-check 0
unguarded · msgexact 55/55 · lnblank **536/536 at `REPEAT=2`** · logicops ·
array · linemax 60/60 · direct-ctrl 40/40 · diskbasic · float · string · error ·
error-trap · abort · stop-trap · arrdim · clearpool · input · input-devices ·
time · intarg · math · missing · width · sound · play · beep · str-domain.
**No ROM is rebuilt; `make -q build/zerobas-main-eu.rom` exit 0 throughout.**

⚠️ **The fix changes the delivery alignment of every probe in the tree.** That is
the whole blast radius, and the corpus is the only thing that can price it. If
any suite moves a verdict, the fix does not land and this spec records the row.

---

## 4bis. What landed, and what it measured

`probes/lib/omsx_repl.py` (`key_proc`, factored out of `_tcl` so the gate scores
the shipped injector rather than a copy), a new `probes/lib/latch_check.py`, and
one Makefile target. **No `basic/`, `sub/`, `disk/` or `tape/` source touched;
`make -q build/zerobas-main-eu.rom` exit 0 throughout, so no ROM was rebuilt.**

### 4bis.1 The biconditional — P1, P2, P3, P5, P6 hit exactly

Across seven instrumented batches: **2039 slots, 6 at `$1197`, 6 mis-deliveries,
and not one mis-delivery at any other slot.** The buffer was drained before
2039/2039 injections and `HL == GETPNT` at all 6 fatal slots. Phase Q2's slot 88
is the sharpest number in the slice: the swallowed line's predecessor is
`20 SCREEN0:A=BASE(10)`, 22 bytes with its CR, and `HL` read `KEYBUF + 22`.

### 4bis.2 🔴 P4's prediction was WRONG, and it corrects a reading in D-ECHO

The 26-byte predecessor — D-ECHO's *"the batch delivered clean"* row — **does**
hit the trigger, `HL = KEYBUF + 26`. The swallow simply exceeds the 20-byte
payload, so the read runs past it, wraps the circular buffer, and delivers the
real line **after** garbage. The echo oracle sees the typed text on screen and
says clean; the stored oracle reports `0, 10, 20, 30, 40` — a spurious line `0`.

D-ECHO read that row from `mis_echoed` alone. Two oracles, and the one that was
asked was the blind one [[readout-blind-to-its-own-subject]]. The lesson is
sharper than the correction: **the trigger and the damage are different
questions.** Every fatal slot swallows `N`; whether that is visible at all
depends on how `N` compares with the payload length.

### 4bis.3 The knives, scored

K1–K7 hit exactly, with the swallow law reproduced **on demand** at four
predecessor lengths (4, 8, 9, 14 → `RINT"ABCDEFG"`, `"ABCDEFG"`, `ABCDEFG"`,
`FG"`) and the three neighbouring boundaries delivering intact under the
identical predecessor. K6 — the plausible half-fix, "stop writing `GETPNT`" —
mangles exactly as before, which is why the fix is *write at `GETPNT`* and not
*don't write `GETPNT`*. Full table in the characterisation doc §6–§7.

**Three knives this spec did not pre-register** were added once the gate existed,
and are aimed at the gate rather than at the machine: K8 reverts the fix under
the gate's row B (**6/9, exit 1**), K9 hands row A the *fixed* injector so the
positive control loses its subject (**6/9, exit 1**), K10 breaks the byte
signature (**refuses to judge**, non-zero). K9 is the K2-shaped one: emission,
call site and judgement all intact, only the subject removed.

### 4bis.4 🔴 Fixing the fault silenced the only control the oracles had

D-ECHO §3.5 is explicit that cross-oracle disagreement was the standing positive
control for both delivery oracles, precisely because a batch of identical cases
does not reproduce the race. Removing the race makes both oracles permanently
silent — still wired in, still called on every suite, and with nothing left that
would notice if they stopped working. That is
[[gate-can-be-green-while-measuring-nothing]] arriving *as a consequence of
success*, which is the version nobody looks for.

`make latch-check` is the replacement, and it is **not** optional. It does not
wait for the race, it forces it, and its row A requires the frozen pre-fix
injector to **still fail** — so if the experiment ever stops reproducing, the
gate goes red rather than quietly certifying nothing.

### 4bis.5 Corpus

Run sequentially, no two emulator gates at once, all exit 0: unit · deadcode ·
preflight-check · **latch-check 9/9** · msgexact · kwsweep · sysvarsweep ·
logicops · array · linemax · direct-ctrl · string · missing · width · float ·
arrdim · clearpool · error · error-trap · abort · stop-trap · input ·
input-devices · time · intarg · math · sound · play · beep · cursor · binfre ·
str-domain · badfnum · lof · graphics-floor · subrom · interval/key/sprite/strig
-trap · diskbasic · bdos · **graphics-acceptance PASS** · **lnblank-acceptance
`REPEAT=2` 536/536, allowlist EMPTY** · lnblank-echo. The five re-pointed trap
gates were re-run after §6's change, and `latch-check` after its own last edit.

🎯 **Zero `MIS-ECHOED`, `MIS-DELIVERED`, `ORACLES DISAGREE` or `APPARATUS FAILURE`
lines anywhere in either run** — where D-ECHO's corpus announced one per suite in
six `direct`-mode suites and four in `graphics-acceptance`. That is the fix's
whole claim, checked across the corpus rather than on the batch that found it.

⚠️ **`lof-acceptance` exited 2 once, on a single `ORACLE DRIFT` row**
(`wm_app_put`, recorded 61, live `None`; 0 unfiled divergences, 0 mangled). It
did **not** reproduce: two further runs on this tree and one with `HEAD`'s
injector restored all came back **0 drift, exit 0**. Recorded as a flake rather
than attributed — it is not attributed to the fix, and it is not dismissed
either.

⚠️ **`lnblank-say-acceptance` (204 rows, ~3.5–4 h) was NOT run.** It is a standing
corpus member and it is in the blast radius; it was left out on cost, not on an
argument that it is safe. Filed in `TODO.md`.

---

## 5. The gate

[`probes/lib/latch_check.py`](../probes/lib/latch_check.py), `make latch-check`.
Nine boots, ~40 s, on the `repack-machine` prerequisite every emulator gate
already needs.

* It derives `chget` from the **published** `CHGET $009F` jump-table entry and
  vouches for `chget_wait` with a seven-byte signature. A mismatch **exits
  non-zero saying so** [[guard-that-cannot-judge-must-say-so]]; it never scores a
  guessed address.
* **Row A** runs the frozen pre-D-LATCH injector and requires it to mangle, with
  the exact `HL` the swallow law predicts. That is the anti-vacuity clause.
* **Row B** imports `key_proc` from `omsx_repl`, so the thing scored cannot drift
  from the thing shipped [[coverage-gate-cannot-see-a-gutted-guard]].
* **Row C** checks the three never-fatal boundaries still deliver.
* **Subject-only.** Locating the same boundary in the reference would need a
  disassembly this project does not do [[no-reference-rom-disasm]]; the
  reference's role is the zero-RED outcome control it has always been.

---

## 6. Coverage limits, stated

* **The second window is open** (§2.5) and both oracles stay armed because of it.
* **One probe file still carries its own pre-D-LATCH `__key`.** Six did. The five
  trap probes (`interval`, `key`, `sprite`, `strig`, `stop`) each held a
  byte-identical copy of the old injector; each now calls `key_proc()` and their
  five gates were re-run. `probes/disk/disk_probe_getput.py` still has one, and
  it is **left alone deliberately**: no Makefile target runs it, so a change
  there could not be scored, and an unverifiable edit to a probe is worse than a
  filed one [[gate-can-be-green-while-measuring-nothing]]. D-ECHO §6 filed this
  class as a *coverage* limit; it is a **correctness** limit now, because the
  shared injector no longer has the race and a copy still does.
* **`$1197` is not a stable number.** It is derived per run and signature-checked;
  a C-BIOS bump moves it and the gate says so.
