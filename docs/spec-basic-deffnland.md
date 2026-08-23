# SPEC — D-DEFFNLAND: DEF FN ships, and the last 28 bytes

Status: **LANDED.** 2026-08-23, branch `deffn-draft` on top of D-XREG
(`e5c27f2`). `make basic-reloc` builds the SHIPPING feature set
(`G6/G7/G8_RESIDENT = 1`) for the first time since the verb was written, and
`make kwsweep` no longer prints a `MISSING=` line at all.

> **🔴 THE ONE THING THAT MUST HAPPEN FIRST: `sub/deffn.asm` IS A SIZING STUB.**
> It answers ERR 18 to everything, by construction and in its own header. **The
> verb does not work on `deffn-draft`.**
> — the state this slice inherited, [`spec-basic-deffnev.md`](spec-basic-deffnev.md) §5

---

## 1. The numbers

Every row read with `scratchpad/deffn_measure_over.py` (the shipping feature
set, with only the `$8000` ceiling assert neutralised), except the last, which
is `make basic-reloc` itself.

| step | page 1 vs `$8000` | low free | gap |
|---|---|---|---|
| inherited (`e5c27f2`, the stub) | +128 | 102 | **26** |
| the REAL tenant + the `DE` guard (§3.2) | +130 | 102 | **28** |
| the phase byte moved into `L` (§4.1) | +123 | 102 | **21** |
| `sav_flag_a` + `arga_pack_*` collapsed (§4.2, §4.3) | +110 | **129** | **−19** |
| **`poke.asm` + `sound.asm` PROMOTED into the low region (§5)** | **−2** | **17** | — |

> ### the verb SHIPS, with 2 B of page 1 and 17 B of low region to spare.
> ROMs `031184d9` / `34bb8554`.

**47 B of main ROM were carved against a 28 B gap.** The 19 B of slack is
exactly the 2 + 17 that shipped.

🎯 **THE FIRST KNOWN UNKNOWN IS ANSWERED AND THE ANSWER IS "NOTHING".** *"Does
the real tenant change the main-side cost at all? (An extra request kind is
~3 B of dispatcher.)"* — no new request kind was needed; the four-request
protocol as designed was sufficient, and the only main-side byte the real
tenant forced is the 2 B of §3.2, which is a **defect fix**, not a dispatcher
arm. The 428 B of real parse cost sub page 0 (3016 → 2563 B free) and the main
ROM zero.

---

## 2. The tenant

`sub/deffn.asm`, 428 B of sub page 0. It owes exactly what the eviction slice
said it owed and now pays it: the name resolve and its ERR 18, the two lists
walked together, the delimiter agreement that IS the arity rule, the shadow
slot with its `FN_SLOTP`/`FN_FEND` growth and the ERR 5 ceiling that is a
division, both directions of ERR 13, and the `$FFFF`-keyed result slot.

**Sub-side clones**, because a page-0 tenant has no import path to main page 1
([`spec-basic-deffnev.md`](spec-basic-deffnev.md) §3.1): `dfn_name_key`
(`var_name_key`), `dfn_ident_cont` (`is_ident_cont`) and `dfn_deftbl`
(`deftbl_lookup`). Everything else was already co-resident in sub page 0 —
`skip_spaces` (readdata.asm), `is_letter`/`upcase` (sub.asm / tkfloat.asm), and
the one that mattered, `scv_find` (arrays.asm), one page-local `call` away.

⚠️ **THE TYPE COMES BACK IN `A`, NOT IN `(VARTYPE)`**, and that is not a style
choice: between the resolve and its use the servicer runs `eval`, which re-runs
the *resident* `var_name_key` for every variable factor in the actual and
overwrites the global.

### 2.1 The phase machine, and the two cells it did not get

`FN_AREA` is 99 and `FN_MAXP` is exactly **9 with zero bytes to spare**, so the
tenant could not have a phase cell of its own. It recovers all five re-entry
points from state that was already there:

* **`L` on entry** — 0 (fresh call) / `$81` (numeric) / `$82` (string) / `$83`
  (stored). §4.1 is why this is a register and not RAM.
* **`FN_KEY`'s name0 byte** — `$FF` marks the BODY/RESULT phases, because a
  formal's name0 is always an upcased letter. It is the same argument the
  result slot's own `$FFFF` re-key already rides on.

⚠️ **AND `FN_PTR` CARRIES TWO DIFFERENT CURSORS.** While the formal list is
walked it is the CALL cursor. Once the list closes, the definition cursor IS
the body — so the two swap, and `FN_DPTR` parks the call cursor across the
body's evaluation. `dfn_bodydone` puts it back before either terminal request,
because `fn_fin` reads `FN_PTR`.

---

## 3. 🔴 Three defects, and only a build that RUNS could see any of them

### 3.1 `cp low FN_PAREA_END` was `cp 0` — 44 rows of the battery

The ceiling test was

    ld  a,(FN_SLOTP)
    cp  low FN_PAREA_END
    jp  nc,fn_toomany       ; ERR 5

and it was **correct when it was written**. D-DEFFNEV then grew `FN_CELLS` from
3 to 11 (a nested call eats the tenant's ABI, that slice's §3), which slid
`FN_PAREA` up from `$EA95` to `$EA9D` and put `FN_PAREA_END` at **`$EB00`
exactly** — so `low FN_PAREA_END` became **0** and the compare was
unconditionally NC. Every FN call with at least one formal answered `Illegal
function call`: **44 of 69 subject rows**, while the 25 rows with no formals
(`b.noarg`, `o.argnoarg`, `o.noeq`, `o.lazybody`, …) passed.

🎯 **AND THE MIRROR FAULT WAS UNDERNEATH IT.** The ninth formal leaves
`FN_SLOTP` wrapped to `$00`, which that same compare would have read as
**legal** — so the constant going to zero broke the test in both directions at
once. The fix subtracts the base first, which turns the wrap into a borrow:

    ld  a,(FN_SLOTP)
    sub low FN_PAREA        ; A = the next slot's byte offset
    jp  c,dfn_err5          ; ...wrapped off the top of the page
    cp  FN_AREA             ; = FN_MAXP*FN_SLOTSZ; nothing here spells 9
    jp  nc,dfn_err5

🔴 **THE CLASS: A CONSTANT FALSIFIED BY AN EDIT TO A DIFFERENT SYMBOL IN A
DIFFERENT FILE.** `low FN_PAREA_END` is not a magic number — it is derived, it
is in terms of the right symbols, and it still stopped meaning what it said. No
gate reads an 8-bit compare for page-relative validity, the four `IF` asserts
that ship beside the allocation all still passed (the area does not cross a
page and `FN_MAXP` is still 9 — both true, both irrelevant), and the only
instrument that could see it was a build that RUNS. It survived the whole of
D-DEFFNEV precisely because the tenant was a stub.

### 3.2 The servicer lost an INT result to the CALSLT

`var_store_fac`'s own header: *"(DE, valid iff the CURRENT (FACTYP)==2; else
FAC/FACTYP hold the RHS's own float value)"*, and `fac_to_int_strict` is
literally `cp 2 / ret z` — it does not re-derive from FAC. The servicer's
request 1 (`call eval`) and request 2 (`call var_store_fac`) are separated by a
whole tenant bounce, and `subrom_call`'s own header says CALSLT clobbers all
registers on the way back.

So **every INT-typed actual and every `DEFINT`/`%` function would have been
handed a leftover register** — which is, one bounce further out, the exact
defect the 69-row battery found in the draft's own `fn_leave` (six rows, six
bodies, one identical `-3392`,
[`deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §4.2).

Fixed with `push de` / `pop de` around the bounce in `fn_lp`: **2 B**, in the
resident half, whose stack is the one thing a tenant re-entry cannot disturb.

🔬 **K-DE1 CUTS, AND IT CUTS WIDER THAN PREDICTED.**
`scratchpad/deffn_de_knife.py` deletes the two bytes (main `031184d9` →
`0b2a239f`, `sub.rom` unchanged as a page-1 edit should leave it) and
`deffn-strict` goes from 0 to **31 of 69 rows divergent**; restoring by writing
the bytes back returns main to `031184d9` exactly. **The prediction was "the
DEFINT rows" and that was too narrow** — an integer LITERAL actual is FACTYP=2
too, so `DEF FNA(X)=X+1 : PRINT FNA(2)` is in the class as much as
`DEFINT A-Z` is. 🔴 **And every wrong answer is a plausible number rather than
damage**: `22529`, `45058`, `11264`, `16640`, one shared value per shape. That
is [[a-scratch-register-that-was-the-callers-value]] verbatim, two slices later,
one bounce further out.

⚠️ **AND THE ALTERNATIVE — THE TENANT PRESERVING DE — WOULD HAVE MEASURED GREEN
ON THIS MACHINE AND BEEN WRONG.** C-BIOS's own `calslt` is `ex af,af' / exx` at
entry and the mirrored pair on the way out, so it *does* hand the callee's DE
back; a tenant-side `push de`/`pop de` would have passed the battery for a
reason that is a property of one BIOS. `subrom_call` documents the opposite,
and every other tenant in this tree marshals through RAM. **2 B in main is a
claim about the protocol; 2 B in the tenant would have been a claim about
C-BIOS.**

### 3.3 An `equ` alias had silently made `G8_RESIDENT` unflippable

The verb still needed a scaffold to be RUN before it fit
([[a-scaffolded-build-is-a-different-machine]]), and
`scratchpad/deffn_scaffold.py` could not set `G8_RESIDENT equ 0`:

    ERROR: Symbol 'g8_missing' is undefined  on line 299 of file basic/missing.asm

D-DUPSPAN2 had aliased `loc_missing equ g8_missing` — an always-assembled site
pointing at a symbol that exists only under `IF G8_RESIDENT`. **The build switch
had been broken since that carve and nothing could tell**: no gate in this tree
runs with a switch flipped, `tools/dupspan_indep.py` decides POSITION-
independence and REGION and has no notion of conditional assembly, and the
eleven emulator batteries all measure the enabled build. It was found by the one
thing that ever flips a switch — a scaffold.

`scratchpad/alias_gate_sweep.py` was then written to ask the question of the
whole family, and the answer is small and exact: **1 of the 107 label aliases in
`basic/` crosses a build gate**, and it is that one. Fixed by gating the alias
with an `ELSE` arm that costs the shipping build **zero bytes** (it is not
assembled there).

### 3.4 …and the dead-code gate caught the fourth, in this slice's own carve

`sav_ascii_flag`'s twenty bytes end by FALLING THROUGH into `ascii_save`. The
first draft of §4.2 put the shared body in place, *between* them — so the flag
scan ran twice and `ascii_save` was reachable from nothing. `make basic-reloc`
said so on a build that had otherwise just succeeded:

    FAIL: 5 unreachable span(s)
      [main] ascii_save   basic/save.asm   0x69c4 PAGE1  ~23 B

🎯 **THE SAME BLIND SPOT AS D-DUPSPAN'S, FROM THE OTHER SIDE.** That slice
learned that a byte-identical span may be *entered* differently; this one is
that a carve which PRESERVES a fallthrough has to preserve **what is next in the
file**, not just what the labels say.

---

## 4. Where the 47 B came from

### 4.1 The phase byte is a register — **7 B**, predicted 7

Filed as *"the servicer's answer in `E`: 5 B"*. It went in **`L`** instead,
because `E` was needed for §3.2, and it is worth more: `ld l,0` / `ld l,a` /
`ld l,$83` replace three `ld (FN_REQ),a` sequences, and the `FN_REQ` **cell is
gone** (`FN_CELLS` 11 → 10).

🎯 *"A CALSLT is not resumable, so the phase lives in RAM"* is true of the
TENANT's state and **false of the SERVICER's**. The servicer is ordinary
main-ROM code holding an ordinary register across a `call`; an inner `fn_call`
runs entirely inside the outer one's `call eval`, and the outer sets `L` again
on the way back. The phase never has to survive anything.

### 4.2 `sav_flag_a` — **13 B**, predicted 13

`sav_ascii_flag` and `sav_cas_flag` were twenty bytes of the same `,A` parse,
twice. `tools/clone_scout.py` named the pair; D-DUPSPAN2 was right to leave it
alone, because they are byte-identical and each falls through to a DIFFERENT
next routine. One `call` + two preserved fallthroughs. §3.4 is what happened to
the first draft.

### 4.3 `arga_pack_fac` / `arga_pack_single` — **27 B**, `clone_scout` said 14

Thirty-five bytes of nibble-packing, twice, differing in **one loop count**
(`ld b,7` vs `ld b,3`). Now two entry points setting `C` and falling into one
body — the shape this file already uses for `fac_to_int_addr`/
`fac_to_int_strict` and for `widen_fac_to`/`widen_lhsframe_to`.

📏 **THE ESTIMATE WAS HALF THE TRUTH, AND THE REASON IS A LESSON ABOUT THE
INSTRUMENT.** `clone_scout` priced only the 22-byte HEADER spans, because
`apf_lp`/`aps_lp` are separate symbols — so the two identical 13-byte LOOPS were
invisible to it. **A ranked estimate is a floor on its own SHAPE**, and the
shape here was "label-block", not "routine".

🔴 `BC` is GUARDED rather than re-documented: this is a resident-ABI entry with
six sub-ROM math-pack callers whose headers quote its *"Clobbers A, B, HL, DE"*
contract. `push bc`/`pop bc` costs 2 B and STRENGTHENS the contract instead of
widening it.

### 4.4 🔴 What did NOT survive contact — and the third known unknown

> *"Where do the last 26 B come from — and does `ev_t_mul`/`ev_t_div`'s shared
> prologue survive `push_lhs_frame`'s stack layout?"*

**No. REFUTED, at 0 B.** `ev_t_mul`/`ev_t_div` and `ev_e_add`/`ev_e_sub` share a
9-byte prologue (`inc ix` / `push de` / `call push_lhs_frame` / `call
set_factyp_int_ret`), and it **cannot be factored into a helper**: the `push de`
is a PERSISTENT frame the matching `combine_*` pops later, so a helper's own
return address would sit underneath it and its `ret` would pop the frame's first
word instead. That is precisely the hazard `push_lhs_frame` already documents
and solves for itself with a pop/push-the-return-address dance — and the dance
uses `DE`, which here IS the value being pushed. Every route out (select the
combiner in `HL` — `push_lhs_frame` clobbers it; stash the token — it costs what
it saves) prices at zero or worse. **`clone_scout`'s 18 B for those two groups
is unrecoverable**, and the same argument disposes of `dde_div`/`pn_div`/
`pfi_div` (10 B): their `push af` digits are a persistent frame too.

---

## 5. 💰 The step nobody had priced: the promotion

**A NEGATIVE GAP IS NOT A BUILD.** After §4 the arithmetic read −19 B, and the
image still did not assemble: page 1 was 110 B over its `$8000` ceiling while
the 129 B of slack sat below `$4000`. The gap figure every slice in this arc has
quoted is `over − lowfree`, and it is the right figure — but only because
`basic/main.asm` says the two are fungible:

> page 1 and the low region are co-mapped slot-0 pages, so a pressure-placed
> leaf can be moved between them freely and the walls are COUPLED

R1 used that in one direction (80 B of message pool promoted UP into page 1 when
the low region was full). DEF FN needed the reverse, and **112 B of real bytes
had to cross the boundary**: `basic/poke.asm` (29 B) and `basic/sound.asm`
(83 B), moved from the page-1 include block to the low-region one.

🎯 **`sound.asm` NAMED ITS OWN PLACEMENT AS PRESSURE, IN THE SLICE THAT PLACED
IT** — *"Lands in page 1 (which the disk/file eviction freed to ~1.1 KB) rather
than the now-full reclaimed low region"*. That is the definition of a promotable
leaf, written down two arcs early. `poke.asm` is the smallest statement handler
in the ROM and reaches only `eval_addr` + `eval_byte_checked`, both already low.

🔴 **AND THE DIRECTION IS WHY THIS IS SAFE.** Promoting DOWN can never break
reachability: low-region code is visible whenever page 0 is mapped, which is
always except inside a page-0 CALSLT, where no MAIN code runs at all. It is the
other direction that has bitten this tree — leaving in page 1 something the ISR
or a page-1 tenant needs, which is why `htimi_guard` exists.
`scratchpad/region_sizes.py` is the instrument that picked the pair: per-include
sizes split by region, from the sym.

---

## 6. What was run

**Static, all rc=0:** `basic-reloc` (all four walls), `unit-test` (59/59 files),
`deadcode` (0 dead, both builds), `audit-citations`, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check`, `diskdep-check`, `diskdep-selftest`.

**The verb:** `deffn-strict` — **0 of 69 subject rows divergent, 0 of 8 controls
failed, 3 of 3 address claims PASS**, on the SHIPPING build. `deffn-selftest`
18/18.

**`kwsweep`:** the `MISSING=` line is gone; `SUPPORTED` 29 → **30**. The one
`DIVERGENT` is `csrlin`, pre-existing and unrelated.

**The eleven emulator batteries** the ROM move makes mandatory, all rc=0 on
`031184d9` / `34bb8554`:

| battery | reading |
|---|---|
| `graphics-acceptance` | 383 rows, **0 DIFF** |
| `graphics-floor-acceptance` | PASS (page-0 tenant under EI: JIFFY delta 40; DI-latch mismatches 0) |
| `lineerr-acceptance` | 210/210 |
| `namspc-acceptance` | 102/102 (3 deferred) |
| `strparen-acceptance` | 16/16 |
| `fldwidth-acceptance` | 47/47 (2 deferred) |
| `cassave-acceptance` | 20/20 |
| `castail-acceptance` | 31/31 (1 pinned) |
| `dskmsg-acceptance` | 15/15 |
| `diskbasic-acceptance` | 34/34 verbs converged |
| `fat-error-acceptance` | 8/8 FIND + 3/3 MOUNT over a live FAT layer |

🎯 **`cassave-acceptance` AND `castail-acceptance` ARE §4.2's COVERAGE, not a
bystander.** `sav_flag_a` is the `,A` parse of `SAVE`, and those two batteries
are the SAVE-path differentials — 51 scored rows across both entries of the body
that was collapsed. That is a stronger statement than the demo row this slice
also has, because those rows were written to score SAVE, not to score a carve.

---

## 8. The closing demo

`scratchpad/deffn_demo.py` — real MSX BASIC on the shipping ROM against both
references, one row per rule the verb owes plus one per carve. Its readout shape
is inherited from `scratchpad/dupspan2_demo.py` **and its two blind drafts**: the
value goes inside the brackets, the fall-through line prints nothing so a row
that produced no value reads `<NO OUTPUT>`, and an error answers through the
handler. Results: `scratchpad/deffn_demo.out` — **17 of 19 zerobas readings
match the VG-8020, 18 of 19 references agree with each other.**

| row | before (recorded) | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `DEF FNA(X)=X+1 : PRINT FNA(2)` | ERR 2 | 3 | 3 | **3** |
| `DEFINT A-Z` + the same | ERR 2 | 3 | 3 | **3** |
| `DEF FNA%(X)=X/2 : PRINT FNA%(5)` | ERR 2 | 2 | 2 | **2** |
| `DEF FNA!(X)=X/2 : PRINT FNA!(5)` | ERR 2 | 2.5 | 2.5 | **2.5** |
| `DEF FNA$(X$)=X$+"!" : PRINT FNA$("hi")` | ERR 2 | hi! | hi! | **hi!** |
| `X=5 : DEF FNA(X)=X*10 : PRINT FNA(9);X` | ERR 2 | 90 5 | 90 5 | **90 5** |
| `X=5 : DEF FNA(X)=X*10 : PRINT FNA(X+1)` | ERR 2 | 60 | 60 | **60** |
| `DEF FNA(X)=X : DEF FNB(X)=FNA(X+1)+X : PRINT FNB(3)` | ERR 2 | 7 | 7 | **7** |
| `DEF FNA(X)=X : PRINT FNA(1,2)` | ERR 2 | ERR 2 | ERR 2 | **ERR 2** |
| ten formals, called with ten actuals | ERR 2 | ERR 5 | ERR 5 | **ERR 5** |
| `PRINT FNZ(1)` | ERR 2 | ERR 18 | ERR 18 | **ERR 18** |
| `PRINT 1/3` (`arga_pack_fac`) | same | .33333333333333 | .33333333333333 | **.33333333333333** |
| `A!=1/3 : PRINT A!` (`arga_pack_single`) | same | .333333 | .333333 | **.333333** |
| `POKE &HE000,65 : PRINT PEEK(&HE000)` (promoted) | same | 65 | 65 | **65** |
| `SOUND 14,0` (promoted) | same | ERR 5 | ERR 5 | **ERR 5** |
| `LOCATE ,` (`loc_missing`) | same | ERR 24 | ERR 24 | **ERR 24** |

🔴 **THREE ROWS READ `<NO OUTPUT>` AND ARE NOT EVIDENCE — INCLUDING ONE THAT
"AGREED".** They are listed here rather than quietly dropped, because a demo
that reports its blind rows as agreement is the failure this readout shape
exists to prevent:

* `DEF FNA(X)=X : CLEAR : PRINT FNA(1)` reads `<NO OUTPUT>` on **all three**
  machines — `CLEAR` also clears the `ON ERROR` trap, so the handler that was
  supposed to print `[ERR 18]` is gone by the time the fault happens. It agrees,
  and it agrees for a reason that has nothing to do with `DEF FN`
  ([[a-case-that-agrees-can-agree-for-the-wrong-reason]]). The rule itself is
  scored by `o.clearwipe3` in `deffn-acceptance`, which passes.
* the two `SAVE"...",B` rows read `<NO OUTPUT>` on zerobas because `load error`
  is **printed, not raised** — the standing D-LOADERR residual — so no handler
  fires. And their reference columns differ from each other (VG-8020 ERR 56 vs
  CF-3300 ERR 2) for the ordinary reason that one of them has no disk. §4.2's
  real coverage is `cassave-acceptance` 20/20 + `castail-acceptance` 31/31, and
  it always was.

---

## 7. What is NOT claimed

* **No knives for the verb.** It has none, and it now has a shipping ROM to cut
  against for the first time. The three defects this arc found are the obvious
  first four: `fn_slot`'s `E`, `fn_leave`'s `DE`, PRINT's item classification,
  and now §3.2's `DE`-across-the-bounce, which HAS one: K-DE1, §3.2.
* **Nothing about the aliasing of two formals of one call**, the string formal's
  shadow slot not being a GC root, or `RESUME`/`CONT`/`TRON`/array actuals —
  the impl slice's own filed list, unchanged.
* 📏 **"THE FOUR PREDECESSOR KNIFE SUITES' PINNED BASELINES ARE STALE" IS
  REFUTED** — none of `dupspan_knives.py`, `paintbord_knives.py`,
  `paintmc_knives.py` or `paints2seed_knives.py` contains a hardcoded ROM hash
  at all (`grep -E "'[0-9a-f]{8}'"`: zero hits in each). Every one of them
  computes `base_h = hashes()` from its own clean build BEFORE the baseline
  runs, and uses it only to assert that each knife MOVED the image. **The
  `('834c45b5','b91622a9')` pair lives in their prior RUN LOGS, not in their
  code** — so a ROM move does not stale them, and there was nothing to
  re-baseline. They are re-run in §9 as ordinary regressions.
* **2 B of page 1 is not headroom.** The next slice that adds a byte to page 1
  has to carve one first, or promote again — `scratchpad/region_sizes.py` is how
  to pick.

---

## 9. The four predecessor knife suites, re-run

All four, sequentially (two suites driving `make` at once would each score the
other's ROM), on the shipping DEF FN image — `scratchpad/knives1/`:

| suite | rows | verdict |
|---|---|---|
| `dupspan_knives.py` | 5 | **5/5 EXACT**, all five sources byte-identical after restore |
| `paintbord_knives.py` | 4 | **4/4 EXACT** |
| `paintmc_knives.py` | 4 | **4/4 EXACT** |
| `paints2seed_knives.py` | 2 | **2/2 EXACT** |

📏 **AND THE HANDOFF'S "THEIR PINNED BASELINES ARE STALE" IS REFUTED** (§7):
they carry no pinned hash. Each builds clean, takes `base_h = hashes()` itself,
and uses it only to assert that a knife MOVED the image.

⚠️ **TWO ARTEFACTS, TWO HASHES, ONE BUILD — do not read them as a
contradiction.** These suites hash `build/basic-reloc.rom` (the relocated BASIC,
22510 B) and `build/sub.rom`; the rest of this document quotes
`build/zerobas-main-eu.rom` (the merged 32 KB cartridge image). For this build
they are `7942cc20` / `34bb8554` and `031184d9` / `34bb8554` respectively. It is
the same trap as §7's pinned-baseline claim in miniature: **a hexadecimal
identity in a report says nothing about WHICH file it identifies unless the
report says so.**
