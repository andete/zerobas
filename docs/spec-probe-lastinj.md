# D-LASTINJ — the last injector copy, and the suite nobody priced

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— one probe file, one new checker, one new Makefile target, and one long
standing-corpus run — so no sign-off gate applies. Written up as a slice anyway,
with predicted RED/GREEN sets fixed at exact values before the change.

Closes the two apparatus items [`docs/spec-probe-latch.md`](spec-probe-latch.md)
§6 filed and did not do:

> **`lnblank-say-acceptance` (204 rows, ~3.5–4 h) was NOT run.** It is a standing
> corpus member and it is in the blast radius; it was left out on cost, not on an
> argument that it is safe.

> **One probe file still carries its own pre-D-LATCH `__key`.** …
> `probes/disk/disk_probe_getput.py` still has one, and it is **left alone
> deliberately**: no Makefile target runs it, so a change there could not be
> scored.

Companion: [`docs/lastinj-characterization.md`](lastinj-characterization.md).

---

## 1. The two filed items, and what each one actually is

**Item A — the blast radius nobody priced.** D-LATCH changed the delivery
alignment of *every* probe in the tree (spec §4.3's own warning). Every standing
corpus member was re-run against it except one, and that one is the most
expensive: `make lnblank-say-acceptance`, 204 gating rows across three sides,
boot-per-case, ~3.5–4 h. Skipping it was a cost decision, not a safety argument,
and an unpriced blast radius is not the same thing as a small one.

**Item B — the last injector copy.** Six probe files composed their own
pre-D-LATCH injector — write the payload at `KEYBUF`, set `GETPNT = KEYBUF`,
`PUTPNT = KEYBUF + n`. That is the exact body D-LATCH proved carries the race.
Five were re-pointed at `omsx_repl.key_proc()`; `probes/disk/disk_probe_getput.py`
was left, on a stated reason.

---

## 2. What was measured before designing

### 2.1 🔴 The stated reason for leaving item B alone is FALSE

D-LATCH §6, `docs/latch-trigger-characterization.md` §9 and `TODO.md` all record
the same justification: *"no Makefile target runs it, so a change there could not
be scored."*

Three pieces of structural evidence, all present on `76ea851`:

| evidence | where |
|---|---|
| `("GET/PUT", "disk_probe_getput.py", [], "live")` is a registry row | [`probes/disk/diskbasic_acceptance.py:81`](../probes/disk/diskbasic_acceptance.py:81) |
| that registry is what `make diskbasic-acceptance` dispatches | [`Makefile:527`](../Makefile:527) |
| a **second** row imports its openMSX driver | [`probes/disk/disk_probe_openlen.py:34`](../probes/disk/disk_probe_openlen.py:34) — `from disk_probe_getput import run` |

Confirmed live: `python3 probes/disk/diskbasic_acceptance.py --list` prints both
`GET/PUT -> disk_probe_getput.py` and `OPEN(LEN=) -> disk_probe_openlen.py`.

So the file **was** gated all along — under a label that does not contain its
name, by a target that does not contain its name, and it was in D-LATCH's own
corpus (§4bis.5, "diskbasic"). The justification failed for the same reason
[[readout-blind-to-its-own-subject]] fails: the question asked was *"is there a
target called `getput`?"* and the answer to that question is not the answer to
*"is this file scored?"*.

⚠️ This does **not** make item B a non-issue. It relocates it. The copy is
scored for *whether the probe still converges*, which is not the same as scored
for *whether it carries the race*. §3.2 says which of those the existing gate can
actually do, and §4.2 measures it rather than assuming.

### 2.2 The copy is semantically the frozen fault `latch-check` already scores

`disk_probe_getput.build_tcl`'s `__inj` and `latch_check.OLD_KEY` +
`proc __inj {s} { append s "\r"; __key $s }` are the same program: append CR,
write `n` bytes from `KEYBUF`, set `GETPNT := KEYBUF`, set `PUTPNT := KEYBUF + n`,
no wrap. The difference is packaging (one proc vs two) and a build-time length
check, neither of which touches a pointer. §4.1 B2 checks this mechanically
rather than by reading, because "these two look the same" is exactly the claim
this repo does not accept by eye.

### 2.3 The `--say` denominator, derived rather than quoted

`--only lnrd-,kwgd-,lnrt-,dlt-,lst-,lse-,cln-,cle-,clp-,cld-,csv-,dsk-,crf-`
selects **204** cases, all 204 `SAY_ONLY`, **0** `INFORMATIONAL`, **5** in
`KNOWN_DIVERGE` (`crf-oomlst`, `crf-oomsay`, `csv-tok`, `kwgd-renum`,
`lnrt-forret`), **5** `SIDE_LOCK`ed `capability` (`dsk-*`, cf3300+zb only — both
in the side list, so all five still answer on two sides and still gate).
`ngate` is therefore **204**, not 199 and not 209.

---

## 3. Design

### 3.1 Item A — run it, and say what "zero announcements" is worth

`make lnblank-say-acceptance`, default `REPEAT=1`, all three sides. The
D-LATCH-specific readout is not the row tally — it is the **absence** of
`MIS-ECHOED` / `MIS-DELIVERED` / `ORACLES DISAGREE` / `APPARATUS FAILURE`
announcements, which `omsx_repl` writes to **stderr**, so stderr is captured.

🔴 **Zero announcements is only a finding if the guard was armed on these rows.**
`[[echo-guard-never-saw-say-rows]]` is this probe's own history: a guard filtered
away from its subject reports zero by construction. `--say` and `--echo` are
different passes, and the `SAY_ONLY` filter is what once removed every one of
these rows from the echo pass. So the run must show the in-harness guard is live
here (§4.1 T3), not merely silent.

### 3.2 Item B — what the existing gate can and cannot say

`make diskbasic-acceptance ONLY='GET/PUT,OPEN(LEN=)'` scores the probe's own
`records == EXPECT` comparison over a 16-line injected program. It can therefore
say **"a change to the injector did not break delivery for this probe"** — which
is precisely the guarantee §1's "gate it first, then re-point it" is after.

It cannot say "the race was or was not firing here": the race needs the callback
to land on one instruction boundary, and 16 slots is a denominator three orders
of magnitude below the one that found 6 hits. §4.2 M1 measures the boundary
directly instead of inferring it from a green gate.

### 3.3 Item B — the re-point

`build_tcl` drops its inline `__inj` and emits `omsx_repl.key_proc()` plus the
one-line CR wrapper `omsx_repl` itself uses. The addresses and the length check
come from `omsx_repl` too, so the probe stops carrying a second copy of the
memory map.

### 3.4 🎯 Closing the CLASS, not the instance — and giving it a live subject

Re-pointing this file leaves the tree with exactly one injector. Nothing stops
the next probe from composing a seventh, and nothing would notice — which is the
shape D-ECHO §6 and D-LATCH §6 both filed and neither closed.

`tools/check_probe_injectors.py` / `make injector-check` is the denominator gate,
shaped like `preflight-check`: every `.py` under `probes/`, `tools/`, `tests/` is
classified, and a file that emits `debug write memory` **and** names the
type-ahead cursors composes an injector. Two exemptions, both structural and
named: `probes/lib/omsx_repl.py` (the one shipped injector) and
`probes/lib/latch_check.py` (the frozen fault, which is that gate's subject).

> ⚠️ **Superseded 2026-08-05 by D-INJSINK** ([`spec-probe-injsink.md`](spec-probe-injsink.md)):
> this is now rule **(a)** of two, and the exemptions are **four**, each stating a
> class. Rule (b) closes what this one could not see — a frozen injector body
> named across a module boundary, which shipped `ALL PASS` past this gate.

🔴 **And it needs its own row A.** After the re-point this checker has **zero**
offenders in the tree, so it would pass with its judgement deleted — the exact
failure D-LATCH hit when fixing the fault silenced the only control the delivery
oracles had [[fixing-the-fault-silences-the-control]]. So the classifier is
scored on every run against two frozen bodies: the pre-D-LATCH `__inj` verbatim,
which **must** classify as composing, and a call-site-only body, which **must**
classify clean. Loosen the classifier until it stops matching the real fault and
the gate goes red instead of quietly certifying an empty walk. It fails **closed**
— a file it cannot classify is an offender, not an exemption
[[guard-that-cannot-judge-must-say-so]].

### 3.5 What does NOT change

Both delivery oracles, `key_proc` itself, `latch-check`, the `EXPECT` pair, the
CF-3300 differential, `MAX_DIRECT`. No `basic/`, `sub/`, `disk/` or `tape/`
source is touched and no ROM is rebuilt.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline: `76ea851`, tree clean, `make -q build/zerobas-main-eu.rom` **exit 0**,
`make repack-machine` run first. Subject `C-BIOS_MSX1_EU_REPACK_DISK`, references
`Philips_VG_8020` / `National_CF-3300`. No two emulator gates run concurrently.

### 4.1 Item A — the blast-radius run

| # | run | predicted |
|---|---|---|
| **T1** | `make lnblank-say-acceptance` | `204/204 gating rows agree across ['vg8020', 'cf3300', 'zb'] (5 of them allowlisted as KNOWN_DIVERGE, pinned to their exact value)`, **exit 0** |
| **T2** | the same run, stdout **and stderr** | **zero** `MIS-ECHOED`, **zero** `MIS-DELIVERED`, **zero** `ORACLES DISAGREE`, **zero** `APPARATUS FAILURE` lines |
| **T3** | 🔴 T2's non-vacuity control | the in-harness guard is **armed** on these rows: no `ZEROBAS_ECHOGUARD=off` banner, `verify_delivery` left at its default, and the run reaches `run_cases` for all 204 |
| **T4** | the three failure lists | no `ALLOWLIST FAILURE`, no `MEASURED BUT NOT GATING`, no `DIVERGENT` section |
| **T5** | any row that moves | 🎯 **attributed, not shrugged** — re-measured against `HEAD~1`'s `probes/lib/omsx_repl.py` before it is called a D-LATCH regression or a flake |

### 4.2 Item B — the copy

| # | run | predicted |
|---|---|---|
| **B1** | `make diskbasic-acceptance ONLY='GET/PUT,OPEN(LEN=)'`, **before any edit** | `2/2 verbs converged`, both rows `PASS [live    ]`, **exit 0** — the pre-change score item B said could not be taken |
| **B2** | normalise `disk_probe_getput`'s `__inj` and `latch_check.OLD_KEY` + wrapper (strip whitespace/comments, substitute address literals) and compare | **character-identical** — the copy is the frozen fault `latch-check` row A already forces |
| **M1** | the old injector, instrumented with D-LATCH §2.1's zero-cost register readout, zb side, 16 injections | **0 of 16** slots at the derived trigger — the race is **latent** here, not live. GREEN control: all 16 slots report a PC (the instrument is not blind) and at least one reads `$11A0` |
| **C1** | `make diskbasic-acceptance ONLY='GET/PUT,OPEN(LEN=)'`, **after** the re-point | `2/2`, **exit 0** |
| **C2** | `make diskbasic-acceptance` (full) | **34/34 verbs converged**, exit 0 |
| **C3** | `make latch-check` | **9/9**, exit 0 (its subject did not move) |
| **C4** | `make preflight-check` | **0 unguarded** (the re-point adds no spawn site; the new checker spawns nothing) |
| **C5** | `make -q build/zerobas-main-eu.rom` | **exit 0** throughout — apparatus only, no ROM rebuilt |
| **C6** | `make unit-test` | **57/57** |

### 4.3 Predicted RED — the knives

| knife | cut | predicted RED | predicted GREEN control |
|---|---|---|---|
| **K1** | `__inj` mangled to drop the first character of every injected line | both rows **FAIL**, `0/2`, **exit 1** — the gate is sensitive to delivery | B1 on the unmodified tree: `2/2` |
| **K2** | 🎯 K2-shaped: K1's mangle **kept**, and only the probe's judgement gutted (`okf`/`okr` forced true). Emission intact — `records:` still printed, `CF-3300 differential` still printed, so `REF_MARKERS` still matches; call site intact | the acceptance runner reports **`2/2`, PASS, exit 0** on visibly wrong records — the runner contributes **no** judgement of its own; the probe's `== EXPECT` is the entire gate | K1 in the same session: `0/2`, exit 1 |
| **K3** | `injector-check` run on the tree **before** the re-point | 🎯 **1 offender** (`probes/disk/disk_probe_getput.py`), **exit 1** — it must be shown to find the one that exists before it may report zero | after the re-point: **0 offenders**, exit 0 |
| **K4** | `injector-check`'s frozen row A: the classifier fed the verbatim pre-D-LATCH `__inj` body | classifies **composes**; if a loosened classifier returns clean, the gate **refuses to judge**, non-zero | the frozen clean body classifies **clean** in the same run (two-sided, so "flag everything" cannot pass either) |
| **K5** | K2-shaped on `injector-check`: keep the walk, keep the report, gut only the verdict (every file classified clean) | on the **pre**-re-point tree, `0 offenders, exit 0` — a green gate over a tree that has one. This is why K3's ordering is load-bearing and why K4 is scored every run | K3's pre-change run: 1 offender, exit 1 |

### 4.4 Corpus

Unchanged and all exit 0, run sequentially: unit · deadcode · preflight-check ·
**injector-check** · **latch-check 9/9** · **diskbasic-acceptance 34/34** ·
**lnblank-say-acceptance 204/204**.

⚠️ The re-point touches one probe file consumed by exactly two registry rows
(`GET/PUT` directly, `OPEN(LEN=)` by import). That is the whole blast radius of
item B, and `make diskbasic-acceptance` in full is what prices it.

---

## 4bis. What landed, and what it measured

`probes/disk/disk_probe_getput.py` (its inline injector replaced by
`omsx_repl.key_proc()`, and its private copy of the memory map deleted), a new
`tools/check_probe_injectors.py`, one Makefile target, and the corrected claim in
D-LATCH's two docs. **No `basic/`, `sub/`, `disk/` or `tape/` source touched;
`make -q build/zerobas-main-eu.rom` exit 0 throughout, so no ROM was rebuilt.**

### 4bis.1 🔴 The premise was false, and the copy was the frozen fault verbatim

`make diskbasic-acceptance` had been running this file all along, as registry row
`GET/PUT`, with a second row (`OPEN(LEN=)`) importing its driver — so it sat
inside D-LATCH's own corpus under the name `diskbasic`. And B2 measured the copy
**character-identical** (after constant folding) to `latch_check.OLD_KEY`: not
merely similar to the pre-D-LATCH injector but the exact body `make latch-check`
row A forces onto the trigger and requires to **mangle**, nine boots a run.

### 4bis.2 🎯 The mechanism was loaded at every slot; only the alignment was missing

M1 predicted 0 hits and measured **0 of 16** slots at `$1197`. Two readings stop
that from being an all-clear: slot 11 landed at `$119B`, *inside* `chget`'s wait
loop one instruction off the fatal boundary, and the swallow law's precondition —
`GETPNT` left at `KEYBUF + len(predecessor incl. CR)` by the drained previous
line — held at **15/15** slots that have a predecessor. Every slot in the probe
was in the state that turns a `$1197` landing into a swallowed line.

### 4bis.3 The knives, scored

B1/K1/K2 and C1–C6 hit exactly. **K2 is the one worth keeping**: with the mangle
in place and only the probes' `== EXPECT` gutted, `diskbasic-acceptance` reports
`2/2 verbs converged, ALL CONVERGED`, exit 0, over `records: []`. The runner
contributes **no judgement of its own** — it checks an exit code and that the
string `CF-3300` appeared — and all 34 registry rows inherit that.

🔴 **K4b did not cut on the first attempt, and that is a finding about the new
gate, not about the tree.** `injector-check`'s negative control emitted no
`debug write memory` at all, so it was clean for a trivial reason and the
"flag everything" half of the two-sided self-test was decorative. Rebuilt as a
probe that pokes an unrelated address, both halves bite (§6.1 of the
characterisation) [[knife-found-defect-in-own-fix]].

🔴 **K5's prediction was wrong, in the safe direction.** Gutting the verdict does
not produce a green walk over a dirty tree: the frozen self-test runs *before*
the walk and trips first (`CANNOT JUDGE`, rc 2). Recorded as a wrong prediction
rather than rewritten to match.

### 4bis.4 The blast radius, and 🎯 the cost that was never re-measured

`make lnblank-say-acceptance`: **204/204 gating rows agree** across all three
sides, exit 0, and **zero** `MIS-ECHOED` / `MIS-DELIVERED` / `ORACLES DISAGREE` /
`APPARATUS FAILURE` lines — stderr was **0 bytes**. No row moved, so T5's
attribution path was never needed.

T3 is what makes that zero mean anything: with `key_proc` monkeypatched to
swallow one byte, the same `--say --gate` rows produce `APPARATUS FAILURE` plus
five `MIS-ECHOED` announcements and rc 1, and the identical unpatched subset is
silent. The guard is armed on say rows, which is precisely what this probe's
history says not to assume [[echo-guard-never-saw-say-rows]].

🎯 **And the suite costs 8 min 58 s, not the ~3.5–4 h on file** — about 0.9 s per
boot for 612 boot-per-case runs, which is what an unthrottled openMSX costs on
this host [[emulator-gates-are-fast-dont-sleep-poll]]. The estimate that
justified skipping it had not been re-measured since the harness stopped
sleep-polling. A stale cost figure is a standing argument for not running a gate,
and it had already won that argument once. Corrected in `Makefile` and `TODO.md`.

### 4bis.5 Corpus

Run sequentially, no two emulator gates at once, all exit 0: unit **57/57** ·
preflight-check **0 unguarded / 94 guarded** · **injector-check 0 offenders,
self-test PASS** · **latch-check 9/9** · **diskbasic-acceptance 34/34** ·
**lnblank-say-acceptance 204/204**. `make -q build/zerobas-main-eu.rom` exit 0
throughout.

---

## 5. Coverage limits, stated in advance

* **M1 measuring 0 does not mean safe.** D-LATCH's rate was 6 hits in 2039 slots;
  16 slots has an expected count of ~0.05. A zero here is consistent with the
  race and consistent with its absence, and it will be reported as the weak
  reading it is.
* **The second latch window stays open** (D-LATCH §2.5). Nothing here touches it.
* **`injector-check` is a text classifier**, not a semantic one. It catches the
  shape that has occurred six times; a probe that reaches the cursors by some
  other spelling would pass it. It fails closed on files it cannot classify,
  which is the mitigation, not a proof.
* **The CF-3300 side of `getput` is not boundary-analysed.** `key_proc` is
  already proven on that machine by every `omsx_repl` probe; locating its `chget`
  would need a disassembly this project does not do [[no-reference-rom-disasm]].
