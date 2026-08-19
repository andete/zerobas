# D-DSKJUDGE — what a `build/disk.rom` content gate would catch, measured

Closes the residual D-ROMJUDGE filed in `TODO.md`: **`build/disk.rom` has no
content-reading gate at all**, and carries **68 of the tree's 74 `ds <fixed> - $`
sites** — the padding shape whose overrun D-P0BASE proved is silent. Predecessors:
[docs/spec-rom-gate-judge.md](spec-rom-gate-judge.md),
[docs/spec-rom-region-p0base.md](spec-rom-region-p0base.md) §6.3.

Baseline for every figure here: `rm -rf build && make all && make repack-machine`
at `fd58b3a`. `sha256(build/disk.rom) = 2c630d3d…33c27`,
`sha256(build/sub.rom) = b2935188…97e5e`,
`sha256(build/basic-reloc.rom) = 3f1cd586…594af`.

**VERDICT: the gate is DECLINED, measured.** Every one of six corrupted
`disk.rom` images is caught by the existing corpus — the opposite of the sub-ROM
result that motivated the residual, where five of six passed at rc 0. The
measurement did find a live defect, in a different place from the one the
residual named: **`make fat-error-acceptance` reports `ALL PASS  8/8` on an
entirely-`$00` disk ROM**, and on all five other corruptions too. That is fixed
here.

---

## 0. The question this slice was told to answer FIRST

Not *"add a content gate for `disk.rom`"*. The load-bearing question is **what
would a `disk.rom` content gate CATCH that the existing corpus does not** — and a
measured DECLINE is a valid answer.

The handed-over framing carried four claims. Checked before any change:

| filed claim | measured |
|---|---|
| "`build/disk.rom` has **no content-reading gate at all**" | **half true, and the half that is true does not matter.** No *host-side* tool reads its bytes and judges them (§1). But `install-repack-machine.py` writes its absolute path into the machine XML, so **four gate families execute all 16384 bytes**, and they catch **6 of 6** corruptions (§2.1) |
| "68 of 74 `ds <fixed> - $` sites are under `disk/`" | **confirmed exactly** — 74 directives in 8 files (7 further matches are comment text), 68 under `disk/`. But the count was never the risk: **all 68 have positive slack, minimum 1 B**, and a pad is *self-anchoring* — the canonical entry cannot drift from body growth (§1.3) |
| "the padding shape whose overrun D-P0BASE proved is silent" | **not silent here.** An overrun at any of the 68 gives pasmo a negative `ds` → 0 bytes → `pad_rom.py` refuses → `.DELETE_ON_ERROR:` removes the artifact. Falsified on the **disk** rule specifically, twice each (§2.3) |
| "is the length half already closed?" | **yes, and re-measured on the disk build rather than inherited**: `build/disk.rom: 16384 bytes (exact -- the assembler wrote the whole image)`, zero slack for `--pad` to absorb |

[[filed-justification-is-a-claim]]: eighth slice running. This time the filed
claims are **mostly right and pointed at the wrong risk** — which is a new failure
mode for this counter, and the reason the deliverable is a decline rather than a
fix.

---

## 1. The denominator: who reads `build/disk.rom`'s BYTES?

### 1.1 Host side — classified the way D-ROMJUDGE §1 did

Every hit for `disk.rom` / `DISK_ROM` / `--disk-rom` across `tools/`, `probes/`
and `tests/`, classified by what it actually opens.

| reader | reads ROM **BYTES** | judges them |
|---|---|---|
| `tools/pad_rom.py` (Makefile:232) | **length only** | **YES** — exact 16384, refuses SHORT and EMPTY |
| `tools/install-repack-machine.py` | no — `os.path.abspath` into the machine XML | — |
| `tools/install-openmsx-machine.py` | no — path + `os.path.isfile` | — |
| `probes/basic/basic_probe_kwsweep.py:442` | **all 16384**, `sha256[:12]` | **NO** — a report fingerprint, printed so a concurrent `make` cannot silently re-target a measurement |
| `tests/test_getdpb.py` and every other `tests/test_*.py` | no — **re-assembles `disk/disk.asm` into `/tmp`** | (SOURCE reader) |
| `probes/disk/wrblk_perf.py` | no — re-assembles, optionally at a git ref | (SOURCE reader) |
| `probes/disk/disk_probe_diskrom_crossvendor.py` | other vendors' ROMs, not ours | — |
| everything else in `probes/disk/` | no — the string is in a *docstring* telling you to run `install-openmsx-machine.py` | — |

**Host-side content-readers of `build/disk.rom` that JUDGE: zero.** The filed
claim is correct as stated. One reader consumes 100 % of the image and only
reports (`kwsweep`, and `make kwsweep` is a coverage report, not a gate).

That is a *larger* hole than sub.rom's on paper — sub.rom had exactly one judging
content reader at 3.2 % — and §2 is where it stops mattering.

### 1.2 The instrument that does exist: the emulator

`tools/install-repack-machine.py:136` writes `build/disk.rom`'s **absolute path**
into `~/.openMSX/share/machines/C-BIOS_MSX1_EU_REPACK_DISK.xml`, slot 3-1. Every
gate whose Makefile line carries `repack-machine` therefore executes the exact
bytes on disk. Four families read it by **running** it:

* `make probe` — `disk_probe_dskio.py`, the `$4010` DSKIO differential vs CF-3300
* `make bdos-acceptance` — 12 gated BDOSX differentials, 0-byte-diff vs stock
* `make diskbasic-acceptance` — 34 Disk-BASIC verb differentials
* `make fat-error-acceptance` — 8 error-disposition rows + a directory check

⚠️ Their sensitivity is **inherited from each probe's own assertion**
([[acceptance-runner-adds-no-judgement]]) — which is exactly how the fourth one
turns out to be blind.

### 1.3 The 68 pads are self-anchoring, and that is the whole answer to "68 of 74"

Every `ds <fixed> - $` directive under `disk/`, with the pad length **measured
from the golden image** (count the `$00` run below each pinned address):

```
68 sites, min pad 1 B ($4C29 fat.asm:838, $50C8 kernel.asm:193),
          max pad 3464 B ($75A5 kernel.asm:2046)
sites with ZERO slack: 0
```

A `ds <target> - $` pad makes the address after it **true by construction**:

* body **grows** → the pad shrinks → the canonical entry stays put;
* body grows **past** the target → negative count → pasmo writes **0 bytes** →
  `pad_rom.py` refuses EMPTY (§2.3);
* body **shrinks** → the pad grows → the canonical entry stays put, and the image
  is still 16384 because the final `ds $8000 - $` absorbs the difference.

So "68 `ds` sites" is not 68 chances for a canonical entry to drift. It is 68
places that *pin* one. The only way to move an entry is to edit the pad line
itself — knife **S3**, §5.

`disk/` also carries the tree's only *source-level* address asserts, and they
guard the one region a pad cannot: `disk/runtime.asm:666,677`, the
`IF ($ > $7F80)` / `IF ($ <= $7FBF)` pair around the WD2793 FDC register window.

---

## 2. Falsify by deleting the code under test

### 2.1 The corruption × gate matrix

Six corrupted states of `build/disk.rom`, each written from a golden copy, each
run through all four emulator gate families. **C0 is the green control**, measured
first. C3/C4 are shaped like the real laundering artifact (*pasmo wrote N bytes,
the rest is `$00`*). C5/C6 flip one byte **at** a pinned canonical entry.

| | `probe` | `fat-error` | `bdos-acceptance` | `diskbasic-acceptance` |
|---|---|---|---|---|
| **C0** golden (control) | PASS | PASS | PASS | 34/34 PASS |
| **C1** all-`$00` | **FAIL** | 🔴 **PASS 8/8** | **FAIL** | **FAIL** |
| **C2** all-`$FF` | **FAIL** | 🔴 **PASS 8/8** | **FAIL** | **FAIL** |
| **C3** first 50 % + `$00` (3706 live B lost) | **FAIL** | 🔴 **PASS 8/8** | **FAIL** | **FAIL** |
| **C4** first 99 % + `$00` (43 live B lost) | PASS | 🔴 **PASS 8/8** | **FAIL** | **FAIL** |
| **C5** 1 byte flipped at `$4010` DSKIO | **FAIL** | 🔴 **PASS 8/8** | PASS | **FAIL** |
| **C6** 1 byte flipped at `$5006` SNEXT | PASS | 🔴 **PASS 8/8** | **FAIL** | (see §6) |

**Six of six corruptions are caught, every one by at least two gates.** That is
the inverse of D-ROMJUDGE's sub.rom result (five of six passed at rc 0), and it
is the whole case for the decline.

The rows also prove the matrix is measuring `disk.rom` and not something else:
C5 and C6 differ from golden by **one byte each** and produce **opposite**
`probe`/`bdos` verdicts, so `make` is demonstrably not rebuilding underneath the
knife, and no gate is answering from a cache.

Three readings:

1. **`probe` is a DSKIO instrument, not a ROM instrument.** It goes red on C5
   (the `$4010` veneer it calls) and green on C6 (a BDOS entry it never reaches).
   Correct behaviour; it just is not the backstop.
2. **`bdos-acceptance` is the deep one.** It is the only gate that catches C6, and
   the only one that catches C4 — 43 bytes of `conout_emit_e`'s tail at `$7FD1`,
   which is DOS console output and nothing else. Conversely it passes C5, because
   the DOS path reaches the FDC driver internally rather than through the `$4010`
   veneer.
3. 🔴 **`fat-error-acceptance` is red in ZERO of six.** §2.2.

### 2.2 🔴 The live defect: a gate whose expected answer is an ERROR passes a dead subject

`make fat-error-acceptance` reports, on an **entirely-`$00`** `build/disk.rom`:

```
  PASS  load-missing   LOAD"A:NOSUCH.BAS"                     -> 'load error'
  … 8 rows …
  PASS  append-missing (directory) -> 'NOSUCH  DAT' absent, as on the CF-3300
  ===== FAT error disposition: 8/8 + directory check =====
  ALL PASS
```

exit 0. The eight rows assert that a missing file produces zerobas's lowercase
`load error`. With no working disk ROM **every** file is missing, so all eight
pass — and the directory check passes too, because a machine that cannot write
also cannot create `NOSUCH.DAT`.

⚠️ **The probe's own comment already names this class and closed only one instance
of it.** `disk_probe_fat_error_disposition.py:221`:

> *"With an empty drive every case fails in `fat_mount` and never reaches
> `fat_find` at all — so the whole battery measured the MOUNT miss while the
> docstring claimed the FIND miss, and the two are indistinguishable by their
> answer (`load error` either way)."*

D-APPMISS fixed that by **mounting a disk**. But mounting a disk only removes one
reason `fat_mount` can fail. A dead disk ROM is another, an unhooked HPHYD is
another, and a `pageenv` regression is another — and the gate cannot tell any of
them from the disposition it exists to measure. The fix is not another instance;
it is the **precondition** ([[precondition-is-the-instrument]]): prove the FAT
layer can reach a **SUCCESS** disposition on this machine before believing eight
failures.

### 2.3 The producer half, re-measured on the DISK rule (not inherited)

D-ROMJUDGE's findings were measured on `build/sub.rom`. All three re-run against
`$(DISK_ROM)`:

* **exactness** — `python3 tools/pad_rom.py build/disk.rom 16384` on a clean tree
  prints `16384 bytes (exact -- the assembler wrote the whole image)`. `--pad` has
  zero slack to absorb, same as sub.
* **negative `ds`** — knife S2, §5: an overrun at the tightest disk pad
  (`ds $4C29 - $`, 1 B slack) gives `pasmo` exit 0 and a **0-byte** file, and
  `pad_rom` refuses it.
* **the second `make`** — knife S1/S2 are each run **TWICE**
  ([[refusal-survives-only-if-the-artifact-does]]). `.DELETE_ON_ERROR:` is a
  global directive but its coverage of *this* rule is measured, not assumed.

### 2.4 The blind window, computed

D-ROMJUDGE computed sub.rom's invisible-truncation window as its trailing pad,
**2324 B**. The same measurement on `disk.rom`:

```
trailing $00 run: 2 B (last non-zero byte at $7FFD)
total $00 in image: 9543 B (58.2 %), in 252 runs, largest 3464 B ($681D-$75A4)
```

**The blind window for a short `disk.rom` is 2 bytes.** The image is effectively
full to its ceiling, so a truncation of any consequence lands on live content —
unlike sub.rom, where 2324 bytes could vanish semantically unobserved. This is the
second independent reason the disk build is in a better position than the sub
build, and neither had been written down.

⚠️ It does **not** mean pad damage is visible. 58 % of the image is `$00` pad in
252 runs, and corrupting pad-only bytes remains invisible to every gate **by
design** — closing that needs a whole-image digest, which would pin the ROM
against every legitimate change. Restated as deliberate in §3.4, not fixed.

---

## 3. Design

### 3.1 DECLINED: a `check_reloc.py`-style canonical-entry gate for `disk.rom`

The shape the handover suggested — judge the pinned canonical entry addresses
(`$4010` DSKIO and friends) against the ROM's actual bytes. Declined on three
measurements, each of which alone would be enough:

1. **It has no failure to catch.** Every canonical entry is already pinned *by
   construction* by its own `ds` pad (§1.3), all 68 with positive slack, and the
   one edit that could move one is caught by `bdos-acceptance` (C6, and knife S3).
2. **A `jp` at the right address is not the property that matters.** C5 and C6
   both leave a `C3` at the canonical address and corrupt its *target*; a gate
   that checks "`$4010` holds a `JP`" passes both. To catch what the corpus
   catches, the gate would have to judge the bytes behind the entry — i.e. become
   a whole-image digest, which is §3.4.
3. **`disk.rom` has no `.sym`.** The Makefile rule assembles `--bin` only, so a
   symbol-driven gate would need either a new build output or a second, drifting
   copy of the address list in Python. `tools/check_kwtable_identity.py`'s pinned
   constant is affordable because one table changes rarely; 68 addresses
   maintained by hand is the [[deadcode-gate]] allowlist failure waiting to happen.

The residual is therefore **closed as DECLINED**, in the shape D-PINDATA used for
`input.asm`: measured, written down, and not built.

### 3.2 FIXED: the precondition for `fat-error-acceptance`

`probes/disk/disk_probe_fat_error_disposition.py` gains one batched case that runs
**before** the eight error rows and must produce **positive** evidence:

```
CONTROL = ("fat-alive", 'FILES"A:HI.TXT"', "HI")
```

`HI.TXT` is on `disk/test720.dsk` (26 B). Listing it requires `fat_mount`
(boot-sector read through DSKIO), the root-directory walk, and a `fat_find` **hit**
— the Cy=0 half of `fatprim_bounce` that all eight error rows are the Cy=1 half of.
A dead disk ROM cannot print the name.

⚠️ The assertion is **positive text on screen**, not "no `load error`". The
probe's own docstring records that a broken error tail returns **silently**, so
absence-of-error is exactly the reading a broken build also produces
([[gate-can-be-green-while-measuring-nothing]]: ask which bytes reach the
comparison). A row whose PASS condition can be met by silence is not a control.

When the control fails the probe returns 2 (**not** 1) and says the eight rows
below are **vacuous**, so the two dispositions are distinguishable in a log:
`1` = a real error-disposition regression, `2` = the instrument was not
functioning and the run measured nothing.

### 3.3 DELETED: unreachable dead code in `tools/build_patches.py`

`ensure_basic_rom()` (line 116) is called from exactly one place,
`_build_page1_retired()` (line 153), which has **zero callers** — `build_page1()`
`sys.exit`s the retired mode (lean retirement 2026-07-29). Verified by grep across
`tools/`, `probes/`, `tests/`, both Makefiles. Both functions are deleted.

Worth recording rather than just deleting: the dead body would also **fail if it
ran**. It assembles `basic/main.asm` and calls `pad_rom.py <rom> 16384`, but
`basic/main.asm` has assembled at `BASIC_ORG = $2812` spanning to `$8000` since
the same retirement — 22510 bytes, which `pad_rom` now answers with
`exceeds target 16384`. Dead code does not rot quietly; it rots into a call that
would take the build down the first time anything reached it.

### 3.4 What does NOT change, and why

* **No whole-image digest for `disk.rom`.** It would catch pad-only damage — the
  one class §2.4 leaves open — at the price of pinning 16384 bytes against every
  legitimate change to `disk/*.asm`. Every `ds`-anchored ROM in this tree is
  *supposed* to move when its source moves. Restated as deliberate.
* **No new source-level address asserts.** The pads already are the assert
  (§1.3), and a `ds <target> - $` pad in front of an equality check makes that
  check **vacuous** — [[negative-ds-ships-an-empty-rom]]'s second lesson, landed
  one day before this slice by the same author.
* **`probe`, `bdos-acceptance`, `diskbasic-acceptance` unchanged.** They caught
  6 of 6; there is nothing here to improve them with.
* **No ROM change of any kind.** §6 proves neutrality by hash.

---

## 4. Predicted GREEN — fixed BEFORE the change

Exact values, from the `fd58b3a` clean baseline above.

| reading | predicted |
|---|---|
| `sha256(build/disk.rom)` | `2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27` — **unchanged** |
| `sha256(build/sub.rom)` | `b2935188…97e5e` — unchanged |
| `sha256(build/basic-reloc.rom)` | `3f1cd586…594af` — unchanged |
| low region free | **23 B** |
| page 1 free | **356 B** |
| sub page 0 / page 1 free | **3869 B** / **2324 B** |
| closure walks | abi **122+4**, `--page0` **718+15**, `--page1` **522+41** |
| dead code main / sub | **1551 spans / 285 seeds → 0**, **1451 / 102 → 0** |
| kwtable | **1041 B**, pinned sha256 matches |
| `pad_rom` on disk | `build/disk.rom: 16384 bytes (exact …)` |
| `unit-test` | 58/58 |
| `diskbasic-acceptance` | 34/34 |
| `bdos-acceptance` | 12/12 gated (1 screen skipped) |
| `fat-error-acceptance` | **9 rows** (1 control + 8) + directory check, ALL PASS |
| `lnblank-acceptance REPEAT=2` | 536/536 |
| `linemax-acceptance` | 60/60 |
| `latch-check` / `dexp5-pin` | 16/16 · 16/16 |
| `lof-acceptance` | 45 cases, **0 oracle drift** (sighting 4 watch — full log captured) |

⚠️ **The dead-code seed counts are a prediction about my own prose.**
`check_dead_code.py` scans `tools/` and `sub/` comments for `external_names`, so
deleting 25 lines of `tools/build_patches.py` and adding a docstring to a `probes/`
file must leave main at **285** and sub at **102**. Any movement is a finding about
this slice's writing, not about the ROM.

---

## 5. Predicted RED — the knives

Every knife names the gate **by the file it runs**, not by a plausible target name
([[knife-aimed-at-the-wrong-gate]]). Each refusal knife is run **twice**.

| knife | cut | predicted |
|---|---|---|
| **S1** | comment out `disk/runtime.asm:721` `ds $8000 - $, $00` → short assembly | `make disk` rc 2, `pad_rom` SHORT naming the byte count. **Run 2:** still rc 2, `build/disk.rom` **absent** (`.DELETE_ON_ERROR:` covers this rule) |
| **S2** | insert 4 bytes before `disk/fat.asm:838` `ds $4C29 - $` (1 B slack) → negative `ds` | pasmo warns at **exit 0**, writes **0 bytes**; `pad_rom` refuses EMPTY, rc 2. **Run 2:** still rc 2, artifact absent |
| **S3** | delete `disk/kernel.asm:40` `ds $5006 - $, $00` → `snext` displaced, image **still 16384** | `pad_rom` **GREEN** (the producer cannot see it) → `make bdos-acceptance` **RED** on the SNEXT/DIR differentials. This is the knife that decides §3.1 |
| **K2** | keep the new control's emission and call site, gut only its judgement (`good = True`) | `make fat-error-acceptance` **rc 0 on an all-`$00` disk.rom** — i.e. reproduces §2.2 exactly. Proves the new row's PASS comes from its assertion, not its presence |
| **K3** | delete `tools/build_patches.py`'s deleted functions' *callers* — n/a | no knife: the deletion is proved by `make release` + `make patches` still building, plus the grep in §3.3 |

### 5.1 Stated coverage limit, before running

* **Pad-only damage stays invisible** (§3.4). 9543 of 16384 bytes are `$00` pad;
  a corruption confined to them is caught by nothing, deliberately.
* **The control proves the FAT layer is alive, not that it is CORRECT.** A build
  whose `fat_find` hits are right and whose miss disposition is broken is what the
  eight rows are for; a build where both are broken in the same direction is
  outside any single-observable gate.
* **The matrix corrupts the ARTIFACT, not the source.** Only S1–S3 go through
  `pasmo`, so "what a bad `disk/*.asm` edit produces" is measured at three points,
  not exhaustively.

---

## 6. As-built — ✅ LANDED 2026-08-05

Three changes, none of them the gate the residual asked for:

* **DECLINED** — no `disk.rom` content gate. §3.1, on three independent
  measurements.
* **`probes/disk/disk_probe_fat_error_disposition.py`** — one PRECONDITION row,
  exit code 2 for "not measured". §6.3.
* **`tools/build_patches.py`** — 25 lines of unreachable dead code deleted. §3.3.

### 6.1 GREEN, scored — every §4 prediction hit exactly

🎯 **ROM-neutral, proved by hash.** All six `build/*.rom` byte-identical to
`fd58b3a` after `rm -rf build && make basic-reloc && make all`:

```
2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27  build/disk.rom
b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e  build/sub.rom
3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af  build/basic-reloc.rom
d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e  build/zerobas-main-eu.rom
```

Walls from clean: low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1
**2324 B**. Closure walks abi **122+4**, `--page0` **718+15**, `--page1`
**522+41**. Dead code main **1551 spans / 285 seeds → 0**, sub **1451 / 102 → 0**
(+1 allowlisted) — **the seed counts did not move**, so deleting 25 lines of
`tools/` code and adding this slice's prose to it seeded nothing new. kwtable
**1041 B**, pinned `sha256` matches. `pad_rom`:
`build/disk.rom: 16384 bytes (exact -- the assembler wrote the whole image)`.

Gates: see §6.5.

### 6.2 RED, and what each knife found

| knife | predicted | measured |
|---|---|---|
| **S1** short assembly (`disk/runtime.asm:721` pad cut) | rc 2 twice, artifact gone | ✅ `SHORT -- the assembler wrote 16382 bytes, 2 short of 16384`, **rc 2 both runs**, `make: *** Deleting file 'build/disk.rom'` both times, `ls` says absent both times |
| **S2** negative `ds` at the 1-byte `$4C29` pad | pasmo exit 0 + 0 bytes, EMPTY refusal twice | ✅ `WARNING: 64KB limit passed inside instruction on line 839 of file fat.asm`, **pasmo rc 0**, **0-byte output**, `pad_rom` `EMPTY`, rc 2 both runs, artifact deleted both times |
| **S3** delete the `$5006` pad line | producer green, `bdos-acceptance` red | ✅ `snext` moved `$5006` → **`$4FBB`** (`k_501E` unmoved — the next pad absorbed it), image **16384 exact**, `pad_rom` **GREEN** — and `make bdos-acceptance` **10/12**, the two `BDOSX` dir-search captures `MISALIGNED — ours never reached the anchor`. `make probe` stayed **GREEN** on the same image (the in-knife control) |
| **R1** new control vs all-`$00` `disk.rom` | rc 2, rows unscored | ✅ `FAIL fat-alive … -> 'load error' [PRECONDITION]`, **rc 2**, all eight rows printed `(not scored)`, `NOT MEASURED (precondition failed)` |
| **K2** gut only `ctl_ok` | rc 0, `ALL PASS` on a dead ROM | ✅ **rc 0**, `PASS fat-alive … -> 'load error'`, `8/8 + directory check`. Emission intact, call site intact, judgement gutted — the row's PASS comes from its assertion and nothing else |

**Every RED row has a GREEN control**: S1/S2 against the unmodified rule (which
prints `16384 (exact)`), S3 against `make probe` on the same knifed image, R1/K2
against the golden `disk.rom` run in §6.5.

⚠️ **S1 initially read GREEN for a reason that was mine, not the code's.** The
first two invocations printed `Nothing to be done for 'disk'` — I had restored the
golden `build/disk.rom` *after* editing `disk/runtime.asm`, so the artifact was
newer than its own source and `make` never ran the rule. Before believing a green
knife, check it CUT ([[knife-aimed-at-the-wrong-gate]]): `touch disk/runtime.asm`
and it cuts. The same one-line mistake is what `.DELETE_ON_ERROR:` exists to
prevent when the *build* makes it.

### 6.3 🔴 The finding: `fat-error-acceptance` was red in 0 of 6

The matrix (§2.1) is the whole result, and the row that matters is the third
column. The gate whose stated job is *"measure the half `diskbasic-acceptance`
misses"* is the only one in the corpus that catches nothing at all.

It is not a bug in any of the eight rows, and no amount of hardening them moves
it: **a battery whose expected answer is an error cannot distinguish a correct
refusal from a dead subject.** What separates the two is a boolean the harness
never asked for — *did the FAT layer ever reach a SUCCESS disposition on this
machine?* — which is the same shape as `subrom-inttest`'s capture-path fix one
slice earlier ([[a-band-is-one-sample-of-one-failure-mode]],
[[precondition-is-the-instrument]]). Two consecutive slices, two gates, same
remedy: **assert the precondition instead of calibrating the reading.**

⚠️ And the class was already written down *in this file*, by the person who fixed
one instance of it (`main()`'s "A DISK MUST BE MOUNTED" comment, D-APPMISS
2026-07-31). Mounting a disk removes one reason `fat_mount` can fail. The
precondition removes the need to enumerate them.

### 6.4 🔴 The eighth filed justification, and a new way for one to be wrong

[[filed-justification-is-a-claim]] has counted seven filed claims and seven wrong.
This one breaks the streak in an uncomfortable way: **the claims were accurate and
still misdirected the work.** "No content-reading gate at all" is literally true
of every host tool. "68 of 74 `ds` sites" is exact. Neither is a risk, because the
first ignores the emulator and the second ignores that a pad *pins* the address it
precedes rather than endangering it.

⇒ **a correct claim can still be the wrong question.** The load-bearing question
was never *"does a gate read these bytes?"* but *"what fails if these bytes are
wrong, and does anything notice?"* — and answering the second one is what found a
gate that notices nothing. Same shape as D-LATCH's *"is there a target called
`getput`?"* vs *"is this file scored?"*, reached from the opposite direction: there
the claim was false, here it was true and equally useless.

### 6.5 Corpus — ALL GREEN, sequential, from the clean `fd58b3a` tree

| gate | result |
|---|---|
| `basic-reloc` (deadcode + 3 closure walks + kwtable) | rc 0, every §4 number exact |
| `unit-test` | **58/58** test files |
| `subrom-acceptance` · `subrom-inttest` | PASS · PASS (`capture path = bp`, `delta = 28`) |
| `graphics-floor-acceptance` · `graphics-acceptance` | PASS · PASS |
| `preflight-check` · `injector-check` | ALL PASS · ALL PASS |
| `latch-check` · `dexp5-pin` | **16/16** · ALL PASS |
| `linemax-acceptance` | **60/60** |
| `lnblank-acceptance REPEAT=2` | **536/536** |
| `probe` | smoke OK (disk + basic + tape) |
| `fat-error-acceptance` | **8/8 + directory check, over a LIVE FAT layer** (9 rows incl. the new PRECONDITION) |
| `diskbasic-acceptance` | **34/34** verbs converged |
| `bdos-acceptance` | **12/12** gated differentials (1 screen skipped) |
| `lof-acceptance` | **45 cases, 0 unfiled divergence, 0 oracle drift, 0 mangled** |

⚠️ `lof` **sighting 3 did not occur — fourth consecutive slice.** Full log
captured (`> file 2>&1`), not tailed. Two sightings of intermittent oracle drift
remain on the record with nothing since; a third is still a finding to chase if it
appears.

### 6.6 What this slice did NOT do

* **No `disk.rom` content gate**, and no whole-image digest (§3.1, §3.4). The
  pad-only blind window — 9543 of 16384 bytes, 58.2 %, 252 runs — stays open
  **deliberately** and is re-filed in `TODO.md` as such.
* **No change to `probe` / `bdos-acceptance` / `diskbasic-acceptance`.** They
  caught 6 of 6.
* **No change to any `disk/*.asm` source.** The 68 pads and the two
  `IF ($ > $7F80)` FDC-window asserts are left exactly as they are; §1.3 is the
  argument for why they are already the right instrument.
* **No new source-level address assert.** A `ds <target> - $` pad in front of an
  equality check makes that check vacuous — [[negative-ds-ships-an-empty-rom]]'s
  second lesson, landed the day before this slice.
