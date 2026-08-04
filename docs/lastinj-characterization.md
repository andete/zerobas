# The last injector copy, and the blast radius — every reading, D-LASTINJ

Companion to [`docs/spec-probe-lastinj.md`](spec-probe-lastinj.md). Everything
below was measured on `76ea851` (tree clean, `make -q build/zerobas-main-eu.rom`
exit 0, `make repack-machine` run first). Subject `C-BIOS_MSX1_EU_REPACK_DISK`,
references `Philips_VG_8020` / `National_CF-3300`. No two emulator gates run
concurrently.

---

## 1. 🔴 The premise on file was false, and it was falsifiable without booting anything

D-LATCH §6, `docs/latch-trigger-characterization.md` §9 and `TODO.md` all carry
the same sentence about `probes/disk/disk_probe_getput.py`:

> no Makefile target runs it, so a change there could not be scored

Three structural readings, all present on the commit that wrote that sentence:

| # | reading |
|---|---|
| 1 | `("GET/PUT", "disk_probe_getput.py", [], "live")` is row 7 of the `REGISTRY` in [`probes/disk/diskbasic_acceptance.py:81`](../probes/disk/diskbasic_acceptance.py:81) |
| 2 | that registry is exactly what [`Makefile:527`](../Makefile:527) `diskbasic-acceptance` dispatches |
| 3 | a **second** registry row imports its openMSX driver — [`probes/disk/disk_probe_openlen.py:34`](../probes/disk/disk_probe_openlen.py:34), `from disk_probe_getput import run` |

Confirmed live:

```
$ python3 probes/disk/diskbasic_acceptance.py --list
  [live    ] GET/PUT          -> disk_probe_getput.py
  [live    ] OPEN(LEN=)       -> disk_probe_openlen.py
```

The file was gated all along — by a target whose name does not contain it, under
a label that does not contain it, and it sat inside D-LATCH's own corpus run
(§4bis.5 lists `diskbasic`). The justification was not a lie about the tree; it
was an answer to a different question. *"Is there a target called `getput`?"* and
*"is this file scored?"* have different answers, and only the second one was
load-bearing. Same shape as [[readout-blind-to-its-own-subject]], reached through
a naming convention instead of through an oracle.

⚠️ **It relocates the item, it does not dissolve it.** §3 is what the existing
gate can actually say, measured rather than assumed.

## 2. The copy was the frozen fault, mechanically

`disk_probe_getput.build_tcl`'s `__inj` versus `latch_check.OLD_KEY` + its
`proc __inj {s} { append s "\r"; __key $s }` wrapper, both normalised (comments
stripped, whitespace collapsed, proc names unified, the two packagings folded
together):

| pass | result |
|---|---|
| raw normalisation | **differ in 2 tokens** — `[expr 62458+1]` vs `62459`, `[expr 62456+1]` vs `62457` |
| + constant folding | 🎯 **character-identical** |

Both spell `KEYBUF` 64496 (`$FBF0`), `GETPNT` 62458 (`$F3FA`), `PUTPNT` 62456
(`$F3F8`), buffer size 40 — the same values `omsx_repl` carries.

So the body in this probe was not *similar to* the pre-D-LATCH injector. It was
the body `make latch-check` row A forces onto the trigger and **requires to
mangle**, nine boots a run, every run. The fault was already reproduced on
demand in this tree; it just was not known to still be shipping.

## 3. What the existing gate can say, and what it cannot

`make diskbasic-acceptance ONLY='GET/PUT,OPEN(LEN=)'` scores the probes' own
`records == EXPECT` comparison over a 16-line injected program, both machines.

| # | run | predicted | measured |
|---|---|---|---|
| **B1** | before any edit | `2/2 verbs converged`, exit 0 | ✅ `2/2`, both `PASS [live]`, exit 0 — the pre-change score the filed item said could not be taken |
| **K1** | `__inj` mangled to drop the first character of every line | both rows FAIL, `0/2`, exit 1 | ✅ `0/2`, exit 1, `records: []` on **both** machines — and `OPEN(LEN=)` failed too, so the import coupling is real and gated |
| **K2** | 🎯 K1's mangle KEPT, only the probes' judgement gutted (`okf`/`okr` forced true) | the runner reports `2/2`, exit 0, on visibly wrong records | ✅ `2/2 verbs converged`, `ALL CONVERGED`, exit 0 |

K1 says the gate cuts. K2 says where the cut comes from: **the acceptance runner
contributes no judgement of its own.** Its `gate()` checks an exit code and,
for a `live` row, that the string `CF-3300` appeared — both of which K2 leaves
intact. The probe's own `== EXPECT` is the entire gate, and 34 registry rows
inherit that property. That is not a defect; it is the fact a reader of
`34/34 verbs converged` needs, and it was not written down anywhere.

What the gate cannot say is whether the race was firing here. 16 injection slots
against D-LATCH's observed rate of 6 in 2039 is an expected count of 0.05, so a
green run is consistent with the race and consistent with its absence. §4
measures the boundary instead of inferring it.

## 4. 🎯 The gun was loaded at every slot; the trigger was never pulled

D-LATCH's instrument, unchanged: a string replacement at the **top** of `__inj`,
before a single byte is written, reading `reg pc`, `reg hl`, `reg de`, both
cursors and the opcode at PC. `reg` and `debug read memory` cost zero emulated
time, so the instrument cannot move the alignment it exists to measure
[[apparatus-is-part-of-the-measurement]]. `global __f` in the proc body, because
without it openMSX drops the callback without a word and the instrument reports
nothing while looking perfectly present [[wired-in-and-silent-tcl-global]].

One boot, zb side, the old injector, the probe's own 16-line program. Derived
per run and signature-checked: `chget $118F`, `chget_wait $1194`, trigger
`$1197` — the same three numbers D-LATCH derived.

```
  #     PC  op    HL    DE GETPNT PUTPNT  drained
  0  $11A0  18 $FBF0 $FBF0 $FBF0  $FBF0   yes
  ...
  7  $18EE  c5 $FCC8 $8B00 $FC00  $FC00   yes
  11 $119B  e7 $FC08 $FC08 $FC08  $FC08   yes
  ...
PC histogram: {'11A0': 14, '18EE': 1, '119B': 1}
```

| reading | value |
|---|---|
| slots at the trigger `$1197` | **0 of 16** |
| slots that reported a PC at all (the instrument is not blind) | **16 of 16** |
| slots at `$11A0` (`jr chget_wait`, the halted park) | 14 |
| buffer drained (`GETPNT == PUTPNT`) | **16 of 16** |
| functional result under the instrument | unchanged, `['alpha|  bet', 'gamma|delta']` |

M1 predicted 0 and measured 0. Two readings make that a much less comfortable
zero than it looks:

**Slot 11 sat at `$119B`.** That is `rst $20`, *inside* `chget`'s wait loop, one
instruction past the fatal boundary — one of the three addresses D-LATCH's K3
proved harmless. So this probe's callbacks do land inside the window. They landed
on the safe side of it.

**The swallow law's precondition held at 15/15 slots that have a predecessor.**
`GETPNT - KEYBUF` at each injection against the length of the previous line
including its CR:

| slot | GETPNT | `−KEYBUF` | `len(prev)+CR` |
|---|---|---|---|
| 1 | `$FC02` | 18 | 18 (`open"d.dat" as #1`) |
| 2 | `$FC08` | 24 | 24 (`field#1,5 as a$,5 as b$`) |
| 4 | `$FBFE` | 14 | 14 (`rset b$="bet"`) |
| 9 | `$FBF6` | 6 | 6 (`close`) |
| 13 | `$FC07` | 23 | 23 (`print"<";a$;"|";b$;">"`) |

**Fifteen for fifteen.** Every slot in this probe was in exactly the state that
turns a `$1197` landing into a swallowed line — the drained predecessor had left
`GETPNT` at `KEYBUF + N`, and the old injector was about to move it backwards to
`KEYBUF`. What was missing was the alignment, and alignment is the thing D-LATCH
established you may not rely on: it moves with `step`, with predecessor length,
with any change to CPU timing [[deterministic-mangle-is-still-a-mangle]].

So the honest reading of item B is not *"a latent problem in a file nobody ran"*.
It is *"a loaded mechanism in a file that runs on every `make diskbasic-acceptance`,
which had not yet been aligned"*. §5 unloads it.

## 5. The re-point, scored

`build_tcl` now emits `omsx_repl.key_proc()` plus the one-line CR wrapper, and
the probe no longer carries `_KEYBUF`/`_GETPNT`/`_PUTPNT`/`_KEYBUF_SZ` — the
memory map is imported too. Generated Tcl, verified:

```
proc __key {s} {
  set n [string length $s]
  set g [expr {[debug read memory 62458] + 256*[debug read memory 62459]}]
  for {set i 0} {$i < $n} {incr i} {
    set a [expr {$g + $i}]
    if {$a >= 64536} { incr a -40 }
    debug write memory $a [scan [string index $s $i] %c] }
  set p [expr {$g + $n}]
  if {$p >= 64536} { incr p -40 }
  debug write memory 62456 [expr {$p & 0xFF}]
  debug write memory 62457 [expr {($p >> 8) & 0xFF}] }
proc __inj {s} { append s "\r"; __key $s }
```

`GETPNT` is read and never written.

| # | run | predicted | measured |
|---|---|---|---|
| **C1** | `diskbasic-acceptance ONLY='GET/PUT,OPEN(LEN=)'` | `2/2`, exit 0 | ✅ `2/2`, exit 0 |
| **C2** | `make diskbasic-acceptance` (full) | `34/34`, exit 0 | ✅ `34/34 verbs converged`, exit 0, 47 s |
| **C3** | `make latch-check` | `9/9` | ✅ `9/9 rows`, trigger `$1197`, exit 0 |
| **C4** | `make preflight-check` | 0 unguarded | ✅ 94 guarded, **0** unguarded |
| **C5** | `make -q build/zerobas-main-eu.rom` | exit 0 | ✅ exit 0 throughout — no ROM rebuilt |
| **C6** | `make unit-test` | 57/57 | ✅ `ALL 57 TEST FILE(S) PASSED` |

## 6. Closing the class — and giving the new gate a subject before it has none

`tools/check_probe_injectors.py` / `make injector-check`. AST, not grep: a file
is an offender when its **string literals** emit `debug write memory` and it
**names** a type-ahead cursor. Prose does not count, which matters in a tree that
explains this mechanism at length in comments on files that compose nothing.

| # | run | predicted | measured |
|---|---|---|---|
| **K3** | the checker on the tree **before** the re-point | **1** offender, exit 1 | ✅ `probes/disk/disk_probe_getput.py — emits 'debug write memory' and names _GETPNT, _PUTPNT`, exit 1. 256 files scanned, 3 exempt |
| **K3 ctrl** | the same checker after the re-point | 0 offenders, exit 0 | ✅ `0`, exit 0 |

K3's ordering is the whole anti-vacuity argument: the gate was shown to find the
copy that existed **before** it was allowed to report that none do.

### 6.1 The self-test, and the knife that did not cut

After the re-point this walk has **zero** offenders, so it would pass with its
judgement deleted — [[fixing-the-fault-silences-the-control]] arriving a second
time, in the same slice, on the gate written to close it. So the classifier is
scored on two frozen bodies before every walk.

| # | cut | predicted | measured |
|---|---|---|---|
| **K4a** | cursor detection removed (the "flag nothing" direction) | refuse to judge, non-zero | ✅ `CANNOT JUDGE — the FROZEN pre-D-LATCH injector classifies CLEAN … a clean walk would prove nothing`, **rc 2** |
| **K4b** | cursor requirement dropped (the "flag everything" direction) | refuse to judge, non-zero | 🔴 **first attempt: rc 0, self-test PASS — THE KNIFE DID NOT CUT** |
| **K5** | 🎯 K2-shaped: walk intact, report intact, only the verdict gutted, on the **pre**-re-point tree | `0 offenders, exit 0` — a green gate over a tree that has one | 🔴 **prediction wrong, in the safe direction**: the self-test caught it first — `CANNOT JUDGE`, **rc 2** |

**K4b is the finding of this section.** The negative control was
`FROZEN_CLEAN` — the shape a re-pointed probe has — and as first written it
emitted **no** `debug write memory` at all. It therefore classified CLEAN for a
trivial reason, and a classifier that dropped the cursor half and flagged every
file that writes emulated memory *passed the self-test anyway*. The "flag
everything" side of the two-sided control was decorative.

A negative control has to be the thing that would actually be mis-flagged.
`FROZEN_CLEAN` now pokes an unrelated address (`SCRMOD`) through
`debug write memory` and calls `key_proc()` — the shape dozens of real probes
have. Re-scored:

| # | cut | measured on the strengthened control |
|---|---|---|
| **K4a** | flag-nothing | ✅ `CANNOT JUDGE — … classifies CLEAN … no longer recognises the fault it exists for`, rc 2 |
| **K4b** | flag-everything | ✅ `CANNOT JUDGE — the FROZEN re-pointed body classifies COMPOSES … this classifier flags the FIX, so every walk is noise`, rc 2 |

Both sides bite now. The knife that failed is the reading, not the classifier's
innocence [[knife-found-defect-in-own-fix]] — believing K4b's first result would
have shipped a two-sided self-test with one side asleep, in the same file whose
entire purpose is that a control must have a subject.

**K5's correction is worth keeping too.** It was pre-registered as a green-gate
demonstration and it is not one: the frozen self-test runs *before* the walk, so
gutting the verdict trips the self-test rather than producing a clean tally. The
prediction was written from the shape of the failure D-LATCH hit, and the gate
happens to be built so that failure cannot occur. Recorded as a wrong prediction
rather than quietly rewritten to match [[control-inverted-by-its-own-fix]].

## 7. The blast radius, priced

`make lnblank-say-acceptance`, default `REPEAT=1`, all three sides, stdout and
stderr captured separately because the delivery announcements go to stderr.

| # | predicted | measured |
|---|---|---|
| **T1** | `204/204 gating rows agree across ['vg8020', 'cf3300', 'zb'] (5 of them allowlisted as KNOWN_DIVERGE, pinned to their exact value)`, exit 0 | ✅ **verbatim**, exit 0, 204 rows in the table |
| **T2** | zero `MIS-ECHOED` / `MIS-DELIVERED` / `ORACLES DISAGREE` / `APPARATUS FAILURE` | ✅ **0 / 0 / 0 / 0**, on stdout *and* stderr — stderr was **0 bytes** |
| **T4** | no `ALLOWLIST FAILURE`, no `MEASURED BUT NOT GATING`, no `DIVERGENT` | ✅ none, and no `UNSTABLE` / `NOCAPTURE` / `<NO ECHO>` either |
| **T5** | any row that moves is attributed against `HEAD~1`'s injector | ✅ **not exercised — no row moved** |

Nothing moved. The D-LATCH injector change is priced across the last standing
corpus member that had not seen it, and it costs nothing.

### 7.1 🔴 T3 — zero announcements is worth nothing until the guard is shown to bite

This probe's own history is [[echo-guard-never-saw-say-rows]]: the `SAY_ONLY`
filter once removed every one of these rows from the echo pass, so the guard
reported zero **by construction** while claiming coverage it did not have. A
0-byte stderr has exactly the same shape as that failure.

So the guard was given a subject. `omsx_repl.key_proc` was monkeypatched on the
imported module object — no tracked file touched — to swallow the first byte of
every injection: the same damage the race produces, with a swallow of exactly 1
instead of `len(predecessor)`. Same probe, same `--gate --say` mode, same rows.

| # | run | predicted | measured |
|---|---|---|---|
| **T3** | `--gate --say --sides zb --only lnrd-`, injector swallowing 1 byte | the guard must announce | ✅ `APPARATUS FAILURE — boot-per-case delivery was mangled; nothing was measured.` + **5 × `MIS-ECHOED`** on stderr, **rc 1**, aborted on the first case |
| **T3 ctrl** | the identical subset, shipped injector, same session | silent | ✅ stderr **0 bytes**, rc 0, 7 rows measured |

The announcement is specific enough to be worth quoting — it reports the swallow
count and rules out the alternative explanation by itself:

```
MIS-ECHOED case 0 ... (slot 2): typed 'CLS', machine echoed 'LS'
  -- 1 leading char(s) swallowed, and the screen lost nothing, so no clear
     or scroll erased them. The line was delivered mangled
```

Knife fires, control silent, same subset, same session. **T2's zero is a
measurement.**

### 7.2 🎯 The cost that deferred this suite was wrong by a factor of ~25

| | |
|---|---|
| estimate on file (D-LATCH §4bis.5, `TODO.md`, `Makefile:1266`) | **~3.5–4 h** |
| measured, wall clock, `make repack-machine` included | **8 min 58 s** (07:54:20 → 08:03:18) |

204 rows × 3 sides, boot-per-case — about 0.9 s per boot, which is what an
unthrottled `renderer none` openMSX costs on this host, and exactly what
[[emulator-gates-are-fast-dont-sleep-poll]] already records for other gates.

This is the actual finding of item A. The suite was not skipped because it is
expensive; it was skipped because of a number nobody had re-measured since the
harness stopped sleep-polling. A stale cost estimate is not a neutral piece of
documentation — it is a **standing argument for not running a gate**, and it won
that argument once already, in the slice that filed this item. The estimate is
corrected in the Makefile and in `TODO.md` rather than left for the next reader
to re-derive.

## 8. Open

* **The second latch window is still open** (D-LATCH spec §2.5). Nothing here
  touches it, and both delivery oracles stay armed because of it.
* **`injector-check` is a text classifier**, not a semantic one. It catches the
  shape that has occurred six times; a probe reaching the cursors by another
  spelling passes it. It fails closed on files it cannot parse, which is a
  mitigation and not a proof.
* **M1's zero is a weak reading and is reported as one.** 16 slots against an
  observed rate of 6 in 2039 has an expected count of 0.05. What carries §4 is
  not the zero — it is the 15/15 precondition and the `$119B` landing.
* **The CF-3300 side of `getput` is not boundary-analysed.** `key_proc` is
  already proven there by every `omsx_repl` probe; locating that machine's
  `chget` would need a disassembly this project does not do
  [[no-reference-rom-disasm]].
