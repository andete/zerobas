<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# S3 — RETIRE LEAN: delete the `ROM_BASE` gates, the machinery, and the cart corpus

Step 3 (final) of **RETIRE THE LEAN 16 KB CART** ([`../TODO.md:3476 (T-5EDF8A)`](../TODO.md:3476)).
Follows [`docs/spec-lean-retire-s2-switch.md`](docs/spec-lean-retire-s2-switch.md) (S2,
`4cdb69b`) and [`docs/spec-lean-retire-s1-explicit-machine.md`](docs/spec-lean-retire-s1-explicit-machine.md).

Status: ✅ **LANDED 2026-07-29.** §8 answered by the user, all four as recommended:
**Q1-A** targeted comment sweep · **Q2 append**, provenance history left intact ·
**Q3** retire the 6 named probes · **Q4 nothing** — the §1 hash is the record.
A fifth question arose mid-slice and was answered **port all 8** — see §9, which is the
biggest thing this slice found.

**All four ROMs came out byte-identical** (§6). Wall unchanged: **low 0 B, page 1 7 B.**

**One property governs the whole slice: `build/zerobas-main-eu.rom`, `build/basic-reloc.rom`
AND `build/sub.rom` must come out BYTE-IDENTICAL.** No placement change, no layout change,
no "while I'm in here" — those belong to the ROM REGION STRUCTURE REVIEW, deliberately
sequenced after this ([`TODO.md`](TODO.md)).

---

## 1. Baseline, captured from clean at `b0b3372` BEFORE any edit

`rm -rf build && make all && make basic-reloc && make repack-main` ([[measure-the-wall-from-clean]]):

```
0e802fbd0528a1b81bf7af424c56a60a1aee35e762a0c854fd4a5b398ad411ff  build/basic-reloc.rom
1dbbfe2f87b8ca81769f44e00510270a2219018838b6035ad7c01ed6784b499a  build/sub.rom
2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27  build/disk.rom
5954db13279cf39f2ba0af9995e864a91b9d6a0464025e450831b2eb479725ee  build/zerobas-main-eu.rom
defd6201b78bc922e3ba4db66134d2527c76ad9d81105440a6d667f12511be90  build/basic.rom   (lean — DELETED by this slice)
```

Wall readout, unchanged from `f486594`: **low 0 B free, page 1 7 B free.**

The lean build still assembled at `b0b3372` (16384 B, hash above). It is recorded here
because after this slice it can never be reproduced from the tree again, and the TODO's
DIRECTION is that a future lean build would be **cherry-picked from the finished tree**,
not resurrected from this hash ([[lean-cart-derive-dont-comaintain]]).

---

## 2. 🔴 Two corrections to the brief's scope, both measured

### 2.1 `ROM_BASE` is NOT a main-ROM-only symbol — the SUB-ROM defines its own

The brief scopes the edit to `basic/`. Measured, that is not where the symbol lives:

```
sub/sub.asm:43   SUB_BUILD  equ  1
sub/sub.asm:44   ROM_BASE   equ  $2812        ; <- a SECOND, independent definition
sub/sub.asm:45              include "basic/sysvars.inc"
```

`sub/sub.asm` includes **20 shared `basic/*.inc` files** — `sysvars.inc` (18 gates),
`tokenise.inc` (9), `kwtable.inc` (4), `detok.inc` (2), and the `*-body.inc` family — so a
large fraction of the gates this slice deletes are evaluated **twice**, once per ROM. It
also carries two gates of its own ([`sub/arrays.asm:83`](sub/arrays.asm:83),
[`sub/strheap.asm:87`](sub/strheap.asm:87)).

Both definitions are `$2812`, so the fold is the same on both sides and the edit is still
mechanical. Two consequences that are **not** optional:

* `sub/sub.asm`, `sub/arrays.asm`, `sub/strheap.asm` are **in scope**.
* **`build/sub.rom` joins the byte-identity gate.** The brief names only the main pair; a
  shared-include edit that silently moved a sub-ROM byte would have gone straight past it.
  `build/disk.rom` is added too as a cheap control — it references no `ROM_BASE` and must
  therefore be trivially identical; if it ever moves, the harness is lying.

### 2.2 "311 gates" is a grep count, not a directive count

`grep -rn 'IF ROM_BASE' basic/ | wc -l` → 311, but that counts **prose**. Parsed:

| | directives | comment mentions | docs |
|---|---|---|---|
| `basic/*.asm`, `basic/*.inc` | **282** | 22 | — |
| `basic/PROVENANCE.md` | — | — | 7 |
| `sub/*.asm` | **2** | — | — |
| **total to delete** | **284** | | |

Structure, from a nesting-aware parse of all 351 `IF`/`IFDEF`/`IFNDEF` directives in
`basic/` + `sub/` (script kept in the scratchpad, results reproduced below):

| shape | count | disposition |
|---|---|---|
| `IF ROM_BASE < $4000` … `ENDIF` | 136 | unwrap: delete 2 directive lines, keep body |
| `IF ROM_BASE < $4000` … `ELSE` … `ENDIF` | 131 | keep the IF body, **delete the ELSE body** |
| `IF ROM_BASE >= $4000` … `ENDIF` | 12 | **delete whole block** (lean alternative) |
| `IF ROM_BASE >= $4000` … `ELSE` … `ENDIF` | 5 | delete the IF body, **keep the ELSE body** |
| **total** | **284** | |

Three facts that make the edit safe and that I measured rather than assumed:

1. **Max nesting depth 2.** 11 gates sit inside another gate; every one of those outer
   gates is `< $4000` (`expr.asm` ×6, `interp.asm` ×3, `missing.asm`, `program.asm`).
   **No `<` gate is nested inside a `>=` gate**, so no block's disposition depends on
   another's. A recursive outer-first fold still handles it, and is what I will use.
2. **Gate bodies are NOT indented relative to their surroundings.** Verified across the
   file set: the `IF`/`ELSE`/`ENDIF` lines sit at 4 columns, bodies at the file's ordinary
   16-column instruction indent. **So the edit is pure line deletion — no reindentation,
   and therefore no whitespace churn in the diff.**
3. The only other `ROM_BASE` consumers are `org ROM_BASE` and the `IF $ < ROM_BASE`
   wrap-guard, both in [`basic/main.asm`](basic/main.asm) (§3.2).

The 17 `>= $4000` blocks are enumerated in §3.1 — they are the only places where **code is
deleted rather than unwrapped**, so they get read individually rather than folded blind.

---

## 3. What S3 changes

### 3.1 The 284 gates

Folded by a script under `ROM_BASE = $2812`, then **reviewed as a diff**. The script is a
convenience, not the authority — the authority is byte-identity (§5) plus a read of the
17 deletion sites, which are:

| site | span | shape |
|---|---|---|
| [`basic/fat.asm:63`](basic/fat.asm:63) | 63–265 | ELSE @72 — the big one: 9 lines of lean FAT primitives deleted, 193 kept |
| [`basic/tokenise.inc:456`](basic/tokenise.inc:456) | 294–366 | no ELSE — **72 lines deleted outright** (the lean inline tokeniser) |
| [`basic/files.asm:1330`](basic/files.asm:1330), [`:1353`](basic/files.asm:1452) | 30 each | ELSE — lean file-verb bodies deleted |
| [`basic/expr.asm:434`](basic/expr.asm:434) | 25 | no ELSE — lean `cmp16_bits` (repack has it in `float-arith.asm`) |
| [`basic/print.asm:403`](basic/print.asm:403) | 14 | no ELSE |
| [`basic/fat.asm:333`](basic/fat.asm:333), [`:360`](basic/fat.asm:360) | 14, 11 | ELSE |
| [`basic/program.asm:318`](basic/program.asm:318) | 5 | no ELSE |
| [`basic/interp.asm:108`](basic/interp.asm:108), [`:601`](basic/interp.asm:727), [`:622`](basic/interp.asm:750), [`:649`](basic/interp.asm:649) | 2–4 | no ELSE |
| [`basic/files.asm:364`](basic/files.asm:364), [`:1069`](basic/files.asm:973), [`:1086`](basic/files.asm:990) | 2–4 | no ELSE |
| [`basic/save.asm:575`](basic/save.asm:575) | 2 | no ELSE |

### 3.2 The machinery, and the surviving entry point

**Decision: `basic/main.asm` survives; `basic/main-reloc.asm` is deleted.** It is the file
every include path, every `SRC`, and every doc already names; the wrapper exists only to
set a symbol that is about to stop existing. Concretely:

* [`basic/main.asm:35-37`](basic/main.asm:35) — the `IFNDEF ROM_BASE` / `equ $4000` /
  `ENDIF` block is replaced by an unconditional constant.
* **The constant is renamed `BASIC_ORG`, not kept as `ROM_BASE`.** `ROM_BASE` reads as a
  knob with two settings, which is exactly the thing being retired; after this slice it has
  one value and no override path. `org ROM_BASE` → `org BASIC_ORG`, and the
  `IF $ < ROM_BASE` 64 K-wrap guard ([`basic/main.asm:381`](basic/main.asm:381)) →
  `IF $ < BASIC_ORG`. The `$8000` ceiling guard's diagnostic symbol
  `BASIC_IMAGE_OVERRAN_8000_CEILING__GATE_FEATURE_ON_ROM_BASE_OR_TRIM` loses its now-
  meaningless advice → `…__TRIM_IT_OR_EVICT_TO_SUBROM`.
* [`basic/main-reloc.asm`](basic/main-reloc.asm) is **deleted**. `sub/sub.asm`'s
  `ROM_BASE equ $2812` is deleted (nothing reads it once the shared includes are folded;
  `SUB_BUILD` stays — it gates a genuinely two-sided `*-body.inc`).
* Makefile: `$(RELOC_SYM)`, `$(RELOC_ROM)` and `$(MAIN_ROM)` retarget from
  `basic/main-reloc.asm` to `$(SRC)` = `basic/main.asm`. **`$(ROM)` and its file rule are
  deleted**, as is the now-unused `ROM :=` variable; `build/basic.rom` becomes
  unbuildable, which is the point.

⚠️ **`org BASIC_ORG` now sits at `$2812` unconditionally, so `basic/main.asm` alone
assembles the relocated image.** That is the whole reason byte-identity is a total gate
here: the org, the include set, and the fold all have to be right simultaneously or the
32 KB output moves.

### 3.3 The `--cart` probe corpus

Measured, not taken from the brief's "~20". `--cart` appears in **31 probe files**; they
split three ways, and the split is not the one the brief implies:

**(a) 5 files use `--cart` for their OWN generated Z80 probe cart, never `basic.rom`** —
[`probes/tape/bios_probe_casin.py`](probes/tape/bios_probe_casin.py),
[`_tapraw`](probes/tape/bios_probe_tapraw.py), [`_tapread`](probes/tape/bios_probe_tapread.py),
[`_tapfile`](probes/tape/bios_probe_tapfile.py), [`_realtape`](probes/tape/bios_probe_realtape.py).
**Out of scope, untouched.** (`_realtape` inserts a `build_read_cart()` blob, not BASIC.)

**(b) 3 files already have a machine path** —
[`_print`](probes/basic/basic_probe_print.py) (ported in S2),
[`_crunch`](probes/basic/basic_probe_crunch.py) (`--zb-machine`, mutually exclusive group),
[`_bload`](probes/basic/basic_probe_bload.py) (`--cart` optional, works on any machine).
Disposition: **drop the dead `--cart` arm** from `_print` and `_crunch` (`_crunch`'s
mutually-exclusive group collapses to a required `--zb-machine`); `_bload`'s stays — it is
a generic "insert a cartridge" option, not a lean reference.

**(c) 9 cassette probes + 11 older cart probes.** 🔴 **The shared harness is ALREADY
machine-aware, which the brief did not know and which shrinks this item a lot:**
[`run_typed`](probes/basic/basic_probe_cas_verbs.py:71) and
[`run_save`](probes/basic/basic_probe_tape_save.py) both do
`if zb_machine == MACHINE_TAPE: cmd += ["-cart", cart]`, and
`_tape_save` / `_cas_leader_budget` / `_cas_match` already read
`ZEROBAS_BASIC_MACHINE`. The port is therefore mostly **flipping a default and deleting a
branch**, not writing a rig.

| probe | disposition | why |
|---|---|---|
| `_cas_verbs`, `_cas_match`, `_cas_ascii`, `_cas_options`, `_cas_verify`, `_cas_leader_budget`, `_tape_save`, `_cload_ondevice` | **PORT** to `C-BIOS_MSX1_EU_REPACK_DISK` | the cassette surface is charter BASIC; the machine has `<CassettePort/>` and the merged ROM bakes in `tape/tape.asm`; harness already supports it |
| `_bload_openstack` | **PORT**, keeping `--cart` for the *write* cart | it inserts TWO carts: a generated writer (stays) and `basic.rom` (becomes the machine). Its `_TAPE` machine is the point of the test — stock BIOS, open cassette stack |
| `_clear`, `_cont`, `_list`, `_strvar`, `_usr`, `_statements` | **PORT** — mechanical | each is a `--cart`-required VG-8020/C-BIOS_MSX1 probe of a verb the repack corpus does not otherwise cover at this depth |
| `_data`, `_loops`, `_controlflow`, `_vdpio`, `_screen`, `_cload` | **RETIRE** — see §3.3.1 | superseded; each names a specific successor |

⚠️ **The margin hazard applies to exactly 4 of these**, and I measured which rather than
guarding all of them: only `_list`, `_strvar`, `_vdpio` and `_cas_verify` read the SCREEN 0
name table. The rest capture RAM/registers/witness bytes and are **margin-immune** — moving
them between machines cannot shift the reading the way S2 §5.1's did. The four that do read
VRAM get `_print`'s per-capture `_margin`/`_strip_margin` treatment, and I will **falsify it
by asserting the two machines' margins differ** (§5, F-M), not by assuming they do.

#### 3.3.1 The six retirements, each with its successor named

Retiring a probe deletes coverage-of-record, so each needs a reason that is not "it was
awkward to port". Proposed, for review in §8-Q3:

🔴 **One of my five claims was WRONG, and F-R caught it before anything was deleted:
`basic_probe_readdata.py` DOES NOT EXIST.** Named from memory, not from the tree — exactly
the failure [[answer-signoff-questions-by-measuring]] describes. The successor I then
verified by running it is `tests/test_control_flow.py`, which covers `READ`/`DATA`/
`RESTORE` (3 rows), `FOR`/`NEXT`, `GOSUB`/`RETURN` and `ON…GOTO` — and, since §4a, does so
**against the shipped image**, which it never did before. Final table, every successor RUN:

| retire | successor, verified by running it |
|---|---|
| `_data` | `tests/test_control_flow.py` — `READ A`/`READ B`/`READ C after RESTORE` all PASS |
| `_loops`, `_controlflow` | same file — `FOR` sum 15, `FOR STEP` 30, nested 12, `GOSUB/RETURN` 11, `IF/THEN/GOTO` — plus `basic_probe_direct_ctrl.py` and the abort (31/31) / error-trap gates |
| `_vdpio` | `tests/test_vdpio.py` — 4 `VPOKE` + 4 `OUT` rows, ALL PASS; plus the gated `basic_probe_graphics*.py` |
| `_screen` | `basic_probe_width.py` (gated, 76/76) |
| `_cload` | `_cas_verbs` + `_cas_match` + `_cas_verify`, all ported above |

Note what the correction changed: the successors for the three biggest retirements are
**unit tests that this slice had to fix first** (§4a.2). Retiring them against a successor
that was itself testing the lean build would have been a coverage loss dressed as a
consolidation.

### 3.4 Tools

* [`tools/install-openmsx-machine.py:35-37`](tools/install-openmsx-machine.py:35) — the
  `_TAPE` docstring still tells the reader to insert `build/basic.rom`. Rewritten to name
  the ported corpus and the repack machine. The `_TAPE` machines themselves **stay** — they
  carry only the tape patch and `bios_probe_realtape.py` + the tape regression need them.
* [`tools/clone_scout.py:91`](tools/clone_scout.py:91) — classifies each clone group
  `repack`/`lean`/`other` by matching `ROM_BASE < $4000` / `>= $4000`. After S3 every group
  is unconditionally resident, so the classifier is dead and would silently label
  everything `other`. The gate column and its docstring paragraph are removed;
  [[carve-scout-before-proposing]]'s "a candidate's risk is which GATE it sits under" now
  reads off `SUB_BUILD` and region alone.
* [`tools/check_reloc.py:7`](tools/check_reloc.py:7) and
  [`tools/build_mainrom.py:47`](tools/build_mainrom.py:47) — docstring/comment references
  to `basic/main-reloc.asm, ROM_BASE=$2812`. One line each.
* [`tools/overlay_page1.py`](tools/overlay_page1.py) — its docstring describes the retired
  page-1 lean splice as its purpose. It is **still live** (`build_mainrom.py` imports
  `refs_into`/`spans`), so it stays; the docstring gains one sentence saying the splice path
  is retired and the module survives for its reference-safety scan.

### 3.5 Docs

* [`README.md:328-357`](README.md:328) — the probe block with S2's warning banner and six
  `--cart build/basic.rom` invocations, rewritten to the ported commands.
  [`:213`](README.md:213) (the "region-universal page-1 splice carrying a lean build" note)
  and [`:401`](README.md:401) (`main.asm # cartridge header…`) corrected.
  ⚠️ **FLAGGED, NOT FIXED (pre-existing, per the brief):** README's "Limitations (this
  slice)" section is stale doc debt predating the lean arc. Left alone; filed in TODO.
* [`probes/README.md`](probes/README.md) — the `lib/` row and the run examples.
* [`basic/PROVENANCE.md`](basic/PROVENANCE.md) — **7 `IF ROM_BASE` mentions across dated
  historical entries.** See §8-Q2: my recommendation is **do not rewrite provenance
  history**; add one dated entry recording that the gates were folded at `ROM_BASE=$2812`
  and that earlier entries' lean/repack framing is historical.
* [`TODO.md`](TODO.md) lean-cart entry closed out; `docs/dev-workflow.md` swept.

---

## 4. What S3 does NOT do

* **No placement, layout, region or eviction change.** Byte-identity forbids it, and the
  ROM REGION STRUCTURE REVIEW is sequenced after this precisely so it reads a tree with no
  gates obscuring which region things are in.
* No claim that this frees ROM space. **It frees none** — the gates emitted nothing.
* No regionalisation of the repack build (still EU-only, S2 §2.1).
* No fix for the two open run-loop-exit defects, the `lof_new` −1 bug, or the lean `TOKBUF`
  crunch overrun (explicitly carry-forward: the lean build it afflicted no longer exists).

---

## 4a. 🔴 What the slice FOUND: `make unit-test` was measuring the retired build

This was not in the plan and it is the most consequential thing here.

[`tests/msxtest.py`](tests/msxtest.py)'s `Machine.__init__` defaulted
`rom_base=0x4000` — **the lean cart's org.** Every test that built `basic/main.asm`
without naming a base therefore assembled and asserted against the LEAN build:
**18 of the 54 files.** The 17 files that passed `RELOC_BASE=$2812` explicitly were the
ones testing the shipped image. S2 had declared lean "no longer measured"; a third of the
unit suite was measuring nothing else.

**The fix is S1's own fix, applied one layer down: `rom_base` is now MANDATORY** and named
at all 74 call sites ([[lean-retire-s1-explicit-machine]] — *assert on the config, not on
source text*). A default is how this happened, so there is no default. Three legitimate
values, and they are genuinely different address spaces, not build variants: `$2812` the
BASIC image, `$4000` the disk ROM, `$0000` the sub ROM.

### 4a.1 Making it mandatory found two consumers OUTSIDE `tests/`

* 🔴 [`probes/disk/bas_tokenise.py`](probes/disk/bas_tokenise.py) builds `basic/main.asm`
  to get a real tokeniser for the **disk acceptance corpus's `.BAS` fixtures** — on the
  default base, i.e. **the disk corpus's fixtures were crunched by the LEAN tokeniser.**
  Now `$2812`; `diskbasic-acceptance` still converges **34/34**, so the corpus now passes
  with the shipped tokeniser, which is a strictly stronger reading than before.
* [`probes/disk/wrblk_perf.py`](probes/disk/wrblk_perf.py) loads `disk.rom` — `$4000`,
  correct by accident, now stated.

Neither was reachable from `grep` over `tests/`. **Making the argument required is what
found them**; a sweep of the directory I expected them in would not have.

### 4a.2 Eight tests could not just be re-pointed — and one of them exposed dead ROM code

44/54 went green on the base fix alone. The other 8 asserted against structures the
shipped build does not have. All eight were ported (§9); the diagnosis per test:

| test | what was actually wrong |
|---|---|
| `test_vars` | drove `var_set_key`/`var_get_key` — see below — and `STRTAB` |
| `test_strvar` | the 8-slot `STRTAB` pool; shipped strings are `[len][ptr]` into a heap |
| `test_control_flow`, `test_statements` | read results via `var_get_key`, so every variable read back **0** |
| `test_field`, `test_printusing` | seeded `[len][bytes]` descriptors; the engine derefs `[len][ptr]` |
| `test_open_len` | drove `frnd_calc`, which the shipped build **evicts to the sub-ROM** |
| `test_expr` | asserted `ERRMARK=$DD` for `5/0`; the shipped build sets **`FPERR=2`** |

🔴 **`test_control_flow` led to dead code in the shipped ROM.**
[`vars.asm`](basic/vars.asm)'s `var_get_key` / `var_set_key` have **zero callers** in
`basic/` or `sub/`, and `var_find` is called only by those two — pasmo's own
`Var … is never used` warnings say the same thing, at `b0b3372` as well. The comment at
[`vars.asm:268`](basic/vars.asm:268) named it all along: *"the LEAN build's int-only
4-byte-stride walk"*. Shipped scalars live in the contiguous chain the ARY sub-ROM tenant
manages. `VARTAB`/`VARENTSZ`/`VARSLOTS` are likewise read by nothing.

**Not taken here** — it is a carve and S3 is byte-identical by contract. Filed under the
ROM REGION STRUCTURE REVIEW, with the sysvars/vars comments updated to say so.

🔴 **And `test_expr` showed why a pending error is not inert.** `5/0` leaves `FPERR=2`;
the real interpreter zeroes it at every statement start
([`interp.asm:196`](basic/interp.asm:196)). Leaving it set made the NEXT group's `VPEEK`
run off into FAT code and die on an invalid opcode at `$63CD`. The crash was three groups
downstream of its cause — **a stale flag, not a broken routine.**

---

## 5. Falsification — every gate made to FIRE

House rule: a guard that never goes red is not a guard. Observed results:

| # | Perturbation | Observed |
|---|---|---|
| **F0** | **control:** comment-only edit to `expr.asm` | ✅ hash **UNCHANGED** — the harness is not red-for-everything |
| **F1** | **control:** full clean rebuild after the fold | ✅ all four hashes **equal §1**; wall **low 0 B / page 1 7 B** |
| **F2** | re-fold `basic/fat.asm` at `ROM_BASE=$4000` (keep the LEAN branches) | ✅ RED — `ERROR: Symbol 'fch_flush_active' is undefined`, a label the wrong-way fold dropped |
| **F3** | delete one KEPT instruction (`ld h,b` in `vdpio.asm`) | ✅ RED — **hash MOVED** to `21dbd058…`. Byte-level detection, not merely build/no-build |
| **F4** | re-fold `sub/strheap.asm` at `$4000` | ✅ RED via **`build/sub.rom`** — `ERROR: Symbol 'strheap_engine' is undefined`. §2.1's finding is instrumented |
| **F5** | `make build/basic.rom` | ✅ `No rule to make target 'build/basic.rom'` |
| **F6** | `grep -rnE '^\s*IF\s+ROM_BASE' basic/ sub/` | ✅ **0** (denominator 284 → 0); 0 non-comment `ROM_BASE` tokens left |
| **F7** | `basic/main-reloc.asm` | ✅ absent |
| **F-U** | omit `rom_base` at a `Machine(...)` call site | ✅ `TypeError: missing 1 required positional argument` — §4a's guard cannot be skipped, and it caught two consumers outside `tests/` (§4a.1) |
| **F-R** | run each retirement's named successor | ✅ see §3.3.1 — one claim was **WRONG** and was corrected |

### 5.1 🔴 The falsification harness itself was wrong twice, and both were silent

Recorded because it is the point, not an aside.

**(a) `git checkout --` restored to the wrong state.** The fold is uncommitted, so
reverting a perturbed file returned it to **pre-fold `HEAD`** — re-gated — not to the
folded working tree. Two of the three rows then built against a tree with `ROM_BASE`
undefined and reported RED for a reason unrelated to their own perturbation. Save/restore
is now a file copy, and **every row reports its reason** so a red is attributable.

**(b) `make build/basic-reloc.rom` is a NO-OP FOLLOWER.** It is the grouped-target
workaround (GNU make 3.81 has no `&:`): the recipe lives on the `.sym` target and the
`.rom` rule is `@:`. Removing only the `.rom` left the `.sym` up to date, so `@:` ran, the
file was never recreated — and the harness read *"file missing"* as *"build failed"*, i.e.
**RED for a row that never ran at all.**

Both are the standing lesson inverted: not a green gate measuring nothing, but a **RED**
gate measuring nothing — which is worse, because red reads as success for a falsification
row. F0 exists to catch exactly this: a control that must stay GREEN. Without it, "all
rows red" was indistinguishable from "the harness is broken".

### 5.2 F-M: the margin hazard was MEASURED, not assumed

S2 §5.1's hazard is that moving a probe between machines measures the machine's SCREEN
MARGIN. Measured directly, by typing one `PRINT` and reading the first non-blank name-table
row:

| machine | SCREEN 0 left margin |
|---|---|
| `Philips_VG_8020` | **2** |
| `C-BIOS_MSX1_EU_REPACK_DISK` | **1** |

So the hazard is real and reproduced. **But it applies only to a VG-8020 ↔ C-BIOS move**,
and of the ported probes that read VRAM (`_list`, `_strvar`, `_cas_verify`) **none crosses
that boundary** — all three were already on a C-BIOS machine (`C-BIOS_MSX1` /
`C-BIOS_MSX1_EU_TAPE`). `_list` and `_strvar` pass unmodified, confirmed by running them.
The probes that WERE on the VG-8020 and read VRAM (`_screen`, `_vdpio`) are retired.

**No `_margin` fix was needed, and that conclusion came from measuring both margins rather
than from reasoning about the port** ([[width-domain-slice]]).

⚠️ **F2/F3/F4 are the important rows.** The failure mode of a 284-site mechanical edit is
not "one gate folded wrong" — it is "the byte-identity harness was never capable of
noticing." Falsify by **breaking the thing under test**.

---

## 6. Gates — RUN, not assumed

`rm -rf build` first ([[measure-the-wall-from-clean]]). All green:

| gate | result |
|---|---|
| `rm -rf build && make basic-reloc` | ✅ **low 0 B free, page 1 7 B free** — identical to `b0b3372` |
| **byte identity, all four ROMs** | ✅ `basic-reloc.rom`, `sub.rom`, `disk.rom`, `zerobas-main-eu.rom` **all equal §1** |
| `make unit-test` | ✅ **ALL 54** (was 18 red on the base fix, then 8; all ported — §4a.2/§9) |
| `make diskbasic-acceptance` | ✅ **34/34**, `build=repack` — and now with fixtures tokenised by the SHIPPED tokeniser (§4a.1) |
| `make bdos-acceptance` | ✅ 12/12 |
| `make fat-error-acceptance` | ✅ 7/7 |
| `make abort-acceptance` | ✅ 31/31 |
| `make error-trap-acceptance` | ✅ ALL PASS |
| `make chancost-characterize` | ✅ 39 cases / 1 filed |
| `make probe` | ✅ smoke OK (disk + basic + tape) |
| `make machines` | ✅ writes the release machines + the `zerobas-disk` extension |
| ported probes run | ✅ `basic_probe_list.py` ALL PASS, `basic_probe_strvar.py` ALL PASS |

⚠️ **`pasmo` emits ~230 `Var … is never used` warnings. They are PRE-EXISTING** — verified
by assembling `b0b3372` and diffing the list. `raise_error_forced`, `var_get_key` and
`var_set_key` are all in it at `b0b3372` too; the last two are §4a.2's dead-code finding,
which pasmo had been reporting all along.

### 6.1 Not run, and why

The ported cassette corpus (`_cas_verbs`, `_cas_match`, `_cas_ascii`, `_cas_options`,
`_cas_verify`, `_cas_leader_budget`, `_tape_save`, `_cload_ondevice`, `_bload_openstack`)
and `_clear`/`_cont`/`_usr`/`_statements` were ported and syntax-checked but **not
end-to-end run** — each boots openMSX per case with multi-second cassette settling, and
none is a Makefile gate. `_list` and `_strvar` were run as representatives of the group
that shares the same port shape. **Stated rather than implied**: if one of the cassette
probes has a residual timing or margin problem, this slice did not find it.

---

## 7. Order of work

1. Fold `basic/` + `sub/` gates (script) → `make basic-reloc`, `sub`, `repack-main` →
   **hash check**. Read the 17 deletion sites as a diff.
2. Machinery: `BASIC_ORG`, delete `main-reloc.asm`, retarget Makefile, delete `$(ROM)` →
   **hash check again**.
3. F2–F7 falsification.
4. Probes: port, then retire (retirements last, after their successors are confirmed).
5. Tools + docs sweep.
6. Full gate run from clean.
7. Comment prose (§8-Q1's answer decides the size of this step).

Steps 1–2 are the byte-risk; 4–7 cannot move a byte at all.

---

## 8. Sign-off questions

### ⛔ Question 1 — how much of the COMMENT PROSE gets rewritten? (blocks step 7)

**388 lines in 66 `basic/`+`sub/` files mention the lean build**, far beyond the 284 gates:
`sysvars.inc` 55, `expr.asm` 27, `program.asm` 24, `files.asm` 22, `interp.asm` 19… Most
are load-bearing placement rationale of the form *"lean 16 KB cart (`ROM_BASE >= $4000`):
inline here; repack build (`ROM_BASE < $4000`): evicted to sub-ROM page 0"* — a
**two-column present-tense description of a build that will not exist.** Comments emit no
bytes, so byte-identity protects none of this; it is pure judgement.

* **Q1-A — targeted (recommended).** Rewrite only comments that assert a *live* two-build
  fact ("lean stays byte-identical", "gated `IF ROM_BASE < $4000`", the two-column
  placement headers). Keep historical *rationale* that is still true ("sited in the low
  region because page 1 was full"), stripped of its lean framing where lean is the subject.
  Estimated ~120–150 lines across ~40 files. Leaves no false present-tense claim, keeps the
  archaeology that explains why code sits where it does.
* **Q1-B — full sweep.** Touch all 388. Most thorough, and roughly triples step 7; risks
  deleting placement archaeology that the ROM REGION STRUCTURE REVIEW is about to need.
* **Q1-C — none this slice.** Fastest, and leaves 388 lines describing a deleted build as
  current. Given [[dual-mission-docs-as-deliverable]] I do not recommend this.

I recommend **Q1-A**, with the rule stated explicitly in the commit so the next reader knows
which comments were deliberately left historical.

✅ **Answered Q1-A. And the 388 was WRONG — the real figure is 207.**
`grep -i lean` matches **"clean"**, and this tree says *clean-room* constantly. Counted with
`grep -iE '\blean\b'`: **207** lines, not 388. The estimate that fed the question was
inflated by ~45%. A count is a measurement, and this one was not taken carefully; it did
not change the answer, but it would have if the choice had been close.

Swept to **~13 remaining mentions**, all deliberate: dated historical notes ("the retired
lean 16 KB cart …"), plus two ordinary-English uses in `sub/graphics.asm` ("keep the
page-0 tenant lean"). The mechanical first pass produced *worse* prose than the source it
replaced (`"Wholly repack-only (repack-only in the old two-build tree)"`), so it was
reverted and the sweep done by hand, file by file. All non-comment `ROM_BASE` tokens are
gone from `basic/` and `sub/`.

### Question 2 — `basic/PROVENANCE.md`: rewrite, or append?

7 `IF ROM_BASE` mentions sit inside **dated clean-room provenance entries**. My reading:
provenance is a *record of what was done when*, and rewriting it to match today's tree
damages the thing that makes it a provenance document. **Recommendation: append one dated
entry, leave the history.** Confirm — it is the opposite of how the other docs are treated.

### Question 3 — confirm the 6 probe retirements (§3.3.1)

`_data`, `_loops`, `_controlflow`, `_vdpio`, `_screen`, `_cload` retired against named
successors; the other 14 ported. Each retirement is contingent on F-R confirming its
successor actually covers the rows. Say if any of these six should be ported instead —
retiring is the only irreversible thing in this slice.

### Question 4 — anything to preserve about the lean build before it becomes unbuildable?

After S3 the tree cannot produce `build/basic.rom` again. §1 records its hash; the TODO's
DIRECTION says a future lean build gets **cherry-picked from the finished tree**, not
resurrected. **Recommendation: no tag, no frozen artifact, no archive branch** — the hash
in this spec is the record. Confirm, since it is the last moment where the alternative is
cheap.

✅ **Q2 = append.** One dated entry added to the tail of
[`basic/PROVENANCE.md`](basic/PROVENANCE.md), and it says explicitly that earlier entries'
lean/repack framing is historical and deliberately not rewritten. The 7 in-history mentions
stand. Source *comments* were swept (Q1-A) because a comment describes the code beside it;
a provenance entry describes a date.

✅ **Q3 = retire the 6 — but one successor claim was wrong.** See §3.3.1: F-R found
`basic_probe_readdata.py` does not exist. The retirements went ahead against verified
successors instead, three of which are unit tests this slice had to fix first.

✅ **Q4 = nothing.** No tag, no frozen artifact. §1's hash
(`defd6201b78bc922e3ba4db66134d2527c76ad9d81105440a6d667f12511be90`, 16384 B) is the record,
and `basic/PROVENANCE.md`'s new entry points at this spec.

---

## 9. Question 5, raised mid-slice — the 8 lean-testing unit tests

Not foreseen in §8. Arose from §4a: after `rom_base` became mandatory, 8 of 54 unit test
files were red because they asserted against lean-only structures, and `make unit-test` is
a listed gate that must be green. Options put to the user were *port all 8* / *port 6 and
delete the 2 whose subject is gone* / *split the tests into their own item*.

✅ **Answered: port all 8.** Done — `make unit-test` is **54/54**. What each port had to
change, because "re-point at the other base" was not sufficient for any of them:

| test | port |
|---|---|
| `test_control_flow`, `test_statements` | read through `var_get` (deftbl-resolved, ARY-tenant-backed) instead of the dead `var_get_key` |
| `test_field`, `test_printusing` | seed `[len][ptr]` descriptors with the body in its own buffer |
| `test_open_len` | **split across two ROMs** — `frnd_calc` from the SUB image, `oo_parse_reclen` from the main one |
| `test_expr` | assert `FPERR=2` for `5/0` (not `ERRMARK=$DD`), and clear it at the statement boundary as `interp.asm` does |
| `test_strvar` | `[len][ptr]` throughout; a literal's descriptor points **into the token stream** (no copy), so the old `== STRSCR` assert would have gated a copy the engine does not make; `STRMAX` is 255, so the old *clamp* case became a *round-trips-intact-at-the-boundary* case, and needs `CLEAR 512` to fit |
| `test_vars` | keyed stores through `var_store_fac`/`var_load_fac`; `clear_vars` **+ `vars_reset`**, because `clear_vars` alone deliberately does not wipe the chain ([`vars.asm` §13a](basic/vars.asm)) — and the interop case must use the letter's DEFAULT type (8/double) or the two paths address different entries |
| `test_stmt_dispatch` | collapsed its **two-build loop** to one; `EXPECTED`'s 74 rows lost their per-entry guard field. Left alone it would have assembled the same image twice and loaded one copy at the wrong base |

Two of these ports are two-sided rather than one-sided, deliberately: `test_vars`' clear
case asserts the variable **was** set before asserting it is gone, and `test_strvar`'s
literal case pins both the descriptor address and the body address
([[clearpool-slice]] — a control must be two-sided).
