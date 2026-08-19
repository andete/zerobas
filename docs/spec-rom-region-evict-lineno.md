# D-EVLNO — rank 4 opened: one per-file eviction, costed by building it; and the page-0 island is FULL

Filed against `a191119` (tree clean, all gates green). Opens rank **4** of
[`rom-region-structure-review.md`](rom-region-structure-review.md) §7 — the last
unopened part of the ROM REGION STRUCTURE REVIEW entry in [`TODO.md`](../TODO.md).

The filed item:

> evict a page-1 file to a sub **page-0** tenant — frees (body − stub), 12–42 B
> stub, "open, not costed per-file". **Prefer page 0**: a page-0 tenant may call
> main page 1, which is exactly what page-1 tenants cannot do and why they force
> the 457 B of duplication.

§7's own instruction is that this tier is opened **one candidate at a time, costed
by BUILDING it** — because every eviction in the arc's history was dominated by
*siting, not substance* (D-FCH S-FCH-1: 43 → 9 → 5 B for the same fix).

**Three results.** (1) 🔴 The **sub page-0 entry table is FULL** — 13 rows,
`$0010..$0036`, **one spare byte** before the fixed `$0038` vector. No new page-0
tenant fits, so the review's "prefer page 0" costing rule is not merely a
preference today, it is *unavailable* without relocating `SUBROM_ENTRY_BASE_P0`.
The fact is recorded in `sub/sub.asm` and `sub/equates.inc` (and re-measured here,
because filed claims are claims); **what is new is that the review's own rank-4
recommendation contradicts it**, and nothing connected the two. (2) 🔴 `carve_scout.py` — the third sibling of the
two tools D-PINDATA fixed — had the **same data-reference blind spot**, and it
graded a live candidate `page-0-tenant CLEAN` while that candidate does
`ld hl,htimi_guard`. Fixed and falsified both ways. (3) The candidate itself,
`parse_lineno`, is evicted and the tier is **costed for the first time**:
**73 B body, 18 B stub, 55 B net** at the wall that binds.

---

## 1. The instrument, and its own control

All wall figures are from a **cold tree** (`rm -rf build && make basic-reloc`),
per [[measure-the-wall-from-clean]]. Byte spans come from `build/basic-reloc.sym`
label-to-label distance — the same accounting `make basic-reloc` reports the wall
in, so a span and a wall movement are commensurable and the build checks the
arithmetic.

⚠️ **The instrument's control is that the numbers close.** A predicted body of
73 B and a predicted stub of 18 B must show up as **exactly 55 B** of wall
movement; a mismatch means the span model is wrong, not that the estimate was
"close". §4 G2 is that row.

Baseline, cold, at `a191119`:

| | value |
|---|---|
| main low `$2812-$3FFF` free | **23 B** |
| main page 1 `$4000-$7FFF` free | **301 B** (`__MEAS_PAGE1_END` `$7ED3`) |
| `build/basic-reloc.rom` | `057d6a4f5363…` |
| `build/sub.rom` | `5aef318139a8…` |
| sub page 0 / page 1 trailing `$FF` | **3913 B** / **2411 B** |
| closure walks | abi **122**+4 · `--page0` **718**+15 · `--page1` **515**+41 |
| dead-code sweep | main **1556** spans / **284** seeds → 0 · sub **1443** / **100** → 0 (+1 allowlisted) |

---

## 2. What was measured before designing

### 2.1 🔴 The scout that decides what to ATTEMPT was blind, again

[`tools/carve_scout.py`](../tools/carve_scout.py) imports `build_callgraph` from
`check_tenant_closure` and nothing else. D-PINDATA
([spec §2.3](spec-rom-region-promote-input.md)) found and fixed exactly that
blindness in `check_tenant_closure.py` (the SHIP gate) and `promote_scout.py`
(the promotion scout); `carve_scout.py` — **the scout for this tier** — was not
audited then.

It is not a theoretical hole. Measured on the unmodified tree:

```
$ python3 tools/carve_scout.py build/basic-reloc.sym --entries play_install,play_service
    closure 11 labels; 0 absent-region callees (0 of them BIOS)
    VERDICT: page-0-tenant CLEAN
```

[`basic/playsvc.asm:59`](../basic/playsvc.asm:59) is `ld hl,htimi_guard`, and
`htimi_guard` is at **`$3C7E`** — the main low region, switched out under a page-0
call. Same *shape* as the `ld hl,zkey_hook` reference that made the review build
a data-aware closure in the first place (§0.1 error 3), a different instance, in
the one tool that never got the fix. **A green grade that lies, for the second
time in this tool** ([[carve-scout-before-proposing]] point 5).

### 2.2 🔴 The page-0 entry table has ONE SPARE BYTE

[`sub/sub.asm:124`](../sub/sub.asm:124)'s own comment says so; **filed claims are
claims** ([[filed-justification-is-a-claim]] — five slices, five wrong), so it was
re-measured from `build/sub.rom` and `build/sub.sym`:

| | measured |
|---|---|
| page-0 table | 13 rows, `$0010`..`$0036` |
| `$0037` | `FF` — the one spare byte |
| `$0038` | `C3 0A F1` = `jp SUB_INT_RAM`, the fixed IM1 vector |
| a 14th row | would end at **`$0039`**, overwriting the vector |
| page-1 table | 23 rows, `$4010`..`$4054`; next index **23** |

**The comment is right.** So rank 4's "prefer page 0" is, today, not a preference
between two open options — page 0 is closed. Opening it means relocating
`SUBROM_ENTRY_BASE_P0` past `$0038` (both `equ` sites, `basic/sysvars.inc` and
`sub/equates.inc`, plus the `IF $ - SUBROM_ENTRY_BASE_P0` header assert). That is
cheap and mechanical, but it is an **ABI move** and it is not this slice's scope.
Filed in `TODO.md`.

### 2.3 The candidate landscape, scouted before anything was named

`carve_scout --files X --census` over every `basic/*.asm`, then a per-label
closure sweep (each page-1 label's own transitive closure under the *fixed*
control+data model) grouped into call-connected clusters, each cluster's external
entry points counted. What survives is thin, and the reason is structural:

**almost every statement-shaped entry reaches `eval` → the float pack, and every
printing path reaches `pchar` → `CHPUT`.** 172 of 209 `do_*`/`ex_*`/`ev_*` entries
already sat at 298–299 escapes when D-CLP measured it; the count today is ~310.

Clusters ≥ 50 B whose whole closure is page-0/page-1 legal:

| body | entries | where | verdict |
|---|---|---|---|
| **217 B** | 1 (`play_service`) | `playsvc.asm` | 🔴 **REJECTED — H.TIMI.** The per-VBLANK PLAY servicer. A CALSLT inside the VBLANK handler, and circular besides: a page-0 tenant runs with the `$0038` ISR paged out. Already filed: [`sub/beep.asm`](../sub/beep.asm)'s header rejected `psv_fetch`/`psv_env` for this exact reason. My rejection is a **confirmation**, not a finding. |
| **193 B** | 9 | `fat.asm`+`field.asm` | rejected: 9 stubs, and its closure reaches `fatprim_bounce` → a **page-1** tenant. A page-0 tenant cannot call sub page 1. |
| **81 B** | 1 (`parse_lineno`) | `program.asm` | ✅ **the candidate** |
| 78 B | 2 (`trap_return_check`, `ztrap_entry` 9 callers) | `traps.asm` | rejected: T4/T5 measure handler cost in **jiffies**, and `ztrap_entry` costs 9 stubs |
| 74 B / 66 B / 64 B / … | 5–7 each | mixed | rejected on stub count |

⚠️ **My exploratory sweep treated `subrom_call` as non-propagating** (the scout's
own depth-1 "plumbing is re-expressible" rule, applied transitively). That rule is
**unsound when the plumbing call targets a tenant on the OTHER island**, which is
exactly what hid `fat.asm`'s `fatprim_bounce`. The shipped tool does **not** do
this — it only exempts plumbing at depth 1 and still counts everything beyond —
and the exploratory version was not shipped. Recorded because the next reader will
be tempted by the same shortcut.

### 2.4 The candidate, vetted with the FIXED tool

`parse_lineno` — [`basic/program.asm:274`](../basic/program.asm:274), the ASCII
line-number scanner `dl_store` calls once per typed/loaded numbered line.

```
$750F parse_lineno   3 B     $753D pl_blank    4 B
$7512 pl_lp         38 B     $7541 pl_bl_lp   17 B
$7538 pl_sat         5 B     $7552 pl_bl_end   6 B
```

**Contiguous, `$750F..$7558` = 73 B, 6 labels**, ending cleanly before `new_prog`.

```
$ python3 tools/carve_scout.py build/basic-reloc.sym --entries parse_lineno --equ-mentions
    closure 6 labels; 0 absent-region callees (0 of them BIOS); 0 absent-region DATA targets
    VERDICT: page-0-tenant CLEAN
    equ-mentions not classifiable by the label-only rule: 22 (0 with a value < $4000)
```

The last line is [[data-edge-pins-its-target-not-its-successors]]'s stated
coverage limit — an `equ` is a value, so a data reference to BIOS ROM data would
be unclassifiable — **checked empty for this candidate**, not waved past
([[exemption-as-a-checked-claim]]).

Why it is a good candidate on the axes that are not size:

* **One call site**, [`basic/program.asm:81`](../basic/program.asm:81). Live
  across it: `HL` in, `BC`+`HL` out. `DE` is dead (set two lines later), `A` is
  documented-clobbered, no `IX`/`IY`, no cursor.
* **Same cold path as an existing tenant.** `dl_store` calls `tokenise` — itself a
  page-0 tenant — five instructions later, and
  [`basic/interp.asm:110`](../basic/interp.asm:110) already argues the coldness:
  "line-entry / program-LOAD only, so a whole-line DI span is cosmetic".
* **The best-gated behaviour surface in the tree.** This routine *is* D-LNBLANK:
  `lnblank-acceptance` is **536 rows**, `lnblank-say-acceptance` another 204, and
  `linemax` 60 — all over the line-entry path.
* Pure register/RAM arithmetic over `LINEBUF`, which is page-3 RAM and stays
  mapped from either island.

### 2.5 🔴 Siting: page 1, and the review's own rule says so once it is measured

The item says **prefer page 0**, because a page-0 tenant may call main page 1.
`parse_lineno` **calls nothing at all** — it needs neither island's privilege. So
the preference has no force here, and §2.2 says page 0 has no room. **It is sited
on sub page 1, index 23.**

That is not a dodge of the item. The item's reason for preferring page 0 is a
statement about *what a tenant may call*; a closed leaf falsifies its premise
rather than evading it, and the *measurement* — page 0 is full — is the part a
future rank-4 candidate that genuinely needs main page 1 will be blocked by.

---

## 3. Design

### 3.1 What changes

1. **`sub/lineno.asm` (new)** — `parseln_tenant`, page-1 index 23. The scanner
   body moves **VERBATIM**, internal labels and all (`pl_lp`, `pl_sat`,
   `pl_blank`, `pl_bl_lp`, `pl_bl_end`), so the diff against
   `git show a191119:basic/program.asm` is a pure move. The single renamed label
   is the entry, `pln_scan`, so no name exists in both builds. An 11 B wrapper
   marshals the two results out:

   ```
   parseln_tenant: call pln_scan
                   ld (PLN_NUM),bc
                   ld (PLN_PTR),hl
                   ret
   ```

   Marshalling via RAM is the ABI, not caution: `subrom_call` passes `HL`/`DE`
   **in**, and results ride in RAM — `fatprim_bounce` reloads
   `ld hl,(DISKOP_HL)` / `ld a,(DISKOP_A)` for exactly this reason.

2. **`basic/program.asm`** — the 73 B body becomes an 18 B stub:

   ```
   parse_lineno:   ld ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_PARSELN
                   call subrom_call
                   jp c,subrom_absent_error
                   ld bc,(PLN_NUM)
                   ld hl,(PLN_PTR)
                   ret
   ```

   `dl_store`'s call site is **unchanged** — same label, same contract.

3. **`basic/sysvars.inc`** — `PLN_NUM` `$E234`, `PLN_PTR` `$E236`, inside the
   free `$E234..$E23F` window (§4 of the review); leaves `$E238..$E23F`.
4. **`sub/equates.inc` + `basic/sysvars.inc`** — `SUBROM_IDX_PARSELN equ 23`,
   the IFNDEF-guarded mirror pair.
5. **`sub/sub.asm`** — one `jp parseln_tenant` table row + one `include`.
6. **`Makefile`** — `sub/lineno.asm` added to `SUB_PARTS`
   ([[makefile-subparts-stale-tenant]]: a missing prerequisite silently ships a
   stale `sub.rom`).

### 3.2 What does NOT change

`dl_store`'s ceiling check, the D-LNBLANK blank rules, the `$FFFF` saturation
contract, the `pl_bl_end` zero-separator rule — none of it is touched. This is a
**relocation**, and every behavioural row in §5 exists to prove that.

### 3.3 Stated coverage limit, before running

The stub's absent-sub-ROM arm (`jp c,subrom_absent_error`) is **not reachable on
the merged machine**, which always ships the sub-ROM — the same limit every other
tenant stub carries. It is not gated here and this slice does not claim it is.

---

## 4. Predicted GREEN — fixed before the change

| id | prediction, exact |
|---|---|
| G1 | `make basic-reloc` exit 0; `--page1` walk **515 → 522** routines (+7: `parseln_tenant`, `pln_scan`, `pl_lp`, `pl_sat`, `pl_blank`, `pl_bl_lp`, `pl_bl_end`), **41** data-referenced, 0 escapes; abi **122**+4 and `--page0` **718**+15 **unchanged** |
| G2 | main page 1 free **301 → 356 B** (+73 body, −18 stub = **+55**); `__MEAS_PAGE1_END` `$7ED3 → $7E9C`; **low free stays 23 B** |
| G3 | sub page-1 trailing `$FF` **2411 → 2324 B** (−73 body, −11 wrapper, −3 table row = **−87**); sub page 0 **3913 B unchanged** |
| G4 | p1 table **23 → 24** rows, `$4010..$4057`; p0 table **untouched**, 13 rows, `$0037` still `FF` |
| G5 | dead-code: main **1556 → 1551** spans (5 internal labels leave; the stub keeps the name), **284** seeds, 0 dead; sub **1443 → 1450** spans, **100 → 101** seeds, 0 dead (+1 allowlisted) |
| G6 | `carve_scout --entries parse_lineno`: **CLEAN before AND after** the tool fix — the fix does not simply redden everything |
| G7 | `lnblank-acceptance REPEAT=2` **536/536**; `lnblank-say-acceptance` **204/204**; `linemax` **60/60**; unit **58**; the standing corpus green |

---

## 5. Predicted RED — the knives

### 5.1 K1 — the tool's blind spot, made a verdict

Already measured in §2.1 as the before-state.

| id | instrument | prediction |
|---|---|---|
| K1a | `carve_scout --entries play_install,play_service` **at `a191119`** | `page-0-tenant CLEAN`, 0 escapes ← the false negative |
| K1b | same, **after** | `CONDITIONAL — 1 data escape(s) …, NOT clean`, naming `htimi_guard @ $3C7E` |
| K1c | `carve_scout --entries parse_lineno` before/after | **CLEAN both** — the green control that stops K1b being a tool that reddens everything |
| K1d | three known-`NOT page-0-evictable` entry sets, before/after | **unchanged verdicts** — no direction flip, no flood |

### 5.2 K2 — an illegal tenant, and then the gate's judgement gutted

| id | instrument | prediction |
|---|---|---|
| K2a | add `call skip_spaces` (a **main page-1** routine) to `parseln_tenant`; run `check_tenant_closure --page1` | **exit 1**, naming `skip_spaces` as a main-BASIC page-1 escape. This is a real crash if shipped, not a style violation |
| K2b | on the K2a tree, keep the walk and its **printed count** and delete only the region test | **exit 0**, same `522 routines … + 41 data-referenced` line. Coverage survives, efficacy dies — [[coverage-gate-cannot-see-a-gutted-guard]] |

### 5.3 K3 — the behaviour knife, with its green control in the same run

Delete the one byte `ret z` at `pl_bl_end` in the **tenant** — the rule that a
zero-valued line number eats **no** separator blank.

| id | rows | prediction |
|---|---|---|
| K3-red | `body-z1` (`0 REMX`), `body-z0` (`00 REMX`), `body-z00` (`0 0 REMX`) | **RED** — the body loses its leading blank |
| K3-green | `body-zl` (`01 REMX`, value 1), `num-zero`, `num-plain`, `num-blank1`, `num-blank3` | **GREEN in the same run** |

K3's green half is what makes the red half mean something: a knife that reddens
the whole corpus proves the ROM booted, not that the corpus resolves this
routine. **A knife is only believed if it CUT and the fault reproduced in the same
run.** K3's discrimination is also the answer to "does the corpus see the code
under test at all" — the deletion-of-the-subject falsification
[[apparatus-is-part-of-the-measurement]] demands, done surgically so the answer
carries a row set instead of a boot failure.

---

## 5bis. What landed, and what it measured

Shipped: [`sub/lineno.asm`](../sub/lineno.asm) (new page-1 tenant, index 23),
[`basic/program.asm`](../basic/program.asm) (the 18 B stub),
`SUBROM_IDX_PARSELN` + `PLN_NUM`/`PLN_PTR`, one `sub_p1_table` row, one
`SUB_PARTS` prerequisite, and the data pass in
[`tools/carve_scout.py`](../tools/carve_scout.py).

### 5bis.1 GREEN, scored

| id | result |
|---|---|
| G1 | ✅ **exact.** `--page1` **522** routines / **41** data-referenced, 0 escapes; abi **122**+4 and `--page0` **718**+15 unchanged |
| G2 | ✅ **exact.** page 1 **301 → 356 B**, `__MEAS_PAGE1_END` **`$7ED3 → $7E9C`**, low **23 B** unchanged |
| G3 | ✅ **exact.** sub page 1 **2411 → 2324 B** (−87); sub page 0 **3913 B** unchanged |
| G4 | ✅ **exact.** p1 table **24** rows `$4010..$4057`; p0 untouched — 13 rows, `$0037` still `FF`, `$0038` still `C3 0A F1` |
| G5 | 🔴 **3 of 6 numbers wrong** — see below |
| G6 | ✅ `parse_lineno` grades `page-0-tenant CLEAN` **before and after** the tool fix |
| G7 | ✅ `lnblank-acceptance REPEAT=2` **536/536** (2:34) · `lnblank-say-acceptance` **204/204** (4:36) · `linemax` **60/60** · unit **58/58** |
| **G8** | ✅ **added after the fact, and it is the strongest row here:** the 73 B body at its new address `$76A3..$76EC` in `sub.rom` is **byte-identical** to `$750F..$7558` in `a191119`'s `basic-reloc.rom`. The move is provably verbatim, not verbatim-by-assertion |

🔴 **G5 was wrong three ways, and my own predictions were the claim being
tested** ([[filed-justification-is-a-claim]] — this time with me as the author,
for the second slice running). Measured: main **1551** spans ✅ / **285** seeds ✗
(predicted 284) · sub **1451** spans ✗ (predicted 1450) / **102** seeds ✗
(predicted 101). All three chased to ground rather than filed:

* **sub +8 spans, +2 seeds, not +7 and +1.** I counted the 7 labels and forgot
  that `check_dead_code` gives every *file* a `@prologue:` span, which is also a
  seed. A new file costs one of each before it contains anything.
* 🔴 **main +1 seed because of my own prose.** `external_names` scans `sub/` and
  `tools/` for identifiers *anywhere*, comments included. `sub/lineno.asm`'s
  header names `fatprim_bounce` and `trap_return_check` while explaining why
  those candidates were **rejected**, which seeds both; `pl_bl_end` (named in
  `sub/tkfloat.asm`) left the main build. 284 − 1 + 2 = 285, exactly. This is the
  hazard D-PINDATA filed against `tools/*.py` comments, and it is **wider than
  filed**: `sub/` counts too, and the trigger here was *documenting a rejection*.
  Nothing is masked (0 dead before and after) — see §7.

### 5bis.2 RED, scored

| id | result |
|---|---|
| K1a | ✅ `page-0-tenant CLEAN`, 0 escapes — the false negative, measured at `a191119` |
| K1b | ✅ `CONDITIONAL — 1 data escape(s) …, NOT clean`, naming `htimi_guard @ $3C7E` |
| K1c | ✅ `parse_lineno` CLEAN both sides — the fix does not redden everything |
| K1d | ✅ three `NOT page-0-evictable` sets unchanged — no flood, no direction flip |
| K2a | ✅ cut, exit 1 — **with the reason string wrong in my prediction**: `skip_spaces` has a **sub-local twin** at `$2BBB`, so the gate reports it as a *sub page-0* escape, not a main page-1 one. Fatal either way, named correctly |
| K2a′ | 🔴 **GREEN — see below** |
| K2b | ✅ exit 0, printing the identical `523 routines … + 41 data-referenced` line. Coverage survives, efficacy dies — [[coverage-gate-cannot-see-a-gutted-guard]] |
| K3 | ✅ cut **33/33 → 27/33** |

🔴 **K2a′ came back green, and the green is a coverage boundary worth writing
down.** `call new_prog` from `parseln_tenant` — a call straight into main page 1,
switched OUT while a page-1 tenant runs — and
`check_tenant_closure --page1` printed `OK … No main-page-1 escape`, **rc 0**.
The closure grew **522 → 523**, so the edge *was* walked; it was dropped at the
classification step, because the gate resolves addresses from `build/sub.sym` and
`new_prog` is a **main** label that does not exist there (`syms.get(n) is None →
continue`).

**It is not a hole, because the assembler is the gate for that case:**

```
ERROR: Symbol 'new_prog' is undefined  on line 56 of file lineno.asm
```

So the division of labour is — *a name that exists on both sides* is caught by
the closure walk (K2a), and *a main-only name* is caught by the build, loudly.
That is the same shape as the review's own §4.1 finding ("`disk_putword` … only
the assembler caught it"), arrived at from the other direction. It was nowhere
written down, and my prediction assumed the closure gate covered both.

**K3, scored row by row**, and my prediction was wrong on one row *in the safe
direction*:

| row | input | predicted | measured |
|---|---|---|---|
| `body-z1` | `0 REMX` | RED | ✅ RED |
| `body-z0` | `00 REMX` | RED | ✅ RED |
| `body-z00` | `0 0 REMX` | RED | ✅ RED |
| `num-zero` | `0 REMX` | **GREEN** | 🔴 **RED** |
| `body-z2`, `body-zx` | zero-valued | not named | RED |
| `body-zl` | `01 REMX` (value **1**) | GREEN | ✅ **GREEN** |
| `num-plain`, `num-blank1`, `num-blank3` | | GREEN | ✅ GREEN |

I predicted `num-zero` green on the reasoning that a `num-`-prefixed row checks
the line *number*, which K3 does not change. It does not: **every row in this
probe carries `line <n> | <body>`**, so a body-only fault reddens `num-` rows
too. The readout says so on its face and I read the prefix instead.

**The knife CUT and the fault reproduced in the same run**, and `body-zl` — the
value-1 half of the `00`/`01` discriminator — stayed green, which is what makes
the six reds mean "the corpus resolves this rule" rather than "the ROM changed".

---

## 6. Corpus

Sequential, never two emulator gates at once; `make repack-machine` after the ROM
change ([[stale-machine-reads-as-unimplemented]]); every wall read from a cold
tree.

`unit-test` **58/58** · `basic-reloc` (carries `deadcode` + all three closure
walks) · `preflight-check` **0 unguarded** · `injector-check` **ALL PASS** ·
`latch-check` **16/16** · `subrom-acceptance` PASS ·
`lnblank-acceptance REPEAT=2` **536/536** · `lnblank-say-acceptance` **204/204** ·
`linemax-acceptance` **60/60** · `dexp5-pin` **16/16** · `probe` OK ·
`diskbasic-acceptance` **34/34** · `error-trap-acceptance` ALL PASS ·
`kwsweep` (162-word denominator, unchanged) · `sysvarsweep` apparatus OK ·
`graphics-acceptance` PASS · `direct-ctrl-acceptance` **40/40** ·
`abort-acceptance` **49/49** · `error-acceptance` ALL PASS ·
`input-acceptance` ALL PASS · `string-acceptance` PASS ·
`float-acceptance` ALL PASS · `lof-acceptance` **45 cases, 0 oracle drift**
(standing flake watch — sighting 3 did **not** occur; full log captured this
time, per [[capture-a-flaky-gate-in-full]]).

**Blast radius, and why it is this wide.** Unlike D-PINDATA, this slice moves ROM
bytes: every main page-1 label above `$750F` shifts down 55 B and `sub.rom`
changes. Nothing in the sub image moves (`lineno.asm` is included last, before
the pad), the low region is untouched, and the 11 resident-ABI addresses are
unchanged — which is why the disk/float/graphics half of the corpus is a
regression check rather than a targeted one.

---

## 7. What this leaves open

* 🔴 **The sub page-0 entry table is FULL** — 13 rows, one spare byte before the
  fixed `$0038` vector. **The review's rank-4 rule "prefer page 0" cannot be
  applied to any future candidate** without relocating `SUBROM_ENTRY_BASE_P0`
  past the vector (two `equ` sites + the `IF $ - SUBROM_ENTRY_BASE_P0` header
  assert; every call site is symbolic, so the move is mechanical). Cheap, but an
  ABI move, and not costed here. **The next rank-4 candidate that genuinely needs
  to call main page 1 is blocked until it is done.**
* **Rank 4 is now costed, and the tier is thin.** §2.3 is the whole surviving
  candidate list: after this one, nothing left is both single-entry and free of
  interrupt/gate hazard. The structural reason is not going to change — every
  statement-shaped entry reaches `eval` → the float pack, and every printing path
  reaches `pchar` → `CHPUT`.
* ⚠️ **`carve_scout.py` is still a source walk**, so it shares K2a′'s boundary: it
  cannot classify a name that is not in the sym file it was handed. The build is
  the backstop, and that is now stated in the tool's own header.
* ⚠️ **The dead-code sweep's seed set moves on prose.** `external_names` scans
  `sub/` and `tools/` for identifiers including comments, so *naming a rejected
  candidate in a justification comment* seeds it. Widened from D-PINDATA's
  `tools/`-only filing; still unfixed, still masking nothing.
* **The stub's absent-sub-ROM arm is ungated** (§3.3), as for every other tenant.
