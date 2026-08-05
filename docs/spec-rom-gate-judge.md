# D-ROMJUDGE — the gates that read a ROM's CONTENT, and what each survives

Closes the two residuals D-P0BASE filed in `TODO.md` under ROM REGION STRUCTURE
REVIEW: **(a)** a partially truncated ROM is still laundered by
`tools/pad_rom.py`, and **(b)** `tools/check_kwtable_identity.py` prints its own
denominator and does not judge it. Predecessor:
[docs/spec-rom-region-p0base.md](spec-rom-region-p0base.md) §6.3.

Baseline for every figure here: `rm -rf build && make basic-reloc` at `9bfcfb9`.
Low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B**; closure
walks abi 122+4, `--page0` 718+15, `--page1` 522+41; dead code main 1551
spans/285 seeds → 0, sub 1451/102 → 0 (+1 allowlisted).
`sha256(build/sub.rom) = b2935188…97e5e`,
`sha256(build/basic-reloc.rom) = 3f1cd586…594af`.

---

## 0. The question this slice was told to answer FIRST

Not *"add a bound to two tools"*. The load-bearing question is **which gates read
an artifact's CONTENT, and which of them would survive that content being
wrong** — measured, not read off the Makefile's comments.

The handed-over framing carried three claims. All three were checked, and **two
of them are wrong**:

| filed claim | measured |
|---|---|
| "zerobas has at least three `ds <fixed> - $` sites" | **74 sites in 8 files** — and **68 of them are in `disk/`**, whose ROM goes through the same `pad_rom.py` and is **not covered by `make basic-reloc` at all** |
| "(b) needs a lower bound on the table size" | 🔴 a **lower** bound is the wrong shape. A single flipped byte makes the reported size go **UP**, 1041 → **6140 B**, and a floor passes that. [[one-sided-bound-passes-a-runaway]] again, one slice later |
| "a partial output is still padded silently" | true, but **not by the route named**. A negative `ds` never produces a partial file — measured, three shapes, all **0 bytes**. The reachable route is different (§2.3) |

[[filed-justification-is-a-claim]]: seventh slice running, and the count of wrong
filed claims goes up again — this time including one of my own predecessors'
one-day-old *fixes* (§2.4).

---

## 1. The denominator: who reads BYTES?

Every step of `make basic-reloc`, classified by what it actually opens.
"SOURCE" includes re-assembling.

| step | reads `.sym` | reads `*.asm` / `.inc` | reads ROM **BYTES** |
|---|---|---|---|
| `pasmo` (main) | writes | yes | writes |
| `pasmo -I sub` + `pad_rom.py` | writes | yes | **`build/sub.rom` — size only** |
| `check_reloc.py` | yes | — | **`basic-reloc.rom`: size, `"AB"` @ `$4000`, low region not all-`$00`** |
| `check_kwtable_identity.py` | yes ×2 | — | **`sub.rom`: walk from `kwtable`.** Also opens `basic-reloc.rom` and **never uses it** |
| `check_resident_abi.py` | yes | `.inc` | — |
| `check_tenant_closure.py` ×3 | yes | `sub.asm` | — |
| `check_dead_code.py` | yes ×2 | `tools/`, `sub/` (for `external_names`) | — |

**Content-readers of `build/sub.rom` inside `make basic-reloc`: exactly one**
(`check_kwtable_identity`), and it reads **1041 of 32768 bytes = 3.2 %** of the
image. D-P0BASE's "~1" is confirmed, and now has a percentage attached.

Two further facts fell out of the same sweep:

* 🔴 `check_kwtable_identity.py:66` does `reloc = open(sys.argv[1], "rb").read()`
  and **the name `reloc` is never referenced again** — a *required* ROM argument
  that is dead. The gate that exists to prove the resident copy is gone proves it
  **only from the symbol table**.
* `make unit-test` is structurally blind to `build/sub.rom` by design: every
  `tests/test_*.py` that needs a sub-ROM **re-assembles its own** into `/tmp`
  (`tests/msxtest.py:74`, `test_float.py:61`, `test_graphics.py:631`, …). It is a
  SOURCE reader, correctly classified, and cannot score a build artifact.

Outside `basic-reloc`, `build/sub.rom` reaches the emulator corpus verbatim:
`tools/install-repack-machine.py` writes its **absolute path** into
`~/.openMSX/share/machines/C-BIOS_MSX1_EU_REPACK_DISK.xml`, so every
`repack-machine` gate executes the exact bytes on disk. Those gates read content
by **running** it — which is a different instrument with a different blind spot,
measured in §2.2.

---

## 2. Falsify by deleting the code under test

### 2.1 The corruption × gate matrix

Seven states of `build/sub.rom`, each written from the golden copy, each run
through the whole chain. X0 is the **green control** and was re-run interleaved.
X3/X4 are shaped like the real laundering artifact: *pasmo wrote N bytes, then
`pad_rom` filled the rest with `$00`*.

| | `make basic-reloc` | kwtable **reported** | `subrom-acceptance` | `subrom-inttest` | `graphics-floor` |
|---|---|---|---|---|---|
| **X0** golden | rc 0 | **1041 B** ✅ | PASS | PASS | PASS |
| **X1** all-`$00` | 🔴 **rc 0** | 1 B | FAIL | FAIL | FAIL |
| **X2** all-`$FF` | rc 2 — **`IndexError` traceback**, not a judgement | — | FAIL | 🔴 **PASS** (§2.4) | — |
| **X3** first 50 % + `$00` | 🔴 **rc 0** | **1041 B** | FAIL (page-1 CALSLT) | PASS | PASS |
| **X4** first 99 % + `$00` | 🔴 **rc 0** | **1041 B** | PASS | PASS | PASS |
| **X5** one byte flipped in the table | 🔴 **rc 0** | **6140 B** | PASS | PASS | PASS |
| **X6** table terminated early | 🔴 **rc 0** | 9 B | PASS | PASS | PASS |

**Five of six corruptions pass the entire static chain at rc 0.** The sixth does
not *refuse* — it dies of an unhandled `IndexError` walking off the end of the
image, which is a crash that happens to have the right exit code.

Three readings that decide the design:

1. **X5 is why a floor is the wrong shape.** One flipped byte moved the reported
   size **up** by 5099 B and the gate said `OK`. A lower bound passes it; only an
   **exact** match refuses it.
2. **X3/X4 are why the kwtable check cannot close (a).** `kwtable` lives at
   `$2CD2`, so a truncation at 16384 or at 32440 leaves it **completely intact**
   and it reports its healthy 1041 B. A 3.2 % content check cannot certify a
   32 KB image. (a) and (b) are genuinely different instruments.
3. **X4 is invisible to everything.** Bytes 32440–32767 are inside sub page 1's
   2324-byte `$FF` pad, so zeroing them changes no behaviour at all. The blind
   window for a short `sub.rom` is **exactly the trailing pad length, 2324 B** —
   below that, no gate anywhere in the corpus can see it, by construction.

### 2.2 What the emulator corpus does and does not catch

The emulator column is the strong half: X1 turns **all three** sub-ROM gates red,
which is what the static chain could not do. But it is not uniform —
`subrom-inttest` and `graphics-floor` are **page-0** tenants, so X3 (page 1
entirely `$00`) leaves them green; only `subrom-acceptance`'s page-1 CALSLT
`$4010 -> $C1` sees it. And X5/X6, which damage only the tokeniser's data table,
are invisible to all three, because every one of them CALSLTs a tenant directly
and never tokenises a line.

### 2.3 🔴 (a): the reachable route is not the one that was filed

A negative `ds` does **not** truncate — measured three ways against the shipped
`pasmo`, and every one writes **zero** bytes at exit 0:

```
org $0000 / db 8 bytes / ds $0004-$,$FF                      -> 0 B
… + a later `org $0100` segment after the bad pad             -> 0 B
a good 256-byte segment FIRST, then the bad pad               -> 0 B
```

So the filed route for (a) was already closed by D-P0BASE's empty-input refusal.
**The reachable route is a short assembly, and it is trivially reachable.**
Knife A-pre — comment out `sub/sub.asm`'s final `ds $8000 - $, $FF`, which is one
line and exactly the shape of an ordinary source edit:

```
pasmo -I sub --bin sub/sub.asm      -> 30444 B  (short by exactly 2324)
python3 tools/pad_rom.py … 32768    -> "build/sub.rom: 32768 bytes"   ← rc 0
make basic-reloc                    -> rc 0, every gate OK
make subrom-acceptance              -> PASS
```

`pad_rom.py` printed a line **indistinguishable from a healthy build** while
inventing 2324 bytes. It reports the size it *wrote*, never the size it *read* —
[[guard-that-cannot-judge-must-say-so]] and the same shape as (b) one layer down.

And the invariant is already written down, unenforced. `Makefile:225`:

> *"the source spans `$0000-$7FFF` so pad_rom just asserts the 32 KB size"*

Measured pre-pad sizes of **every live caller**: `sub.rom` **32768/32768**,
`disk.rom` **16384/16384**, `sub-unguarded.rom` **32768/32768**. **All three pad
exactly zero bytes today**, so an exact-by-default rule has *zero* slack to
absorb — it is falsifiable on the first byte. (A fourth call site,
`tools/build_patches.py:125`, is unreachable: only `_build_page1_retired()` calls
it and nothing calls that; `build_page1()` `sys.exit`s. Filed, not touched.)

### 2.4 🔴 And the measurement found a live false negative in D-P0BASE's own fix

X2 — an **entirely `$FF`** sub-ROM, i.e. no zerobas code at all — is reported by
`subrom-inttest` as `JIFFY delta = 57 ticks (expect 1..64) … PASS`, **rc 0**.

D-P0BASE closed exactly this class **yesterday** with `DELTA_MAX = 64`, sized at
"a bit over 2×" the measured healthy 28 and "nowhere near the 255 a runaway
reads". 255 was the reading for a *partial* pad. With the whole ROM pad the
reading is **57**, which is inside the band. The bound was set from one sample of
one failure mode.

Instrumented, the discriminator is exact and free — **which capture path fired**:

| tree | capture path | delta | verdict today |
|---|---|---|---|
| X0 golden | `bp` (the stub's `halt` was reached) | 28 | PASS |
| X2 all-`$FF` | 🔴 `net` (12 s safety net; the stub **never returned**) | 57 | PASS |

The probe's own comment on that safety net says *"capture anyway (delta stays
0)"*. **It does not stay 0.** Executing `$FF` is `rst 38h` recursing forever; the
stack walks down through the whole address space and overwrites `$C100` — the
57 is a **stack byte**, not a timer reading. [[precondition-is-the-instrument]]:
"the tenant returned" is a precondition of the delta meaning anything, it is
already observable, and it was being thrown away.

---

## 3. Design

### 3.1 `tools/pad_rom.py` — stop inventing bytes

Padding becomes **opt-in**. Default: the input must already be exactly `<size>`;
anything shorter is a FAIL naming the cause. `--pad` restores the old behaviour
for a caller that genuinely needs it — **no live caller does** (§2.3), so the
flag exists to keep the *decision* explicit rather than to serve anyone.

The readout says what was judged, not what was written:
`build/sub.rom: 32768 bytes (exact — the assembler wrote the whole image)`.

No Makefile call site changes.

### 3.2 `tools/check_kwtable_identity.py` — judge the denominator, and read the ROM it is given

Four gates instead of two, and the previously-dead `RELOC.rom` argument becomes a
real content reader:

* **1a** (unchanged, `.sym`): no `kwtable` symbol in `basic-reloc.sym`.
* **1a′** (new, **BYTES**): the table's 1041 bytes occur **0 times** in
  `basic-reloc.rom`. A symbol can be lost while the bytes stay; this is the
  stronger form of the same claim, and it is what the argument was always for.
* **1b** (hardened, **BYTES**): the walk is **bounded** — running past the end of
  the image is a FAIL with a message, not an `IndexError` — and the result is
  matched **EXACTLY**, both size and `sha256`, against a pinned baseline.
* **1c** (new, **BYTES**): the table occurs **exactly once** in `sub.rom`. This
  is the gate's own name ("single-copy") finally measured, and it doubles as the
  **in-run positive control** for the byte-search primitive that 1a′ depends on:
  if the search stops finding things, 1c goes red in the same run.

**EXACT, not a floor, and the reason is measured** (§2.1 reading 1): X5 moves the
size *up*. The pin is a control that must keep matching — the same standing that
`tools/deadcode-allow.txt` has and that `check_reloc.py`'s `SIZE = 22510` has.
Adding a keyword to `basic/kwtable.inc` moves both constants; the failure text
says so and prints the new values ready to paste. That bump is a **feature**: it
makes the crunch table's content a reviewed change rather than a silent one.

Pinned values, measured from `rm -rf build && make basic-reloc` at `9bfcfb9`:

```
kwtable @ $2CD2   size 1041 B   sha256 8f120510b13498746029962b833146a37d6d1ed88a812212b662fa649d28f397
```

### 3.3 `probes/basic/basic_probe_subrom_inttest.py` — assert the precondition

The Tcl capture records which path fired (`bp` / `net`); the gate FAILs on `net`
whatever the delta says, and the failure text names the cause. Host-side only, no
ROM change. Fixed in-slice rather than filed, because a control that is known to
fail must be fixed in the slice that finds it
([[control-that-fails-must-be-fixed]]) — and because it is the second time this
one probe has been the false negative.

### 3.4 What does NOT change

**No ROM byte.** `build/sub.rom` and `build/basic-reloc.rom` must be byte-identical
to `9bfcfb9`. Nothing in `basic/`, `sub/`, `disk/` or `tape/` is touched; the
whole change is `tools/` + one probe + docs.

---

## 4. Predicted GREEN — fixed BEFORE the change

From `rm -rf build && make basic-reloc`:

* `sha256(build/sub.rom)` = `b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e`
* `sha256(build/basic-reloc.rom)` = `3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af`
* low **23 B**, page 1 **356 B**; sub p0 **3869 B**, sub p1 **2324 B**
* closure: **122**+4 · **718**+15 (13 tenants) · **522**+41 (24 tenants)
* dead code: main **1551** spans / **285** seeds → 0; sub **1451** / **102** → 0 (+1 allowlisted)
* `pad_rom`: `build/sub.rom: 32768 bytes`, `build/disk.rom: 16384 bytes`
* `check_kwtable_identity`: **1041 B**
* `subrom-inttest`: delta **28**, path **bp**

⚠️ The dead-code seed counts are a prediction about **my own prose**: `check_dead_code`'s
`external_names` scans `tools/*.py` and `sub/` **including comments**, so a new asm
label name written into a tools docstring becomes a seed. **285 / 102 must not move.**

## 5. Predicted RED — the knives

Every row paired with the X0 green control, and each knife checked for having
**CUT** ([[knife-aimed-at-the-wrong-gate]] — grep the Makefile for the FILE).

| knife | subject | predicted |
|---|---|---|
| **K1a** | X1 all-`$00` → `make basic-reloc` | rc ≠ 0 at `check_kwtable_identity`, naming size 1 ≠ 1041 |
| **K1b** | X5 flipped byte → `make basic-reloc` | rc ≠ 0, naming size **6140** ≠ 1041 — the row a floor would pass |
| **K1c** | X6 early terminator | rc ≠ 0, naming size 9 ≠ 1041 |
| **K1d** | X2 all-`$FF` | rc ≠ 0 with a **message**, no `IndexError` |
| **K1e** | resident-copy bytes spliced into a scratch `basic-reloc.rom`, sym untouched | 1a′ FAILs where 1a (sym) still passes — proves the dead argument is now load-bearing |
| **K1f** | X0 golden | **PASS** (green control) |
| **K2** | 🔪 **K2-shaped**: keep the walk, the digest and the print; delete only the comparison | X1 goes **green again** — proves the comparison is what refuses, not the walk |
| **K3a** | knife A-pre (`sub/sub.asm` final pad commented out) on the FIXED `pad_rom` | rc ≠ 0 at `pad_rom`, naming 30444 ≠ 32768 and the cause |
| **K3b** | knife A-pre on the fixed tree, `--pad` passed | pads, prints that it padded — the escape valve works and is loud |
| **K3c** | unmodified tree | `pad_rom` PASSes, 0 bytes padded (green control) |
| **K4a** | X2 → `subrom-inttest` on the fixed probe | **FAIL**, `path=net` |
| **K4b** | X0 → `subrom-inttest` on the fixed probe | **PASS**, `path=bp`, delta 28 (green control) |

### 5.1 Stated coverage limit, before running

This slice does **not** make `build/sub.rom` fully certified. After it lands:

* a short assembler output is caught **exactly** (§3.1) — the 2324 B blind window
  of §2.1 reading 3 closes at the build step, where it is a length question;
* a corrupted `sub.rom` is caught only where a gate reads or executes the damaged
  bytes. **X4-shaped damage confined to pad remains invisible, deliberately** — it
  is semantically nothing, and the instrument that would see it is a whole-image
  digest, which pins the ROM against every legitimate change too.
* `build/disk.rom` gains the same `pad_rom` protection and **nothing else** — it
  has no content-reading gate at all, and 68 of the repo's 74 `ds <fixed> - $`
  sites are in `disk/`. Filed, not fixed here.

---

## 6. As-built — ✅ LANDED 2026-08-05

Three tools changed, one probe, one Makefile line. **No `basic/`, `sub/`, `disk/`
or `tape/` source touched.**

### 6.1 GREEN, scored

`rm -rf build && make basic-reloc` reproduced **every** §4 prediction:

* `sha256(build/sub.rom)` = `b2935188…97e5e` and
  `sha256(build/basic-reloc.rom)` = `3f1cd586…594af` — **byte-identical to
  `9bfcfb9`.** The slice is ROM-neutral, proved by hash, not argued.
* low **23 B** · page 1 **356 B** · sub p0 **3869** · sub p1 **2324**
* closure **122**+4 · **718**+15 · **522**+41
* dead code main **1551**/**285** → 0 · sub **1451**/**102** → 0 (+1 allowlisted)
  — the seed counts did **not** move, so this slice's `tools/` prose introduced
  no accidental `external_names` seed.

Corpus, sequential, all from the clean tree:

| gate | result |
|---|---|
| `basic-reloc` | all OK, figures above |
| `unit-test` | **58/58** files |
| `preflight-check` · `injector-check` | ALL PASS · ALL PASS |
| `subrom-acceptance` | PASS |
| `subrom-inttest` | PASS — path **bp**, delta **28** |
| `graphics-floor-acceptance` · `graphics-acceptance` | PASS · PASS |
| `graphics-floor-teeth` | PASS (the third `pad_rom` caller: **exact**, 0 padded) |
| `latch-check` · `dexp5-pin` | **16/16** · **16/16** |
| `probe` | smoke OK (disk + basic + tape) |
| `linemax-acceptance` | **60/60** |
| `diskbasic-acceptance` | **34/34** verbs converged |
| `lnblank-acceptance REPEAT=2` | **536/536** |
| `lof-acceptance` | **45 cases, 0 oracle drift, 0 mangled** — full log captured |

⚠️ `lof-acceptance` drift **sighting 3 did not occur**, third slice running
(D-EVLNO, D-P0BASE, D-ROMJUDGE). The full 59-line log was captured, not tailed.

### 6.2 RED, and what each knife found

| knife | result |
|---|---|
| **K1a** X1 all-`$00` | RED — `1 B ≠ 1041 B`, sha mismatch |
| **K1b** X5 flipped byte | RED — **`6140 B ≠ 1041 B`**, the row a floor would have passed |
| **K1c** X6 early terminator | RED — `9 B ≠ 1041 B` |
| **K1d** X2 all-`$FF` | RED **with a message** — *"the walk ran off the end of the 32768-byte sub image (started at `0x2cd2`) … the image is corrupt, truncated, or was never assembled"*. No traceback |
| **K1e** table spliced into a scratch `basic-reloc.rom`, **sym untouched** | RED on **1a′** while 1a (sym) still passed — the argument that was dead is now load-bearing |
| **K1f** X0 golden | **PASS** (green control, re-run interleaved) |
| **K2** comparison gutted | X5 and X6 **green again** — clean cut. ⚠️ X1 stayed RED under the knife, on gate **1c** (an all-`$00` image walks to a 1-byte "table" that occurs 32768 times), so the two gates overlap on that row; the isolating subjects are X5/X6 |
| **K3a** short assembly, fixed `pad_rom` | RED at `pad_rom`, naming **30444 ≠ 32768** and the cause |
| **K3b** same tree, `--pad` | pads and **says so**: *"2324 bytes of `$00` INVENTED here, only 30444 came from the assembler"* |
| **K3c** unmodified tree | PASS, *"exact — the assembler wrote the whole image"* (green control) |
| **K4a** X2 → `subrom-inttest` | **RED** on the new precondition (`path = net`) while the delta row **still printed PASS** at 57 — exactly the reading the band alone cannot refuse |
| **K4b** X0 → `subrom-inttest` | PASS, `path = bp`, delta **28** (green control) |
| **K4c** precondition comparison gutted | X2 **green again** — the capture still recorded and printed `net`; only the comparison refuses |

### 6.3 🔴 K3 found the biggest defect in the slice, and it defeats D-P0BASE's fix too

Running K3a a second time exposed something neither residual had named:

```
make build/sub.rom     -> rc 2, pad_rom REFUSES … and leaves a 30444-byte build/sub.rom
make build/sub.rom     -> "build/sub.rom is up to date"          ← the refusal is GONE
make basic-reloc       -> rc 0, EVERY GATE OK, on a 30444-byte image
```

**A refusal that leaves the bad artifact on disk is defeated by running `make`
twice.** GNU make had already stamped the target file, so the second invocation
never re-ran the step that refused. And this is not a defect in the new guard —
the same thing happens to **D-P0BASE's one-day-old empty-input refusal**, measured
directly: first `make` refuses, leaves a **0-byte** `build/sub.rom`, second `make`
calls it up to date. (On that tree the chain now dies at the new bounded walk —
*"`kwtable` resolves to offset `0x2cd2`, outside the 0-byte sub image"* — where
before D-ROMJUDGE it was an `IndexError` and before D-P0BASE it was laundered to
32 KB and passed.)

Fixed with `.DELETE_ON_ERROR:` — one line, and it covers **every** rule in the
Makefile, not just this one. Re-falsified: both knives now delete the artifact and
stay red across repeated invocations.

This is [[a-fix-can-open-a-new-window]] read the other way round. The window was
already open; adding a guard behind an artifact-producing step is what made it
observable. **Ask of any new refusal: what does the SECOND `make` do?**

### 6.4 🔴 And the seventh filed justification, this time one day old

`subrom-inttest` on an entirely-`$FF` sub-ROM read `delta = 57` and **PASSED** —
inside the `1..64` band D-P0BASE had just installed to close this exact class.
Detail in §2.4. Two lessons, both general:

* **A two-sided bound is still one sample of one failure mode.** 255 was measured
  from a *partial* pad; the *total* pad reads 57. Sizing a band from the failure
  you happened to construct does not cover the failures you did not.
* **The precondition was already observable and was being discarded.** "The tenant
  returned" is a boolean the harness had in hand (which capture path fired) and
  threw away in favour of a scalar it then had to reason about. Asserting the
  precondition costs nothing and does not need a threshold at all.

Also corrected: the safety net's comment claimed the delta *"stays 0"* on that
path. It does not — a runaway `rst 38h` walks the stack through the whole address
space and lands a stack byte in the result cell.

### 6.5 What this slice did NOT do

* **`build/disk.rom` still has no content-reading gate at all.** It gains the
  `pad_rom` length guard and nothing else, and **68 of the tree's 74
  `ds <fixed> - $` sites are under `disk/`**. Filed.
* **Pad-only damage stays invisible** (§5.1) — deliberately. Closing it means a
  whole-image digest, which pins the ROM against every legitimate change too.
* **`tools/build_patches.py:125`'s `pad_rom` call is unreachable** —
  `ensure_basic_rom()` is called only by `_build_page1_retired()`, which nothing
  calls, since `build_page1()` `sys.exit`s (lean retirement, 2026-07-29). Left
  alone, filed: it is a `build_patches.py` question, not a gate question.
* **`check_reloc.py`'s three content checks were not touched.** They already
  judge exactly (size `== 22510`, `"AB"` at `$4000`, low region not all-`$00`) —
  measured, not assumed, in §1.
