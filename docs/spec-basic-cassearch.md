<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASSEARCH — the tape-search progress row

Closes the residual [castail-msx1-characterization.md](castail-msx1-characterization.md)
§5 filed and [spec-basic-castail.md](spec-basic-castail.md) §7 listed as out of
scope. Reference reading:
[cassearch-msx1-characterization.md](cassearch-msx1-characterization.md).
Gate: `make castail-acceptance`
([`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)).

## 1. What was filed, and what the scout found

Filed: *"zerobas prints NO tape-search progress line (`Found:` / `Skip :`)"* —
both references print one while `LOAD"CAS:x"` / `RUN"CAS:x"` / `CLOAD` hunt the
tape, and zerobas prints neither, so a user watching a tape load sees nothing
until it finishes.

The entry carried a **cost line that had already been withdrawn unmeasured**
(`bc5d3f5`): *"a print in `cas_open_match`'s match/skip arms, costing main
page-1 bytes"*. `cas_open_match` is a marshalling shim; the match/skip loop is a
**sub-ROM page-1 tenant** (`sub/casmatch.asm` + `basic/casmatch-body.inc`,
`SUBROM_IDX_CASMATCH`). The entry then named the thing to scout: `print_msg` is
at `$7687` — **main page 1** — which
[`tools/check_tenant_closure.py`](../tools/check_tenant_closure.py) `--page1`
forbids a page-1 tenant to call.

**Scouted and measured, before proposing anything:**

* 🟢 **The tenant can print, and there is a landed precedent for exactly this.**
  `CHPUT` is at `$00A2` — page-0 BIOS, `< $4000`, legal for a page-1 tenant, and
  `title_tenant` (`sub/title.asm`, `SUBROM_IDX_TITLE`) is a page-1 tenant whose
  *entire* reason for being page-1 rather than page-0 is that it calls
  `INITXT`/`CHPUT`. The body already calls page-0 BIOS (`TAPION`/`TAPIN`), so
  the tenancy question was settled before this slice existed.
* 🟢 **So the split the entry offered as the alternative — "the shim prints
  `Found:` on the way out while `Skip :` needs the tenant" — is not needed and
  is not taken.** It would have cost main page-1 bytes (165 B free) to buy
  nothing, and it would have printed the two arms from two different files.
* 📏 **Priced by building it: 57 B, all of it in sub page 1** (1540 → 1483 B
  free). Main page 1, main low and sub page 0 do not move at all.

**And the measurement changed the design in a way no code reading could have.**
The residual named `LOAD` / `RUN` / `CLOAD`. `cas_open_match` has **three**
callers — the third and fourth verbs are `MERGE"CAS:"` and `OPEN"CAS:" FOR
INPUT` (`basic/files.asm`). A print sited in the shared engine prints for them
too, so if a reference were **silent** there this siting would close one
divergence by opening two. Measured: **all four verbs print the identical rows**
(characterization §3). The shared engine is therefore not merely the cheap site,
it is the *correct* one.

## 2. The mechanism

`basic/casmatch-body.inc`'s `cas_open_match` walks the tape's files: `TAPION`
each header block, read the file-type id and the 6-char name into
`CAS_HDRNAME`, then decide.

* `com_match` — this file is taken. Reached **two** ways: through the compare
  loop (a named search that matched), and by `jr z,com_match` for the bare form
  (`CAS_WANT_ON = 0`, load-next), which never enters the compare loop at all.
* `com_miss` — this file is stepped over: `cas_skip_data` consumes its data and
  the loop tries the next header.

Those two labels are exactly the reference's two rows (characterization §2), and
the name they must print is the one the loop already has in RAM.

## 3. The change

### 3.1 One emit at each arm, through `CHPUT`

`cm_say` takes `HL` → a **6-character** prefix and prints
`<prefix><CAS_HDRNAME><CR><LF>` through `CHPUT`. Both prefixes are exactly six
characters (`"Found:"`, `"Skip :"` — the reference's own spacing, characterization
§1), and `CAS_HDRNAME` is exactly six bytes, so **one** count-6 loop serves both
halves and there is no terminator byte to carry.

| site | change | bytes |
|---|---|---|
| `com_match` | `ld hl,cm_s_found` / `call cm_say` | +6 |
| `com_miss` | `ld hl,cm_s_skip` / `call cm_say` | +6 |
| `cm_say` | prefix, name, CR, LF | +19 |
| `cm_six` | the shared 6-char `CHPUT` loop | +14 |
| `cm_s_found` / `cm_s_skip` | the two 6-char prefixes | +12 |
| **total** | | **+57**, all in **sub page 1** |

`HL` and `BC` are guarded across each `CHPUT` (the `title-body.inc` `st_loop`
precedent). `com_match`'s `or a` still runs **after** the call, so the CF-clear
contract `cas_open_match` publishes is unchanged; `com_miss` prints **before**
`cas_skip_data`, matching the reference's row order.

### 3.2 What is deliberately NOT done

* 🔴 **`print_msg` is not called, and cannot be.** `$7687` is main page 1;
  `check_tenant_closure.py --page1` forbids a page-1 tenant to reach it. The
  strings are the tenant's own bytes and the sink is BIOS.
* 🔴 **The `OPEN"CAS:name"` name-match defect is NOT fixed** (characterization
  §5). It is a different verb's name handling, in a different file, and it needs
  its own reference battery. **Pinned and filed.**
* **The name is emitted as all six header bytes**, not trimmed. A trailing pad
  space is indistinguishable from unwritten screen (characterization §6), so no
  battery can score the difference and trimming would only cost bytes.

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

| measurement | baseline `cc1e20e` | predicted after |
|---|---|---|
| `castail-acceptance` | 9/9 + 1 pin | **17/17 scored readings agree**, 13 cases, 7 positive controls, **3** pinned divergence rows, exit 0 |
| sub page 1 free | 1540 B | **1483 B** (1540 − 57) |
| main low / main page 1 / sub p0 free | 3 / 165 / 3843 B | **unchanged** — the body is included ONLY by `sub/casmatch.asm` |
| `sub.rom` hash | `6ea374de…` | **CHANGES** |
| `disk.rom` / `basic-reloc.rom` / `zerobas-main-eu.rom` hashes | `2c630d3d…` / `86ccd666…` / `7dfedd72…` | 🔴 **ALL THREE UNCHANGED** — see below |
| closure `--page1` | 582+41 | **unchanged** — `CHPUT` is `< $4000`, an already-legal edge |
| `deadcode` main spans / seeds | 1566 / 287 | **1566 / 287** — the main seed set is `external_names(['sub','tools'])`, and this slice writes no words under either |
| `deadcode` sub spans / seeds | 1512 / 102 | **1517 / 102** — five new labels (`cm_say`, `cm_six`, `cm_six_ch`, `cm_s_found`, `cm_s_skip`), all live, 0 dead |
| `audit-citations` files swept | 720 | **722** — two new `.md` |
| `audit-citations` basic files / provenance-bearing | 107 / 186 | **107 / 187** — no new file under `basic/`, one new citing comment block in `casmatch-body.inc` |
| `injector-check` | 331 | **unchanged** — no new file under `probes/` |
| `preflight-check` | 181/86/95/95/0 | **unchanged** |
| `unit-test` / `latch-check` | 58 / 16-16 | **unchanged** |
| `runtail` / `fat-error` / `dskmsg` / `diskbasic` / `lptverb` | 9/9 · 8/8 · 5/5 · 34/34 · 44/44 | **unchanged** |

⚠️ **THREE OF THE FOUR ROM HASHES ARE PREDICTED TO HOLD, AND THAT IS A CLAIM,
NOT AN OMISSION.** `basic/casmatch-body.inc` is `include`d by **one** file —
`sub/casmatch.asm` (grep-verified over `*.asm`/`*.inc`; the lean cart that was
its second home is retired). The merged `zerobas-main-eu.rom` is repacked C-BIOS
+ `basic-reloc.rom` + tape, and the sub ROM is a **separate** slot-3-2 image, so
a sub-only change cannot move it. Editing the file *does* retrigger the
`$(MAIN_ROM)` rule (it is listed in `DEPS`), which is exactly the case where a
byte-identical rebuild is the correct outcome and not a skipped one.

⚠️ **The ROM still moves, so every emulator gate stays meaningful and is run in
full.** The tenant lives in `sub.rom`, which the repack machine loads in slot
3-2; nothing here is a doc-only change.

## 5. The knives — predicted RED **and** predicted GREEN survivors

Every cut is **byte-neutral**, the subject is the probe invoked directly (never
`make`), each is run **twice**, the runner rebuilds from clean **before every
probe run including the ones that follow a restore**, hashes all four ROMs after
every cut build, parses **all three** report shapes (exit 0/1 carry a tally line;
exit 2 is a complete report of `....` rows with **no** tally), and restores in a
`finally`.

🔴 **TWO KNIVES ARE SITED AT A STRING'S BODY RATHER THAN AT THE POINTER THAT
NAMES IT, AND THAT IS THE NEW RULE BEING APPLIED, NOT A PREFERENCE.**
`dev-workflow.md` §Knives, 2026-08-07: re-pointing `ld hl,cm_s_found` →
`ld hl,cm_s_skip` would leave `cm_s_found` with **zero** references, and
`check_dead_code.py` would refuse the *build* — a knife aimed at the search
refused by the dead-code gate, exactly as D-DKNAME's K-NAME2 was. Cutting the
`db` **body** is byte-neutral, orphans nothing, and tests the identical claim.

| # | cut | predicted RED | predicted GREEN survivors | rc |
|---|---|---|---|---|
| **K-FOUND** | `cm_s_found`'s body `db "Found:"` → `db "Skip :"` — the MATCH arm names the wrong row | `cas2-load`, `cas2-merge`, `cas2-cload`, `cas2-bare`; **ROT** on `cas-load-plain:search` and `cas2-open` | 🔴 **all six filtered subject rows HOLD** (`Skip :RT` is in the filter too), `cas2-open:echo`, all 5 `:listing` controls, `bare-run` | 1 |
| **K-SKIP** | `cm_s_skip`'s body `db "Skip :"` → `db "Found:"` — the MISS arm names the wrong row | `cas2-load`, `cas2-merge`, `cas2-cload` | 🎯 **`cas2-bare` HOLDS, and BOTH `Found:`-only pins HOLD** — none of the three ever skips a file; plus the six filtered rows and every control | 1 |
| **K-NAME** | `cm_say`'s `ld hl,CAS_HDRNAME` → `ld hl,cm_s_skip` — the name half prints a CONSTANT | all 4 `cas2-*` subjects, **all six filtered subject rows** (the emitted row no longer matches the exact-string filter), **all 3 pins ROT** | `bare-run`, all 5 `:listing` controls, `cas2-open:echo` | 1 |
| **K-ORDER** | `com_miss`: the print moves to **after** `cas_skip_data` | **nothing — a declared PREDICTED MISS** | every row | 0 |

⚠️ **K-FOUND AND K-SKIP SEPARATE THE TWO ARMS, AND THE SEPARATION IS CARRIED BY
ROWS THAT WERE BUILT FOR IT.** `cas2-bare` (`LOAD"CAS:"`, no name → straight to
`com_match`, no compare loop) and the two `Found:`-only pins reach a match
**without ever skipping**, so a broken skip arm is invisible to them. They red
under K-FOUND and hold under K-SKIP. Without `cas2-bare` no row could tell the
two cuts apart on the match side.

⚠️ **K-NAME IS ALSO THE PROOF THAT `SEARCH_ROWS` IS AN EXACT-STRING FILTER.**
Under it the emitted row becomes `Found:Skip :`, which a `Found:`-prefix rule
would still have eaten — leaving the six subject rows green over a search that
prints garbage. They red, so the filter is doing what its comment claims.

⚠️ **K-NAME EXITS 1, NOT 2.** `cas-run-hit` reads `Found:Skip : / ZQ9`, which
*contains* `ZQ9`, so its containment control holds and the row merely DIFFs —
the same shape D-CASTAIL measured for K-CAS-A1 (§6.3 there).

⚠️ **K-ORDER IS A PREDICTED MISS AND IS RUN ANYWAY.** Printing before or after
`cas_skip_data` produces the same screen rows in the same order, because nothing
else prints in between — so the battery can see **that** the miss arm prints, not
**where** in it. Running it makes the ROM-hash guard separate *"the cut landed
and reddened nothing"* — the finding — from *"the cut never happened"*
([[knife-runner-needs-a-rom-hash-guard]], `spec-basic-msgmigrate.md` §8's
**DID-NOT-HAPPEN**).

## 6. The gate — the pin ROTS on purpose, and is RE-MEASURED, never loosened

`cas-load-plain:search` pinned `zb='<nothing>'`. This slice makes zerobas print,
so **the pin rots and the gate fails — by design**
([[a-pinned-divergence-is-a-live-detector]]). It is re-pinned to
`zb='Found:RT'`, its **measured** new reading. That is a re-measurement: the row
is still a per-side EXACT match, and it is now the only row in the battery that
asserts the search line by **value** rather than by cross-side agreement.

### 6.1 🎯 `SEARCH_ROWS` KEEPS its filter — decided explicitly, with the reason

The filter drops the two exact progress strings from the six D-CASTAIL subject
rows. Now that all three sides print them, it could be removed. **It is kept**,
and the [[readout-blind-to-its-own-subject]] hazard it was flagged for is what
decides it:

* That hazard was *"a normalisation that is a no-op on the side under test"* —
  it fired only on a reference, so it blessed one machine's silence. **After this
  slice it fires on all three sides.** It now normalises an **agreement**, which
  is the honest use of a filter, not a blessing.
* 🔴 **Removing it would break the ONE normalisation this battery guards
  hardest.** `<load-failed>` fires only when the tail is **EXACTLY** the side's
  own message — deliberately, so that an extra row is always the subject. With
  the filter gone, every abort row's tail becomes `Skip :RT` **plus** the
  message, so no row would normalise and all three abort rows would DIFF on the
  quarantined *wording* divergence this battery exists to hold out of scope.
  Rescuing them would mean weakening the normalisation from whole-tail to
  per-row — trading a rule that is load-bearing for coverage the pin and four new
  unfiltered rows already provide.

So: six rows stay filtered and keep asking their own question; **five** rows
(the pin plus `cas2-load` / `cas2-merge` / `cas2-cload` / `cas2-bare`, and the
`cas2-open` pin) read the search UNFILTERED and are its detectors.

## 7. As-built

### 7.1 The change, and the walls

**+57 B, all of it in sub page 1, to the byte** — §3.1's price was exact, and it
was taken from a throwaway scout build *before* anything was proposed
([[carve-scout-before-proposing]]). Measured from clean (`rm -rf build && make
basic-reloc`):

| wall | before | after |
|---|---|---|
| main low region | 3 B | **3 B** |
| main page 1 | 165 B | **165 B** |
| sub page 0 | 3843 B | **3843 B** |
| sub page 1 | 1540 B | **1483 B** |

ROM hashes: `sub.rom` `6ea374de… → b3761022…`; `disk.rom 2c630d3d…`,
`basic-reloc.rom 86ccd666…` and `zerobas-main-eu.rom 7dfedd72…` **all three
unchanged**, as §4 predicted and for the reason it gave. The eight independent
knife builds re-confirm it: every one moved `sub.rom` and **only** `sub.rom`.

🎯 **THE WITHDRAWN COST LINE WAS WRONG ABOUT THE WALL, AND THE SCOUT IS WHY THAT
IS NOW A MEASUREMENT.** The residual first said *"costing main page-1 bytes"* —
165 B free, where 57 would have been a third of the remaining budget. The real
wall has **1540 B free** and the slice spends 3.7 % of it. Nothing about the
change would have differed; what would have differed is whether it looked
affordable.

### 7.2 Predictions, scored

| prediction | outcome |
|---|---|
| `castail-acceptance` **17/17**, 13 cases, 7 controls, 3 pins, exit 0 | ✅ exact, three-sided |
| every pinned `zb` value, written down BEFORE the change | ✅ all three exact — `Found:RT`, `Found:SK`, `10 PRINT"ZQ8"` |
| sub page 1 1540 → **1483 B** | ✅ exact |
| main low / main p1 / sub p0 unmoved | ✅ 3 / 165 / 3843 |
| `sub.rom` moves; the other **three** hashes hold | ✅ exact — and re-confirmed by 8 knife builds |
| `deadcode` main **1566 spans / 287 seeds** | ✅ exact — both halves |
| `deadcode` sub **1517 spans / 102 seeds**, 0 dead | ✅ exact — the five new labels, all live |
| `audit-citations` 720 → **722** files swept | ✅ exact |
| `injector-check` **331**, `preflight-check` **181/86/95/95/0** | ✅ unchanged |
| `unit-test` **58**, `latch-check` **16/16** | ✅ unchanged |
| closure `--page1`: **no main-page-1 escape** | ✅ — `CHPUT` is `< $4000`, an already-legal edge, and the build's own gate proves it |
| closure `--page1` counts unchanged at 582+41 | ❌ **585+43**, §7.5 |
| `audit-citations` basic provenance-bearing 186 → **187** | ❌ **186 — it did not move**, §7.5 |

### 7.3 🎯 The knives — 4 designed, 4 run, each TWICE, both rounds identical

| # | cut (all byte-neutral) | rc | RED | HELD |
|---|---|---|---|---|
| **K-FOUND** | `cm_s_found`'s body → `db "Skip :"` | 1 | `cas2-load`, `cas2-merge`, `cas2-cload`, `cas2-bare`; **ROT** on `cas-load-plain:search` and `cas2-open` | 14 rows — **all seven filtered rows**, `cas2-open:echo`, all 5 `:listing` controls, `bare-run` |
| **K-SKIP** | `cm_s_skip`'s body → `db "Found:"` | 1 | `cas2-load`, `cas2-merge`, `cas2-cload` | 17 rows — 🎯 **`cas2-bare` AND BOTH `Found:`-only pins included** |
| **K-NAME** | `cm_say`'s `ld hl,CAS_HDRNAME` → `ld hl,cm_s_skip` | 1 | 13 rows: all 4 `cas2-*` subjects, **all seven filtered rows**, 2 pins ROT | `bare-run`, all 5 `:listing` controls, **`cas2-open:echo`** |
| **K-ORDER** | `com_miss`: the print moves **after** `cas_skip_data` | 0 | **nothing — the declared predicted miss** | every row |

All four reached the artifact — `sub.rom` moved on every cut build, so the
runner's guard never had to declare DID-NOT-HAPPEN, **including K-ORDER**, which
is the whole reason that knife is run. The tree hashed back to baseline after
the restore (`b3761022`, other three unchanged).

🎯 **K-FOUND AND K-SKIP SEPARATE THE TWO ARMS, AND THE SEPARATION IS CARRIED BY
ROWS BUILT FOR IT.** Under K-FOUND `cas2-bare` reads `Skip :SK` where the
references read `Found:SK`, and the `cas-load-plain:search` pin reads `Skip :RT`
where it is pinned at `Found:RT`. Under K-SKIP **all three of those hold**,
because a bare load and a first-header match never step over a file at all —
`cas2-load` / `cas2-merge` / `cas2-cload` read `Found:SK / Found:RT` and red
alone. Without `cas2-bare` (added precisely because the bare form reaches
`com_match` by a path no other row uses) no row could tell the two cuts apart on
the match side.

🎯 **AND ALL FOUR VERBS RED TOGETHER FROM ONE CUT.** `LOAD"CAS:"`, `MERGE"CAS:"`,
`CLOAD` and `OPEN"CAS:"` move as one under K-FOUND and K-NAME. That is the
evidence for §1's claim that the shared search engine is the site: one edit
serves four verbs, and a knife there is visible at all four.

⚠️ **K-NAME ALSO PROVES `SEARCH_ROWS` IS AN EXACT-STRING FILTER.** Under it the
emitted row becomes `Found:Skip :`, which a `Found:`-**prefix** rule would still
have swallowed — leaving all seven filtered rows green over a search printing
garbage. They red. The comment claiming the exactness is load-bearing now has a
measurement behind it.

### 7.4 🔴 One knife's predicted RED set was wrong in TWO places that cancelled

**K-NAME predicted 13 red rows and measured 13 red rows, and they are not the
same 13.** The arithmetic agreed; the membership did not.

* Predicted *"all six filtered subject rows"*. There are **seven** filtered rows
  — `cas-load-plain` is filtered too, and it is one of the reddest here
  (`<nothing>` → `Found:Skip :`). It was left out because §5 was written from the
  D-CASTAIL docstring's phrase *"all six subject rows"*, which counts the rows
  that ask about the tail and silently excludes the control that shares their
  filter.
* Predicted *"all 3 pins ROT"*. Only **two** did. `cas2-open:echo` reads the
  **text of the opened file**, not a search row, so an emit that prints the wrong
  name cannot reach it — and it HELD, correctly, under every knife.

🔴 **A MATCHING COUNT IS NOT A MATCHING SET**, and this is the shape in which a
prediction gets marked ✅ while being wrong twice. It was caught only because the
runner prints the row NAMES rather than a tally; a runner that diffed counts
would have scored this knife as an exact hit.

### 7.5 🔴 TWO count misses, in OPPOSITE directions, from the same habit

Both of this slice's wrong predictions are the same failure wearing two faces:
**a count was predicted from a story about it instead of from its definition.**

**(a) The closure counts moved and §4 said unchanged.** `check_tenant_closure.py
--page1` reads **585 routines + 43 data-referenced labels**, not 582+41. The
substantive half of the prediction — *"no main-page-1 escape"* — held and is the
half the gate exists for. But the numbers were trivially derivable: this slice
adds three routines to a page-1 tenant's closure (`cm_say`, `cm_six`,
`cm_six_ch`) and two data labels (`cm_s_found`, `cm_s_skip`), so 582+3 and 41+2.
Predicting "unchanged" for *the size of a closure* in a slice that adds code to a
tenant inside it is not a prediction.

**(b) A citation count that did NOT move, predicted to.**

`audit-citations` reports `basic` **186** provenance-bearing where §4 predicted
**187** — and the interesting part is *why* I predicted a move.

[spec-basic-castail.md](spec-basic-castail.md) §6.5 recorded its own 185 → 186 as
*"the slice's own footprint — `cload.asm`'s new `do_tape_prog` contract block
cites `spec-basic-castail.md`"*, and drew the lesson that predicting "unchanged"
for *"comment blocks that cite a document"* is a habit rather than a prediction.
I applied that lesson, saw that this slice adds a citing comment block to
`casmatch-body.inc`, and predicted +1.

**The number in that record was right and its explanation was wrong.**
`provenance-bearing` is not a count of comment blocks at all —
`tools/audit_citations.py:141` `provenance_files()` returns a list of **FILES**:
the target's `.asm`, its `PROVENANCE.md`, and `probes/<target>/*.py` +
`**/*.asm`. D-CASTAIL's +1 was its **new probe file**,
`probes/basic/basic_probe_castail.py`. This slice adds no file under `basic/` or
`probes/basic/` — it extends the existing probe — so the count could not move,
and the *original* shape of the prediction ("unchanged") was the correct one.

🔴 **A RECORDED EXPLANATION OF A NUMBER IS A CLAIM, AND A WRONG ONE MISPREDICTS
THE NEXT SLICE IN THE OPPOSITE DIRECTION** ([[a-recommendation-in-the-record-is-still-a-claim]],
[[filed-justification-is-a-claim]]). D-CASTAIL missed by predicting no change;
this slice missed by predicting a change, from the same file, one slice apart.

✅ **BOTH WRONG RECORDS ARE NOW CORRECTED IN PLACE** — `spec-basic-runtail.md`
§6.5's table row and `spec-basic-castail.md` §6.5 both carried the comment-block
explanation, and both now carry the measurement instead. Leaving them would have
mispredicted the next slice too, which is exactly what they did to this one.
The disproof is one line: `cload.asm` was ALREADY in the file list, so a comment
block added inside it cannot move the count by construction — and D-RUNTAIL's own
table names the real cause ("the new probe is a file under `probes/`") **one row
above** the row that got it wrong.

🎯 **AND (a) AND (b) TOGETHER ARE THE ACTUAL LESSON.** I inherited D-CASTAIL's
"don't say unchanged" habit, spent it on the counter where it did not apply, and
then said *unchanged* on the closure counter where it did. Swapping one habit for
its opposite moves the error, it does not remove it. **The counts this slice got
exactly right — `deadcode`'s 1566/287 and 1517/102, `audit-citations`' 722 — are
the three whose definitions I actually opened and read** (`external_names`,
span-per-label, the swept-suffix walk). The two I got wrong are the two I
predicted from a narrative. A count whose definition is one line of Python is
predicted by reading that line; it takes under a minute, and both misses here
cost less than that to avoid.

### 7.6 Corpus — 20 gates, sequential from clean, all PASS

`unit-test` **ALL 58 files** · `audit-citations` CLEAN (**722** files swept,
basic **107 files / 186** provenance-bearing) · `preflight-check`
**181/86/95/95/0** · `injector-check` ALL PASS, **331** files · `latch-check`
**16/16 rows** · page-1 closure **585 routines + 43 data labels, no main-page-1
escape** · `deadcode` main **1566 spans / 287 seeds** → 0 dead, sub
**1517 / 102** → 0 dead (+1 allowlisted) · `lnblank-acceptance REPEAT=2` ·
`lnblank-say-acceptance` · `logicops-acceptance` · `float-acceptance` ·
`linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` · `lptverb-acceptance`
**44/44** · `dskmsg-acceptance` **5/5** · `diskbasic-acceptance` **34/34** ·
`fat-error-acceptance` **8/8 scored + 2/2 mount + 5 directory checks, 8 of 8
verb controls** · `runtail-acceptance` **9/9** · `castail-acceptance`
**17/17 + 3 pins**.

⚠️ **The ROM moved, so no emulator gate is skipped or waved through.** The
tenant lives in `sub.rom`, which the repack machine loads in slot 3-2; the fact
that three of the four hashes hold makes the *unchanged* gates a stronger
statement, not a reason to skip them.

## 8. Out of scope, said explicitly

* **`OPEN"CAS:name" FOR INPUT` ignores the name** and opens the next file on the
  tape, delivering the wrong file's bytes — found by these rows, **pinned** by
  the gate on both halves, filed in `TODO.md`, not fixed here. It is the OPEN
  verb's name handling (`basic/files.asm`, **main page 1** — a different wall),
  and three reference readings it needs are unmeasured: bare `OPEN"CAS:"`, case
  sensitivity, and `FOR OUTPUT` naming. **This entry carries no byte count on
  purpose** — the whole first half of §1 is what happens when one is written
  before the scout.
  ✅ **CLOSED 2026-08-07 by D-CASOPEN** ([spec-basic-casopen.md](spec-basic-casopen.md),
  reading [casopen-msx1-characterization.md](casopen-msx1-characterization.md))
  for **7 B in main page 1**. All three readings were taken first and all three
  mattered: the compare is case-sensitive, the bare form takes the next file, and
  `FOR OUTPUT` was **already correct** — so the defect was narrower than filed
  (the name was parsed all along; only the hand-off to the search was missing).
  🎯 **Refusing to price it here is what made that possible**: an inherited byte
  count would have been a number for the wrong fix.
* **Whether the reference pads the name to 6 on screen** — a non-claim, not a
  measurement (characterization §6). No screen-scraping battery can answer it and
  no behaviour depends on it.
* **`SAVE"CAS:"` / `CSAVE` / `OPEN"CAS:" FOR OUTPUT`** never run the search, so
  nothing here can reach them.
* **The wording of the failure message** stays the quarantined divergence,
  normalised per side — §6.1 is the reason the filter that protects it is kept.
