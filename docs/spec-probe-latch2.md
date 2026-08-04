# D-LATCH2 — the second window is real, and the first fix did not close it

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— `probes/lib/omsx_repl.py`, `probes/lib/latch_check.py` and their host unit
tests only, so no sign-off gate applies. Written up as a slice anyway, with
predicted RED/GREEN sets fixed at exact values before the change.

Closes the last open item of the delivery-race arc, filed by D-LATCH
([`docs/spec-probe-latch.md`](spec-probe-latch.md) §2.5, §6;
[`docs/latch-trigger-characterization.md`](latch-trigger-characterization.md) §9)
and carried in `TODO.md` as *"THE SECOND LATCH WINDOW IS OPEN AND HAS NEVER BEEN
OBSERVED"*:

> If the buffer is **not** drained the CPU can be inside `chget_char`
> (`$11A2`–`$119D`), holding a stale `HL` it is about to write back to `GETPNT`.
> That window is ~7 instructions wide and produces a swallow of
> `HL - KEYBUF + 1`. It has never been observed.

Companion: [`docs/latch2-window-characterization.md`](latch2-window-characterization.md).

---

## 1. What D-LATCH left standing, and the one thing it got wrong about it

D-LATCH closed the **first** window: an `after time` callback landing on the one
instruction boundary at `$1197` saw an injector that moved `GETPNT` *backwards*
under a CPU that had already latched it into `HL`. The fix — `key_proc` writes at
the **current** `GETPNT` and never moves it — is immune there by construction,
forced from 100 % to 0 % at that address.

It said explicitly that this **did not** close the second window, and it named
the second window's precondition: a **non-drained** buffer. It then recorded that
the buffer was measured drained before **2039/2039** injections (D-LATCH) and
**490/490** (D-DELIVER), *"a measurement, not a proof"*, and left both delivery
oracles armed because of it.

🔴 **The filed statement of the window is wrong in one load-bearing detail, and
wrong in the direction that makes the fault look like someone else's.**
`HL - KEYBUF + 1` is the swallow of the **pre-D-LATCH** injector. It is not the
swallow of the shipped one. The shipped injector has its own swallow in this
window, it is **exactly 1**, and no arithmetic on file predicts it
([[filed-justification-is-a-claim]] — the third time in three slices that a filed
claim rested on an unchecked justification).

---

## 2. The map, derived per run and vouched for

`$009F` (`CHGET`, published MSX BIOS jump table) holds `C3 8F 11`. Forty bytes
read from `$118F` on the subject machine, this run:

```
cdc2fde5d52afaf3ed5bf8f3e72004fb7618f27ef5237dfe18200321f0fb22faf3f1d1e1c9e5d5c5
```

which decodes one instruction for one onto `chget` in C-BIOS's own **source**
(`~/projects/cbios/src/main.asm:1691`, pinned `v0.29-3-gb5ad9cb`, BSD-2 source
this repo already carries patches against). No reference ROM was disassembled
[[no-reference-rom-disasm]].

```
$118F  chget         CD C2 FD      call H_CHGE
$1192                E5            push hl
$1193                D5            push de
$1194  chget_wait    2A FA F3      ld hl,(GETPNT)        <-- HL latched here
$1197                ED 5B F8 F3   ld de,(PUTPNT)        <-- D-LATCH's trigger, CLOSED
$119B                E7            rst $20               (DCOMPR)
$119C                20 04         jr nz,chget_char
$119E                FB            ei
$119F                76            halt
$11A0                18 F2         jr chget_wait
$11A2  chget_char    7E            ld a,(hl)             <-- the SECOND window opens
$11A3                F5            push af
$11A4                23            inc hl
$11A5                7D            ld a,l
$11A6                FE 18         cp $18                (low byte of KEYBUF+40)
$11A8                20 03         jr nz,chget_nowrap
$11AA                21 F0 FB      ld hl,KEYBUF          <-- reached ONLY on wrap
$11AD  chget_nowrap  22 FA F3      ld (GETPNT),hl        <-- the window closes AFTER this
$11B0                F1            pop af
$11B1                D1            pop de
$11B2                E1            pop hl
$11B3                C9            ret
```

🔴 **The filed range `$11A2`–`$119D` is not an address range at all** — its second
endpoint is *below* its first. The window is `$11A3`–`$11AD`, and §4 says why
`$11A2` itself is on the safe side of it.

`chget_char` is **only ever entered when `GETPNT != PUTPNT`**, so a CPU inside it
is a CPU with a non-drained buffer, and the in-memory `GETPNT` stays stale until
`$11AD` executes. That is the whole of §3.

---

## 3. Manufacturing a non-drained buffer — the precondition, by construction

Every reading in D-LATCH and D-DELIVER had `GETPNT == PUTPNT` at the moment of
injection, because the `step` between injections is three orders of magnitude
longer than a line takes to consume. Waiting for the opposite is hopeless.

**A breakpoint inside `chget_char` cannot be hit unless the buffer is
non-drained.** That is not a lucky property of the harness, it is the branch at
`$119C`: the CPU reaches `$11A2` only when `rst $20` said `HL != DE`, i.e. only
when `GETPNT != PUTPNT`. So the manufacture and the force are the *same*
instrument:

1. In one atomic callback: arm `debug set_bp <addr> {} { fire }`, **then** inject
   a predecessor line.
2. The CPU resumes, finds a key waiting, enters `chget_char`, and hits the
   breakpoint — once per character consumed. A hit counter selects the `k`-th.
3. `fire` records `reg pc`, `reg hl`, the A register, `GETPNT` and `PUTPNT`
   **before writing a byte**, then injects the target line and disarms itself.

⚠️ **The precondition is read, not assumed.** A run whose recorded `GETPNT ==
PUTPNT` measures nothing and is scored as such — that reading is the entire
difference between this slice and the 2039 that came before it.

### 3.1 The readout: the stored line number IS the swallow count

The predecessor is **ten spaces**. Whatever prefix the machine has already
consumed is therefore invisible to the tokeniser, which skips leading blanks —
so the typed line reduces to the payload with its head bitten off, and nothing
else. The payload is `54321 PRINT"X"`:

| swallow | typed | `__lines` (the standing stored-program oracle) |
|---|---|---|
| 0 | `54321 PRINT"X"` | `54321` |
| 1 | `4321 PRINT"X"` | `4321` |
| 2 | `321 PRINT"X"` | `321` |
| 3 | `21 PRINT"X"` | `21` |
| 4 | `1 PRINT"X"` | `1` |
| ≥5 | ` PRINT"X"` | `''` (direct mode; nothing stored) |

No screen decoding, no new oracle: the swallow is read off the existing delivery
oracle as a **number**. The screen is captured as a second opinion and is not the
judgement [[readout-blind-to-its-own-subject]].

### 3.2 The discovery run — not a prediction

Breakpoint `$11A3`, hit 1, shipped `key_proc`, predecessor 10 spaces:

```
pc 11A3   hl FBF4   a 32   getpnt FBF4   putpnt FBFF   chain 4321
screen:  ZB 4321 PRINT"X"
```

**Non-drained: 11 bytes pending.** `HL == GETPNT`. The shipped injector lost the
head of the line. Everything below was written down before it was run.

---

## 4. The mechanism, stated as arithmetic

Let `G` = in-memory `GETPNT` when `fire` runs, `base` = where the predecessor was
written, `k` = the hit number, `n` = payload length incl. CR (15).

The two injectors differ only in **where they write**:

| injector | writes payload at | sets `GETPNT` | `base` for the predecessor |
|---|---|---|---|
| `OLD_KEY` (pre-D-LATCH, frozen in the gate) | `KEYBUF` | `:= KEYBUF` | always `$FBF0` |
| `key_proc` (shipped since D-LATCH) | `G` | never | wherever `GETPNT` stood (`$FBF4` here) |

At hit `k`, `G = base + k - 1` — `GETPNT` advances one per **completed**
character, and this one is not complete. `HL` is `G` at `$11A2`–`$11A4` and
`G + 1` from `$11A5` on. The CPU then executes `ld (GETPNT),hl` at `$11AD`,
**overwriting whatever the injector just did**.

* **`$11A2` is safe for `key_proc`**: `ld a,(hl)` has not run, `HL == G`, and the
  payload was written *at* `G` — so the CPU reads `payload[0]` and stores
  `G + 1`. The injection is invisible to the write-back and correct anyway.
* **`$11A3`–`$11AD` are fatal**: `A` already holds the *pre-injection* byte
  (it is delivered as a stray character no matter what), and the write-back
  advances `GETPNT` one past the payload's first byte.
* **`$11B0` onwards is safe**: `ld (GETPNT),hl` has already run, so the injector
  reads the settled `GETPNT` and writes where the CPU will actually look.

Hence the two swallows, and they are **not** the same number:

> **`key_proc` swallows exactly 1, independent of `k`. `OLD_KEY` swallows `k`.**

The stray leading character is not the fault and is not fixable by any injector:
the machine received it before the injection existed.

### 4.1 The wrap sub-window — reachable only because of D-LATCH's fix

`$11AA` (`ld hl,KEYBUF`) is entered only when `l == $18`, i.e. only when the
consuming pointer crosses `KEYBUF + 40`. `OLD_KEY` resets `GETPNT := KEYBUF` on
every injection and a payload is at most 39 bytes, so **`OLD_KEY` can never reach
it**. `key_proc` walks the circular buffer, so it crosses that address every ~40
injected bytes.

🎯 **D-LATCH's fix opened a sub-window its predecessor could not reach.** That is
the sharpest thing this slice has to say about the previous one, and §5 predicts
it at an exact value rather than asserting it.

---

## 5. Predicted RED and GREEN — fixed at exact values before the change

Subject `C-BIOS_MSX1_EU_REPACK_DISK`, `make repack-machine` run first, tree clean
at `53825bf`, `make -q build/zerobas-main-eu.rom` exit 0. Predecessor 10 spaces,
payload `54321 PRINT"X"`. **Reference machine not driven** — locating the same
boundary in it would need a disassembly this project does not do; its role stays
the zero-RED outcome control it has always been.

### 5.1 M1 — the boundary walk, `k = 1`, both injectors

`chain` predicted for every instruction boundary in and around the window.

| # | bp | instruction | `key_proc` | `OLD_KEY` |
|---|---|---|---|---|
| M1a | `$11A2` | `ld a,(hl)` | **`54321`** | **`54321`** |
| M1b | `$11A3` | `push af` | **`4321`** | **`4321`** |
| M1c | `$11A4` | `inc hl` | **`4321`** | **`4321`** |
| M1d | `$11A5` | `ld a,l` | **`4321`** | **`4321`** |
| M1e | `$11A6` | `cp $18` | **`4321`** | **`4321`** |
| M1f | `$11A8` | `jr nz` | **`4321`** | **`4321`** |
| M1g | `$11AD` | `ld (GETPNT),hl` | **`4321`** | **`4321`** |
| M1h | `$11B0` | `pop af` | **`54321`** | **`54321`** |
| M1i | `$11B3` | `ret` | **`54321`** | **`54321`** |

M1a, M1h and M1i are the **GREEN controls**: a walk in which everything mangles
proves only that the machine dislikes being interrupted.

### 5.2 M2 — the swallow law, `k = 4`: the two injectors separate

| # | bp | `key_proc` | `OLD_KEY` |
|---|---|---|---|
| M2a | `$11A2` | **`54321`** (swallow 0) | **`21`** (swallow 3 = `k-1`) |
| M2b | `$11AD` | **`4321`** (swallow 1) | **`1`** (swallow 4 = `k`) |
| M2c | `$11B0` | **`54321`** | **`54321`** |

### 5.3 M3 — the precondition, read at every fired hit

| # | predicted |
|---|---|
| M3a | `GETPNT != PUTPNT` at **every** recorded hit, in every run in §5.1–§5.4 |
| M3b | `PUTPNT - GETPNT == 12 - k` exactly (11 bytes pending at `k = 1`, 8 at `k = 4`) |
| M3c | `HL == GETPNT` at `$11A2`–`$11A4`; `HL == GETPNT + 1` at `$11A5`–`$11AD` |
| M3d | `A == 32` (the predecessor's space) at every boundary from `$11A3` on |
| M3e | `pc` equals the armed breakpoint address in every run |

### 5.4 M4 — the wrap sub-window (§4.1)

Filler `31 spaces + CR` consumed first, so `GETPNT` stands at `$FC14`;
predecessor 10 spaces; fire at `k = 4`, where `HL = $FC17` and `inc hl` wraps.

| # | bp | `key_proc` | `OLD_KEY` |
|---|---|---|---|
| M4a | `$11AA` | **`4321`** — hit, and mangled | **never hit** (`hits_total 0`, `chain ''`): structurally unreachable |
| M4b | `$11AD` (wrapped) | **`4321`** | not reachable |

### 5.5 The fix, and its predicted GREEN

> **The injector may not write into a buffer the machine is still consuming.**
> A non-drained buffer is the exact and only precondition of this window, and it
> is readable from two published sysvars on any machine.

`__key` re-reads `GETPNT`/`PUTPNT`; while they differ it **defers** itself by a
small emulated interval, up to a bounded number of attempts, and only then
injects anyway.

⚠️ **The bound is load-bearing, not decoration.** `omsx_repl.py:133` records a
standing contract: during a cassette LOAD/SAVE the harness keeps injecting for
10–30 emulated seconds while the machine is *not* reading the keyboard, and each
`__key` **overwrites whatever is still pending**. An unbounded wait would convert
that documented collapse into a hang. The bounded fallback preserves it exactly.
The states in which the bound is exhausted are the states in which the CPU is
**not** inside `chget_char` at all, which is why the residual in §7 is what it is.

| # | after the fix | predicted |
|---|---|---|
| F1 | every row of M1, M2, M4 | **`54321`** — 100 % → 0 % on every fatal boundary, both `k`, wrap included |
| F2 | the deferral counter, at every fatal boundary | **≥ 1** — the guard is proved to have *fired*, not merely to have been present |
| F3 | `make latch-check` rows A/B/C (the `$1197` window) | **unchanged, 9/9** — the buffer is drained there, so the guard does not fire and the Tcl behaves identically |
| F4 | a drained injection (every existing probe in the tree) | **byte-identical delivery** — two extra `debug read memory` calls, zero emulated time, no deferral, no alignment change |

### 5.6 Predicted RED — the knives

| knife | cut | predicted RED | GREEN control |
|---|---|---|---|
| **K1** | the fix in place, forced at `$11AD`, `k = 1` | **`54321`** where the frozen body gives `4321` | the frozen body in the **same session** still gives `4321` — the fault must reproduce in the run that claims to have fixed it [[knife-runner-false-negatives]] |
| **K2** | the drain guard's **body gutted** (condition evaluated, result discarded), emission and call site intact | the new gate's row E goes **RED** | rows A/B/C stay green — a gutted guard must not be invisible [[coverage-gate-cannot-see-a-gutted-guard]] |
| **K3** | the new gate's row D handed the **fixed** injector (its subject removed) | row D **RED**, exit non-zero | rows A/B/C/E unmoved [[fixing-the-fault-silences-the-control]] |
| **K4** | the `chget_char` byte signature set to a value that cannot match | **refuses to judge**, exit non-zero | the unmodified signature judges [[guard-that-cannot-judge-must-say-so]] |
| **K5** | the retry bound set to 0 (defer never, inject always) | row E **RED** — the bound's fallback is reachable and the guard is what delivers, not the deferral's mere existence | row F unmoved |
| **K6** | the deferral made unbounded, then a non-consuming machine | the tape contract breaks (injection never lands). **Not shipped**; run once to price the bound |

### 5.7 The gate, and its live subject

⚠️ Fixing this fault removes the only subject the new rows have — the same trap
D-LATCH walked into and the reason `latch-check` row A exists at all
[[fixing-the-fault-silences-the-control]]. So the D-LATCH-era injector is
**frozen into the gate verbatim** as `GETPNT_KEY`, exactly as its predecessor was:

| row | subject | forced at | must |
|---|---|---|---|
| **A** | `OLD_KEY` (pre-D-LATCH, frozen) | `$1197` | MANGLE — unchanged |
| **B** | `key_proc` | `$1197` | DELIVER — unchanged |
| **C** | `key_proc` | 3 safe boundaries | DELIVER — unchanged |
| **D** | `GETPNT_KEY` (pre-D-LATCH2, frozen) | `$11A3`, `$11AD` | **MANGLE (`4321`)** — the new positive control |
| **E** | `key_proc` | `$11A3`, `$11AD` | **DELIVER (`54321`)** |
| **F** | `GETPNT_KEY` | `$11B0` | **DELIVER (`54321`)** — the far-side GREEN control |

Predicted cost: 15 rows, one boot each, **≈ 20 s** — re-measured, not inherited
[[stale-cost-estimate-defers-gates]].

### 5.8 Corpus, predicted unchanged

`unit-test` (57 + the new rows) · `deadcode` 0/0 · `preflight-check` 0 unguarded
· `injector-check` 0 offenders / 256 files · `latch-check` 15/15 ·
`graphics-acceptance` 290/290 · `direct-ctrl` 40/40 · `diskbasic-acceptance`
34/34 · `lnblank-acceptance` `REPEAT=2` 536/536. **No ROM rebuilt**;
`make -q build/zerobas-main-eu.rom` exit 0 throughout. Per F4 the delivered Tcl
is behaviourally identical on a drained buffer, so a moved verdict anywhere is a
falsification of F4, not a cost of the fix.

---

## 6. What landed, and what it measured

`probes/lib/omsx_repl.py` (`key_proc` + two constants), `probes/lib/latch_check.py`
(rows D/E/F and a second frozen body), `tools/check_probe_injectors.py` (one
named exemption) and a new `tests/test_key_drain_guard.py`. **No `basic/`,
`sub/`, `disk/` or `tape/` source touched; `make -q build/zerobas-main-eu.rom`
exit 0 throughout, so no ROM was rebuilt.**

### 6.1 The answer to the question, in one line

> **The window is real, `key_proc` was vulnerable, and its swallow is 1 — a
> number no arithmetic on file predicted.**

**44 of 46 predicted values hit exactly** (M1 18/18, M2 6/6, M4 4/4, F1/F2 and
K1 22/22, K2–K5 4/4). The two misses are both mine, both in §5.3, and both
recorded in the characterisation doc §5.1:

* **M3b partial** — `PUTPNT - GETPNT == 12 - k` is exact inside the window and
  `11 - k` past `$11AD`. The off-by-one *is* the write-back, appearing in an
  independent reading.
* **M3d wrong** — I predicted the delivered character sits in `A` throughout.
  `push af` puts it on the **stack** and `ld a,l` overwrites `A`. The correction
  matters: the stray leading character survives anything an injector does to
  memory, which is why the fix targets the precondition and not the payload.

### 6.2 🔴 Three things on file were wrong, all in the safe direction for the filer

* **The swallow.** `HL - KEYBUF + 1` is the *pre-D-LATCH* injector's number.
  The shipped injector swallows **exactly 1, independent of `k`** — measured at
  seven boundaries and two `k` values [[filed-justification-is-a-claim]].
* **The range.** `$11A2`–`$119D` is not a range; its second endpoint is below
  its first. It is `$11A3`–`$11AD`, and `$11A2` is on the **safe** side.
* **The cost.** The gate's own *"nine boots, ~40 s"* is **2.05 s**, timed on
  HEAD's own file. My §5.7 then predicted ≈20 s for 15 rows and measured **3.1 s
  for 16** — a stale figure propagating into the estimate of someone citing
  [[stale-cost-estimate-defers-gates]] while writing it.

### 6.3 🎯 D-LATCH's fix opened a sub-window its predecessor could not reach

`$11AA` (`ld hl,KEYBUF`) is entered only when the consuming pointer crosses
`KEYBUF + 40`. `OLD_KEY` resets `GETPNT := KEYBUF` every injection and a payload
is at most 39 B, so it can **never** get there — measured, `hits_total 0`.
`key_proc` walks the circular buffer and mangles there. Neither injector
dominates the other: this one is strictly `key_proc`'s.

### 6.4 The corpus found a false positive in a different gate

`make injector-check` went red on this slice's own host test, whose
`debug write memory` is the **needle of a regex** and not an emission: a gate
that detects injectors classifies its own detector as one. Closed as a fourth
named structural exemption rather than by renaming the needle to slip past it
(characterisation §10.1) [[echo-guard-false-positives-found-by-corpus]].

---

## 7. Coverage limits, stated

* **The residual, exactly.** The guard defers while non-drained, bounded at 4×
  the buffer's own worst-case drain. What survives is a machine still
  non-drained after 80 ms — i.e. one that is *not consuming*, hence not inside
  `chget_char` — whose final attempt still lands in the 11-byte window. Not
  zero; not reachable by the states the cassette contract describes.
* **Subject-only, and portable anyway.** The gate drives only the repack machine
  [[no-reference-rom-disasm]]. The *fix* is portable because it reads two
  published sysvars rather than testing a PC range — a PC-range guard would have
  been subject-only by construction, and would not have worked on the reference.
* **`$11A2` and the addresses are not stable numbers.** Derived per run from
  `$009F` and vouched for by an 18-byte signature spanning the whole window,
  which also pins `KEYBUF` and `GETPNT`. A C-BIOS bump moves them and the gate
  **refuses to judge** (K4).
* **M4a' is not a gate row.** "Zero observations" passes just as happily when
  the probe is broken; it is recorded as a measurement only.

---

## 8. 🔴 Do the two delivery oracles still have a reason to stay armed?

The arc has to answer this, because the reason on file is now **spent**. D-LATCH
kept both oracles armed with an explicit justification — *"⚠️ It does not close
§2.5's window. Both delivery oracles stay armed; that is what they are for."*
§2.5 is closed. Leaving that sentence in place would leave the tree carrying a
justification that no longer holds, which is the exact failure this arc has now
found three times [[filed-justification-is-a-claim]].

**They stay armed, on different grounds, stated here so the next reader inherits
the real ones:**

1. **They were never only about the latch.** D-DELIVER's finding was a case whose
   program was *never stored*; D-ECHO's was a line the machine never echoed.
   Neither needs a race — a line over `MAX_DIRECT`, a case that reset the
   machine, a suite that mis-schedules its own timeline all produce them.
2. **They cost zero emulated time.** A `puts` callback is atomic w.r.t. the CPU,
   so keeping them cannot move the alignment they watch
   [[apparatus-is-part-of-the-measurement]].
3. **What they may NOT be relied on for any more is this race.** Both windows are
   now forced deterministically by `make latch-check`, which is the positive
   control the oracles cannot be [[fixing-the-fault-silences-the-control]]. An
   oracle whose subject never occurs is green while measuring nothing
   [[gate-can-be-green-while-measuring-nothing]] — so `latch-check` is the gate
   that must not be skipped, and the oracles are breadth, not proof.
