<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASSAVE — `SAVE"CAS:name"` writes an ASCII tape

Closes the residual [dotgaps-msx1-characterization.md](dotgaps-msx1-characterization.md)
§3.2 found, pinned as `csv-tok` and filed. Reference reading:
[cassave-msx1-characterization.md](cassave-msx1-characterization.md).
Gate: `make cassave-acceptance`
([`probes/basic/basic_probe_cassave.py`](../probes/basic/basic_probe_cassave.py)).

## 1. What was filed, and what the scout found

Filed: *"`SAVE"CAS:name"` writes a TOKENISED tape; both references write ASCII."*
On an MSX1 `CSAVE` is the tokenised cassette write and `SAVE"CAS:"` is the ASCII
one, `,A` or not. zerobas already **has** the ASCII cassette writer
(`cas_ascii_save`, M2 of `spec-cas-ascii-saveload.md`), so the fix is a dispatch
default in [`basic/save.asm`](../basic/save.asm) `sav_is_cas`.

**Scouted and measured, before proposing anything:**

* 📏 **Priced by building it: 0 B.** `sav_is_cas`'s no-flag arm ends
  `jp tape_save_basic`; the fix is `jp cas_ascii_save` — one absolute jump for
  another, byte for byte. All four walls unmoved (3 / 158 / 3843 / 1483), and
  `basic-reloc.rom` moves, so the change reaches the artifact.
* 🟢 **Nothing is orphaned.** `tape_save_basic` keeps both `CSAVE` callers (the
  `,speed` path's `jr` and `csav_noname`'s fall-through), so `check_dead_code`
  has nothing to refuse.
* 🟢 **The exit convention already matches.** `sav_cas_flag` falls straight into
  `cas_ascii_save` today, so the `,A` spelling has been returning from there since
  M2; the no-flag arm reaching the same label is the same code doing the same
  thing.

### 1.1 🔴 A 0-BYTE FIX IS THE SHAPE THAT HIDES A CONFLATION, and this one is nameable

[[a-filed-zero-byte-fix-can-hide-a-conflation]] is a landed defect in this tree,
and the hazard here is concrete rather than theoretical: the fix makes
`SAVE"CAS:x"` and `SAVE"CAS:x",A` **literally one code path**. A one-line diff
cannot tell you whether that merged two behaviours which should stay apart — only
a measurement of **both forms on both references** can, and `,A` had never been
decoded.

Measured (reading §3): same `:id`, same `:name` shape, **identical** `:text`.
The conflation is refuted rather than assumed.

### 1.2 🔴 And the FILED reading was one machine, on a SHIPPED format

§3.2 decoded the VG-8020 only. Re-specifying a save format zerobas already ships,
on one machine's word, is exactly what the two-reference rule exists to stop.
Measured: the CF-3300 writes `$EA` too, on both `SAVE` forms, and `$D3` for
`CSAVE` — twenty readings, two references agreeing on all twenty.

## 2. The mechanism

```
sav_is_cas:   call tape_parse_name        ; TSV_NAME; HL -> closing '"'
              ... optional ',' ...
              jp   tape_save_basic        ; <- no flag: TOKENISED ($D3 header)
sav_cas_flag: ... require 'A' ...
              ; falls into
cas_ascii_save:                           ; <- ',A': ASCII ($EA header + listing)
```

`tape_save_basic` sets `SV_OP_SAV_CAS` and enters the sub-ROM page-1 save tenant;
`cas_ascii_save` writes the `$EA` header and drives `list_all` through the page-0
detokeniser into the cassette sink. Both already ship. **The defect is one jump
target**, and `CSAVE` reaches `tape_save_basic` by its own two paths, so it is
unaffected.

## 3. The change

| site | change | bytes |
|---|---|---|
| `sav_is_cas` no-flag arm | `jp tape_save_basic` → `jp cas_ascii_save` | **±0** |
| `basic/save.asm:12` header | the format table now documents ASCII for `SAVE"CAS:"` | comment |
| `basic_probe_tape_save.py` `test_save_cas_format` | oracle inverted: `$EA` + the listing, not `$D3` + the image | probe |
| `basic_probe_lnblank.py` `KNOWN_DIVERGE` | `csv-tok` re-measured — §4.1 | probe |

### 3.1 What is deliberately NOT done

* 🔴 **`CSAVE` is not touched.** Reading §4: `$D3` on all three sides, zerobas
  already correct. Knife K-CS3 is what proves the fix did not reach it.
* 🔴 **The read side is not touched.** `LOAD"CAS:"` accepting a tokenised tape
  where the reference does not return is a **separate filed residual**, and it is
  a judgement call about bug-for-bug fidelity costing a working feature. Nothing
  here changes what any loader accepts.
* **`BSAVE"CAS:"` (`$D0`) and the `,speed` clause** are untouched and unmeasured.

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

⚠️ Every count predicted by opening the line that computes it — the
[spec-basic-cassearch.md](spec-basic-cassearch.md) §7.5 discipline, and its
behavioural twin [spec-basic-casopen.md](spec-basic-casopen.md) §7.4.

| measurement | baseline `21d7538` | predicted after |
|---|---|---|
| `cassave-acceptance` | 16/20 | **20/20 readings agree (4 cases, 8 positive controls)**, exit 0 |
| `sav-cas:id` / `sav-cas-bare:id` (zb) | `D3` | **`EA`** |
| `sav-cas:text` / `sav-cas-bare:text` (zb) | ` ZQ8 /  ZQ9` | **`10 REM ZQ8 / 20 REM ZQ9`** |
| `csave:*` (zb) | `D3`, ` ZQ8 /  ZQ9` | **unchanged** — the control |
| `sav-cas-a:*` (zb) | `EA`, the listing | **unchanged** |
| all four walls | 3 / 158 / 3843 / 1483 | **unchanged — 0 B** |
| `basic-reloc.rom` hash | `8b352603…` | **`2acb25db…`** — the scout build's hash, since the shipped code differs from it only in comments |
| `zerobas-main-eu.rom` hash | `37d0f328…` | **CHANGES** |
| `sub.rom` / `disk.rom` | `b3761022…` / `2c630d3d…` | **BOTH UNCHANGED** |
| `lnblank-acceptance` `csv-tok` | pinned `' 5  0 '` | 🔴 **ROTS BY DESIGN → `' 40  0 '`**, §4.1 |
| `deadcode` main / sub | 1566/287 · 1517/102 | **unchanged** — no label defined or deleted; `tape_save_basic` keeps its two `CSAVE` callers |
| closure `--page1` | 585 + 43 | **unchanged** — a main-ROM edit is not in a sub-ROM tenant's closure |
| `audit-citations` files swept | 724 | **727** — `sweep_files()` walks every `.md/.asm/.inc/.py/…`; this slice adds two `.md` and one `.py` |
| `audit-citations` basic files / provenance-bearing | 107 / 186 | **107 / 187** — `provenance_files('basic')` is a list of FILES including `probes/basic/*.py`, and this slice adds **one**; `TARGETS['basic']` (the `.asm` list) is untouched |
| `injector-check` | 331 | **332** — one new file under `probes/` |
| `preflight-check` | 181/86/95/95/0 | **unchanged** — the new probe drives `omsx_repl` and contributes **no launch site**, exactly like `basic_probe_castail.py` |
| `unit-test` / `latch-check` | 58 / 16-16 | **unchanged** |
| `castail-acceptance` | 31/31 + 1 pin | **unchanged** — nothing here touches the read side or `cas_write_ea_header` |
| every other acceptance gate | | **unchanged** |

⚠️ **`audit-citations` basic provenance-bearing is predicted to MOVE this time,
and that is not a reversal of the previous slice's lesson — it is the lesson.**
[spec-basic-cassearch.md](spec-basic-cassearch.md) §7.5(b) established that the
counter counts **files**; D-CASOPEN extended an existing probe, so it correctly
predicted no change. This slice adds a **new** `probes/basic/*.py`, so the same
definition predicts **+1**. The rule is the definition, not the direction.

## 4.1 🎯 The `csv-tok` pin ROTS on purpose — RE-MEASURED, and then RECLASSIFIED

`basic_probe_lnblank.py`'s `KNOWN_DIVERGE` pins `csv-tok` at zerobas's exact
` 5  0 `, with a comment naming this slice as its owner and saying *"fix the
format and this row goes green with no `.` change at all."* The moment the format
lands, the pin rots and `lnblank-acceptance` **fails — by design**
([[a-pinned-divergence-is-a-live-detector]]).

**The decision: `csv-tok` is REMOVED from `KNOWN_DIVERGE` and becomes an ordinary
scored row**, predicted to agree at ` 40  0 ` on all three sides — the value both
references already read (`dotgaps` §3.1). That is not a loosening: a
`KNOWN_DIVERGE` entry *suppresses* a row from the agreement verdict, so deleting
it makes the row **stricter**, not weaker, and its neighbours `csv-asc` and
`csv-csave` are already scored agreement rows of exactly that shape.

🎯 **And this is the rare pin that is discharged by a fix in a DIFFERENT
battery.** `csv-tok`'s subject is `.`; its cause is a save format. The row goes
green **with no `.` change at all**, which is the prediction its own comment
wrote down, and scoring it is how that prediction gets tested.

## 5. The knives — predicted RED **and** predicted GREEN survivors

Every cut is **byte-neutral**, the subject is the probe invoked directly (never
`make`), each runs **twice**, the runner rebuilds from clean before every probe
run, hashes **all four** ROMs after every cut build, parses every exit-code shape,
diffs **per-side readings and never report lines**
([[never-diff-report-lines-diff-readings]], landed one slice ago), and restores
from a scratchpad snapshot in a `finally`.

🔴 **EVERY KNIFE RUNS BOTH `cassave` AND `castail`**, because one of the cuts
lands in an emitter the two batteries **share** (`cas_write_ea_header` serves
`SAVE"CAS:",A` *and* `OPEN"CAS:" FOR OUTPUT`). Running only the subject battery
would let K-CS2's reach be *asserted* instead of measured, and asserting the reach
of a shared routine is the mistake
[[a-shared-engine-fix-must-measure-its-other-callers]] records.

| # | cut | predicted RED | predicted GREEN survivors | rc |
|---|---|---|---|---|
| **K-CS1** | `sav_is_cas`: `jp cas_ascii_save` → `jp tape_save_basic` — the fix, reverted | `sav-cas:id`, `sav-cas:text`, `sav-cas-bare:id`, `sav-cas-bare:text` | `csave:*` **all four**, `sav-cas-a:*` **all four**, every `:name`, every `:alive`, every subject `<nothing>`; **castail 31/31 + 1 pin, entirely green** | **1** |
| **K-CS2** | `cas_write_ea_header`: `ld a,ASCII_ID` → `ld a,BASIC_ID` — every `$EA` header becomes `$D3` | `sav-cas:id`, `sav-cas-a:id`, `sav-cas-bare:id` — **the `:id` readings ONLY**; 🔴 **and in castail, `cas-openout:tape` + `cas-openoutbare:tape`, the SHARED-emitter reach** | every `:text` (the body is untouched), every `:name`, `csave:*`, and castail's 26 other rows | **1** cassave / **2** castail |
| **K-CS3** | `tape_save_basic`: `ld a,SV_OP_SAV_CAS` / `jp sv_tenant` → `nop` / `nop` / `jp cas_ascii_save` — the fix OVER-REACHES to `CSAVE` | `csave:id`, `csave:text` | 🎯 **`sav-cas:*` and `sav-cas-a:*` unchanged** — this cut isolates the control; castail entirely green | **1** |

⚠️ **K-CS1 AND K-CS3 EXIT 1, NOT 2, AND THAT IS PREDICTED RATHER THAN HOPED.**
`:text` is a containment control wanting `ZQ8` **and** `ZQ9`, and a *tokenised*
body still contains both (` ZQ8 /  ZQ9`). So the controls HOLD and the rows merely
DIFF. A runner assuming "a control row that moves means exit 2" would be wrong on
both.

⚠️ **K-CS2 IS THE ONE THAT SEPARATES THE ID FROM THE BODY.** K-CS1 moves both
halves of a format at once; K-CS2 moves only the header byte. If `:text` did not
hold under it, `:text` would be reading the header rather than the data block and
the whole `:text` design would be wrong.

⚠️ **K-CS3 IS A KNIFE OF THE CONTROL.** `csave` exists to say *"the fix did not
reach the tokenised writer"* — invisible while the fix is correct. Built wrong,
the row must red; if it does not, §3.1's claim rests on nothing.

⚠️ **NO PREDICTED-MISS KNIFE HERE, and it is declared rather than omitted
silently.** All three cuts are predicted to move readings, so the ROM-hash guard
is exercised by all three; there is no site in this one-jump change whose
relocation would be unobservable, so a K-CS4 in the shape of D-CASOPEN's K-CO4
would be invented rather than found.

## 6. As-built

### 6.1 The change, and the walls

**0 B — one absolute jump for another.** Measured from clean:

| wall | before | after |
|---|---|---|
| main low region | 3 B | **3 B** |
| main page 1 | 158 B | **158 B** |
| sub page 0 | 3843 B | **3843 B** |
| sub page 1 | 1483 B | **1483 B** |

ROM hashes: `basic-reloc.rom` `8b352603… → 2acb25db…` and `zerobas-main-eu.rom`
`37d0f328… → fd0bfa21…`; `sub.rom b3761022…` and `disk.rom 2c630d3d…` **both
unchanged**. The six knife builds re-confirm it: every one moved those two and
only those two, and the tree hashed back to all four baselines after the restore.

⚠️ **A zero-byte change still moves the ROM, and that matters here**: `2acb25db`
is a *different image* from `8b352603` at the same size, which is what separates
this from a comment-only edit and is why the knife runner's hash guard never had
to declare DID-NOT-HAPPEN.

### 6.2 Predictions, scored

| prediction | outcome |
|---|---|
| `cassave-acceptance` **20/20**, 4 cases, 8 controls, exit 0 | ✅ exact, three-sided |
| `sav-cas:id` / `sav-cas-bare:id` (zb) → `EA` | ✅ exact |
| `sav-cas:text` / `sav-cas-bare:text` (zb) → the full listing | ✅ exact |
| `csave:*` unchanged (`D3`, ` ZQ8 /  ZQ9`) | ✅ exact — the fix did not over-reach |
| `sav-cas-a:*` unchanged | ✅ exact |
| all four walls unchanged at **0 B** | ✅ 3 / 158 / 3843 / 1483 |
| `basic-reloc.rom` = **`2acb25db…`**, the scout build's hash | ✅ exact — the shipped code differs from the scout only in comments |
| `zerobas-main-eu.rom` moves; `sub.rom` + `disk.rom` hold | ✅ exact |
| `lnblank` `csv-tok` rots → ` 40  0 `, de-pinned into the scored set | ✅ §6.5 |
| `deadcode`, closure, `injector-check`, `audit-citations`, `preflight-check` counts | ✅ §6.5 |
| **K-CS2's `castail` red set** | ❌ **under-counted: predicted 2, measured 4 — §6.4** |

### 6.3 🎯 The knives — 3 designed, 3 run, each TWICE, on BOTH batteries

| # | cut | probe | rc | RED | HELD |
|---|---|---|---|---|---|
| **K-CS1** | `sav_is_cas`: `jp cas_ascii_save` → `jp tape_save_basic` (the fix, reverted) | `cassave` | **1** | 🎯 **exactly 4** — `sav-cas:id`, `sav-cas:text`, `sav-cas-bare:id`, `sav-cas-bare:text` | 16 |
| | | `castail` | **0** | 🎯 **nothing — 31/31 + 1 pin** | 32 |
| **K-CS2** | `cas_write_ea_header`: `ld a,ASCII_ID` → `ld a,BASIC_ID` | `cassave` | **1** | 🎯 **exactly 3 — the `:id` readings ONLY** | 17 |
| | | `castail` | **2** | 4 — the two `:tape` **and** the two `:data`, §6.4 | 28 |
| **K-CS3** | `tape_save_basic` → `nop`/`nop`/`jp cas_ascii_save` (the fix OVER-REACHES to `CSAVE`) | `cassave` | **1** | 🎯 **exactly 2 — `csave:id`, `csave:text`** | 18 |
| | | `castail` | **0** | 🎯 **nothing** | 32 |

**10 of 12 runs EXACT on rc *and* on the red set**, both rounds byte-identical.

🎯 **K-CS2 SEPARATES THE HEADER FROM THE BODY, and that is what validates the
`:text` design.** It moves only the id byte, and every `:text` reading holds. Had
`:text` moved under it, `:text` would have been reading the header rather than the
data block and the whole cross-side-comparable-payload idea would be wrong.

🎯 **K-CS3 IS A KNIFE OF THE CONTROL, AND THE CONTROL PASSED.** `csave` exists to
say *"the fix did not reach the tokenised writer"* — invisible while the fix is
correct. Built wrong, `csave:id` and `csave:text` red and **`sav-cas*` does not
move**, so §3.1's "CSAVE is not touched" rests on a measurement.

🎯 **AND `castail` BEING GREEN UNDER K-CS1 AND K-CS3 IS A RESULT, NOT A
FORMALITY.** It says the SAVE dispatch and the tokenised writer are not on
`OPEN"CAS:"`'s path — measured, on the slice right after one whose whole lesson
was that a shared engine's other callers must be measured.

### 6.4 🔴 K-CS2's cross-probe red set was UNDER-COUNTED, from a function I wrote last slice

Predicted *"`cas-openout:tape` + `cas-openoutbare:tape`"*; measured **four** —
both `:tape` readings **and** both `:data` readings.

The cause is one line: `basic_probe_castail.py`'s `tape_readback` returns the
sentinel for **both** of its readings when the `$EA` run is absent
(`return "<NO $EA HEADER>", "<NO $EA HEADER>"`). With the id byte knifed to `$D3`
there is no `$EA` run, so the `:data` half moves too — necessarily, by
construction.

🔴 **I predicted from the narrative *"the shared emitter writes the id, so the id
readings move"* instead of from the function's own return statement** — and I
wrote that function one slice ago. This is
[[a-count-is-predicted-by-reading-its-definition]] on a definition of my own,
which is the version that feels safest to skip.

🎯 **The substantive claim held and is the reason the cross-probe run exists.**
K-CS2's *reach* — that `cas_write_ea_header` is shared by `SAVE"CAS:",A` and
`OPEN"CAS:" FOR OUTPUT`, so a cut there is visible in a battery this slice does
not own — was predicted, measured, and is stronger than predicted. Asserting that
reach instead of measuring it is the mistake
[[a-shared-engine-fix-must-measure-its-other-callers]] records.

### 6.5 Corpus — 20 gates, sequential from clean, all PASS

`unit-test` **ALL 58 files** · `audit-citations` CLEAN (**727** files swept,
basic **107 files / 187** provenance-bearing) · `preflight-check`
**181/86/95/95/0** · `injector-check` ALL PASS, **332** files · `latch-check`
**16/16 rows** · page-1 closure **585 + 43**, no main-page-1 escape · `deadcode`
main **1566 spans / 287 seeds** → 0 dead, sub **1517 / 102** → 0 dead
(+1 allowlisted) · `lnblank-acceptance REPEAT=2` **539/539 gating rows** ·
`lnblank-say-acceptance` · `logicops` · `float` · `linemax` · `dexp5-pin` ·
`editverb` **61/61** · `lptverb` **44/44** · `dskmsg` **5/5** · `diskbasic`
**34/34 verbs** · `fat-error` **8/8 FIND + 2/2 MOUNT + 5 directory checks** ·
`runtail` **9/9** · `castail` **31/31 + 1 pin** · `cassave` **20/20**.

Hashes at the end of the corpus run, identical to §6.1 and to the six knife
restores: `basic-reloc.rom 2acb25db…`, `sub.rom b3761022…`,
`disk.rom 2c630d3d…`, `zerobas-main-eu.rom fd0bfa21…`.

🎯 **`audit-citations` basic 186 → 187 IS THE PREDICTION THAT MATTERS HERE.**
[spec-basic-cassearch.md](spec-basic-cassearch.md) §7.5(b) got this counter wrong
by predicting a move that could not happen, and D-CASOPEN got it right by
predicting no move. This slice predicts **+1** and measures **+1** — from the same
one-line definition, in the opposite direction, because it adds a real
`probes/basic/*.py`. The rule is the definition, not the direction.

### 6.6 🎯 `csv-tok` — the pin discharged by a fix in a DIFFERENT battery

| row | VG-8020 | CF-3300 | zb before | zb after |
|---|---|---|---|---|
| `csv-ctl` 🟢 | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` |
| `csv-asc` (`SAVE"CAS:D",A`) | ` 40  0 ` | ` 40  0 ` | ` 40  0 ` | ` 40  0 ` |
| **`csv-tok`** (`SAVE"CAS:E"`) | ` 40  0 ` | ` 40  0 ` | **` 5  0 `** 📌 | **` 40  0 `** ✅ |
| `csv-csave` 🟢 (`CSAVE"F"`) | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` | ` 5  0 ` |

**4/4 gating rows agree, 0 allowlisted as `KNOWN_DIVERGE`.** The row went green
with **no `.` change at all** — which is the prediction its own pin comment wrote
down, and de-pinning it is how that prediction got tested rather than assumed.

🎯 **`csv-csave` holding at ` 5  0 ` is the other half of the result.** If the fix
had reached `CSAVE`, that row would have moved to ` 40  0 ` too and the `.` rule
*"an ASCII output walk writes it; a tokenised write does not"* would have lost its
contrast. It is the same claim K-CS3 knifes, measured here by a different battery
on a different readout.

## 7. Out of scope, said explicitly

* **The read side.** `LOAD"CAS:"` accepting a tokenised tape where the reference
  waits forever stays filed in `TODO.md` — bug-for-bug fidelity there costs a
  working feature and the judgement is not this slice's.
* **`BSAVE"CAS:"`**, the `,speed` clause, and names longer than six characters.
* **Byte-exact block framing** of the ASCII cassette file — `:text` reads the
  printable content, which is what a format question needs.
