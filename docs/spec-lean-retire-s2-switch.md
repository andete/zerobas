<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# S2 — RETIRE LEAN: stop building it, stop shipping it, stop measuring it

Step 2 of **RETIRE THE LEAN 16 KB CART** ([`../TODO.md:3156 (T-783F00)`](../TODO.md:3156)).
Follows [`docs/spec-lean-retire-s1-explicit-machine.md`](docs/spec-lean-retire-s1-explicit-machine.md).

Status: ✅ **LANDED 2026-07-29.** §8 answered by the user:
**A1** (ship the repack pair, delete the lean pair) · **B: note the region loss and
revisit later** (TODO entry filed, §2.1) · **C: S3 next session** (§4.5).

Touches **no assembly** and changes **no ROM byte** of the repack build. The 311
`IF ROM_BASE` gates are **not** in this slice (§7).

---

## 1. What still consumes lean, measured at `f486594`

Not "what the brief listed" — the tree, swept.

| # | consumer | where | kind |
|---|---|---|---|
| 1 | `$(ROM)` = `build/basic.rom` is in the default goal `all` | [`Makefile:180`](Makefile:180) | build |
| 2 | `zerobas-msx1.ips` / `.bps` built from `$(ROM)`, tracked at root, in `all` | [`Makefile:176`](Makefile:176), [`:314`](Makefile:314) | **ship** |
| 3 | `machines` → 12 release machines carrying the lean IPS | [`Makefile:335`](Makefile:335), [`tools/install-openmsx-machine.py:72`](tools/install-openmsx-machine.py:72) | **ship** |
| 4 | `install` = `all` + `machines` — the user-facing install path is lean | [`Makefile:345`](Makefile:345) | **ship** |
| 5 | `diskbasic-acceptance` — the 34/34 lean acceptance column | [`Makefile:411`](Makefile:411) | gate |
| 6 | `check_reloc.py` check #4 (frozen `LEAN_SHA256`); `basic-reloc` takes `$(ROM)` | [`tools/check_reloc.py:84`](tools/check_reloc.py:84), [`Makefile:281`](Makefile:281) | gate |
| 7 | `make probe` → `basic_probe_print.py --cart $(ROM)` | [`Makefile:379`](Makefile:379) | gate |
| 8 | ~20 non-gate probes booting the lean cart (`--cart build/basic.rom`) | `probes/basic/`, `probes/tape/` | corpus |
| 9 | 311 `IF ROM_BASE` gates + the `ROM_BASE` equ/org/ceiling machinery | `basic/` | source |
| 10 | README / dev-workflow / probes README describe the lean pair as the deliverable | docs | doc |

### 1.1 The `--cart` corpus is bigger than the brief's item 1

The brief names `make probe`. Measured: **27 files** mention `--cart`; of the probes that
boot zerobas that way, the live method is `C-BIOS_MSX1_EU_TAPE --cart build/basic.rom`
(23 literal hits) — the whole cassette corpus (`basic_probe_cas_*`, `_cload*`,
`_tape_save`, `_bload_openstack`) plus 8 older `C-BIOS_MSX1` cart probes
(`_clear`, `_cont`, `_list`, `_strvar`, `_usr`, `_print`, …).

**Only one of them is a Makefile gate** — `basic_probe_print.py`, via `make probe`
([`Makefile:379`](Makefile:379)). The rest are historical/investigation probes with no
target. `probes/basic/` is otherwise already repack: **61** `C-BIOS_MSX1_EU_REPACK_DISK`
literals against **1** `C-BIOS_MSX1_EU_BASIC`.

⚠️ The lean cart is a **cartridge**; the repack build is a **slot-0 32 KB main ROM**.
There is no "swap the cart" port. But the repack machine already declares
`<CassettePort/>` and the merged ROM already bakes in `tape/tape.asm`
([`Makefile:303`](Makefile:303), [`tools/install-repack-machine.py:112`](tools/install-repack-machine.py:112)),
so the cassette corpus *can* move to the repack machine — it just is not a one-line move.

### 1.2 Two consumers that must be retired TOGETHER

`check_reloc.py` check #4 is what makes the shipped `zerobas-msx1.ips` byte-stable —
S1 §1.3(b) measured that the committed pair is byte-identical to a rebuild *because of*
that freeze, despite being older than `build/basic.rom`.

So: **delete check #4 while still shipping the lean pair, and the shipped artifact
becomes silently drift-prone** — with nothing else testing lean, a drift would go
unnoticed. Check #4's removal and the ship retirement are therefore **one atomic
change**, which is why §8 question A blocks this slice rather than a later one.

---

## 2. The decisive measurement: the repack patch installs on a stock openMSX ROM

This is the fact the shipped-artifact decision turns on, and it was not on record.

The lean pair patches **openMSX's own bundled C-BIOS ROM**. The repack pair is built by
diffing the merged ROM against a `pristine` C-BIOS built from a pinned tag in the user's
own checkout ([`tools/build_patches.py:182`](tools/build_patches.py:182)) — which reads
as "end users need a C-BIOS checkout too." **They do not.** Measured directly:

```
build/cbios_main_msx1_eu-pristine.rom  ==  openMSX's cbios_main_msx1_eu.rom
  sha256 ad114c0d8d1c8eae408fb6876a16ddadd8e336699c53eb04661bda8ebbc4aeab   IDENTICAL
```

and end-to-end, applying the tracked patch to **openMSX's shipped ROM**:

```
rom_patch.py apply <openMSX cbios_main_msx1_eu.rom> zerobas-main-eu.ips out.rom
  out.rom == build/zerobas-main-eu.rom       →  True   (32768 B)
```

So `zerobas-main-eu.ips/.bps` is exactly as installable as `zerobas-msx1.ips/.bps` for a
user with openMSX. **The C-BIOS checkout is a BUILD-TIME requirement for regenerating the
patch, not a RUN-TIME one for applying it.** The `.bps` CRC-lock holds for the same reason.

### 2.1 …but it costs three regions and adds a second file

Measured, and this is the real price:

* **Region coverage 4 → 1.** The lean IPS is a page-1 splice and is region-universal:
  `make machines` writes 12 machines across `cbios_main_msx1{,_br,_eu,_jp}.rom`. The
  repack rewrites the C-BIOS page-0 layout and is **EU-only by construction** —
  [`tools/build_repacked_cbios.py:37`](tools/build_repacked_cbios.py:37) applies
  `cbios-repack/eu-drop-statements.patch` and reads `derived/bin/cbios_main_msx1_eu.rom`.
  Regionalising it is separate work, not part of this slice.
* **The machine needs a second artifact.** The repack build calls page-0 and page-1
  tenants in the sub-ROM (`fp_sqrt`…`fp_rnd`, `format_tenant`, detok/arrays/strheap/
  printusing), which the machine places in slot 3-2 from `build/sub.rom`
  ([`tools/install-repack-machine.py:68`](tools/install-repack-machine.py:68)). Lean needs
  no sub-ROM.

  🔴 **MEASURED, and the tenant-map reading UNDERSTATED it** (F8, §5). I wrote this as
  "a machine without it loses those verbs." Booting one says otherwise: with slot 3-2
  empty the release machine **never reaches a prompt** — the screen fills with garbage.
  BASIC reaches into the sub-ROM during *startup*, so the sub-ROM is a boot requirement,
  not a per-verb dependency.

  Two consequences, both taken: `--sub-rom` **defaults ON** in
  [`install-openmsx-machine.py`](tools/install-openmsx-machine.py) and a missing file is a
  hard error, rather than the opt-in-plus-warning the first cut had — the installer must
  not be able to quietly write an unbootable release machine. And this is another instance
  of the standing lesson: **a claim read off the source is a hypothesis until something
  boots** ([[answer-signoff-questions-by-measuring]], D-ARR-C §7a).

### 2.2 What the user actually gets, either way

| | lean pair (today) | repack pair |
|---|---|---|
| regions | MSX1 / BR / EU / JP | **EU only** |
| files to install | 1 IPS (+ tape IPS) | 1 IPS + `sub.rom` |
| strings / `INPUT` / floats / arrays / error codes / KEY traps | **absent** | present |
| free space in the image | ~68 B of 16384 | the gated wall |
| tested against the CF-3300 oracle | yes (34/34) | yes (34/34) |

The lean cart is not a smaller build of the same BASIC — it is a BASIC **missing seven
source files**. That asymmetry is why I do not recommend keeping it as a "universal
fallback" (§8).

---

## 3. Scope: what S2 does, and what it defers

Two steps remain after this one is scoped:

* **S2 (this slice)** — lean stops being built by default, shipped, and measured.
  Everything in §1 rows 1–8 and 10.
* **S3 (next)** — delete the 311 `IF ROM_BASE` gates and the `ROM_BASE` machinery,
  collapsing `basic/main-reloc.asm` into `basic/main.asm`. Row 9. Purely mechanical,
  and it gets a gate that is both cheap and total: **`build/zerobas-main-eu.rom` must be
  byte-identical across the change.** Deferred because it is a large mechanical edit to
  assembly and it cannot land while anything still builds the lean variant.

---

## 4. What S2 builds

### 4.1 The acceptance column (row 5)

`diskbasic-acceptance-repack` **becomes** `diskbasic-acceptance` — the repack gate is
the gate. `diskbasic-acceptance-repack` stays for one arc as a `.PHONY` alias so existing
docs and muscle memory keep working; `LEAN_MACHINE` is deleted.

⚠️ **`--expect-build lean` and the `lean` branch of the §3.1.4 classifier STAY** in
[`diskbasic_acceptance.py`](probes/disk/diskbasic_acceptance.py). They are what makes
"this gate is accidentally pointed at a lean machine" a loud death. Deleting the
classification because lean retired would delete the guard that proves it retired.

Net: the corpus keeps running 34/34, on the build the charter names. No coverage is lost —
the same 34 probes already pass on repack ([S1 §5](docs/spec-lean-retire-s1-explicit-machine.md)).

### 4.2 The wall stays measurable — this is the load-bearing bit (row 6)

`check_reloc.py` today is `check_reloc.py <reloc.rom> <basic.rom> [<reloc.sym>]`. Checks
1–3 read **only** `<reloc.rom>`; the `__MEAS_LOW_END` / `__MEAS_PAGE1_END` readout reads
**only** `<reloc.sym>`. **Check #4 is the sole reader of `<basic.rom>`.**

So the change is a deletion, not a redesign:

```
python3 tools/check_reloc.py build/basic-reloc.rom build/basic-reloc.sym
```

* delete check #4, `LEAN_SHA256`, and the `ship` positional; `<reloc.sym>` moves to
  argv[2] and becomes **required** (it is always passed today);
* checks **1 (span $2812–$7FFF = 22510 B), 2 ("AB" pinned at $4000), 3 (low region
  occupied)** are untouched, byte for byte;
* the wall readout is untouched — **both `measure:` lines still print**, and
  `make basic-reloc` still ends with the two numbers every slice is costed against;
* the OK line drops its `, lean basic.rom byte-identical` tail;
* `basic-reloc:`'s prerequisite list drops `$(ROM)`.

Making `<reloc.sym>` required (rather than optional as today) is deliberate: an optional
sym is exactly the shape in which a wall readout can silently stop printing.

### 4.3 `make probe` (row 7)

`basic_probe_print.py` gains `--zb-machine` alongside `--cart` (mutually exclusive, one
required), matching the convention already used by 61 sites in `probes/basic/`. `make probe`
passes `--zb-machine $(REPACK_MACHINE)`; `probe:` drops `$(ROM)` and gains `repack-machine`.

⚠️ **This trades away a property, and the spec should say so rather than bury it.** Today
both sides of that differential run the *identical* Philips VG-8020 hardware, differing
only in the inserted cart. On the repack machine the zerobas side is C-BIOS + TMS9929A,
so the comparison is machine-to-machine, not cart-to-cart. That is the same footing the
other 61 probes already stand on, and `make probe` is a **smoke** target — but it is a
real reduction in control, not a free port.

### 4.4 The ship path (rows 1–4, 10) — **A1, signed off**

* `zerobas-main-eu.ips` / `.bps` (already tracked) become **the** deliverable pair.
  `zerobas-msx1.ips` / `.bps` are **deleted from the tree**.
* `all` drops `$(ROM)` and `$(PATCHES)`, keeping exactly what needs **no C-BIOS checkout**:
  `$(DISK_ROM) $(SUB_ROM) $(TAPE_PATCHES)`. A new `release:` target regenerates
  `$(MAIN_PATCHES)` from source and is the maintainer's pre-commit step.

#### Refinement 1 — `sub.rom` is a PREREQUISITE, not a tracked file

§2.1 is right that the shipped machine needs the sub-ROM, but it does **not** follow that
the 32 KB binary should be committed. `build/sub.rom` is built by `pasmo` alone — no
C-BIOS, no external input — so a user who clones and runs `make` already has it. Tracking
it would commit a build artifact that every clone can reproduce. It becomes a
**prerequisite of `machines`** and is referenced by absolute path in the config, exactly
as `build/disk.rom` already is.

#### Refinement 2 — `machines` must NOT force the patch to regenerate

Making `machines` depend on `$(MAIN_PATCHES)` would drag `$(MAIN_ROM)` in, and with it
`CBIOS=<checkout>` — destroying the very property §2 measured, that a user needs no
C-BIOS checkout. So `machines` consumes the **tracked** patch as a file and the installer
**dies loudly if it is absent**, naming `make release`.

This is not a new staleness hole. S1 §1.3(a) measured that the lean gate had no build
dependency on the artifact it tested either, and the freshness that actually matters —
*a gate testing stale BASIC* — is covered by `$(MAIN_ROM)`'s real file rule via
`repack-machine`, which every acceptance gate already depends on
([[ips-rebuild-after-basic-change]]). `machines` is the **release-install** path, not a
gate path. Regenerating the committed pair is `make release`, the maintainer's job.
* `install-openmsx-machine.py` writes EU-only `_BASIC` / `_BASIC_DISK` from the repack IPS
  (one patch, not two — tape is baked into the merged ROM) with `sub.rom` in slot 3-2.
  **`_TAPE` machines survive unchanged**: they carry only the tape patch, never lean, and
  the cassette corpus and `bios_probe_realtape.py` depend on them.
* README §385 / §180, [`docs/dev-workflow.md:116`](docs/dev-workflow.md:116),
  [`probes/README.md:34`](probes/README.md:34) updated.

### 4.5 The `--cart` corpus (row 8) — **kept working, honestly labelled**

`$(ROM)` keeps its file rule. `make build/basic.rom` still assembles, so none of the ~20
historical cart probes break in S2. They break in **S3**, when the source gates go.

⚠️ **State it plainly rather than let it rot silently: after S2 the lean build is
UNGATED.** Nothing asserts it still assembles, nothing asserts what it does. That is
acceptable for a build the charter does not target and S3 deletes — but it is an exposure
with a clock on it, and the mitigation is that S3 follows next, not "eventually".

S3 disposes of the corpus: port the cassette probes to the repack machine (`<CassettePort/>`
is already there, §1.1) or retire the ones the repack corpus has superseded. **Sized in S3,
not hand-waved here.**

---

## 5. Falsification — every new/changed guard made to FIRE

House rule: a guard that never goes red in testing is not a guard. Observed output recorded
here before the slice is called done.

| # | Perturbation | What must fire | Observed |
|---|---|---|---|
| F1 | zero the low region of `build/basic-reloc.rom` | check #3 (low region occupied) | ✅ rc=1, `reclaimed low region $2812-$3FFF is empty ($00)` |
| F2 | truncate `build/basic-reloc.rom` by 1 B | check #1 (span) | ✅ rc=1, `reloc size 22509 != 22510` |
| F3 | overwrite the 2 B at offset `$4000-$2812` | check #2 ("AB" header) | ✅ rc=1, `"AB" header not at $4000 (offset 0x17ee): b'XX'` |
| F4 | omit the sym argument | new required-arg | ✅ rc=1, usage — **not** a silent skip of the readout |
| F4b | sym present but defining **neither** `__MEAS_` label | new readout guard | ✅ rc=1, `the WALL READOUT every slice is costed against would print nothing` |
| F5 | **control:** `rm -rf build && make basic-reloc` | — | ✅ both `measure:` lines print, **low 0 B / page 1 7 B — equal to `f486594`** |
| F6 | release machine + `--expect-build lean` | §3.1.5 | ✅ rc=1, `is a REPACK machine` |
| F6b | **stale lean machine** + `--expect-build repack` | §3.1.5 lean branch | ✅ rc=1, `is a LEAN machine … The LEAN build is RETIRED … Re-run make machines` |
| F6c | stale lean machine with the IPS **deleted** | §3.1.4 missing-refs | ✅ rc=1, names `zerobas-msx1.ips` as the missing artifact |
| F6d | stock `C-BIOS_MSX1_EU` | §3.1.4 | ✅ rc=1, `references NO zerobas artifact`, listing all three marks |
| F6e | machine that does not exist | §3.1.3 | ✅ rc=1, names both dirs searched — no 240 s timeout |
| F7 | **control:** release + dev repack machines, `--expect-build repack` | — | ✅ rc=0, both `build=repack` |
| F8 | run the release machine with slot 3-2 **empty** | §2.1's sub-ROM claim | 🔴 **does not reach a prompt at all** — garbage screen. §2.1's tenant-map reading ("loses those verbs") was WRONG; see §2.1 |
| F8b | **control:** release machine as installed | — | ✅ boots, `print sqr(2)` → `1.4142135623731` (the `fp_sqrt` tenant runs) |
| F9 | installer run where openMSX has no EU C-BIOS machine | new zero-BASIC-machine guard | ✅ dies naming the region and listing what it found |

### 5.1 🔴 What the falsification caught: `make probe`'s port was WRONG

F1–F9 all behaved. The defect came from the row I had reasoned about instead of run.

Ported to `--zb-machine` (§4.3), `basic_probe_print.py` failed **all six** rows — each by
exactly one leading space, content identical (`ref='   1  2  3'` vs `zb='  1  2  3'`).

The tempting reading is "the repack build prints one space fewer." **Measured instead**,
with the pre-S2 path as a control:

| build | machine | `print 1;2;3` | screen left margin |
|---|---|---|---|
| lean cart | Philips VG-8020 | `   1  2  3` | **2** |
| lean cart | C-BIOS_MSX1_EU_TAPE | `  1  2  3` | **1** |
| repack | C-BIOS_MSX1_EU_REPACK_DISK | `  1  2  3` | **1** |

The *identical build* moves by one column when the machine changes. **The machines
disagree about column 0** — a VG-8020 lays SCREEN 0 text out at column 2, a C-BIOS
machine at column 1 — so a raw name-table diff across machines measures the MARGIN and
reports it as a PRINT defect. This is [[width-domain-slice]] exactly: the port MOVED THE
INSTRUMENT.

Fixed by pinning the instrument **per capture**: `output_row`/`output_block` read the
margin off that capture's own echo row and strip exactly that many columns — never more,
so the sign space in ` 1` (which is in scope) survives. A machine with a third margin
cannot shift the result either.

### 5.2 …and a stale readout it exposed underneath

With the margin pinned, the probe's "documented divergence" block — real MSX-BASIC wraps
the third comma zone to a new line, zerobas does not — printed
`divergence present as documented: NO (re-check)`. **The divergence is gone:** on the
repack build zerobas wraps exactly like the reference. It was a property of the lean
build, narrated rather than gated, still describing a build the project had stopped
shipping.

Promoted to a real `check()`. It PASSES on the repack build and correctly goes **red** on
the retired lean cart (falsified both ways) — a converged row should be gated, not
narrated ([[vacuous-gate-row-steers-not-just-misses]]).

F5 is the two-sided half ([[control-that-fails-must-be-fixed]], [[clearpool-slice]]): F1–F4
prove the checks *can* fire, F5 proves the wall readout did not quietly become a
0-denominator ([[gate-can-be-green-while-measuring-nothing]]).

⚠️ **F1–F3 are the important rows.** The failure mode of this slice is not "check #4
removed wrong" — it is "the deletion damaged checks 1–3 or the readout and nobody noticed
because they were green anyway." Falsify by **breaking the thing under test**
([[gate-can-be-green-while-measuring-nothing]]).

---

## 6. Gates to keep green

Run, not assumed. `rm -rf build` first ([[measure-the-wall-from-clean]]). All green:

| gate | result |
|---|---|
| `rm -rf build && make basic-reloc` | ✅ **low 0 B free, page 1 7 B free** — *identical* to `f486594`; `build/basic.rom` is not built at all |
| `make unit-test` | ✅ ALL 54 |
| `make diskbasic-acceptance` *(now the repack gate)* | ✅ **34/34**, `build=repack` |
| `make diskbasic-acceptance-repack` *(alias)* | ✅ resolves, `build=repack` |
| `make bdos-acceptance` | ✅ 12/12 |
| `make fat-error-acceptance` | ✅ 7/7 |
| `make abort-acceptance` | ✅ 31/31 |
| `make error-trap-acceptance` | ✅ ALL PASS |
| `make chancost-characterize` | ✅ 39 cases / 1 filed |
| `make probe` | ✅ smoke OK (disk + basic + tape) — **after §5.1** |

The slice touches no assembly: `git diff --stat -- basic/ sub/ disk/ tape/` is **empty**.
Also verified the shipped pair is not stale — rebuilding `build/zerobas-main-eu.rom` from
clean and applying the tracked `zerobas-main-eu.ips` to openMSX's stock EU ROM reproduces
it byte-for-byte, so no `make release` was needed.

---

## 7. Explicitly NOT in this slice

* The 311 `IF ROM_BASE` gates and the `ROM_BASE` machinery — **S3**.
* Collapsing `basic/main-reloc.asm` into `basic/main.asm` — S3.
* Porting or retiring the ~20 lean-cart probes — S3 (§4.5).
* Regionalising the repack build to BR / JP / region-less (§2.1) — separate work, only
  relevant if the region loss is judged to matter.
* Any claim that this frees ROM space. **It frees none.**

---

## 8. Sign-off questions

### ⛔ Question A (USER-FACING RELEASE DECISION — blocks the slice)

What does zerobas ship?

* **A1 — ship the repack pair, delete the lean pair.** ✅ **Recommended.**
  `zerobas-main-eu.ips/.bps` + `build/sub.rom`. Installs on stock openMSX with no C-BIOS
  checkout (**measured**, §2). Cost: **EU only** (4 regions → 1), and a second file to
  install. Gain: the shipped artifact is the BASIC the charter describes, and it is the
  one the acceptance gates actually measure.
* **A2 — keep shipping the lean pair as a universal fallback.** Cheapest to users with a
  BR/JP C-BIOS. But check #4 must stay, lean must keep being built, and §1.2 means the
  whole retirement stalls here. It also ships, under the project's name, a BASIC with no
  strings, no `INPUT`, no floats, no arrays, no error codes and no KEY traps.
* **A3 — ship repack, and keep the lean pair frozen as an explicitly-legacy artifact.**
  Retires the *maintenance* (no rebuild, no gate) without dropping the universal
  fallback. Honest only if the tree says loudly that it is a 2026-07-29 snapshot of a
  crippled build; otherwise it is A2 wearing a label.

I recommend **A1**: A2 blocks the arc, and A3's artifact is one a user would reasonably
mistake for "zerobas, smaller."

### Question B — is the region loss acceptable, or does it need work first?

A1 drops BR / JP / region-less C-BIOS support. If that matters, regionalising
`build_repacked_cbios.py` should be specced **before** S2 lands, not after. My reading:
these are C-BIOS *region* variants, not hardware the project targets, and the acceptance
oracle (CF-3300) and every gate already run EU-only — so the loss is nominal. **Confirm.**

### Question C — S3 immediately after, or is a gap acceptable?

§4.5 leaves the lean build ungated between S2 and S3. Recommendation: **S3 next session**,
so the ungated window is one item wide.
