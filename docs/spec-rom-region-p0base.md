# D-P0BASE — relocate `SUBROM_ENTRY_BASE_P0` past the `$0038` vector; and the review's own justification for "prefer page 0" is the WRONG ONE

Status: **spec written 2026-08-05, before any source change.**
Baseline `52b2386` (D-EVLNO), tree clean.

Opens the blocker [D-EVLNO](spec-rom-region-evict-lineno.md) §2.2 found while
applying rank 4 of the [ROM REGION STRUCTURE REVIEW](rom-region-structure-review.md)
§7: the sub-ROM **page-0 entry table is full** — 13 `jp` rows at `$0010..$0036`,
one spare byte, then the fixed `$0038` IM1 vector — so the review's §6 costing
rule *"future evictions should prefer page 0"* cannot be obeyed.

---

## 0. The question this slice was told to answer FIRST

> *Is there any page-1 cluster whose only blocker is that it needs to call main
> page 1 (i.e. it is page-0-legal but NOT page-1-legal)? If the answer is "none",
> the right deliverable is a measured DECLINE.*

**Measured answer: NONE — and that is a finding about the review, not about the
move.** §2.1 and §2.2 below. The review justified "prefer page 0" by
**visibility** (a page-0 tenant may call main page 1). That justification is worth
**at most 95 B of sub-ROM**, it is claimed by **zero** real candidates, and it is
**structurally unreachable** — measured, not argued.

**The move still has a customer, and it is a different one: CAPACITY.** §2.3. The
sub-ROM walls have a history, and the history says page 0 has been frozen since
the table filled while page 1 absorbed everything. That is the reading that
decides this slice, and it is the reading nobody had taken — the review compared
the two islands' free space **once**, at a single instant, and drew the wrong
conclusion from it.

⇒ **PROCEED**, on a premise the review did not state.

---

## 1. The instrument, and its own control

All figures from `rm -rf build && make basic-reloc` (`52b2386`), plus the shipped
gates. Sub-ROM free space = trailing `$FF` run per 16 KB page of `build/sub.rom`.

| | value |
|---|---|
| main low `$2812-$3FFF` free | **23 B** (`__MEAS_LOW_END` `$3FE9`) |
| main page 1 `$4000-$7FFF` free | **356 B** (`__MEAS_PAGE1_END` `$7E9C`) |
| sub page 0 / page 1 trailing `$FF` | **3913 B** / **2324 B** |
| closure walks | abi **122**+4 · `--page0` **718**+15 · `--page1` **522**+41 |
| dead-code sweep | main **1551** spans / **285** seeds → 0 · sub **1451** / **102** → 0 (+1 allowlisted) |
| `sub_p0_table` / `sub_p0_ping` / `sub_int_selftest` | `$0010` / `$003B` / `$0041` |

**The instrument's own control.** The free-space reader is a trailing-`$FF` scan,
so it is worth knowing it agrees with figures filed by other authors before
believing a trend built on it. Two independent checks, both **exact**:

| filed elsewhere | commit | my reading |
|---|---|---|
| review §6: "sub page 0 has **4054 B** free vs page 1's **3357 B**" | `2aee774` | **4054 / 3357** ✅ |
| [[evlno-slice]]: "sub page 1 **2411 → 2324**" | `638a141 → 52b2386` | **2411 → 2324** ✅ |

### 1.1 🔴 The filed justification was wrong in two places, and this is the FIFTH slice running

[[filed-justification-is-a-claim]] — checked before building on it, as required.

| filed claim | where | measured |
|---|---|---|
| *"Free space starts at `$003B`"* | the item as handed to this slice | 🔴 **FALSE.** `$003B..$0040` is `sub_p0_ping` (6 B: `3E C0 32 05 F1 C9`), `$0041` is `sub_int_selftest`. There is **no** free space below the page-0 body region; free space is the trailing run at the far end of the page. Picking a new base "in the gap after the vector" would have overwritten the PING — the one tenant every boot gate calls. |
| *"Every call site computes `IX = BASE + 3*index` **symbolically**, so the change is mechanical"* | `TODO.md:2147`, [[capacity-wall-is-not-the-free-byte-count]], review §6 | 🟠 **TRUE of `basic/*.asm` (18 sites, all symbolic) and FALSE of the harness.** Three probes carry the entry address as a **hardcoded byte** inside an injected machine-code array — §3.2. The claim was made about the ROM and repeated as if it were about the change. |

The second one is the shape the task itself predicted ("a hardcoded address in a
probe is exactly the shape that would ship green and break later") — and it is
worse than a comment: `0xDD, 0x21, 0x28, 0x00` is *executed*, not read.

---

## 2. The customer question, measured

### 2.1 The visibility justification: 268 legal candidates, and none of them wants it

A candidate is a **customer** for this move iff it is **page-0-legal** (its
closure never touches the BIOS or the main low region, both absent from page 0)
and **not page-1-legal** (it must call main page 1, absent from page 1). Swept at
label granularity — the granularity D-EVLNO actually evicted at — reusing the
**shipped** closure passes (`build_callgraph` + `build_datagraph` +
`data_targets`, with `carve_scout`'s exact semantics: a data edge marks its
target and does not propagate control flow).

| | measured |
|---|---|
| main page-1 labels (denominator) | **1045** |
| **page-0-legal** (whole closure stays ≥ `$4000`) | **268** |
| of those, with a non-zero page-1 clone cost | **101** |
| **largest clone page-0 siting would avoid, across all 268** | **95 B** (`psv_env`) |
| largest for a candidate that is not a loop label of its own body | **54 B** (`var_name_key`: `deftbl_lookup` 16, `is_letter` 15, `is_ident_cont` 14, `upcase` 9) — and it has **28** external callers, so it is not a tenant |

At file granularity the customer count is **0 of 32** files with page-1 content.

### 2.2 🔴 And the clone is paid on the wrong wall — the main-ROM saving is IDENTICAL on both islands

The review's §6 sentence chains "a page-1 tenant may only call the low region"
to "which is what forces the §3.1 duplication", and §3.1 heads its column
**"Main-ROM cost"**. Follow the bytes:

* evict cluster *C* from main page 1. Its **shared** members (callers outside *C*)
  stay resident in main **on either island** — that is what "shared" means.
* **page-1 siting**: main loses `|private|` − stub. Sub gains `private` + `clone(shared)`.
* **page-0 siting**: main loses `|private|` − stub. Sub gains `private`, and calls
  `shared` in place.

⇒ **The clone is a SUB-ROM cost. The main-ROM saving is the same number both
ways.** §3.1's 473 B table measures the main-side bytes of eight shared body
`.inc` files, which is the (closed) question of whether main's own copies can be
deleted; it is not the price of siting a tenant on page 1.

So the review's rule is justified by ≤ 95 B spent on **sub-ROM** space, of which
there is **6237 B** free. On its stated grounds the rule does not earn its
keep.

**Why the 95 B ceiling is structural, not an accident of today's tree.** 777 of
the 1045 page-1 labels are page-0-**illegal**, and every one of the 268 legal ones
is a leaf. Tenants are leaves by construction; a leaf calls small helpers, and a
small helper clones for 9–51 B. A *non*-leaf tenant is exactly the thing that
would want to call main page 1 — and reaching into main page 1 reaches `eval` →
the float pack (low region) or `pchar` → `CHPUT` (BIOS) and becomes page-0-illegal
in the same step. D-EVLNO said this in prose about its own tier ("every
statement-shaped entry reaches `eval`; every printing path reaches `pchar`"); this
is the same fact measured over the whole region.

### 2.3 🎯 The real customer: which sub wall binds is a HISTORY question

[[which-wall-binds-is-a-history-question]] — D-PINDATA's lesson, applied to the
**sub** walls, which nobody had done. `build/sub.rom` rebuilt from clean at 31
commits (worktree at each; trailing-`$FF` per page):

| commit | date | sub p0 free | sub p1 free | |
|---|---|---|---|---|
| `6c72931` | 07-29 | 4264 | 3497 | **the 13th page-0 row lands** (`fld_lookup`) — table FULL from here |
| `2aee774` | 07-30 | 4054 | 3357 | the review is written HERE, on this single instant |
| `224d03f` | 07-31 | 4078 | 3339 | |
| `cffa9e5` | 08-01 | 4024 | 3339 | |
| `6efafed` | 08-01 | 3910 | 3339 | |
| `3a25449` | 08-02 | **3913** | 3339 | |
| `406b9e3` | 08-02 | **3913** | 3145 | |
| `4d43294` | 08-02 | **3913** | 3067 | |
| `902d14d` | 08-02 | **3913** | 2740 | D-MSGSUB |
| `40647bd` | 08-02 | **3913** | 2428 | D-MSGMIGRATE |
| `638a141` | 08-02 | **3913** | 2411 | |
| `b4f5f54` | 08-03 | **3913** | 2411 | |
| `52b2386` | 08-05 | **3913** | **2324** | D-EVLNO |

Read it:

* the page-0 table has been **full for 32 commits / 7 days**, since `6c72931`
  (verified structurally: 13 `jp` rows at `6c72931`, 12 at `6c72931^`);
* since it filled, sub page 0 has moved **only** through existing tenants growing,
  and has been **frozen at 3913 B for the last 9 commits** — by construction, since
  a new tenant needs a row;
* over the same 9 commits sub page 1 absorbed **1015 B** (3339 → 2324);
* **page 0 now holds 63 % of the sub-ROM's free space and can accept no new
  tenant.**

One displacement is already documented in the tree rather than inferred:
`sub/equates.inc:159-162` records that `parseln_tenant` (D-EVLNO, 87 B) is on page
1 *"for a reason unlike every tenant above it: the body calls NOTHING AT ALL … the
tie is broken by capacity, the page-0 table being full"*. That is the customer,
observed once and about to recur.

⇒ The review compared the two islands' free space **at one instant** and concluded
"page 0 is the roomier island, so prefer it". The trend says something stronger
and different: **page 0 is roomier because it is CLOSED.**

### 2.4 The counterweight, so the decision is not one-sided

* sub page 1 has **no** matching wall: its table is 24 rows `$4010..$4077`, the
  next byte is `sub_p1_ping`, and there is no fixed vector above it. Page 1 can
  keep taking rows indefinitely.
* at 2324 B free and ~113 B/commit over the last 9 commits, page 1 is not about to
  fail. This is not an emergency.
* the move costs sub page-0 bytes (§3.1) and touches an ABI.

The decision rests on cost: §3.1 prices it at **44 B of the non-binding wall** for
three `equ`/assert edits and three probe constants. 44 B to restore access to
3913 B is the trade, and it is the reason this is a BUILD and not a DECLINE.

---

## 3. Design

### 3.1 What changes

**`SUBROM_ENTRY_BASE_P0` `$0010` → `$0040`.** Chosen deliberately:

* **past the fixed `$0038..$003A` vector** — the whole point;
* a **round number**: `$0040 + 3*idx` is checkable by hand (idx 8 → `$0058`,
  idx 12 → `$0064`), where `$003B + 3*idx` is not. `$003B` would also save only
  5 B;
* it leaves `$0010..$003F` as inert `$FF`, so the RST slots `$10/$18/$20/$28/$30`
  land on pad instead of **mid-instruction inside a table row**, which is where
  they land today;
* `BASE + 3*idx` stays below `$0100` up to index 63, so the `ld ix,` high byte
  stays `$00` and no stub grows.

Four source sites:

1. `sub/equates.inc:14` — the definition.
2. `basic/sysvars.inc:3622` — the `IFNDEF` mirror. ⚠️ `sub.asm` includes
   `equates.inc` first, so the sub build takes that one and the main build takes
   this one. **Nothing cross-checks them** — see K1.
3. `sub/sub.asm` — the table moves below the `$0038` vector; the existing
   `IF $ - SUBROM_ENTRY_BASE_P0` drift assert moves with it, and its error label
   `SUB_P0_TABLE_NOT_AT_0010__HEADER_SIZE_DRIFT` is renamed (it names the old
   address). The `IF $ > $0038` overrun assert stays where it is, now guarding
   only the header.
4. **NEW assert** — `IF SUBROM_ENTRY_BASE_P0 <= $003A` → error. Today nothing
   stops the base being set below the vector; after this move that is the only
   way to re-break it. K3.

### 3.2 🔴 The three probes that carry the address as a BYTE

These are call sites the filed justification did not count. Each injects Z80
machine code as a Python byte list:

| probe | gate | line | today | after |
|---|---|---|---|---|
| `probes/basic/basic_probe_subrom_boot.py:73` | `subrom-acceptance` | `0xDD,0x21,0x10,0x00` | `ld ix,$0010` (index 0, PING) | `0x40` |
| `probes/basic/basic_probe_subrom_inttest.py:71` | `subrom-inttest` | `0xDD,0x21,0x19,0x00` | `ld ix,$0019` (index 3) | `0x49` |
| `probes/basic/basic_probe_graphics_floor.py:76` | `graphics-acceptance` | `0xDD,0x21,0x28,0x00` | `ld ix,$0028` (index 8) | `0x58` |

Their surrounding comments and docstrings carry the arithmetic too, and
`basic/graphics.asm:73` and `sub/equates.inc:184` both spell "= `$0028`".

⚠️ **Not fixed here, filed:** the constants stay hardcoded. Deriving them from
`sub/equates.inc` is a real improvement and a different change — these probes
inject raw bytes into a bare machine precisely so they depend on nothing, and
giving them a source-parsing dependency needs its own falsification. Recorded in
`TODO.md`. What this slice does add is that **all three are in the corpus**, so
the next base move reddens them rather than shipping past them.

`tests/msxtest.py`'s sub-ROM bridge routes on `cpu.ix < 0x4000`, **not** on the
base, so it is immune; only its docstring's "`$0010+`" is stale prose (corrected).
`tools/check_tenant_closure.py` keys its page-0 seeds off the `sub_p0_table:`
**label**, not an address — also immune.

### 3.3 What does NOT change

* every `SUBROM_IDX_*` value — this is a **base** move, not a renumber. No tenant
  changes index, no stub changes its index constant.
* the `$0038` vector: `jp SUB_INT_RAM`, same three bytes at the same address.
* the page-1 table, its base, and all 24 rows.
* main-ROM size and layout: 18 `ld ix,nn` immediates change value, not length.

### 3.4 Predicted layout

| | before | after |
|---|---|---|
| `$0010..$0036` | table, 13 rows | `$FF` pad |
| `$0037` | `$FF` | `$FF` pad |
| `$0038..$003A` | `C3 0A F1` | **unchanged** |
| `$003B..$003F` | `sub_p0_ping` (6 B) | `$FF` pad (5 B) |
| `$0040..$0066` | body | **table, 13 rows** |
| `$0067..$006C` | body | `sub_p0_ping` |
| `$006D` | body | `sub_int_selftest` |

Every page-0 body shifts **+`$2C` = +44 B**.

---

## 4. Predicted GREEN — fixed before the change

| id | prediction, exact |
|---|---|
| **G1** | main walls **unchanged**: low **23 B** (`__MEAS_LOW_END $3FE9`), page 1 **356 B** (`__MEAS_PAGE1_END $7E9C`) |
| **G2** | `build/sub.rom` page 0 trailing `$FF` **3913 → 3869** (−44); page 1 **2324 B unchanged** |
| **G3** | `build/sub.rom[$4000:$8000]` **byte-identical** to baseline — nothing on page 1 depends on the page-0 base |
| **G4** | `build/basic-reloc.rom` differs in **exactly 18 bytes**, one per `ld ix,SUBROM_ENTRY_BASE_P0` site, each the **low** byte of the immediate and each **old + `$30`**. No high byte moves, no other byte moves |
| **G5** | symbols: `sub_p0_table` `$0010 → $0040`; `sub_p0_ping` `$003B → $0067`; `sub_int_selftest` `$0041 → $006D`; `tokenise` `$03F6 → $0422`; **every** page-0 label +`$2C`, **every** page-1 label unchanged |
| **G6** | page-0 **relocation-aware diff**: every differing byte in `sub.rom[$0000:$4000]` is explained as (a) the `$0010..$0066` table/pad relayout, or (b) a 16-bit operand whose old value is in the shifted range and whose new value is old + `$2C`. Zero unexplained bytes. This is the [[verbatim-move-proved-by-bytes]] row in the only form a shifted move admits — stronger than byte-identity, because it checks the relocation arithmetic |
| **G7** | closure walks **unchanged**: abi **122**+4 · `--page0` **718**+15 (same 13 named seeds) · `--page1` **522**+41 |
| **G8** | dead-code sweep **unchanged**: main **1551** spans / **285** seeds → 0 · sub **1451** / **102** → 0 (+1 allowlisted). ⚠️ Predicted at the seed level deliberately: `external_names` scans `sub/` **including comments**, so any asm label named in this slice's new prose moves it ([[evlno-slice]] G5). A move here is a finding about my own text |
| **G9** | corpus green: unit **58** · `subrom-acceptance` PING `$C0`/`$C1` · `subrom-inttest` delta ≥ 1 · `graphics-acceptance` PASS · `lnblank-acceptance REPEAT=2` **536/536** · `linemax` **60/60** · `latch-check` **16/16** · `dexp5-pin` **16/16** · `injector-check` ALL PASS · `preflight-check` OK · `probe` ALL PASS · `diskbasic-acceptance` **34/34** · `lof-acceptance` (full log captured) |

---

## 5. Predicted RED — the knives

Every red row paired with a green control, and before believing a knife: check it
**CUT**, and that the fault reproduced in that same run.

### 5.1 K1 — the two mirrors, and the fact that nothing cross-checks them

| id | instrument | prediction |
|---|---|---|
| **K1a** | move `sub/equates.inc` to `$0040`, leave `basic/sysvars.inc` at `$0010` | **both builds SUCCEED** (no gate compares them). Sub table at `$0040`; main stubs dispatch to `$0010` = `$FF` pad. `make unit-test` **RED** — the first tokenise through the main stub runs pad |
| **K1b** | the mirror image: `basic/sysvars.inc` `$0040`, `sub/equates.inc` `$0010` | **RED** the same way, from the other side |
| **K1c** | K1a's tree, `make subrom-acceptance` | ⚠️ predicted **GREEN** — the boot probe CALSLTs the hardcoded `$0040` directly and never goes through a main stub. The gate most obviously "on the changed ABI" is **blind to this defect**; `unit-test` is the one that catches it. Recorded as a prediction so it cannot be read as coverage after the fact |
| **K1d** | both mirrors moved (the shipped change) | **GREEN** — the control that stops K1a/K1b being "any edit reddens unit-test" |

### 5.2 K2 — K2-shaped: keep the emission and the call site, gut only the judgement

| id | instrument | prediction |
|---|---|---|
| **K2a** | insert a real header drift (`db 0` before `sub_p0_table:`) with the relocated assert intact | **build FAILS**, undefined symbol naming the drift label |
| **K2b** | same drift, but the assert's condition replaced by `IF 0` — the directive, its error `db` and its comment all still present at the same call site | **build SUCCEEDS, exit 0**, and ships a table off by one byte. Coverage survives, efficacy dies — [[coverage-gate-cannot-see-a-gutted-guard]] |
| **K2c** | no drift, assert intact | **build SUCCEEDS** — the green control |

### 5.3 K3 — the new guard, and proof it was absent

| id | instrument | prediction |
|---|---|---|
| **K3a** | set the base to `$0037` **with the new `<= $003A` assert removed** | **build SUCCEEDS** and silently ships a row 0 at `$0037..$0039` overwriting the IM1 vector — i.e. the hazard has no guard today |
| **K3b** | same base, **with** the new assert | **build FAILS**, naming the vector-collision label |
| **K3c** | base `$0040`, assert present | **SUCCEEDS** — the green control |

### 5.4 K4 — the probes are on the changed ABI, not decoration

| id | instrument | prediction |
|---|---|---|
| **K4a** | after the move, revert `basic_probe_graphics_floor.py` byte to `0x28` | `graphics-acceptance` **RED** |
| **K4b** | after the move, revert `basic_probe_subrom_inttest.py` byte to `0x19` | `subrom-inttest` **RED** (delta 0 — the CALSLT lands on pad) |
| **K4c** | after the move, revert `basic_probe_subrom_boot.py` byte to `0x10` | `subrom-acceptance` **RED** (`SUB_PING` never stamped `$C0`) |
| **K4d** | all three at their new values | **GREEN** — the control |

### 5.5 Stated coverage limit, before running

The customer sweep (§2.1) inherits `build_datagraph`'s documented limit: a symbol
imported by `equ` is a value, not a location, so a data reference to BIOS ROM data
is unclassifiable. It therefore **under**-reports page-0 escapes, i.e. it
over-reports the customer set — which is the safe direction for a slice that
concludes "no customer on those grounds".

---

## 6. As-built — ✅ LANDED 2026-08-05

`SUBROM_ENTRY_BASE_P0` is **`$0040`**. Page 0 takes tenants again; **index 13 is
free and the table has no cap.**

### 6.1 GREEN, scored

| id | result |
|---|---|
| G1 | ✅ **exact.** low **23 B** (`__MEAS_LOW_END $3FE9`), page 1 **356 B** (`__MEAS_PAGE1_END $7E9C`) — both unchanged |
| G2 | ✅ **exact.** sub page 0 **3913 → 3869** (−44); page 1 **2324 B** unchanged |
| G3 | ✅ `sub.rom[$4000:$8000]` **byte-identical** |
| G4 | ✅ **exact.** `basic-reloc.rom` differs in **exactly 18 bytes**, every one the low byte of a `DD 21 xx 00` immediate, every delta **+`$30`**, no high byte moved |
| G5 | ✅ **exact.** `sub_p0_table` `$0010→$0040`, `sub_p0_ping` `$003B→$0067`, `sub_int_selftest` `$0041→$006D`, `tokenise` `$03F6→$0422`; **735** page-0 label definitions shifted **+`$2C`**, 0 page-1 labels moved, 0 symbols added or removed. (Two apparent anomalies, both predicted: `sub_p0_table` itself moves +`$30` because it *is* the table, and 11 labels sit at delta 0 — they are the resident-ABI imports `fp_add`/`vars_reset`/… , main low-region addresses brought in by `equ`.) |
| G6 | ✅ **0 unexplained bytes.** 699 raw mismatches inside the shifted body, **1196 bytes** all explained as 16-bit operands relocated by exactly +`$2C`; the `$0038` vector byte-identical (`C3 0A F1`); all 13 rows `jp`, all relocated +`$2C`; `$0010..$0037` and `$003B..$003F` all `$FF` |
| G7 | ✅ **exact.** abi **122**+4 · `--page0` **718**+15 (same 13 seeds) · `--page1` **522**+41 |
| G8 | ✅ **exact.** main **1551**/**285** → 0 · sub **1451**/**102** → 0 (+1 allowlisted). My prose moved no seed |
| G9 | ✅ unit **58/58** · `subrom-acceptance` PASS · `subrom-inttest` PASS (delta 28) · `graphics-acceptance` PASS · `graphics-floor-acceptance` PASS · `lnblank REPEAT=2` **536/536** · `linemax` **60/60** · `latch-check` **16/16** · `dexp5-pin` **16/16** · `injector-check` ALL PASS · `preflight-check` ALL PASS · `probe` OK · `diskbasic` **34/34** · `lof` **45 cases, 0 oracle drift, 0 mangled** (full 59-line log captured — **sighting 3 did NOT occur**) |

### 6.2 RED, and what each knife actually found

| id | result |
|---|---|
| K1a | ✅ **exact, and the prediction was the point.** `make basic-reloc` **rc 0** — *nothing cross-checks the two `equ` mirrors* — and `unit-test` **13/58 files RED** |
| K1c | ✅ **exact.** `subrom-acceptance` — the gate nominated as "most directly on the changed ABI" — **PASSED** on that tree. It CALSLTs the entry address directly and never goes through a main-ROM stub, so it is structurally blind to a mirror mismatch. `unit-test` is the gate that catches it |
| K1d | ✅ green control |
| K2 | 🔴 **found a defect in my own fix** — see §6.3 |
| K3a/b/c | ✅ base `$0037` with the new assert removed still fails, but on the *drift* assert, naming the wrong cause; with the assert it fails naming `SUB_P0_BASE_BELOW_0038_VECTOR__TABLE_WOULD_CLOBBER_IT`; `$0040` builds. The new assert's value is the **correct diagnosis**, not the catch |
| K4a | 🔴 **the knife did not CUT on the first attempt** — see §6.4 |
| K4b | 🔴 **found a live false-negative in a shipped gate** — see §6.5 |
| K4c | ✅ **exact.** boot probe reverted to `$0010` → `SUB_PING = $39` (expect `$C0`), **FAIL** |

### 6.3 🔴 K2: the pad I added made the pre-existing drift assert VACUOUS, and pasmo hides the failure

The old assert was `IF $ - SUBROM_ENTRY_BASE_P0` — an **equality** test, load-bearing
because the table began immediately after the header, so `$` was either exactly the
base or wrong. My first design put a `ds SUBROM_ENTRY_BASE_P0 - $, $FF` pad in front
of it. **A pad FORCES `$` to the base**, so the equality is true by construction:
[[gate-can-be-green-while-measuring-nothing]], introduced by the fix itself.

I only found it because the first K2 knife came back **green** and I checked why
instead of moving on. The knife was aimed wrong (it drifted the table *after* the
assert); re-aiming it found the assert could not fire at all.

**And the failure it was supposed to catch is silent.** Measured directly:

> `pasmo` answers a **negative `ds` count** with a *WARNING* and **exit 0**,
> writing a **zero-byte** output file.

`tools/pad_rom.py` then padded that to a legitimate-looking 32 KB image of `$00`,
and **the entire `make basic-reloc` gate chain passed it at rc 0** — the relocation
check, all three closure walks, the resident-ABI check and the dead-code sweep, none
of which read `sub.rom`'s content. The one gate that *does* read it,
`check_kwtable_identity`, printed:

```
OK: kwtable single-copy — resident dropped (wave 3), sub-ROM copy is the sole source (1 B)
```

**1 B**, against 1041 B on a healthy tree — its own denominator collapsing by three
orders of magnitude, reported and not judged ([[traps-t4-sprite-slice]]: a gate's
DENOMINATOR must be measured).

Fixed two ways, each falsified:

1. the assert is now **`IF $ > SUBROM_ENTRY_BASE_P0`**, which still judges with a pad
   in front of it. K2a (header grown past `$0038`) → **rc 2**; K2a′ (bytes inserted
   between the vector and the table) → **rc 2**; K2b (same tree, judgement replaced
   by `IF 0`) → **rc 0 and a 32 KB all-`$00` ROM**; K2c (clean) → rc 0.
2. `tools/pad_rom.py` now **refuses an empty input** instead of padding it. On the
   K2b tree the build then fails at rc 2 with `EMPTY -- the assembler wrote no
   bytes`; on the shipped tree it prints its normal `32768 bytes`.

The broader hole — a *partially* truncated ROM, and `check_kwtable_identity`'s
unbounded denominator — is **not** fixed here and is filed in `TODO.md`.

### 6.4 🔴 K4a: the knife did not cut, and that exposed a gap in the handed-over corpus

Knifing `basic_probe_graphics_floor.py`'s address and running
**`graphics-acceptance`** — the gate the task's corpus named for the graphics
tenant — came back **PASS**. Before believing a green knife, check it CUT
([[err21-no-resume-slice]] F6): it had not. `graphics-acceptance` runs
`basic_probe_graphics.py`, which reaches the tenant through the main-ROM stub and
its **symbolic** `ld ix`. The probe with the hardcoded address is run by a
different target, **`graphics-floor-acceptance`**, which was not in the corpus.

Re-aimed: `graphics-floor-acceptance` with `$0028` → **rc 2**, `read-back
mismatches = 255`; with `$0058` → **PASS**. ⇒ **`graphics-floor-acceptance` is
now part of this ABI's corpus.** Without the knife, a broken hardcoded address
would have shipped scored by nothing I ran.

### 6.5 🔴 K4b: `subrom-inttest` passed with its CALSLT pointed at PAD

Reverting the inttest probe to `$0019` (now `$FF` pad) produced
`JIFFY delta = 255 ticks` and **PASS, rc 0**. The gate's whole assertion was
`delta >= 1`, and its docstring stated the claim outright:

> *"There is no storm-or-hang path that still reports delta >= 1, so this single
> assertion is the whole proof."*

**Sixth filed justification checked in this arc, sixth one wrong.** Executing pad is
`rst 38h` over and over; the timer keeps ticking while the tenant never runs, so a
one-sided bound cannot separate "the trampoline serviced the interrupt" from "the
CPU spent that time somewhere else entirely".

The tenant's spin is **fixed-length**, so the delta cannot legitimately be large.
Measured **28, 28, 28** on three consecutive runs. `DELTA_MAX = 64` (>2× measured,
room for 50 Hz ≈ 23 vs 60 Hz ≈ 28). Falsified both ways: the `$0019` tree now
**FAILs** with `delta = 255 … TOO LARGE`, naming the cause and the remedy
([[apparatus-is-part-of-the-measurement]]: name the CAUSE in the failure text); the
shipped tree **PASSes** at `delta = 28`.

### 6.6 What this slice did NOT do

* the three probe entry addresses stay **hardcoded**. Deriving them from
  `sub/equates.inc` is a real improvement and a different change — they inject raw
  bytes into a bare machine precisely so they depend on nothing. Filed.
* `SUBROM_IDX_PARSELN` (D-EVLNO) is **left on page 1** although it is the one
  recorded tenant displaced by the cap. An index is an ABI; renumbering it to
  "recover" the siting would cost more than it buys and break the append-only rule.
* `check_kwtable_identity`'s unbounded denominator, and truncated-ROM laundering
  generally. Filed.
