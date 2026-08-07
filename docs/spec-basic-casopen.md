<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASOPEN — `OPEN"CAS:name" FOR INPUT` honours the name

Closes the residual [cassearch-msx1-characterization.md](cassearch-msx1-characterization.md)
§5 found and pinned, and [spec-basic-cassearch.md](spec-basic-cassearch.md) §8
listed as deliberately out of scope. Reference reading:
[casopen-msx1-characterization.md](casopen-msx1-characterization.md).
Gate: `make castail-acceptance`
([`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)).

## 1. What was filed, and what the scout found

Filed: *"`OPEN"CAS:RT" FOR INPUT AS #1` name-matches on both references — it
steps over `SK` and opens `RT`; zerobas opens whatever file comes NEXT, so the
channel delivers the WRONG FILE'S BYTES."* zerobas does this **deliberately and
the source says so** — [`basic/files.asm`](../basic/files.asm) `oo_dev_cas` writes
`xor a` / `ld (CAS_WANT_ON),a` under the comment *"name-matching is Item A's
CLOAD/LOAD/RUN/MERGE scope, not OPEN"*. That scoping decision was a **guess about
the reference that no row had ever checked**, and the guess is measured wrong.

The entry deliberately carried **no byte count**, and named three readings that
had to come first. Both halves of that discipline paid.

**Scouted and measured, before proposing anything
([[carve-scout-before-proposing]]):**

* 🎯 **The name is ALREADY PARSED on the OPEN path, and both arms reach the
  parse.** `oo_dev_cas`'s first instruction is `call tape_parse_name`, which fills
  `TSV_NAME[0..5]` space-padded — it runs *before* the `FOR INPUT` / `FOR OUTPUT`
  dispatch, which is why `FOR OUTPUT` has a name to write into its `$EA` header.
  So the fix is **not** "parse a name that was never parsed"; it is **route the
  name that is already there to the search**. Those price very differently, and
  only opening the file could say which one this was.
* 📏 **Priced by building it: +7 B, all of it in main page 1** (165 → **158 B**
  free). Main low, sub page 0 and sub page 1 do not move at all. That is 4.2 % of
  the remaining page-1 budget — the tightest wall in the tree, and it fits.
* 🟢 **`cas_capture_name` (`basic/cload.asm`) is a drop-in for `tape_parse_name`
  at this site.** Same entry contract (HL → first name char, inside the quotes),
  same exit contract (HL left ON the closing `"` or the NUL), same truncation to
  six, same space padding, same **case preservation**. It additionally sets
  `CAS_WANT_ON = 1` iff at least one name char was present — which is exactly the
  two behaviours the references were measured to have (§3 of the reading:
  case-sensitive; §2: bare = next file). `files.asm` `merge_cas` already calls it,
  so a non-`cload.asm` caller is landed precedent, not a new coupling.
* 💰 **The 7 bytes are ALL the OUTPUT arm's, and none of them are the fix.** The
  call swap is byte-neutral (`call nn` → `call nn`) and deleting the two-instruction
  suppression *frees* 4 B. What costs is putting the name back where the OUTPUT
  header expects it: `CAS_WANT` → `TSV_NAME`, `ldir`, 11 B. Net +7.

**And the measurement changed what the defect IS.** The residual says *"OPEN
ignores the name"*. Measured (reading §5), OPEN **parses** the name and **writes
it to tape** correctly on the OUTPUT arm; what it never does is hand it to the
search on the INPUT arm. The narrower claim is what makes this a re-routing.

### 1.1 🔴 A THIRD face of the divergence, which the pinned row could not see

The pin asks a name that **matches**. A machine that never compares and a machine
that compares case-insensitively answer it identically. The new `cas2-opencase`
row asks `OPEN"CAS:rt"` for a tape holding `RT`: both references compare, miss
**both** files, run off the end of the tape and answer the Ctrl-STOP with a
message; zerobas answers **nothing**, having opened `SK`. That is a second,
independently visible symptom of the same defect, and it is the row that says the
name never reaches the compare at all.

## 2. The mechanism

`oo_dev_cas` (`basic/files.asm`) is one parse feeding two arms:

```
oo_dev_cas:   call tape_parse_name      ; TSV_NAME[0..5]; HL -> closing '"'
              ...  FOR INPUT | FOR OUTPUT ... AS #n ...
  FOR INPUT:  xor a / ld (CAS_WANT_ON),a   ; <- the defect: match OFF, always
              call cas_open_match          ; the shared search engine
  FOR OUTPUT: call cas_write_ea_header     ; writes TSV_NAME into the $EA header
```

`cas_open_match` already honours `CAS_WANT`/`CAS_WANT_ON` for `LOAD`, `RUN`,
`CLOAD` and `MERGE`, and since D-CASSEARCH it prints `Found:` / `Skip :` for all
four. **Nothing in `sub/` or `basic/casmatch-body.inc` is touched by this slice** —
the engine is not the subject, and the site is decided by the fact that the ONLY
caller which withholds the name is this one.

## 3. The change

### 3.1 Capture into `CAS_WANT`, and give `FOR OUTPUT` back its copy

| site | change | bytes |
|---|---|---|
| `oo_dev_cas` | `call tape_parse_name` → `call cas_capture_name` | ±0 |
| the `FOR INPUT` arm | delete `xor a` / `ld (CAS_WANT_ON),a` | **−4** |
| `oocas_do_out` | `ld hl,CAS_WANT` / `ld de,TSV_NAME` / `ld bc,6` / `ldir` | **+11** |
| **total** | | **+7**, all in **main page 1** |

`oocas_do_out` runs **after** both `push de` (the channel) and `push hl` (the
text cursor), and `oocas_mark` pops both, so HL/DE/BC are free there. `CAS_WANT`
survives the `AS #n` parse between the capture and the search for the same reason
`TSV_NAME` already survives it: both are dedicated RAM sysvars and `eval` writes
neither — and `cas-openout:tape` is the row that MEASURES that rather than
asserting it.

### 3.2 What is deliberately NOT done

* 🔴 **No case folding.** Reading §3: the reference compare is byte-exact, the
  same rule `LOAD`/`CLOAD` already implement. Folding case would cost bytes to
  become measurably wrong on `OPEN"CAS:rt"`.
* 🔴 **The bare form is not armed.** `cas_capture_name` sets `CAS_WANT_ON = 0`
  when no name char was present, so `OPEN"CAS:"` still takes the next file
  (reading §2). Arming matching unconditionally is the obvious cheap fix and it is
  wrong; `cas2-openbare` is the row that catches it and K-CO3 is the proof that it
  can.
* 🔴 **`FOR OUTPUT`'s behaviour is not changed, only its supply route.**
  `cas_capture_name` and `tape_parse_name` produce byte-identical six-byte fields
  for every input, so the header the OUTPUT arm writes is unchanged — a claim the
  two new `:tape` readings turn into a measurement, and K-CO2 turns into a
  falsification.
* **`APPEND` / `RANDOM` on a cassette channel** stay refused, unmeasured, out of
  scope.

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

⚠️ **Every count below was predicted by opening the line that computes it**, not
from a narrative about it — [spec-basic-cassearch.md](spec-basic-cassearch.md)
§7.5 is the record of what happens otherwise (two wrong predictions in opposite
directions, one slice apart, from the same habit).

| measurement | baseline `6a32356` | predicted after |
|---|---|---|
| `castail-acceptance` | 17/17 + 3 pins | **31/31 scored readings agree (17 cases, 15 positive controls, 1 pinned divergence row(s))**, exit 0 |
| `cas2-open` (zb) | `Found:SK` | **`Skip :SK / Found:RT`** — all three sides |
| `cas2-open:echo` (zb) | `10 PRINT"ZQ8"` | **`10 PRINT"ZQ9"`** — all three sides |
| `cas2-opencase` (zb) | `<nothing>` | **`<load-failed>`** — all three sides |
| `cas2-openbare` / `:echo` (zb) | `Found:SK` / `10 PRINT"ZQ8"` | **unchanged** — the survivor rows |
| `cas-openout:tape` / `cas-openoutbare:tape` (zb) | `'WX    '` / `'      '` | **unchanged** — byte for byte |
| main page 1 free | 165 B | **158 B** (165 − 7) |
| main low / sub p0 / sub p1 free | 3 / 3843 / 1483 B | **unchanged** — `basic/files.asm` is a main-ROM source |
| `basic-reloc.rom` hash | `86ccd666…` | **`8b352603…`** — the exact hash the scout build produced, since the final code differs from it only in comments |
| `zerobas-main-eu.rom` hash | `7dfedd72…` | **CHANGES** — it embeds `basic-reloc.rom` |
| `sub.rom` / `disk.rom` hashes | `b3761022…` / `2c630d3d…` | 🔴 **BOTH UNCHANGED** — the opposite pattern from D-CASSEARCH, and stated as a claim |
| `deadcode` main spans / seeds | 1566 / 287 | **1566 / 287** — this slice defines and deletes **no label**; `tape_parse_name` keeps its three `save.asm` callers, so nothing is orphaned |
| `deadcode` sub spans / seeds | 1517 / 102 | **1517 / 102** — nothing under `sub/` is edited |
| closure `--page1` | 585 + 43 | **585 + 43** — the closure is over the sub-ROM page-1 tenants; a main-ROM edit is not in it |
| `audit-citations` files swept | 722 | **724** — `sweep_files()` walks every `.md/.asm/.inc/.py/.tcl/.txt/.bas/.yml`, and this slice adds exactly two `.md` |
| `audit-citations` basic files / provenance-bearing | 107 / 186 | **107 / 186** — `provenance_files('basic')` is a list of FILES (sources + `PROVENANCE.md` + `probes/basic/*.py`); this slice adds none and EXTENDS the existing probe |
| `injector-check` | 331 | **331** — the same file count; no new file under `probes/` |
| `preflight-check` | 181/86/95/95/0 | **unchanged** — `basic_probe_castail.py` contributes **no launch site** at all (it goes through `omsx_repl`), so its new `run_cases` calls cannot move any of the five |
| `unit-test` / `latch-check` | 58 / 16-16 | **unchanged** |
| `runtail` / `fat-error` / `dskmsg` / `diskbasic` / `lptverb` | 9/9 · 8/8 · 5/5 · 34/34 · 44/44 | **unchanged** — and `diskbasic` / `fat-error` are called out because `MAXFILES`, the channel-mode table and `oo_parse_as_chan` are SHARED with the disk verbs |

**Where 31 comes from**, counted off `labels_of` rather than guessed: `CASES` 8
rows + 2 extras = 10, `CASES_T2` 6 rows × (1 + 1 extra) = 12, `CASES_T2T` 2,
`CASES_REC` 2 rows × (1 + `:alive` + `:tape` + `:data`) = 8 → **32 readings**,
minus the **1** row still pinned = **31 scored**.

## 4.1 🎯 The two pins are RECLASSIFIED, not re-pinned — and here is why

The moment `OPEN` name-matches, `cas2-open` and `cas2-open:echo` stop being
divergences: all three sides read the same thing. A pin whose three values are
identical is a **hand-written want**, and this battery's stated scoring rule is
the opposite one — *"every row is scored by cross-side agreement, not against a
hand-written want; the references define the answer."*

* **The decision: both rows move to the SCORED set, and `cas2-open:echo` joins
  `CONTROLS` with `("ZQ9",)`.** That makes `cas2-open` structurally identical to
  its three siblings `cas2-load` / `cas2-merge` / `cas2-cload`, which differ from
  it only in the verb and are all scored-with-a-`:listing`-control. Consistency
  with the rows it is compared against is the argument that decides it.
* **A pin IS stricter than agreement, and that strictness is replaced, not
  dropped.** The pin's job was to fail if any side moved. After the change, the
  row is scored across three sides **and** carries a control asserting `ZQ9` — the
  SECOND file's text. A machine that took the wrong file reads `ZQ8` and the
  control fails; a dead machine reads `<nothing>` and the control fails. The
  degenerate case a bare agreement row is vulnerable to is exactly the case the
  control covers, which is why the row is not left without positive evidence.
* **`cas-load-plain:search` STAYS pinned**, untouched. It is D-CASSEARCH's row,
  it is the one row that asserts a search line by VALUE, and this slice has no
  measurement that bears on it. One value-assertion of that class is the point;
  two would be duplication.

The gate therefore goes from **3 pins** to **1**, and the rot is closed by
promotion rather than by loosening.

## 5. The knives — predicted RED **and** predicted GREEN survivors

Every cut is **byte-neutral**, the subject is the probe invoked directly (never
`make`), each runs **twice**, the runner rebuilds from clean **before every probe
run including the ones that follow a restore**, hashes **all four** ROMs after
every cut build, parses every exit code's report shape (0/1 carry a tally line; 2
is a complete report of `....` rows with **no** tally), and restores from a
scratchpad snapshot in a `finally`.

⚠️ **THREE OF THE FOUR KNIVES ARE PREDICTED TO EXIT 2, NOT 1, AND THAT IS THE
POINT.** The new rows' positive evidence is `CONTROLS` entries, and a failed
control makes this probe exit **2** with a complete `....` report and no tally. A
runner that treats exit 2 as "the instrument broke" would abort exactly the
knives whose purpose is to fail a control ([[a-runner-must-know-every-report-shape]]).

⚠️ **THE KNIVES RUN `--sides vg8020,zb`, AND THE RESTRICTION IS DECLARED.** A cut
in zerobas cannot move a reference reading, and the VG-8020 is a full side for
this battery (every MSX1 has a cassette port). Dropping the CF-3300 from the
knife runs halves their wall-clock; the CF-3300 is a full side of the final
three-sided acceptance. Nothing is scored on one side.

| # | cut | predicted RED | predicted GREEN survivors | rc |
|---|---|---|---|---|
| **K-CO1** | `oo_dev_cas`: `call cas_capture_name` → `call tape_parse_name` — the name is parsed and never handed on (the pre-slice code, exactly) | `cas2-open`, `cas2-open:echo` (**control fails**), `cas2-opencase`, `cas-openout:tape` (**control fails**), `cas-openoutbare:tape` | 🔴 `cas2-openbare` + `:echo` **HOLD** (openMSX zero-fills RAM, so `CAS_WANT_ON` is 0 and the bare arm is unaffected); all 8 `CASES` rows, `cas2-load`/`merge`/`cload`/`bare` + listings, `cas-load-plain:search` **pin holds**, both `:data`, both `:alive` | **2** |
| **K-CO2** | `oocas_do_out`: `ldir` → `nop` / `nop` — the captured name never reaches the OUTPUT header | `cas-openout:tape` (**control fails**), `cas-openoutbare:tape` | 🎯 **every INPUT row holds, including all three OPEN-input rows** — this cut separates the OUTPUT half of the change from the INPUT half, and no other cut can | **2** |
| **K-CO3** | `cas_capture_name`'s `ccn_flag`: `jr z,ccn_set` → `jr nz,ccn_set` — matching is armed even for an EMPTY name | `cas2-openbare` + `:echo` (**control fails**), `cas2-bare` + `:listing` (**control fails**) | `cas2-open` + `:echo`, `cas2-opencase`, `cas2-load`/`merge`/`cload` + listings, all `CASES`, both `:tape` rows (OUTPUT never reads the flag) | **2** |
| **K-CO4** | the `ldir` block moves from `oocas_do_out` up to immediately after the capture in `oo_dev_cas` | **nothing — a declared PREDICTED MISS** | every row | 0 |

⚠️ **K-CO1 AND K-CO2 SEPARATE THE TWO HALVES OF A THREE-EDIT CHANGE.** K-CO1
reddens the INPUT rows *and* the OUTPUT `:tape` rows (with the capture gone, the
`ldir` copies a cold `CAS_WANT`); K-CO2 reddens **only** the `:tape` rows. The
difference between the two red sets is precisely the INPUT claim, and neither cut
alone would show it.

⚠️ **K-CO3 IS A KNIFE OF A ROW, NOT OF THIS SLICE'S CODE**, and it is run for
that reason. `cas2-openbare` exists to say *"the fix did not arm the bare form"* —
a claim that is invisible while the fix is correct. K-CO3 builds the wrong fix
(matching always on) and asks whether the row notices. If it does not, the row is
[[gate-can-be-green-while-measuring-nothing]] and the survivor claim in §3.2 rests
on nothing. It reddens `cas2-bare` too, which is correct and worth stating: the
capture is shared with `LOAD"CAS:"`.

⚠️ **K-CO4 IS A PREDICTED MISS AND IS RUN ANYWAY.** Nothing between the capture
and `oocas_do_out` reads `TSV_NAME`, so the copy's site is not observable, and the
battery can see *that* the OUTPUT header carries the name but not *where* it was
copied. Running it makes the ROM-hash guard separate *"the cut landed and reddened
nothing"* — the finding — from *"the cut never happened"*
([[knife-runner-needs-a-rom-hash-guard]], `spec-basic-msgmigrate.md` §8's
**DID-NOT-HAPPEN**). ⚠️ It is also the one cut here that is **not** an
equal-length edit at one site: it moves 11 bytes up by a few instructions, so the
runner must confirm the build succeeded *and* that a ROM moved.

## 6. The gate — what changes in `basic_probe_castail.py`

* **Four new cases, twelve new readings** (reading §1), one new fixture kind (a
  `cassetteplayer new` recording tape) and one new reading source (`cas_decode`
  over the recorded WAV).
* **Two rows leave `PINNED` for the scored set**, and `cas2-open:echo` joins
  `CONTROLS` — §4.1.
* **`cas2-openbare` joins `UNFILTERED_SUBJECTS`; `cas2-opencase` deliberately does
  NOT** — the reading's §3 gives the reason, and getting that backwards would put
  the row on the quarantined wording divergence.
* 🔴 **Each recording row gets its OWN `run_cases` call.** `cassetteplayer new` is
  a **prologue**, a prologue applies to the whole batch, and it truncates the file
  at every boot — two recording rows sharing one call would leave one recording on
  disk and both rows would read it.
* 🔴 **`cas-openoutbare:tape` gets NO containment control, deliberately.** Its
  correct value is six spaces, and *"the reading contains six spaces"* is
  satisfied by every blank and every failure. Its positive evidence is `:data`
  from the **same decode of the same recording**: if the WAV decoded to `ZQ7`, the
  six bytes ahead of it are a real header field and not an absence.

## 7. As-built

### 7.1 The change, and the walls

**+7 B, all of it in main page 1, to the byte** — §3.1's price was exact, and it
was taken from a throwaway scout build *before* anything was proposed. Measured
from clean (`rm -rf build && make basic-reloc`):

| wall | before | after |
|---|---|---|
| main low region | 3 B | **3 B** |
| main page 1 | 165 B | **158 B** |
| sub page 0 | 3843 B | **3843 B** |
| sub page 1 | 1483 B | **1483 B** |

ROM hashes: `basic-reloc.rom` `86ccd666… → 8b352603…` and `zerobas-main-eu.rom`
`7dfedd72… → 37d0f328…`; `sub.rom b3761022…` and `disk.rom 2c630d3d…` **both
unchanged** — the exact mirror image of D-CASSEARCH, and stated as a prediction
rather than noticed afterwards. The eight independent knife builds re-confirm it:
every one moved those two ROMs and **only** those two, and the tree hashed back to
all four baselines after the restore.

🎯 **THE PRICE IS THE OUTPUT ARM'S, NOT THE FIX'S.** The INPUT half — the actual
defect — is byte-**negative**: swapping one `call` target costs nothing and
deleting `xor a` / `ld (CAS_WANT_ON),a` frees 4 B. All 11 spent bytes are the
`CAS_WANT` → `TSV_NAME` copy that keeps `cas_write_ea_header` (shared with
`SAVE"CAS:"`/`CSAVE`) seeing what it has always seen. A cost line written before
the scout would have been a number for a fix that does not exist.

### 7.2 Predictions, scored

| prediction | outcome |
|---|---|
| `castail-acceptance` **31/31**, 17 cases, 15 controls, 1 pin, exit 0 | ✅ exact, three-sided |
| every predicted `zb` value, written down BEFORE the change | ✅ all six exact — `Skip :SK / Found:RT`, `10 PRINT"ZQ9"`, `<load-failed>`, and `Found:SK` / `'WX    '` / `'      '` unchanged |
| main page 1 165 → **158 B** | ✅ exact |
| main low / sub p0 / sub p1 unmoved | ✅ 3 / 3843 / 1483 |
| `basic-reloc.rom` = **`8b352603…`**, the scout build's hash | ✅ exact — the shipped code differs from the scout only in comments, and the claim that this makes them byte-identical is now measured |
| `zerobas-main-eu.rom` moves; `sub.rom` and `disk.rom` hold | ✅ exact — and re-confirmed by 8 knife builds |
| `deadcode` main **1566 spans / 287 seeds**, sub **1517 / 102** | ✅ exact — all four halves; the slice defines and deletes no label |
| closure `--page1` **585 + 43** | ✅ exact — a main-ROM edit is not in a sub-ROM tenant's closure |
| `audit-citations` 722 → **724** files swept | ✅ exact — two new `.md` |
| `audit-citations` basic **107 / 186**, unchanged | ✅ exact — and this is the counter [spec-basic-cassearch.md](spec-basic-cassearch.md) §7.5(b) got wrong one slice ago in the opposite direction. It is a list of FILES; extending a probe cannot move it |
| `injector-check` **331**, `preflight-check` **181/86/95/95/0** | ✅ unchanged |
| `unit-test` **58**, `latch-check` **16/16** | ✅ unchanged |
| every other acceptance gate unchanged | ✅ — §7.6 |
| **K-CO1's predicted RED set** | ❌ **wrong in three memberships, in opposite directions — §7.4** |

### 7.3 🔴 The runner was broken TWICE, in the same place, and only a knife could find it

K-CO1 round 1 **aborted** on a report that was complete: *"report TRUNCATED"* over
32 rows. Two independent faults, both in the runner's parsing of the exit-2 shape,
and neither is visible on any green run:

1. **Layout.** `basic_probe_castail.py` prints `ok `/`DIFF`/`PIN ` rows at column 0
   and exit-2 `....` rows indented two spaces. An `^`-anchored row regex therefore
   matches every green run and **no knifed one** — so the guard that exists to
   catch a truncated report fired on the complete one, killing exactly the knife
   whose purpose was to fail a control.
2. 🔴 **Row notes, which is worse because it does NOT abort.** After fixing (1)
   the runner still scored `cas-load-plain:search` — a pin that never moved —
   as RED under **all three** cutting knives, because the same row carries
   `   [PINNED DIVERGENCE]` at rc 0 and `  (not scored)` at rc 2 and only one of
   them was being stripped. A false CUT, silently, on the one row in the battery
   that asserts a value.

Both are the same underlying mistake: **diffing report LINES instead of readings.**
A cut in zerobas can only move zerobas, so the reading is *the side-under-test's
value*, and everything else on the line is the printer. That rule is now in
[dev-workflow.md](dev-workflow.md) §Knives; the probe-side half — whether a probe
should print ONE row shape on every exit path — is filed in `TODO.md`, unpriced.

⚠️ **The second fault cost a full re-run of every knife**, because the runner kept
no raw reports. It does now. A scorer bug should cost a re-score, not a re-measure.

### 7.4 🔴 K-CO1's red set was wrong in THREE memberships, from ONE inherited claim

**K-CO1 predicted 5 red rows and measured 6, and only 4 of them are the same
rows.** The count is nearly right; the membership is wrong three times, in two
opposite directions, and both directions come from a single sentence I did not
measure.

* **Predicted RED, HELD: `cas2-opencase`.** With the capture cut, `CAS_WANT` holds
  cold-boot RAM, so the search compares **garbage** and misses everything — which
  produces the same `<load-failed>` the correct build produces for `rt`. The row
  separates *compared* from *did not compare*; under this cut the machine still
  compares, just not the user's name. That is a real limit of the row and it is
  worth knowing: `cas2-opencase` is a detector of the SHIPPED defect (where no
  compare happens at all) and **not** of every way the capture can break.
* **Predicted HELD, RED: `cas2-openbare` and `cas2-openbare:echo`.** I predicted
  `CAS_WANT_ON = 0` at cold boot from a comment in `basic/interp.asm` — *"openMSX
  zero-fills RAM, hiding the omission"*. **Measured, it does not, at this
  address**: under K-CO1 `cas-openout:tape` reads `'ÿÿÿÿÿÿ'`, so `CAS_WANT` is
  `FF FF FF FF FF FF` and the flag is non-zero. The bare form therefore tried to
  match too.

🔴 **A SENTENCE IN A COMMENT IS A CLAIM, AND IT WAS WRITTEN ABOUT A DIFFERENT
ADDRESS FOR A DIFFERENT PURPOSE.** That comment is true of the cells it guards
(`ERRFLG`/`ERRLIN`/`DOT`, which `init` explicitly zeroes *because* real hardware
would not). I read it as a statement about openMSX's RAM in general and used it to
predict a knife's red set. This is exactly [spec-basic-cassearch.md](spec-basic-cassearch.md)
§7.5's habit — *predicting from a narrative instead of from the thing itself* —
one slice later, wearing behaviour instead of a count. The three counts this slice
got exactly right are the three whose **definitions** I opened (`sweep_files`,
`provenance_files`, `external_names`); the one I got wrong is the one I took from
prose.

🎯 **And the correction improves the evidence rather than weakening it.** The
measured set says the INPUT half of the change is detected by **four** rows
(`cas2-open`, `:echo`, `cas2-openbare`, `:echo`) and the OUTPUT half by **two**,
and that `cas2-openbare` catches a cut that merely *removes* the capture as well
as the wrong-fix cut K-CO3 was built for. The survivor claim in §3.2 is covered
twice over.

### 7.5 🎯 The knives — 4 designed, 4 run, each TWICE, both rounds identical

| # | cut | rc | RED | HELD |
|---|---|---|---|---|
| **K-CO1** | `oo_dev_cas`: `call cas_capture_name` → `call tape_parse_name` | **2** | 6 rows: `cas2-open`, `cas2-open:echo`, `cas2-openbare`, `cas2-openbare:echo`, `cas-openout:tape`, `cas-openoutbare:tape` | 26 rows — all 8 `CASES`, `cas2-load`/`merge`/`cload`/`bare` + listings, `cas-load-plain:search` **pin holds**, `cas2-opencase` (§7.4), both `:data`, both `:alive` |
| **K-CO2** | `oocas_do_out`: `ldir` → `nop` / `nop` | **2** | 🎯 **exactly 2 — `cas-openout:tape`, `cas-openoutbare:tape`** | 30 rows — **every INPUT row, including all three OPEN-input rows** |
| **K-CO3** | `cas_capture_name`'s `ccn_flag`: `jr z` → `jr nz` (matching armed for the EMPTY name) | **2** | 🎯 **exactly 4 — `cas2-openbare`, `:echo`, `cas2-bare`, `:listing`** | 28 rows — `cas2-open` + `:echo`, `cas2-opencase`, `cas2-load`/`merge`/`cload` + listings, both `:tape` rows |
| **K-CO4** | the `ldir` block moves up to the capture site | **0** | 🎯 **nothing — the declared predicted miss, 32/32 held** | every row |

**Three of four are EXACT on rc *and* on the red SET**, and both rounds of all
four are byte-identical to each other. All four reached the artifact —
`basic-reloc.rom` and `zerobas-main-eu.rom` moved on every cut build, so
DID-NOT-HAPPEN never had to be declared, **including for K-CO4**, which is the
whole reason that knife exists.

🎯 **K-CO2 IS THE ONE THAT SEPARATES THE TWO HALVES OF A THREE-EDIT CHANGE.** It
reddens the two OUTPUT readings and **nothing else** — so the 11 bytes of copy are
attributable, and the INPUT claim is carried by rows that this cut leaves alone.
Nothing else here could show that: K-CO1 reddens both halves at once.

🎯 **K-CO3 IS A KNIFE OF A ROW, AND THE ROW PASSED.** `cas2-openbare` exists to
say *"the fix did not arm the bare form"* — invisible while the fix is correct.
Built wrong (matching always on), the row reddens, and so does `cas2-bare`, which
is the correct and worth-stating consequence: the capture is shared with
`LOAD"CAS:"`. Without it the §3.2 survivor claim would rest on nothing.

### 7.6 Corpus — 19 gates, sequential from clean, all PASS

`unit-test` **ALL 58 files** · `audit-citations` CLEAN (**724** files swept,
basic **107 files / 186** provenance-bearing) · `preflight-check`
**181/86/95/95/0** · `injector-check` ALL PASS, **331** files · `latch-check`
**16/16 rows** · page-1 closure **585 routines + 43 data labels, no main-page-1
escape** · `deadcode` main **1566 spans / 287 seeds** → 0 dead, sub
**1517 / 102** → 0 dead (+1 allowlisted) · `lnblank-acceptance REPEAT=2` ·
`lnblank-say-acceptance` · `logicops-acceptance` · `float-acceptance` ·
`linemax-acceptance` · `dexp5-pin` · `editverb-acceptance` **61/61** ·
`lptverb-acceptance` **44/44** · `dskmsg-acceptance` **5/5** ·
`diskbasic-acceptance` **34/34 verbs** · `fat-error-acceptance` **8/8 FIND +
2/2 MOUNT + 5 directory checks, 8 of 8 verb controls** · `runtail-acceptance`
**9/9** · `castail-acceptance` **31/31 + 1 pin**.

⚠️ **`diskbasic` and `fat-error` are called out on purpose.** `OPEN"CAS:"` shares
`MAXFILES`, the channel-mode table and `oo_parse_as_chan` with the disk verbs, and
this slice edits the file those live in. Both are unchanged, which is a
measurement of that sharing and not a formality.

⚠️ **The ROM moved, so no emulator gate is skipped or waved through.** Two of the
four images change; the two that hold make the unchanged gates a stronger
statement, not a reason to skip them.

Build hashes at the end of the corpus run, identical to §7.1 and to the eight
knife restores: `basic-reloc.rom 8b352603…`, `sub.rom b3761022…`,
`disk.rom 2c630d3d…`, `zerobas-main-eu.rom 37d0f328…`.

## 8. Out of scope, said explicitly

* **The tape-search progress line** is D-CASSEARCH's, closed, and untouched here.
* **`SAVE"CAS:"` / `CSAVE`** never run the search and do not go through
  `oo_dev_cas`; nothing here reaches them.
* **A name longer than six characters** on any cassette verb — the shared capture
  truncates, no row asks, not claimed.
* **The wording of the aborted-load message** stays the quarantined divergence,
  normalised per side.
