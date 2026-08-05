# D-PINDATA — the `input.asm` promotion, re-priced; and the pin the gates could not see

Filed against `ff5f030` (tree clean, all gates green). Closes the "NEXT TIER,
costed but NOT opened" item in [`TODO.md`](../TODO.md) and rank 3 of
[`rom-region-structure-review.md`](rom-region-structure-review.md) §7.

The filed item:

> promote `input.asm` (446 B, pressure-placed whole) — **blocked on 446 B of page 1
> that does not exist**; then per-file eviction to a sub **page-0** tenant.

Three of its four load-bearing claims are re-measured here. **The size is wrong
(458 B, not 446). The blocker is real but smaller than filed (short 157 B, not
439). The "worth it" is wrong — inverted, and measurably so. And the one claim
that survives, "pressure-placed whole", survives only by luck: the tool that
vetted it and the gate that would have caught a mistake are BOTH blind to the
reference kind that would break it.**

---

## 1. The instrument, and its own control

pasmo emits no listing file, so per-file byte extents come from **zero-byte
measurement labels injected around each low-region `include` site** in a throwaway
copy of the tree — the [review](rom-region-structure-review.md) §0 apparatus,
reused.

⚠️ **The instrument's control is byte-identity.** The instrumented image assembles
to `basic-reloc.rom` sha256 `057d6a4f536366ec87d09c4855b1d662ed2f4b663401e2ea51ef15547b639306`
— identical to the shipped build. The labels demonstrably emit nothing.

All figures below are from a **cold tree** (`rm -rf build && make basic-reloc`),
per [[measure-the-wall-from-clean]].

---

## 2. What was measured before designing

### 2.1 The walls, and 🔴 the filed size is stale by 12 B

| region | span | free |
|---|---|---|
| main low | `$2812-$3FFF` | **23 B** |
| main page 1 | `$4000-$7FFF` | **301 B** |

Per-file low-region extents, injected-label measured:

| file | span | bytes |
|---|---|---|
| `basic/str-engine.asm` | `$2812-$2ED5` | 1731 |
| **`basic/input.asm`** | **`$2ED5-$309F`** | **458** |
| `basic/float.asm` | `$309F-$3282` | 483 |
| `basic/float-arith.asm` | `$3282-$3C5C` | 2522 |
| `basic/subromcall.asm` | `$3C5C-$3CCF` | 115 |
| `basic/keytrap.asm` | `$3CCF-$3D05` | 54 |
| `basic/arrays.asm` | `$3D05-$3FE9` | 740 |
| | total | 6103 |

🔴 **`input.asm` is 458 B, not the filed 446 B.** It grew 12 B since the review
measured it on 2026-07-30. The filed arithmetic was re-derived, not reused —
[[filed-justification-is-a-claim]], now five slices running.

**Answer to Q1 (affordable?): NO. 458 B needed, 301 B available — short by
exactly 157 B.** The filed "446 B of page 1 that does not exist" was written when
page 1 held 49 B; the msgmigrate carve has since taken the shortfall from 397 B
to 157 B, so the note is stale in the direction that defers work, but the
conclusion it reaches is still the right one.

### 2.2 🔴 Answer to Q1b (worth it?): NO — and the premise is INVERTED

The item's rationale is that promotion converts page-1 slack into relief at the
**low** wall, "which is the binding one". That is an assertion about which wall
moves, and it is checkable: every commit that touched `basic/` since the review
landed can be assembled and both walls read off. pasmo is 0.1 s, so this is 31
builds and a few seconds.

Both walls, oldest first, every commit touching `basic/` from S3 to `HEAD`:

| commit | low | page 1 | |
|---|---|---|---|
| `19e8bfd` | 0 | 7 | S3 (pre-review) |
| `2aee774` | **80** | 49 | ROM REGION REVIEW + R1 |
| `5c300c7` | 80 | 30 | D-CONTR |
| `217feca` | **23** | 26 | D-ERR21 — low spent 57 B |
| `224d03f` … `1d9beb5` (8 commits) | 23 | 20 → 69 | D-LOF … D-MFDOM |
| `7c54293` … `656d653` (8 commits) | 23 | **8** | D-LNBLANK … D-REHOME |
| `cb698bc` … `6efafed` (4 commits) | **9** | **5–6** | D-DEFSTR … D-KWGAP4 |
| `3a25449` | **23** | 124 | D-RETLN — low recovered |
| `406b9e3` … `902d14d` (4 commits) | 23 | 14 → 82 | D-DELETE … D-MSGSUB |
| `40647bd` | 23 | **311** | D-MSGMIGRATE |
| `638a141` = `HEAD` | 23 | 301 | D-DOTLINE |

**Over 31 commits the low wall moved 3 times and page 1 moved 20+.** Two of low's
three moves are one slice's ±14 B round trip. Low has sat at exactly **23 B** for
25 of the 31; page 1 has ranged **5 B → 311 B** and spent **six consecutive
commits at ≤ 8 B**. Low never went below 9.

⇒ **Page 1 is the wall that binds. Low is the wall that sits.** Promoting
`input.asm` would drive page 1 — the wall that has repeatedly been the one a
slice had to fight — to **zero**, in order to add 458 B to the wall that has
moved three times in a month. That is the trade backwards.

The structural reason, also measured: only **1643 B** of the low region's 6126 B
is contract-forced (`promote_scout` census). The remaining 4483 B of low capacity
is available to the forced set whenever it is wanted. **"Low free = 23 B" measures
a PACKING CHOICE, not a contract** — and because page-1 → low moves are always
legal and low → page-1 needs only the forced-set check, the split can be
re-cut on demand at whatever granularity a future need actually has. There is no
reason to pre-pay for a need that has materialised twice in a month.

### 2.3 🔴 The claim that survives, and why it survives by luck

The one filed claim that holds is "pressure-placed whole". Checked two ways:

| model | `basic/input.asm` |
|---|---|
| call-graph only (`call`/`jp`/`jr`/`djnz`) | 458 B promotable / **0 B pinned** |
| identifier-aware (data references included) | 458 B promotable / **0 B pinned** |

So the verdict on `input.asm` itself is robust. But asking the second question —
the review's §0.1 error 3 was a call-graph-only closure missing `ld hl,zkey_hook`
— turned up that **the fix never reached the shipped tools**:

* [`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py) — the gate
  that decides what may SHIP, and the review's own named "feasibility oracle" —
  builds its graph from `_XFER = call|jp|jr|djnz`. **It cannot see a data
  reference.**
* [`tools/promote_scout.py`](../tools/promote_scout.py) — the scout that decides
  what to ATTEMPT — imports that same `build_callgraph`. Same blindness, papered
  over by hand-seeding `zkey_hook` into `DEFAULT_ISR_SEEDS`: the one known
  instance is patched, the CLASS is not.
* Only [`tools/check_dead_code.py`](../tools/check_dead_code.py) got the fix, and
  it answers a different question (is anything unreachable), not this one.

That is [[carve-scout-before-proposing]] point 5 again — "the scout that decides
what to ATTEMPT was looser than the check that decides what may SHIP" — except
here **both** are loose, in the same way, and the tighter model exists in the tree
three files away.

### 2.4 🔴 The live instance: 15 bytes nothing can see

Running a control+data closure over the resident-ABI seeds finds exactly **three**
low-region labels that are pinned ONLY by a data edge:

| addr | label | bytes |
|---|---|---|
| `$309F` | `tkf_ref32767` | 5 |
| `$30A4` | `tkf_ref65535` | 5 |
| `$30A9` | `tkf_ref32768` | 5 |

They are unpacked-digit bound tables at [`basic/float.asm:29`](../basic/float.asm:29).
The reference is `ld de,tkf_ref32768` at
[`basic/float-arith.asm:1182`](../basic/float-arith.asm:1182) (`dcc_dexp5`) and
[`:1871`](../basic/float-arith.asm:1871) (`cpow_dexp5`) — an **address load**,
never a call. `dcc_dexp5` is reached from `domain_convert_core`, reached from
`flt_to_int16`, which is a **resident-ABI export**
([`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc)) that the page-1
tenant `circleparse_tenant` calls at
[`sub/circleparse.asm:407`](../sub/circleparse.asm:407) (`cpt_round`).

So those 15 bytes are in the **closure of a page-1 tenant's entry point**, reached
by a reference kind no gate walks. They are contract-forced low by the same
standard `check_tenant_closure.py` applies to every callee, and:

> ⚠️ **CORRECTED AFTER RUNNING (§5.3).** This section first said the tenant
> *reads them at runtime*. **It does not.** The only tenant caller
> (`sub/circleparse.asm` `cpt_round`) feeds `flt_to_int16` a value ≤ 256.5, so the
> dexp==5 arm is unreachable from it. The pin below is a **closure-contract** pin,
> not a demonstrated live fault, and K1d is the knife that came back green and
> said so.

* `promote_scout.py --labels tkf_ref32767,tkf_ref65535,tkf_ref32768` today prints
  **`VERDICT: PROMOTABLE`, rc 0** — measured;
* `basic/float.asm` is the **#4 whole-file promotion candidate** in the scout's own
  inventory at **467 B promotable / 16 B pinned**;
* the review's §2 table, produced by its FIXED apparatus, called `float.asm`
  "MIXED (effectively forced)". **The shipped tool disagrees with the review that
  commissioned it**, and the tool is the one a future slice would run.

⚠️ **And no standing gate exercises the path.**
[`probes/basic/basic_probe_graphics.py`](../probes/basic/basic_probe_graphics.py)'s
CIRCLE corpus tops out at coordinate 80, whose `|value|+0.5` has dexp 2. The
dexp==5 arm needs `10000..99999`. So the fault would ship green.

**No live violation exists today** — all three tables are at `$309F`, below
`$4000`. This is a blind gate, not a broken ROM. §5 makes it a fault on purpose
and scores what each instrument says.

### 2.5 Two models that are WRONG, and why the fix is a third

Both obvious repairs were measured and both are false-positive machines:

* **"every identifier is an address"** — floods. On `--page0` it reports **63**
  escapes that are `equ` **values**, not locations: `AUTO_TOKEN $00A9`,
  `PSG_ADDR $00A0`, `GFX_SATR_BASE $1B00`, `CLEARPOOL $0001`, … ⇒ **an `equ` is a
  value; only a `label:` is a location.**
* **"a data edge propagates control flow"** (`check_dead_code`'s model, which is
  correct for *its* question) — over-pins. It falls out of the 5-byte `db` table
  `tkf_ref32768` into the next label `flt_out` and drags in the whole formatter:
  **35 low labels / 482 B** flip to pinned, and `basic/float.asm` reads **17 B
  promotable / 466 B pinned**. A legitimate promotion blocked by a routine nothing
  executes. ⇒ **a data edge pins its TARGET SPAN and does not propagate through
  it.** Reading five bytes is not entering a routine.

---

## 3. Design

### 3.1 What changes

1. [`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py) — a
   **data-reference pass** on all three walks. Same linear spans as the control
   graph; for every span in the control closure, every other identifier it
   mentions that is a `label:` definition is a data target, and the **same region
   predicate** is applied to it. Data targets are reported separately from control
   escapes and do not seed further walking.
2. [`tools/promote_scout.py`](../tools/promote_scout.py) — pin a low-region label
   if it is in the control closure of (resident ABI ∪ ISR seeds) **or** is data-
   referenced from it. The scout then grades on the same rule the gate enforces.

### 3.2 What does NOT change

**No ROM source ships in this slice.** The re-pricing in §2.1/§2.2 is a decision
not to promote, and `tkf_ref*` is already in the right region — the change is that
the tree can now *prove* it rather than accidentally satisfy it. `build/basic-reloc.rom`
and `build/sub.rom` must come out byte-identical.

The `input.asm` promotion is **not attempted, and is re-filed as declined** rather
than blocked — §2.2 is a reason not to want it, which outlives the 157 B.

### 3.3 Stated coverage limit, before running

**A data reference to a symbol imported by `equ` is not classified.** Main
routines enter the sub build as `equ` addresses
(`sub/basic-resident-abi.inc`), and the `label:`-only rule excludes them. That is
a real hole, so it is checked rather than assumed: **measured, none of the 11
resident-ABI names is mentioned non-transfer anywhere in either sub closure — the
hole is empty today.** It is an [[exemption-as-a-checked-claim]], and the check
ships with the gate.

---

## 4. Predicted GREEN — fixed before the change

| id | prediction, exact |
|---|---|
| G1 | `make basic-reloc` exit 0; abi walk **122** control + **4** data-referenced, 0 escapes; `--page0` **718** + **15**, 0 escapes; `--page1` **515** + **41**, 0 escapes |
| G2 | `build/basic-reloc.rom` sha256 `057d6a4f5363…`, `build/sub.rom` `5aef3181…` — **byte-identical**, the change is tooling only |
| G3 | `promote_scout` inventory: `basic/input.asm` **458 / 0** unchanged; `basic/float.asm` **467 / 16 → 452 / 31**; totals **4460 / 1643 → 4445 / 1658** |
| G4 | the 4 data-referenced labels in the abi walk are exactly `ary_reset`, `tkf_ref32767`, `tkf_ref65535`, `tkf_ref32768` |
| G5 | `basic_probe_dexp5_pin.py --expect` → **13/13 SAME** against the recorded baseline |

Baseline for G5, measured before any change, **zerobas agreeing with the VG-8020
oracle on all 13 rows** (4.9 s):

```
TENANT circ_x40000 ERR6 · circ_y40000 ERR6 · circ_x10000 cont · circ_x99999 ERR6
       circ_xneg40000 ERR6 · circ_r40000 ERR6 · circ_ok cont · circ_x300 cont
MAIN   poke_40000 cont · poke_99999 ERR6 · poke_neg40000 ERR6 · vpoke_40000 ERR6
       out_40000 cont
```

## 5. Predicted RED — the knives

### 5.1 K1 — the false negative, made real

Move `tkf_ref32767` / `tkf_ref65535` / `tkf_ref32768` out of `basic/float.asm`
into main page 1. This is the promotion `promote_scout` currently blesses.

| id | instrument | prediction |
|---|---|---|
| K1a | `check_tenant_closure.py` **at `ff5f030`** | `OK: 122 routines … No page-1 escapes`, **exit 0** ← the false negative |
| K1b | `check_tenant_closure.py` **after** | **exit 1**, 3 DATA escapes: `tkf_ref32767`, `tkf_ref65535`, `tkf_ref32768`, each ≥ `$4000` |
| K1c | `promote_scout --labels tkf_ref…` | before: `VERDICT: PROMOTABLE` rc 0 (**already measured**) → after: `PINNED` rc 1 |
| K1d | `basic_probe_dexp5_pin.py --expect` | **≥ 1 of the 6 dexp==5 TENANT rows MOVED**; **all 5 MAIN rows SAME**; both dexp≠5 TENANT rows (`circ_ok`, `circ_x300`) SAME |

K1d's second and third clauses are the control that makes the first mean
something: if the MAIN rows moved too, the fault would be arithmetic, not paging.
**A knife is only believed if it CUT and the fault reproduced in the same run.**

> 🔴 **K1d MEASURED GREEN.** It is left above exactly as predicted, because the
> prediction being wrong is the slice's second finding. §5bis.3 is the chase.

### 5.2 K2 — keep the emission, gut only the judgement

Leave the data pass walking, collecting and **printing its count** in the OK line;
delete only the region test on data targets. Predicted: on the K1 tree the gate
prints the same `… + N data-referenced` clause and **exits 0**. Coverage survives,
efficacy dies — [[coverage-gate-cannot-see-a-gutted-guard]]. The readout must
therefore name escapes, not report a count.

### 5.3 K3 / K4 — the two false-positive controls

Already measured in §2.5 and re-run as rows: K3 (`equ` treated as an address) →
**63** spurious `--page0` escapes on the UNMODIFIED tree. K4 (control flow
propagated through a data edge) → **482 B / 35 labels** spuriously pinned,
`float.asm` **17 / 466**. Both must stay red under the shipped rule, i.e. the
shipped gate must NOT reproduce either number.

---

## 5bis. What landed, and what it measured

Shipped: [`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py)
(`build_datagraph` + `data_targets` + `_abi_data_hole`, wired into all three
walks), [`tools/promote_scout.py`](../tools/promote_scout.py) (pins on the same
rule, and `--why` now names a data pin),
[`probes/basic/basic_probe_dexp5_pin.py`](../probes/basic/basic_probe_dexp5_pin.py)
+ `make dexp5-pin`. **No ROM source.** `input.asm` is NOT promoted.

### 5bis.1 GREEN, scored

| id | predicted | measured |
|---|---|---|
| G1 | abi 122+4, page0 718+15, page1 515+41, all rc 0 | **exact**, all rc 0 |
| G2 | ROM byte-identical | **exact** — `057d6a4f…` / `5aef3181…` |
| G3 | input 458/0, float 467/16 → **452/31** | **exact** |
| G3 | totals 4460/1643 → **4445/1658** | 🔴 **WRONG — 4437/1666** |
| G4 | the 4 = `ary_reset`, `tkf_ref32767/65535/32768` | **exact** |
| G5 | 13/13 SAME | **exact** (and 16/16 PASS vs the VG-8020 after the §5.3 rework) |

🔴 **G3's total was my own arithmetic, and it was wrong by exactly 8 B** — the
`ary_reset` row I had *already written down in G4* and then left out of the sum.
Per-file rows right, total wrong: 4460 − 15 − **8** = 4437. Same shape as
[[filed-justification-is-a-claim]], with me as the author of the unchecked claim.

### 5bis.2 RED, scored

| id | predicted | measured |
|---|---|---|
| K1 cut | tables at ≥ `$4000`; low 23→38, page 1 301→286 | **exact**, `$4010/$4015/$401A` |
| K1a | old gate `OK: 122 routines … No page-1 escapes`, rc 0 | **exact** — the false negative |
| K1b | rc 1, 3 DATA escapes named | **exact** |
| K1c | `PROMOTABLE` rc 0 → `BLOCKED` rc 1 | **exact** |
| K1d | ≥1 tenant row MOVED, MAIN rows SAME | 🔴 **13/13 SAME — predicted RED, measured GREEN** |
| K2 | prints `+ 4 data-referenced`, exits **0** on the K1 tree | **exact** |
| K3 | 63 spurious `--page0` escapes | **exact** — 267 labels, 63 escapes, all `equ` values |
| K4 | 35 labels / 482 B over-pinned, float 17/466 | **exact** |

### 5bis.3 🔴 K1d came back green, and the green was the finding

The knife CUT (K1a–K1c all fired) but the fault did not reproduce. Rather than
file that as noise, it was chased — [[knife-that-reddens-nothing-is-the-finding]],
and a row with two candidate causes needs separating, not choosing between.

**K1e, the separating knife:** leave the tables in the low region and change
their *contents* instead — `tkf_ref32767` from `3,2,7,6,7` to `9,9,9,9,9`. Result:
**5 of 13 rows moved** (`circ_x40000`, `circ_y40000`, `circ_x99999`, `circ_r40000`
→ verdict flipped; `vpoke_40000` → ERR6 to ERR5). So the dexp==5 arm IS reached by
the CIRCLE rows. Cause (a), "the path is dead", is refuted.

The K1/K1e **pair** then localises the reader, which neither does alone:

* K1e moved the `circ_*` rows ⇒ they read these tables;
* K1 (tables relocated into **main page 1**) did **not** move them ⇒ their reader
  sees main page 1 ⇒ **the reader is main-side, not a tenant.**

And the last link, read out of the source once the measurement pointed at it:
`cpt_asp_scale256` ([`sub/circleparse.asm:309`](../sub/circleparse.asm:309)) is
the tenant's only `cpt_round` caller, and it converts `minor_ratio*256` where the
ratio is whichever of `aspect` / `1/aspect` is ≤ 1
([`:186-215`](../sub/circleparse.asm:186)). So the tenant's argument is ≤ 256.5,
**dexp ≤ 3, and the dexp==5 arm is unreachable from the only tenant caller.**

⇒ **The blind spot is real and demonstrated; the runtime consequence for THIS
instance is not.** The gate change stands on the same ground every closure gate
stands on — it enforces the contract over the closure without asking which
arguments are reachable — and §2.4 is corrected to say so. What would have been a
confident wrong sentence in a shipped spec was caught by insisting the knife
reproduce the fault.

⚠️ **My probe's own row labels were wrong too.** Every CIRCLE row was written
`TENANT`; the measurement says `gfx` (main-side). Relabelled from the
measurement, and three genuine `tenant` rows (the aspect path) added, which is
what makes the probe pin the dexp ≤ 3 claim rather than assume it.

### 5bis.4 The probe is a gate that has been shown to move

`make dexp5-pin`, **16/16 vs the VG-8020 in 6.0 s**. Before it, the three bound
tables had no gate at all: `graphics-acceptance`'s CIRCLE corpus tops out at
coordinate 80 (dexp 2) and `intarg-acceptance` never reaches the graphics reader.
K1e is its falsification — a five-byte edit moves five rows.

### 5bis.5 One incidental, recorded not fixed

`check_dead_code.py`'s main seed count moved **283 → 284**: `external_names`
scans `tools/*.py` for identifiers, and a comment added here names `dcc_dexp5`.
⚠️ **Naming an assembler label in a tool comment immunises it from the dead-code
sweep.** Nothing was masked (`dcc_dexp5` is live by a control edge, and the sweep
reported 0 dead both before and after, so an added seed cannot have hidden
anything), but the hazard is real and belongs in `TODO.md`, not in a fix here.

---

## 6. Corpus

Sequentially, never two emulator gates at once: `unit-test` · `basic-reloc`
(carries `deadcode` + all three closure walks) · `preflight-check` ·
`injector-check` · `latch-check` · `graphics-acceptance` · `dexp5-pin` ·
`diskbasic-acceptance` · `lof-acceptance` (standing flake watch — one drift in
six runs, `wm_app_put`; a second sighting is a finding, not a filing).

G2 (ROM byte-identity) is what bounds the blast radius: no shipped ROM byte moves,
so no emulator gate can have changed meaning.

---

## 7. What this leaves open

* **The `input.asm` promotion is DECLINED, not blocked.** §2.2 is the reason and
  it does not expire when 157 B appears. Re-open it only against a measured
  low-region need.
* **Rank 4 (per-file eviction to a sub page-0 tenant) is the only move that
  CREATES bytes** and is now the whole of the next tier. Not opened here.
* **`equ`-imported data references are unclassified** (§3.3) — checked empty, not
  structurally impossible.
* **A data reference to CODE is still ambiguous.** `ld hl,zkey_hook` installs a
  hook that EXECUTES; `ld de,tkf_ref32768` reads bytes. The shipped rule pins both
  and propagates through neither, which is right for a table and *under*-pins a
  hook. Hooks stay explicitly seeded, as `zkey_hook` already is.
