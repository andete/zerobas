<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Decision — slicing and funding the keyword-completeness gaps

**Status:** DECISION DOC, 2026-07-27 — **awaiting sign-off**. No implementation
until D-KW-1..D-KW-3 are answered. Input: the re-pinned sweep
[`kwsweep-msx1-coverage.md`](kwsweep-msx1-coverage.md) (`git=e9843c4`,
`zerobas-main-eu.rom=4ea7a29918df`). Closes the TODO line *"Not yet sliced or
costed"*.

## 1. What this decides

The sweep gave the roadmap a denominator: **34 of 162 MSX1 reserved words are
genuinely absent**, of which **14 matter now** — 8 SILENT-GAP (wrong answer, no
error) and 6 MISSING (honest syntax error). The remaining 20 are the NO-ORACLE
MK/CV family (already deferred under the float pack) and words whose absence is
recorded but unprioritised.

It did **not** say how to build them, in what order, or where the bytes come
from. That is this document.

## 2. The resource picture — and it is not the one the TODO assumes

The TODO's keyword item says *"Page 1 is currently 14 B over the ceiling … so
every one of these needs funding before it needs a spec."* **The first clause is
stale and the second is wrong.** Measured from clean (`rm -rf build && make
basic-reloc`, `e9843c4`):

> 🔄 **UPDATED 2026-07-27 (`6f8ac0f`): main page-1 free is now 375 B, not 8 B.**
> D-KW-1 was answered "first make a few 100 bytes of space", and the
> [FAT tenant-shim collapse](../basic/fat.asm) delivered **+367 B** — thirteen
> byte-identical 34 B shims collapsed onto one shared body. The table below
> records the state that *motivated* the carve; the "scarce?" column no longer
> describes page 1. The **low region is still 5 B** and the per-keyword
> dispatch-glue analysis below is unchanged — it is what made the carve the
> right first move rather than a detour.

| region | free (pre-carve) | scarce? |
|---|---|---|
| main page-1 `$4000–$7FFF` | **8 B** → **375 B** after `6f8ac0f` | no longer |
| main low region `$2812–$3FFF` | **5 B** | **yes** |
| **sub.rom page-0** (`$0000–$2E63` used) | **4509 B** | no |
| **sub.rom page-1** (`$4000–$7257` used) | **3497 B** | no |

`sub.rom` has **≈8 KB free**. Main has **13 B**. The keyword gaps are therefore
a **placement** problem, not a space problem — and two of the three cost
components already live where the space is:

* **`kwtable.inc` entries are free.** Since the wave-3 detokeniser eviction the
  resident copy is *dropped* and the sub-ROM copy is the sole source (913 B,
  gated by `check_kwtable_identity.py`). All 14 entries ≈ 130 B of sub-ROM.
* **Leaf compute is nearly free** — a sub-ROM tenant, per the
  [tenant playbook](subrom-tenant-playbook.md). `BIN$`'s digit loop sits beside
  `sh_oct_build` (23 B) at zero main cost.
* **Dispatch glue is NOT free.** It is main-ROM, it is unavoidable, and it is
  the entire budget.

### 2.1 The dispatch tax, measured

> 🏁 **SUPERSEDED 2026-07-27 — D-KW-2 LANDED.** `exec_stmt` is now a
> `db token, dw handler` table, so the marginal price of a statement keyword is
> **3 B, not 5 B**, and page-1 free went 311 B → **420 B (+109 B)**. The section
> below is kept as the measurement that justified it. See
> [`decision-missing-class-slicing.md`](decision-missing-class-slicing.md) §4 for
> the as-built, including the two near-misses in its gate.

`exec_stmt` ([`basic/interp.asm:160`](../basic/interp.asm:160)) **was** a linear
`cp TOKEN` / `jp z,handler` chain of 67 entries — 5 B per statement token, 335 B
total. `exp_loop` ([`basic/print.asm:151`](../basic/print.asm:151)) and the `$FF`
function dispatch have the same shape. So the marginal main-ROM price of a new
statement keyword is **5 B before it does anything**, against a 13 B budget.

**Three statement keywords is the whole tree.** That is the real constraint, and
it is why §4 recommends levers before words.

## 3. The 14 words, costed

Tokens are **oracle-measured**, not table-read — see the token table in
[`kwsweep-msx1-coverage.md`](kwsweep-msx1-coverage.md). Costs are **estimates**;
this repo's estimates have run optimistic often enough that each slice must open
with a measured spike ([`decision-fund-time-and-t5.md`](decision-fund-time-and-t5.md)
§3.6 is the one time they did not).

| word | token | main-ROM est. | sub-ROM est. | notes |
|---|---|---|---|---|
| `EQV` | `$F9` | **≈ 0 (see §4.1)** | — | new precedence layer |
| `IMP` | `$FA` | **≈ 0 (see §4.1)** | — | new precedence layer |
| `CSRLIN` | `$E8` | ~13 B | 9 B | `(CSRY)−1`; C-BIOS maintains `$F3DC` |
| `POS` | `$FF $91` | ~18 B | 8 B | `(CSRX)−1`; arg is a dummy |
| `SPC(` | `$DF` | ~20 B | 8 B | shares `pcz_pad` with `print_comma_zone` |
| `TAB(` | `$DB` | ~28 B | 8 B | pad-to-column; wraps when already past |
| `BIN$` | `$FF $9D` | ~20 B | ~40 B | leaf beside `sh_oct_build` |
| `FRE` | `$FF $8F` | ~35 B | ~30 B | numeric vs `FRE("")` GC form |
| `TRON`/`TROFF` | `$A2`/`$A3` | ~45 B | 18 B | **run-loop** hook, not evictable |
| `MOTOR` | `$CE` | ~20 B | ~25 B | `ON`/`OFF` parse + cassette motor |
| `LOCATE` | `$D8` | ~17 B | ~55 B | 3 optional args; `POSIT` |
| `SWAP` | `$A4` | ~20 B | ~60 B | two lvalues in the unified var chain |
| `DEF FN`/`FN` | `$97` `$DE` | **200–400 B** | — | **an arc, not a slice** |

`DEF FN` is the outlier by an order of magnitude: it needs a definition table,
argument binding, and re-entrant evaluation. It should not be sliced with the
others.

## 4. The recommendation — levers before words

Two **self-funding generalisations** exist. Both are repack-only (the lean cart
stays byte-frozen), both have many beneficiaries, and both make every *remaining*
keyword cheaper. The standing warning that a shared-code cost is a *down-payment*
— measuring a refactor with its beneficiaries gated *out* tells you what it cost,
not what the alternative cost — cuts **in favour** here: the beneficiary counts
are 67 and 5, not 2.

### 4.1 Lever L2 — table-drive the logical layer (funds `EQV` + `IMP` outright)

`ev_xor`, `ev_or`, `ev_and` ([`basic/expr.asm:53`](../basic/expr.asm:53)) are
**byte-for-byte uniform at 34 B each** — measured from `basic-reloc.sym`, 102 B
for three. The only thing that differs is a 6-byte apply block.

* Naive `EQV` + `IMP` = two more copies = **+68 B**. Unaffordable.
* One generic layer walking a 5-entry `(token, apply, next)` table ≈ 40 B engine
  + 15 B table + ~47 B of apply blocks ≈ **102 B for five layers**, against 102 B
  for three today. **`EQV` and `IMP` land for ≈ 0 net bytes.**

MSX precedence is `NOT` > `AND` > `OR` > `XOR` > `EQV` > `IMP`, with `IMP`
lowest. **That ordering must be characterised against the VG-8020 before it is
encoded**, not asserted from the manual — the spec owes a differential row per
adjacent pair. `EQV` = `NOT (a XOR b)`; `IMP` = `(NOT a) OR b`.

This is the **highest-value slice in the set**: it clears 2 of the 8
SILENT-GAPs, it is the only one that pays for itself, and `PRINT 5 EQV 3`
printing *three separate values* is the most alarming failure in the table.

### 4.2 Lever L1 — table-drive `exec_stmt` — ✅ **LANDED 2026-07-27**

**As built: −109 B measured** (chain 377 B → table 268 B, page-1 311 → 420 B),
against the −114 B predicted here. The estimate below stands up; the shortfall is
the search loop coming out slightly larger than the ~20 B guessed. The
per-keyword tax did drop 5 B → 3 B as designed.

67 entries × 5 B = 335 B of chain. A `(token, handler)` table is 67 × 3 = 201 B
+ a ~20 B search ≈ 221 B → **net ≈ −114 B**, and it is *faster* per entry
(~7 T vs ~19 T). It also converts the marginal statement-keyword price from 5 B
to 3 B, which is what makes `LOCATE`/`SWAP`/`TRON`/`TROFF`/`MOTOR` affordable at
all.

Risks to price in: the chain carries `IF ROM_BASE < $4000` and `IF G6/G7/G8_RESIDENT`
conditionals (the table must be conditionally assembled the same way); the lean
build must keep its chain byte-identical; and the trailing `is_letter → ex_let`
fallback is not a token compare and stays put.

**L1 is a bigger, riskier change than L2 and touches the hottest path in the
interpreter.** It should be spiked and measured before it is committed to — but
if it lands, the remaining 12 words stop competing for a 13-byte budget.

### 4.3 Proposed order

> ✅ **STEP 1 LANDED 2026-07-27** — [`spec-basic-logicops-eqv-imp.md`](spec-basic-logicops-eqv-imp.md),
> gated 156/156. L2 came in at **−5 B for SIX levels** against the three it
> replaced, beating the "≈ 0 net bytes" estimate, and it consumed the `ev_*_lp`
> clone group as §5a required. Two SILENT-GAPs cleared: **6 remain**.
>
> It also turned up two silent divergences that were nobody's keyword gap —
> chained relationals and operators after a string `PRINT` item — landed as
> [`spec-basic-relational-chain.md`](spec-basic-relational-chain.md), 193/193.
> **The precedence characterization was worth more than the feature**: it is what
> made the calibration battery exist, and the calibration battery is what found
> them. See [`logicops-vg8020-characterization.md`](logicops-vg8020-characterization.md).

1. **L2 + `EQV`/`IMP`** — self-funding, clears 2 SILENT-GAPs, small blast radius.
2. **`CSRLIN` + `POS` + `SPC(` + `TAB(`** — the cursor/PRINT cluster, ~79 B main,
   4 SILENT-GAPs, one coherent spec, one gate. Needs funding *or* L1 first.
3. **L1** — the dispatch table, if (2) shows the budget is binding.
4. ✅ **`BIN$` + `FRE` — LANDED `2facfc0`, 83/83.** **THE SILENT-GAP CLASS IS
   EMPTY.** No MSX1 reserved word silently computes a wrong answer any more —
   D-KW-3's exit criterion, met. See
   [`spec-basic-binfre.md`](spec-basic-binfre.md) and
   [`binfre-vg8020-characterization.md`](binfre-vg8020-characterization.md).

   `BIN$` was funded by collapsing its **own family**: `str_fn_hex` (43 B) and
   `str_fn_oct` (38 B) were near-identical low-region clones, and the 5-byte
   difference between them *was* a bug (§5a's shape, found by measurement).
   Low region **7 → 11 B free** with `BIN$` inside it. Two more silent
   divergences fell out of the calibration battery — the **third consecutive
   slice** in which it has paid for itself:
   **D-BF-1** `HEX$`/`OCT$` accepted a string argument and printed `0`;
   **D-BF-2** `OCT$` had no domain check, so `OCT$(65536)` printed `OCT$(0)`.
   Both died in the collapse rather than being fixed three times.

   `FRE` took the **one-gap** model (D-BF-A(c)): zerobas has a single free span
   where the reference has two independent pools, and `CLEAR`'s string-space
   argument is discarded. **Follow-on opened: the `CLEAR` string-pool
   partition**, which would move six recorded-not-gated rows back into the gate.
5. **`LOCATE`, `SWAP`, `TRON`/`TROFF`, `MOTOR`** — the honest-error class.
6. **`DEF FN`** — its own arc, its own spec.

## 5. Decisions — all three answered 2026-07-27

**D-KW-1 — take L2 (`EQV`/`IMP`) as the next slice?** **✅ ANSWERED: carve
first.** The answer was *"first make a few 100 bytes of space"* — the arc opens
with funding, not with a word. Delivered by `6f8ac0f`: the FAT tenant-shim
collapse, **+367 B** (see §2's banner and §6). **`EQV`/`IMP` is now the next
slice and needs a spec.** It no longer has to be self-funding to be affordable,
but the table-driven layer is still the right shape — five operators for roughly
what three cost — and the VG-8020 precedence characterization is still owed.

**D-KW-2 — is L1 (the `exec_stmt` dispatch table) in or out of scope?**
**✅ ANSWERED: defer** until a slice is demonstrably blocked on it.
🏁 **That condition was met on 2026-07-27 and L1 LANDED**: the MISSING class
(300–405 B of bodies against 311 B free) is the slice that blocked on it, exactly
as predicted. "Do not refactor the hottest path on speculation" held — it was
refactored on a measurement instead.
The original deferral reasoning: Do not
refactor the hottest path in the interpreter on speculation; with 375 B free
that is comfortable. The page-1 frontier scout it referenced is now promoted to
[`tools/p1scout.py`](../tools/p1scout.py) — **but read §6's caveat before
trusting its output.**

**D-KW-3 — is "SILENT-GAP class empty" the arc's exit criterion**, with the
6 MISSING words and `DEF FN` as separate follow-on work? **✅ ANSWERED: yes** —
the silent class is the one that is a live landmine in a user program; an honest
`Syntax error` is a diagnosable absence, not a wrong answer.

## 5a. What funding remains of the same kind (measured 2026-07-27)

Asked after the FAT carve: *are there more like that?* Answered by
[`tools/clone_scout.py`](../tools/clone_scout.py) — a new scan for groups of
label-blocks identical but for one or two operands — **calibrated by requiring it
to rediscover the FAT group at `099c809`**, which its first version could not (it
masked one operand; those shims differ in two).

| est. | n × each | region | gating | group |
|---|---|---|---|---|
| ~~~100 B~~ **✅ 143 B taken** | 5 × 32 B | page 1 | **repack-only** | `evmc_atn/cos/rnd/sin/tan` — math-fn tenant call glue. **Done `4bfafa2`**; extending to `SQR`/`LOG`/`EXP` (which share both halves, domain check in between) beat the estimate: 143 B, not 100 B. |
| ~100 B | 5 × 31 B | page 1 | both | `ev_and_lp/ev_idiv_lp/ev_mod_lp/ev_or_lp/ev_xor_lp` |
| ~28 B | 3 × 20 B | page 1 | repack-only | `fat_rand_get/open/put` |

**The well is much shallower than the FAT carve suggested.** That group had
accumulated *thirteen* copies; nothing else in the tree has more than five, and
the whole remaining set of this shape is ~240 B against the 367 B that one carve
returned. The **low region — still 5 B free and the real wall** — has nothing
carveable this way at all: its largest clone group is 14 B.

Recommended handling:

* ~~`evmc_*` is the clean one…~~ **✅ TAKEN 2026-07-27 (`4bfafa2`), +143 B** —
  banked deliberately rather than on demand, so slices stop opening with a hunt
  for space. **Page 1 is now at 518 B free.** Its `ret nz` deferred-error path
  *is* covered by `math-acceptance` (falsified: removing it turns the gate red
  with 7 failures) — unlike the FAT carve, no new gate was needed.
* `ev_*_lp` **must not be done standalone.** It is L2 from §4.1 under another
  name; folding it into the `EQV`/`IMP` slice buys *seven* operator layers for
  what five cost, instead of refactoring the same code twice.
* `fat_rand_*` at 28 B is not worth a session.

## 6. Method notes worth keeping

* **The sweep re-pin was worth running on its own.** The previous pin was taken
  against a build that HEAD could no longer produce (14 B over). The re-pin moved
  the main-ROM hash `05f43b…` → `4ea7a2…` and **changed no tally** — which is the
  only way to know the 8/6/5 finding was not an artifact of the stale ROM.
* **Harvest tokens from the probe you already have.** All 14 token assignments
  came out of Layer 1's own CRUNCH diff (`--layer crunch --only …`, one run,
  ~1 min) as bytes the reference *emitted*. That is a stronger provenance than a
  table lookup and it cost nothing to obtain.
* **Ask where the bytes are, not how many are left.** The TODO framed this item
  as blocked on funding. It is blocked on *placement*: 8 KB is free in `sub.rom`
  and 13 B in main, so the only number that matters per keyword is its
  **main-ROM dispatch glue**.
* ⚠️ **A byte census cannot tell ENGINE from BOILERPLATE, and a ZERO frontier can
  mean "already carved" rather than "free to carve."** `tools/p1scout.py` reported
  `basic/fat.asm` as **811 B of page-1 content with a zero frontier** — which reads
  like an 811 B carve waiting to happen. It was the opposite: the carve had already
  happened years of commits ago, and the frontier was zero *precisely because* what
  remained was glue. Glue calls `subrom_call`; it never calls main page 1. The real
  find was that thirteen copies of that glue were byte-identical. **Read the code
  before believing the scout** — the scout answers a legality question, not a value
  question.
* ⚠️ **`diskbasic-acceptance-repack` stays 34/34 green with the FAT error tail
  deliberately broken.** All 34 oracle differentials exercise the success path only.
  Found by falsification during the carve, not by inspection; closed with
  `make fat-error-acceptance`. Whenever a change lands under a gate, ask what the
  gate would still say if the change were wrong.
