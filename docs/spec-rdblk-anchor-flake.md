# Spec — `GET(RDBLK)` intermittent gate row: make the HOST-LEVEL miss legible

Status: ✅ **LANDED 2026-07-30.** Falsification battery **14/14**; repeatability
`ONLY='GET(RDBLK)'` **10/10 with 0 retries**; standing gates **54/54 · 34/34 · 12/12 ·
7/7**; ROMs byte-identical from clean (`52a0b9bc…` / `01ab5dc2…`), walls unchanged at
low 80 B / page 1 49 B, dead-code sweep 0/0. Results in §9.

🔴 **THE G4 CONTROL CAUGHT A DEFECT IN THE FIX ITSELF — see §9.1.** The first
implementation started the stall clock at `t0`, i.e. **before openMSX had launched**,
charging 0.21–0.82 s of process spawn + machine XML + ROM/symbol load to the emulator.
Under load a healthy run was stall-killed. Shipping that would have replaced one
intermittent gate row with a **corpus-wide** one.

**Rev history.**
Rev 2 rewrote §2.2/§4.1/§4.2 around openMSX's `after realtime` + `reverse savereplay`
after the user asked whether I knew about openMSX's TAS/reverse facilities; the two
open scope questions are decided (§4.1b, §4.2).
Rev 3 adds §2.3/§2.4/§4.0: testing the user's pty-exhaustion hypothesis (which does not
hold) surfaced that the corpus opens a CoreAudio device on **every** boot for nothing —
`sound_driver null` is measured neutral and removes a candidate cause of the wedge.
Filed: 2026-07-30
Parent item: [`TODO.md`](../TODO.md) "**`GET(RDBLK)` IS AN INTERMITTENT GATE ROW — FIX THE ANCHOR**"
Background: [`docs/spec-deadcode-gate.md`](spec-deadcode-gate.md) §9.3 (where it was observed),
[`docs/rom-region-structure-review.md`](rom-region-structure-review.md) (parent arc).
Subjects: [`probes/disk/omsx_session.py`](../probes/disk/omsx_session.py),
[`probes/disk/disk_probe_diff.py`](../probes/disk/disk_probe_diff.py),
[`probes/disk/disk_probe_rdblk_roundtrip.py`](../probes/disk/disk_probe_rdblk_roundtrip.py),
[`probes/disk/diskbasic_acceptance.py`](../probes/disk/diskbasic_acceptance.py).

**No ROM source changes.** `build/basic-reloc.rom` and `build/sub.rom` must stay
byte-identical (`52a0b9bc…` / `01ab5dc2…`, recorded 2026-07-30 at `d30ce03`).

---

## 1. What was observed (carried forward, not re-derived)

`make diskbasic-acceptance` returned **33/34** once, with `GET(RDBLK)` printing

```
*** MISALIGNED — diff NOT meaningful ***
  stock reached anchor: NO (looped / never hit occurrence #1)
  ours  reached anchor: YES t=24.1375
```

It then converged standalone **and** on a full re-run of the byte-identical build
(34/34). The subject is innocent; the apparatus is the defect.

🟢 The probe **refused to report a memory diff between two different logical points**.
That refusal is correct and load-bearing, and this spec does not touch it.

## 2. What I measured (2026-07-30, this session)

A scratchpad driver replayed case (a) of the probe **exactly** — same arm, same
`--mem` window, same `settle=40`, same `keys-at=20` — but through `omsx_session`
directly, so the raw `emit` lines and the per-boot **wall** time are visible.
Three repeats × both machines:

| | emulated anchor `t` | wall time per boot |
|---|---|---|
| ours (`National_CF-3300_ZEROBASDISK`) | **24.137504 s, all 3 runs** | 0.4 – 1.2 s |
| stock (`National_CF-3300`) | **24.450109 s, all 3 runs** | 0.6 s |

Two facts fall out, and they redirect the fix:

* **F-1 — the emulated timeline is bit-deterministic.** `--settle`/`--keys-at` are
  openMSX **emulated** time (`after time`), not host seconds, and the anchor is hit at
  the *identical* emulated instant every run. So "fixed wall-clock injection" is not
  what varies, and **the readout is already gated on the `done` sentinel**: the anchor
  is a breakpoint on `done` that snapshots and exits. Fix direction #1 in the TODO is,
  on inspection, already satisfied inside the emulator.
* **F-2 — the only non-deterministic element in the whole path is the HOST.**
  [`omsx_session.py:208`](../probes/disk/omsx_session.py:208) bounds each boot with
  `deadline = time.time() + timeout` and **SIGKILLs the process group** on expiry.
  That kill is **silent**: `run_job_raw` returns whatever lines exist, and a
  host-killed run is byte-for-byte indistinguishable, to every caller, from
  "the machine ran its whole emulated timeline and never hit the anchor."

So the residual defect is **not** the anchor. It is that an *apparatus* event (the host
killed the emulator, or the emulator died early) is silently laundered into a
*subject-shaped* verdict ("a side never reached the anchor"). That is the recurring
arc lesson in its exact form: the whole apparatus is part of the measurement.

### 2.2 openMSX already offers a LIVENESS signal — measure the stall, don't infer it

Probed on openMSX 21.0 (2026-07-30, this session):

* **`after realtime <s> <cmd>` exists** and its callbacks interleave with free-running
  emulation: a 0.25 s realtime heartbeat fired at host `t=0.251 s` with the machine
  already at emulated `t=33.669 s` (≈134× realtime on this host).
* **`reverse start` is already active in every probe run**
  ([`omsx_session.py:103`](../probes/disk/omsx_session.py:103)) and is recording ≈1
  snapshot per emulated second (`reverse status` at t=8 listed 8 snapshots).
* **`reverse savereplay <path>` works**, producing a replayable `.omr` (7.9 KB at t=8).
* `auto_save_replay` did **not** write a file at `interval 2.0` over 12 host seconds.
  Not relied on.

This supersedes the first draft's discriminator. That draft inferred the apparatus
class from "the run emitted no terminal sentinel" — sound, but an **inference**. A
heartbeat is a **measurement**: the host receives `(emulated_t, host_t)` pairs, so
instead of "a side never reached the anchor" the probe can report *"the emulated clock
stopped advancing at t=24.14 after 6.0 s of host time"*.

🔴 **This is where fix-direction #1 actually belongs.** §2 F-1 showed the *readout* is
already sentinel-gated inside the emulator. The elapsed-seconds gate that remained is
the **host-side process deadline**, and a heartbeat is the sentinel for it.

⚠️ **The specific trigger remains UNCONFIRMED and this spec does not claim one.**
A previous session's host-contention theory was withdrawn (timestamps did not support
it). At 0.4–1.2 s per boot against a 220 s cap there is ~200× headroom, so a *slow*
host is an implausible trigger; a *wedged* one is not — this repo already has
[[openmsx-coreaudio-wedge]] on record ("probe timeouts + a boot at 0 % CPU = wedged
host audio"), which produces exactly a hung openMSX and exactly this signature. The
fix therefore does not depend on knowing which wedge it was: it makes **any** failure
of the emulator to complete its own emulated timeline **legible, classified, and
reported**.

### 2.1 A second, structural finding: the timeout hierarchy is inverted

Measured budgets on the live path today:

| layer | cap | for |
|---|---|---|
| `diskbasic_acceptance.py --timeout` | **240 s** | the WHOLE `GET(RDBLK)` probe (3 cases = **6 boots**) |
| `disk_probe_rdblk_roundtrip.py` `subprocess.run(timeout=…)` | 300 s | ONE case (2 boots) |
| `disk_probe_diff.py --timeout` (default) | 220 s | ONE boot |

A single wedged boot burns 220 s and thereby **blows the 240 s per-probe cap**, so the
same underlying event surfaces as either `MISALIGNED` or a runner `TIMEOUT` depending
on which boot wedged. Nothing is nested; the innermost cap is nearly the outermost.

### 2.3 The corpus opens a CoreAudio device on every boot, for nothing

Prompted by the user asking whether the wedge is really pty exhaustion (§2.4), I
measured the audio path instead of arguing from the note. openMSX exposes
`sound_driver`, an **enumeration `{null sdl}`**, defaulting to `sdl`. The preamble
([`omsx_session.py:98`](../probes/disk/omsx_session.py:98)) sets `renderer none` but
leaves the sound driver at `sdl`, so **every headless probe boot opens a real
CoreAudio device it has no use for** — ≈6 boots per probe × 34 probes ≈ **200
CoreAudio start/stop cycles per `make diskbasic-acceptance` run**.

Measured `sdl` vs `null`, case (a), both machines:

| | anchor emulated `t` | drift vs the §2 baseline | captured block |
|---|---|---|---|
| ours, `sdl` → `null` | 24.137504 → 24.137504 | **+0.000000** | byte-identical |
| stock, `sdl` → `null` | 24.450109 → 24.450109 | **+0.000000** | byte-identical |

`ours == stock` still converges under `null`. **The setting is measurement-neutral: it
does not move the instrument.**

🟢 **Independently corroborated by the user (2026-07-30): the laptop audibly makes
noise during probe runs.** That upgrades the finding. The SDL driver was not merely
*opening* a device, it was **actively streaming PSG/keyclick output** on every headless
boot — and an active stream is a far more credible way to wedge `coreaudiod` than an
idle handle. It is also a second, independent reason to adopt the change: **~200
bursts of MSX boot noise per gate run, on the user's machine, for a measurement that
never reads a sample.**

✅ **Adopt `set sound_driver null` in the preamble.** This is a better class of fix
than anything else in this spec: it **removes a candidate cause** of the wedge instead
of tolerating it, for one line and zero measured cost — and it stops the noise.

⚠️ Deliberately `sound_driver null`, **not** `set mute on` / `master_volume 0`: those
silence the output while still running the SDL/CoreAudio driver, so they would fix the
noise and leave the churn — the wrong half of the problem.

🔴 **It does NOT retire the rest of this spec, and must not be reported as "fixed".**
The trigger is still unconfirmed (§2). This closes one plausible route to a hung
emulator; the heartbeat, the classification and the reporting are what make the *next*
apparatus event — from any cause — legible instead of subject-shaped.

### 2.4 Is the wedge pty exhaustion? — measured, and the answer is no

The hypothesis (user, 2026-07-30): the CoreAudio wedge is a side-effect of Claude Code
leaking ptys for background processes until the host runs out.

| check | result |
|---|---|
| pty-holding PIDs right now | **7, all `zsh`**; `kern.tty.ptmx_max` = 511 |
| openMSX's own pty use | **zero** — `Popen(stdout=DEVNULL, stderr=DEVNULL, start_new_session=True)` allocates none ([[pty-leak-and-agent-reuse]], verified 2026-06-23; consistent with 0 openmsx among today's holders) |
| mechanism | pty exhaustion fails `posix_openpt` → *shells* fail to spawn; CoreAudio clients reach `coreaudiod` over Mach IPC, a different resource |
| falsifier | the pty leak clears on a Claude restart; the wedge did **not** (needed `killall coreaudiod`) |

⚠️ **Stated at its true strength: unsupported, not disproven.** The falsifier is a
recorded claim from 2026-07-28 that I did not re-verify, and the pty count above is
*now*, not during a failing run.

🟢 **The challenge was still productive** — testing it is what surfaced §2.3. The
shared-exhaustion instinct was right in kind; the resource was audio-device churn, and
it is **ours**, not the harness's.

## 3. Non-goals — the guard is not to be touched

🔴 **The `MISALIGNED` refusal in
[`disk_probe_diff.py:339-347`](../probes/disk/disk_probe_diff.py:339) and the
`"MISALIGNED" in txt` test in
[`disk_probe_rdblk_roundtrip.py:119`](../probes/disk/disk_probe_rdblk_roundtrip.py:119)
stay exactly as strict as they are.** No change may let a misaligned capture reach a
numeric memory-diff result. §6 falsifies this explicitly (F3).

Also out of scope: the anchor itself, the `--mem` window, `rdblk_rt.asm`, and any
retry that is not *classified* and *reported*.

## 4. The change

### 4.0 `omsx_session.py` — `set sound_driver null` in the preamble

One line, added beside `set renderer none`. Measured neutral in §2.3 (zero drift, byte-
identical captures, convergence preserved). Removes ~200 CoreAudio start/stop cycles
per gate run, and with them one candidate route to a hung emulator.

Falsification row **F10** (§6) pins the neutrality across the whole corpus rather than
just case (a): the four standing gates must stay at their exact current tallies.

### 4.1 `omsx_session.py` — a liveness HEARTBEAT, and report HOW the run ended

**(a) Heartbeat.** The generated Tcl gains a realtime beat:

```tcl
proc zb_beat {} {
  set f [open {<hbfile>} w]; puts $f "[machine_info time] [clock milliseconds]"; close $f
  after realtime 0.25 zb_beat
}
zb_beat
```

It writes to a **separate file**, never to the `emit` record file. That is deliberate:
an extra `emit` line would ripple through `parse_ctx` and every tag filter in the
~60-probe corpus. The returned `list[str]` is **byte-unchanged**, so blast radius on
existing consumers is nil. (The file is rewritten, not appended — the host only ever
needs the latest beat.)

**(b) Wait on PROGRESS, not on elapsed seconds.** The host loop
([`omsx_session.py:208`](../probes/disk/omsx_session.py:208)) currently kills at
`time.time() + timeout`. It becomes: kill when the **emulated clock has not advanced**
for `stall_timeout` host seconds (default 20 s — ≈2700× the measured 7 ms of host time
per emulated second on this host), with the existing `timeout` retained **unchanged as
an absolute ceiling**.

⚠️ **This is the one decision with corpus-wide reach, so state it plainly:** no probe
can run *longer* than it does today (the ceiling is untouched); some will fail
*faster* and all gain a reason. A wedged boot is caught at the stall, not at the
ceiling — which is what makes a reported retry fit inside the runner's budget at all
(§2.1).

✅ **DECIDED 2026-07-30 (user): CORPUS-WIDE.** `stall_timeout` defaults ON for every
probe. The G4 control (§6) plus the four standing gates are what carry this; if G4
fires — a healthy run stall-killed — the default reverts to opt-in and the spec is
re-opened rather than the threshold quietly raised.

**(c) Report the ending.** `run_job_raw` records on the `OmsxRun` instance:

* `last_killed: bool`, `last_kill_reason: None | "stall" | "ceiling"`
* `last_emul_t: float` — emulated time at the last heartbeat (**the stall point**)
* `last_wall: float`, `last_rc: int | None`

### 4.2 `disk_probe_diff.py` — classify the miss, keep refusing to diff

A run **completed its own emulated timeline** iff it was not host-killed **and** it
emitted one of its terminal sentinels: `ANCHOR` (hit), `NO-ANCHOR` (reached
`--settle`), `TIMEOUT-SAFETY` (reached `settle+safety`), or `ERROR`.

This is a sound discriminator, and that soundness is the crux of the design:

* a **subject/anchor** defect (program hangs, keys mistyped, wrong `--nth`) still lets
  the emulated clock advance, so `NO-ANCHOR` or `TIMEOUT-SAFETY` **always** fires;
* only the emulator **not finishing** — host-killed, crashed, failed to launch — can
  leave no terminal sentinel at all.

The heartbeat (§4.1) is the **primary**, measured signal; this sentinel test is kept as
a cheap second check, because it also covers "the emulator exited on its own without
hitting anything" (a crash or a failed launch), which no heartbeat can catch.

**Replay on a LOGICAL miss** (✅ decided 2026-07-30: include). `reverse start` is
already recording, so when a side
reaches `--settle` without hitting the anchor, the `NO-ANCHOR` callback is still live
and calls `reverse savereplay` before exiting. The flake then stops vanishing: the
failing run is preserved as a replayable `.omr`, and `reverse goto` can interrogate
the timeline (where was the PC, did the keys land, what is on screen).
⚠️ **Honest limitation: this is impossible for the APPARATUS class.** A wedged
emulator cannot run a Tcl callback, so no replay can be taken from it — which is
exactly why the heartbeat, written from *outside* the failing moment, is the load-bearing
instrument there and the replay is only insurance for the other class.

`mode_capture` therefore reports, per side, `LOGICAL` vs `APPARATUS`, and exits:

* **2 — logical miss** (unchanged meaning: fix the anchor/`--nth`/keys);
* **3 — apparatus miss** (new): the emulator did not complete its emulated timeline;
  the printed line names which side, whether it was host-killed, and the wall seconds.

The `*** MISALIGNED — diff NOT meaningful ***` header, the per-side YES/NO lines and
the refusal to print any diff are **unchanged in both classes**. The one-sided
(`--machine ours|stock`) branch gets the same classification and the same 2/3 split,
keeping its existing `"never reached occurrence"` wording (two consumers match on it).

Consumers that key on `rc == 2`
([`disk_bdos_acceptance.py:199`](../probes/disk/disk_bdos_acceptance.py:199),
[`disk_bdos_cbios_selfcheck.py:142`](../probes/disk/disk_bdos_cbios_selfcheck.py:142))
are widened to `rc in (2, 3)` so they do not rest on text matching alone.

### 4.3 `disk_probe_rdblk_roundtrip.py` — bounded, LOUD retry on the apparatus class only

* Nest the budgets from the measurement, not from arithmetic: pass
  `--timeout 45` to each capture (≈40× the measured 0.4–1.2 s boot) and drop the
  per-case `subprocess.run` timeout 300 → **120 s**. Both stay well inside the
  runner's 240 s, so a wedge now fails **fast** and leaves room to retry.
* Retry a case **only** on the apparatus class (capture rc 3, or a
  `subprocess.TimeoutExpired` on the case): **max 2 retries**, and additionally
  bounded by a probe-wide **120 s retry budget** so the worst case cannot reach the
  runner's 240 s cap.
* **A logical `MISALIGNED` (rc 2) is NOT retried** — that is a real anchor defect and
  must stay a hard, immediate FAIL. Retrying it would be exactly the "loosening" §3
  forbids, one level up.
* Every retry prints, on its own line,
  `APPARATUS-RETRY case <k> attempt <n>/3 — <reason> (wall <s>s)`.
* The final summary prints `APPARATUS-RETRY TOTAL: n` whenever `n > 0`, so a green run
  that needed a retry cannot read as a clean run.
* `subprocess.TimeoutExpired` is caught (today it propagates and crashes the probe).

### 4.4 `diskbasic_acceptance.py` — a retry must be visible AT THE GATE

`gate()` currently returns the fixed string `"converged"` on success, so a retried
probe would show an ordinary green row. It is changed to append
`" (⚠ N apparatus retr…)"` to the `why` string whenever the probe's output carries the
`APPARATUS-RETRY TOTAL:` marker. Generic, one line, available to every probe.

## 5. Blast radius

| file | change | risk |
|---|---|---|
| `omsx_session.py` | `set sound_driver null` | corpus-wide, but **measured** neutral (§2.3) and pinned by F10 |
| `omsx_session.py` | heartbeat to a **separate** file; stall-based wait under the existing ceiling; 5 new instance attributes | returned `list[str]` unchanged; **but the wait policy is corpus-wide** — see §4.1(b), the one call that needs your explicit nod |
| `disk_probe_diff.py` | capture-miss classification, new exit 3 | text output of the **converging** path unchanged; only the already-failing path gains lines |
| `disk_bdos_acceptance.py`, `disk_bdos_cbios_selfcheck.py` | `rc == 2` → `rc in (2, 3)` | widening only |
| `disk_probe_rdblk_roundtrip.py` | timeouts + classified retry | its converging output gains nothing when `n == 0` |
| `diskbasic_acceptance.py` | `gate()` surfaces the marker | `why` unchanged when the marker is absent |

## 6. Gate — the defect is INTERMITTENT, so one green run proves nothing

A scratchpad falsification harness, each **red row paired with a GREEN control**
(standing lesson: a falsification row can go red for the wrong reason, and red reads
as success).

| row | how | must show |
|---|---|---|
| **F1** apparatus class is DETECTED | capture with `--timeout 0.2` (host-kills both sides) | `MISALIGNED` + **APPARATUS** classification, **exit 3** |
| **G1** control for F1 | the identical command at the normal timeout | converges, **exit 0** |
| **F2** logical class still distinguished | normal timeout, `--nth 99` (never reached) | `MISALIGNED` + **LOGICAL** classification, **exit 2** |
| **G2** control for F2 | same command, `--nth 1` | converges, **exit 0** |
| **F3** the guard is INTACT | F1 and F2 outputs | **no** `bytes differ` line in either |
| **F4** retry is bounded and REPORTED | probe driven so every attempt is an apparatus miss (monkey-patched capture timeout in the harness — **no test-only hook in shipped code**) | 2 `APPARATUS-RETRY` lines, then FAIL, **exit 1** |
| **G3** control for F4 | probe unpatched | PASS, **no** `APPARATUS-RETRY` line |
| **F5** a TRANSIENT miss is rescued AND reported | harness makes only the FIRST attempt apparatus-miss | PASS, exactly 1 `APPARATUS-RETRY` line, `APPARATUS-RETRY TOTAL: 1` |
| **F6** logical MISALIGNED is NOT retried | harness forces a logical miss inside the probe | FAIL with **zero** retry lines |
| **F7** the gate row surfaces the retry | `diskbasic_acceptance` `gate()` fed an F5-shaped output | PASS row carries the ⚠ marker |
| **F8** a STALL is detected and LOCATED | Tcl that free-runs to ~t=24 then blocks the reactor (`while {1} {}`) | killed on **stall**, reason `stall`, reported `last_emul_t` ≈ the block point — **not** the ceiling |
| **G4** control for F8 — a healthy run is NOT stall-killed | the normal case-(a) capture | `last_killed == False`, converges, exit 0 |
| **F9** replay is written on a LOGICAL miss | F2's `--nth 99` run | an `.omr` exists and is non-empty; `reverse loadreplay` accepts it |

| **F10** `sound_driver null` is neutral CORPUS-WIDE | the four standing gates under the new preamble | **exact same tallies**: 34/34 · 54/54 · 12/12 · 7/7 — a drop anywhere means audio was load-bearing somewhere and the line comes back out |

🔴 **G4 is not optional.** A stall detector that fires on healthy runs would turn every
row red *for the right-looking reason*, and this repo has been bitten twice by a
falsification row going red for the wrong reason. F8 without G4 proves nothing.

**Repeatability gate (the point of the item):**
`make diskbasic-acceptance ONLY='GET(RDBLK)'` **× 10 → 10/10**.

**Standing gates, RUN not assumed:** `make diskbasic-acceptance` 34/34 ·
`make unit-test` 54/54 · `make bdos-acceptance` 12/12 · `make fat-error-acceptance` 7/7.
**ROM byte-identity:** `build/basic-reloc.rom` `52a0b9bc…`, `build/sub.rom` `01ab5dc2…`.

⚠️ Never two emulator gates concurrently; never rebuild during a differential.

## 7. Noted, not fixed

`pasmo` prints `WARNING: Var start is never used on line 33 of probes/disk/rdblk_rt.asm`
on every assemble of the exerciser. `start:` is the documentary label for `$0100`
(`jr main` is the entry); removing it would not change a single emitted byte. It is
probe-side and **not** covered by the new dead-code gate, which sweeps `basic/` +
`sub/` only. Left alone; flag it here so it is on record.

## 8. What this spec deliberately does NOT do

* It does not identify the wedge. It makes the wedge **announce itself**, and now
  **locate itself** (the stall point in emulated time).
* **It does not adopt savestates to skip the boot**, though openMSX's TAS facilities
  make that tempting: booting once to `A>`, snapshotting, and restoring per case would
  cut 6 boots to 1. Rejected *for this item* — this is a **live-oracle differential**,
  and a restored state is a different initial condition on both the subject and the
  oracle side. Changing what the gate measures is not a licence a flake-fix carries.
  Worth its own item; noted, not smuggled in.
* It does not extend the heartbeat's *retry* logic beyond `GET(RDBLK)`. The mechanism
  lands in the shared layer and every probe gains the reason-reporting; adopting the
  classified retry elsewhere is follow-up work.
* It does not make the gate green by being more tolerant. The one thing it adds
  tolerance for is a **classified, bounded, printed** apparatus event; every other
  failure gets stricter, because a host kill can no longer masquerade as one.

---

## 9. Results (2026-07-30)

### 9.1 🔴 What the gate caught — the G4 control found a defect in the FIX

The first `_wait` implementation initialised the stall clock to `t0`. Measured: the
first heartbeat does not arrive until **0.21–0.82 s** after launch (process spawn,
machine XML parse, ROM load, symbol load). So startup latency was charged to the
emulator as though it were a stall, and under the battery's own load a **healthy run
was stall-killed** (`killed=True reason=stall anchor=False wall=3.3 s`, at
`stall_timeout=3`). It did **not** reproduce standalone — both isolated debug runs
converged — which is precisely the shape of the flake this slice exists to remove.

At the production default of 20 s the margin is wide, so this would have been rare —
and rare-but-real on a loaded host is exactly when a long gate run happens. **Shipping
it would have traded one intermittent row for a corpus-wide one.**

Fix: the stall clock starts at the **first beat**, never at `t0`. "Stall" now means
*"it was beating and stopped"*; a run that never beats at all is the ceiling's
business, and is still classified APPARATUS — correctly.

**This is the third time in this slice that measuring beat reasoning**, after §2 (the
anchor was already sentinel-gated; the wall clock was at the process level) and §2.3
(the corpus was streaming audio on every headless boot).

### 9.2 Falsification battery — 14/14 as specified

| row | result |
|---|---|
| F1 apparatus miss → MISALIGNED + APPARATUS, exit 3 | ✅ rc=3 |
| G1 control: same command, normal timeout | ✅ rc=0 |
| F2 logical miss → MISALIGNED + LOGICAL, exit 2 | ✅ rc=2 |
| G2 control: normal keys | ✅ rc=0 |
| F3 guard intact — **no `bytes differ` in either misaligned run** | ✅ |
| F4 persistent apparatus → 2 retries, EXHAUSTED, exit 1 | ✅ |
| G3 control: unpatched probe → PASS, `TOTAL: 0` | ✅ |
| F5 transient → PASS with exactly 1 reported retry, `TOTAL: 1` | ✅ |
| F6 logical miss → FAIL immediately, **ZERO** retries | ✅ |
| F7 gate row marks a retried PASS / F7-control plain `converged` | ✅ |
| F8 wedged reactor → killed on **stall** (3.5 s, not the 200 s ceiling), kill took | ✅ |
| G4 control: healthy run NOT stall-killed | ✅ (after 9.1; 5.1 s wall under load) |
| F9 replay written on a logical miss | ✅ 2 `.omr`, 21–22 KB |
| F10 `sound_driver null` neutral corpus-wide | ✅ all four gates at exact tallies |

### 9.3 Two harness bugs — my rows, not the product's

Both went red for the **wrong reason**, the failure mode this repo has been bitten by
twice. Recording them so the next author does not repeat them:

* **`--nth 99` does not force a logical miss.** `done` is a `jr done` **self-loop**, so
  occurrence #99 arrives microseconds after #1 and the run **converges** (measured
  rc=0, with a real byte diff). F3 then correctly reported `bytes differ` — it was
  reading a *converged* run, not a leak in the guard. A logical miss needs the program
  never to run: type a command that does not exist.
* **Patching `subprocess.run` hit `pasmo`.** `assemble()` shells out through the same
  function; the timeout patch crashed the first attempt. Patch only capture invocations.

Also corrected: F8 asserted a tight emulated-time window for the stall point. At ~134×
realtime one 0.25 s beat spans ~30 emulated seconds, so a machine that blocks at t=6
legitimately reports a last-observed t of 0.0. **The stall point is a coarse hint by
construction**, and the report now prints the beat number to make that visible.

### 9.4 Standing gates + ROM identity

`make unit-test` **54/54** · `make diskbasic-acceptance` **34/34** (0 apparatus
retries) · `make bdos-acceptance` **12/12** · `make fat-error-acceptance` **7/7**.
Repeatability `ONLY='GET(RDBLK)'` **10/10, 0 retries** (make's own exit code, not a
pipeline's). From clean: `basic-reloc.rom` `52a0b9bc…`, `sub.rom` `01ab5dc2…` —
byte-identical; low **80 B**, page 1 **49 B**; dead-code sweep **0 dead both builds**.

### 9.5 What is NOT proven

The original trigger is **still unconfirmed**. The flake did not reproduce during this
session — it never has on demand — so nothing here demonstrates the 2026-07-30 event
would now be caught as APPARATUS. What is proven is that a run which fails to complete
its emulated timeline is detected, attributed, located, retried within a printed bound,
and surfaced at the gate row. **`sound_driver null` removes one candidate cause; it is
not established that it was THE cause.**
