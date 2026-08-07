# D-SUBWALL — a gated readout for the two sub-ROM walls, and the historical series re-derived

Filed against `0cbf495` (D-LFILES landed, tree clean, all gates green).
Closes the first `- [ ]` of [`TODO.md`](../TODO.md) §"Open — standing residuals":
**"THE SUB-ROM WALLS HAVE NO GATED READOUT, AND THE RECORDED FIGURES DO NOT
REPRODUCE"**, filed by D-LFILES
([`spec-basic-lfiles.md`](spec-basic-lfiles.md) §6.3).

---

## 0. The residual, and what the asymmetry actually is

[`tools/check_reloc.py`](../tools/check_reloc.py) prints **both MAIN walls on every
build** — page-0 low region and page 1 — from the zero-byte `__MEAS_LOW_END` /
`__MEAS_PAGE1_END` labels, and `make basic-reloc` runs it. Its own docstring says
why the `.sym` argument is REQUIRED rather than optional: *an optional sym is
precisely the shape in which a wall readout silently stops printing while the gate
still exits 0.*

The sub ROM has neither label and no readout. Every sub-ROM wall figure this repo
has ever recorded is therefore a number some slice measured by hand, with whatever
instrument it reached for that day, and nothing has ever cross-checked one against
the next.

D-LFILES found the consequence: rebuilt at `b5f4135` the sub ROM measures
**3852 / 1821** where D-LPTVERB, D-EDITVERB and `MEMORY.md` all record
**3869 / 1824**.

This slice does three things:

1. adds the two labels and a gated readout (§2);
2. re-derives the whole historical series by **building every commit** (§3), which
   answers *which* recorded figures are wrong and how far back it goes;
3. answers *what the old number was* — the brief's hypotheses (a different page
   end, a different pad convention, a stale `sub/basic-resident-abi.inc`) are each
   TESTED, and each refuted (§3.4).

---

## 1. The datum

Measured from a removed `build/` at `0cbf495`:

| wall | free |
|---|---|
| main page-0 low `$2812-$3FFF` | **3 B** |
| main page 1 `$4000-$7FFF` | **194 B** |
| sub page 0 `$0000-$3FFF` | **3843 B** |
| sub page 1 `$4000-$7FFF` | **1542 B** |

ROM hashes at `0cbf495`: `disk.rom 2c630d3d…`, `sub.rom 01805491…`,
`basic-reloc.rom 29032918…`, `zerobas-main-eu.rom 50a1eaf6…`.

Baselines this slice must not move: `deadcode` main **1564 spans / 286 seeds → 0**,
sub **1510 spans / 102 seeds → 0 (+1 allowlisted)**; `injector-check` **327 files**;
`audit-citations` **706 files swept**; `preflight-check` **181 spawn sites, 86
exempt, 95 guarded, 0 UNGUARDED**; page-1 tenant closure **582+41**.

⚠️ The last two are corrected from the draft, which carried **180/85** and **522+41**
— see §6.5. Both are the newest figure anyone *recorded*, and neither is the figure
at `0cbf495`.

---

## 2. The instrument

### 2.1 Two zero-byte labels, and the control that is free

[`sub/sub.asm`](../sub/sub.asm) gets one label immediately in front of each pad:

```asm
__MEAS_SUB_P0_END:
                ds      $4000 - $, $FF
```
```asm
__MEAS_SUB_P1_END:
                ds      $8000 - $, $FF
```

This is the mechanism [`rom-region-structure-review.md`](rom-region-structure-review.md)
§0 prescribes, and it already names these two labels by these two names — it used
them, in a throwaway tree, and never landed them.

🎯 **THE INSTRUMENT'S OWN CONTROL IS FREE HERE.** A label emits nothing, so
`build/sub.rom` must stay **byte-identical at `01805491…`**. That is the same
argument §0 of the review made for its 111 injected include-site labels (*"both
instrumented images assemble BYTE-IDENTICAL to the shipped ROMs"*), and it is a
stronger control than any assertion about the numbers: **if the hash moves, the
instrument changed its subject.**

### 2.2 `tools/check_sub_walls.py` — the checks

Invoked `python3 tools/check_sub_walls.py build/sub.rom build/sub.sym`, wired into
`make basic-reloc` immediately after `check_reloc.py`, so the four walls print
together on every build.

| # | check | disposition |
|---|---|---|
| 1 | image is exactly 32768 B | instrument fault |
| 2 | `"CD"` at `$0000` and `"S1"` at `$4000` | instrument fault — **the positive control**, §2.4 |
| 3 | `.sym` defines BOTH `__MEAS_SUB_P0_END` and `__MEAS_SUB_P1_END` | instrument fault |
| 4 | each label lies inside its own page | **subject regression** — an overrun |
| 5 | every byte from each label to its page end is `$FF` | instrument fault — **the staleness detector**, §2.3 |
| — | print free = page end − label, for both pages | the readout |
| — | print the `$FF` tail-scan figure and, when it differs, by how much | §2.3 |

### 2.3 🎯 The label is authoritative and the `$FF` scan is a ONE-SIDED cross-check

The review says an `$FF` scan can lie, and this repo has an instance: 
[`spec-basic-msgexact.md`](spec-basic-msgexact.md) §166 records sub page 1 as
*"≈3084 B free (last symbol `$73F4`)"* where the true figure at that commit is
**3067** — a third instrument (last-symbol) over-reporting by the 17 B body of the
final routine.

So the two are NOT asserted equal. The relation that holds by construction is
one-sided:

* everything after the label IS pad, so **scan ≥ label, always**;
* `scan − label` is exactly the count of trailing `$FF` bytes in the real content,
  and is printed rather than hidden — it is the size of the lie a hand scan would
  tell today;
* **`scan < label` is impossible for a matched pair**, so check 5 firing means the
  `.sym` and the `.rom` are not from the same build. That is a staleness gate, and
  staleness is the failure mode this repo keeps paying for
  ([[makefile-subparts-stale-tenant]], [[stale-machine-reads-as-unimplemented]]).

⚠️ A one-sided bound is a shape this project has been burned by
([[one-sided-bound-passes-a-runaway]]), so the other side is covered by a
DIFFERENT check, not by widening this one: a runaway is an overrun, and check 4
catches an overrun by bounding the label inside its page. K5 measures what an
overrun actually does today.

### 2.4 What a DEAD subject scores — and why check 2 exists

[[gate-whose-answer-is-an-error-passes-a-dead-subject]]: for any gate, ask what a
totally dead subject scores.

Point checks 1/3/4/5 at a `build/sub.rom` of 32768 × `$FF` with the REAL `sub.sym`
and every one of them **passes**: the image is the right size, the labels are
present and in range, and every byte after each label is `$FF` — because every byte
is. The readout prints **3843 / 1542**, the correct answer, for a ROM with no ROM in
it. That is the dead-subject pass in its purest form, and it is why check 2 is in
the list: `"CD"` at `$0000` and `"S1"` at `$4000` are structural facts
[`sub/sub.asm`](../sub/sub.asm) states in prose (the MSX2 sub-ROM signature, and the
deliberately-NOT-`"AB"` page-1 marker), and they die on an all-`$FF`, an all-`$00`
and a truncated image alike. It is `check_reloc.py`'s own `"AB"`-at-`$4000` pin,
one ROM over.

**K4 runs this both ways** — with check 2 neutered, to show the hole is real, and
with it restored, to show it closes. A control asserted but not falsified is a
claim.

### 2.5 Exit codes

`1` = the subject regressed (check 4, an overrun). `2` = the instrument was not
functioning and nothing below it was measured (checks 1/2/3/5). ⚠️ The distinction
is only visible when the tool is invoked directly: **`make` exits 2 for any failed
recipe**, so a runner shelling out to `make basic-reloc` cannot tell them apart
([[injjudge-slice]]). Every knife below therefore invokes the SUBJECT, not its make
target.

---

## 3. The historical series, re-derived by BUILDING it

### 3.1 Method, and its denominator

`sub/sub.asm` was added at `c224252` (2026-07-11). Every one of the **436** commits
since was checked out into a throwaway worktree, `build/` removed, `make
build/sub.rom` run, and both pages' trailing-`$FF` runs measured. **424 built; 12
did not**, all of them older than `40647bd` (2026-08-02) and all outside the window
any disputed figure sits in. That is the denominator, and it is stated because a
hand-listed one is a scope claim ([[a-hand-listed-denominator-is-a-scope-claim]]).

The recorded claims were swept mechanically rather than listed: every line in
`docs/*.md`, `TODO.md` and the memory directory pairing a sub-page token with a
3–5 digit number. **112 sites across 45 files.**

### 3.2 The series that matters

| commit | slice | true p0 | true p1 | recorded | |
|---|---|---|---|---|---|
| `2aee774` | ROM REGION REVIEW + R1 | 4054 | 3357 | 4054 / 3357 | ✅ |
| `4b2202e`…`6efafed` | D-EXPBAD … D-KWGAP4 | 4026→3910 | 3339 | as recorded | ✅ |
| `3a25449` | D-RETLN | 3913 | 3339 | 3913 / 3339 | ✅ |
| `406b9e3` | D-DELETE | 3913 | 3145 | 3339 → 3145 | ✅ |
| `902d14d` | D-MSGSUB | 3913 | 2740 | 3067 → 2740 | ✅ |
| `40647bd` | D-MSGMIGRATE | 3913 | 2428 | 2740 → 2428 | ✅ |
| `638a141` | D-DOTLINE | 3913 | 2411 | 2428 → 2411 | ✅ |
| `52b2386` | D-EVLNO | 3913 | 2324 | 2411 → 2324 | ✅ |
| `9bfcfb9` | D-P0BASE | **3869** | 2324 | 3913 → 3869 | ✅ |
| `fd58b3a`…`0b31baa` | the JUDGE arc (9 commits) | 3869 | 2324 | 3869 / 2324 | ✅ |
| `fa0b952` | **D-EDITVERB** | 3869 | **1821** | 3869 / **1824** | 🔴 p1 **+3** |
| `8ca532a` | D-LPTVERB measurement | 3869 | **1821** | 3869 / **1824** | 🔴 inherited |
| `b5f4135` | **D-LPTVERB** | **3852** | **1821** | *"sub sides unchanged"* | 🔴 p0 **+17** |
| `0cbf495` | D-LFILES | 3843 | 1542 | 3843 / 1542 | ✅ |

🎯 **THE DRIFT DOES NOT GO BACK. It is two slices, and they are the last two before
the one that noticed.** Everything from D-P0BASE backwards — including the review's
own 4054 / 3357, D-P0BASE's −44, D-EVLNO's −87, D-MSGSUB's −327 and D-MSGMIGRATE's
−312 — reproduces to the byte. So does every figure in the entire JUDGE arc, and so
do [[funding-carve-save-engine]]'s 4097 and [[traps-t3-key-slice]]'s 4667. This is
not accumulating drift in a hand-carried number; it is **two independent unmeasured
"unchanged" claims**, which is a different defect with a different fix.

Of the 112 recorded sites, **8 are wrong** — 2 in
[`spec-basic-editverb.md`](spec-basic-editverb.md), 3 in
[`spec-basic-lptverb.md`](spec-basic-lptverb.md), 1 in `MEMORY.md`, 1 in
[[editverb-slice]], and `spec-basic-lfiles.md`'s baseline table, which that spec
already flags as disputed. **104 of 112 reproduce exactly.**

### 3.3 🔴 The 17: D-LPTVERB MEASURED IT, and wrote "unchanged" in the row above

Sub page 0 moved `3869 → 3852` at `b5f4135`, and the cause is not in doubt: the
only sub-side change in that commit is `basic/kwtable.inc` gaining the `LPRINT` and
`LPOS` entries, and `basic/kwtable.inc` is a **sub-ROM page-0 tenant** —
`sub/sub.asm` is its sole include site, which is the whole reason D-LFILES §1.1 could
say a keyword entry costs zero MAIN bytes.

D-LPTVERB's own §6.1 scoring table says, two rows below the wall row:

> `kwtable` pin bump | **1041 → 1058 B**, and **+17 is exactly** the 9 B `LPRINT` +
> 8 B `LPOS` entries — the delta itself says the table gained nothing else ✅

and the wall row says:

> 4.2 | low **23 B unchanged**; sub p0 3869 / p1 1824 unchanged | … **sub sides
> unchanged ✅**

⇒ **The old number was not mis-measured. It was not measured at all.** "Unchanged"
was the prediction, copied into the result column, while the refutation sat two rows
below it in the same table, correct, in bold, and connected to nothing. Precisely the
shape D-LFILES §6.3 found one slice later and one level down (*"the spec knew the fact
and the prediction did not use it"*), and precisely what a readout printed on every
build makes impossible: you cannot copy a prediction into a result column when
`make basic-reloc` prints the result.

### 3.4 🔴 The 3: a number no tree this repo has ever had

Sub page 1 at `fa0b952` is **1821**; D-EDITVERB recorded **1824**, in a §6.7 headed
*"run sequentially from a removed `build/`"*. The true carve is **−503**, not the
−500 the record derives from it.

The three hypotheses the residual named were tested, not assumed:

| hypothesis | test | result |
|---|---|---|
| a different **page end** | 1824 requires the page to end at `$8003` | **refuted** — outside a 32 KB image |
| a different **pad convention** | measured at `fa0b952`: `$FF`-tail **1821**; `$00`-tail **0**; `$FF`-or-`$00`-tail **1821** (page 0: 3869 / 0 / 3870) | **refuted** — no convention yields 1824 |
| a stale **`sub/basic-resident-abi.inc`** | assembled `fa0b952` against that file as committed at `0b31baa`, `6270177`, `52b2386` and `fa0b952` | **refuted** — all four give p0 3869 / p1 1821; the file is pure equates and cannot move a wall, and at `fa0b952` the committed copy already equals a fresh regen |
| a stale **`build/`** | the pre-slice value is 2324 | **refuted** — a stale artifact reads 2324, not 1824 |
| **arithmetic** (2324 − a 500 B design figure) | symbol-shift diff `0b31baa → fa0b952`: 203 page-1 labels shift **+503**, 46 shift +23, 408 shift 0 | **refuted** — there is no 500 anywhere in the delta; the record's *"500 B of sub page 1"* is a CONSEQUENCE of the wrong 1824, not its cause |

And the denominator settles it: **`p1=1824` occurs at 0 of the 424 buildable commits
in the sub ROM's entire history.** (`p1=1821` occurs at 5, `p0=3852` at exactly 1,
`p0=3869` at 14.)

⇒ **1824 is not a reading of any tree that has ever existed here.** The only account
left is an uncommitted working tree, three bytes short of what shipped — which is
exactly the class the residual names, and exactly what a per-build readout removes:
after this slice a sub wall figure comes out of `make basic-reloc` against the ROM
that is about to be committed, or it does not exist.

### 3.5 What is corrected, and what is recorded as superseded

**Nothing is rewritten.** The as-built sections of D-EDITVERB and D-LPTVERB are the
record of what those slices believed, and editing the numbers in place would destroy
the only evidence for §3.3's finding. Instead:

* each of the **5 wrong doc sites** gets an inline 🔴 correction line naming the
  measured value and pointing here — an ADDITION, never a substitution;
* `spec-basic-lfiles.md` §6.3 gets the answer appended to the question it filed;
* `MEMORY.md` and [[editverb-slice]] carry live guidance rather than history, so
  their figures are corrected outright;
* this §3.2 is the superseded series, in one place, with the commit for every row.

---

## 4. Predicted GREEN, at exact values — fixed BEFORE the change

1. `build/sub.rom` **byte-identical at `01805491…`**; `basic-reloc.rom
   29032918…`, `disk.rom 2c630d3d…`, `zerobas-main-eu.rom 50a1eaf6…` all
   unchanged. Zero bytes of ROM move.
2. `make basic-reloc` prints, after the two main walls:
   `sub page 0 free = 3843 B` and `sub page 1 free = 1542 B`, from the labels.
3. The `$FF` tail scan agrees with both labels **exactly** at `0cbf495`
   (`scan − label = 0` on both pages), so the readout prints no over-report note.
4. `deadcode`: **sub 1510 → 1512 spans** (two new labels, two new spans), sub seeds
   **102 unchanged**, **0 dead** both builds, +1 allowlisted. Both new spans are
   LIVE by FALLTHROUGH: `__MEAS_SUB_P0_END`'s predecessor span ends on
   `include "basic/kwtable.inc"` and `__MEAS_SUB_P1_END`'s on `include "lineno.asm"`,
   neither a terminator.
5. `deadcode` **main 1564 spans, 286 seeds** — unchanged, **and the seed SET
   unchanged too**. `check_dead_code.py` seeds the main walk with every identifier
   appearing anywhere under `sub/` and `tools/`, so a new tool and new comments can
   move it. The main build has only ten single-word lowercase labels (`detok`,
   `eval`, `exec`, `init`, `logtab`, `pchar`, `relink`, `repl`, `tokenise`,
   `upcase`); the new file and the new comments avoid all ten, and the only main
   labels they DO name — `__MEAS_LOW_END`, `__MEAS_PAGE1_END`, `is_letter` — are
   already seeds (`check_reloc.py` and `sub/sub.asm` name them today).
   ⚠️ Stated as a SET, not a total: a net-zero seed count is not an unchanged seed
   set (D-LFILES §6.4).
6. `audit-citations`: **706 → 708** files swept — this spec (`.md`) and
   `tools/check_sub_walls.py` (`.py`), both under `SWEEP_DIRS`/`SWEEP_EXTS`.
   Self-tests 10/10 11/11 12/12 14/14, 4 advisory all acknowledged.
7. `injector-check`: **327 → 328** files (`_sources()` yields every `.py` in the
   repo), 4 exempt, 3 RECORDs, 0 offenders.
8. `preflight-check`: ~~**180 spawn sites, 85 exempt**~~ → **181 / 86**, 95 require a
   guard, 95 guarded, 0 UNGUARDED — unchanged; the new tool spawns no process.
9. The three closure walks, `check_resident_abi`, `check_kwtable_identity`: OK,
   unchanged (122+4 / 718+15 / ~~522~~ **582**+41).

   ⚠️ §8 and §9 as first written are struck out above: they were **predictions
   copied from the newest RECORDED figure, not measured at the baseline** — §6.5.
   The claim in both ("unchanged") is correct; the numbers were not.
10. Every emulator gate at its recorded value: `unit-test` **58**, `latch-check`
    **16/16**, `lnblank-acceptance REPEAT=2` **539/539**, `lnblank-say-acceptance`
    **204/204**, `logicops-acceptance` **193**, `float-acceptance` ALL PASS,
    `linemax-acceptance` **60/60**, `dexp5-pin` **16**, `editverb-acceptance`
    **61/61**, `lptverb-acceptance` **39/39**. No ROM byte changes, so none of them
    can move; a move is a finding about the apparatus.

---

## 5. Falsification set — every knife names predicted RED **and** GREEN survivors, and is run TWICE

⚠️ Each knife invokes `python3 tools/check_sub_walls.py` directly, so its exit code
is the tool's and not `make`'s (§2.5). Cleanup restores from `HEAD`
([[knife-cleanup-restores-from-head]]).

| # | cut | predicted RED | predicted GREEN survivors |
|---|---|---|---|
| **K1** | delete `__MEAS_SUB_P0_END:` from `sub/sub.asm` — *falsify by deleting the code under test* | check 3 FAILs naming the missing label, **rc 2**; `make basic-reloc` fails | `check_reloc.py` still prints both MAIN walls; `sub.rom` still `01805491…`; dead-code, closure walks, `check_resident_abi` all OK |
| **K2a** | add 16 bytes to sub **page 0** (`db` block before the page-0 pad) | sub p0 free **3843 → 3827**, delta exactly **−16** | sub p1 free **1542 unchanged**; the readout is not reporting one page twice |
| **K2b** | add 16 bytes to sub **page 1** | sub p1 free **1542 → 1526**, delta exactly **−16** | sub p0 free **3843 unchanged** |
| **K3** | run the tool with `sub.sym` from `b5f4135` against `0cbf495`'s `sub.rom` — the historical failure mode, mechanised | check 5 FAILs: a non-`$FF` byte after the claimed pad start, **rc 2** | the matched `b5f4135` pair passes; the matched `0cbf495` pair passes |
| **K4** | 32768 × `$FF` `sub.rom` + the real `sub.sym`, run **twice**: (a) with check 2 removed, (b) intact | (a) **PASS, rc 0, prints 3843 / 1542** — the dead-subject hole, demonstrated not asserted; (b) check 2 FAILs on the `"CD"` signature, **rc 2** | in both, checks 1/3/4 pass — the point being that they cannot see this |
| **K5** | overrun sub page 1 (`ds` goes negative) | the build fails, or ships an empty image that check 1 rejects — **measured, not assumed** ([[negative-ds-ships-an-empty-rom]]) | sub page 0's figure is still computable from its own label |
| **K6** | neuter check 5 (the pad cross-check) alone | **K3 goes GREEN** — proving check 5, not something else, is what catches a stale `.sym` | checks 1/2/3/4 still fire on their own knives |

K2 is the knife that matters, and the reason is
[[readout-blind-to-its-own-subject]]: the question is never *"does it print a
number"* — a readout that prints a constant prints a number. It is **"does the
number MOVE when the wall moves, by exactly the amount the wall moved, on the page
that moved and not the other one."**

---

## 6. As-built — ✅ LANDED 2026-08-07

### 6.1 The control, first

**All four ROM hashes are byte-identical to `0cbf495`:**

| image | sha256 | |
|---|---|---|
| `build/disk.rom` | `2c630d3d…` | unchanged ✅ |
| `build/sub.rom` | `01805491…` | unchanged ✅ |
| `build/basic-reloc.rom` | `29032918…` | unchanged ✅ |
| `build/zerobas-main-eu.rom` | `50a1eaf6…` | unchanged ✅ |

Zero bytes of ROM moved. The labels emit nothing, so the instrument did not change
its subject — which is the strongest statement available about a measurement
apparatus, and the one §2.1 predicted.

### 6.2 Predictions, scored

| § | predicted | measured |
|---|---|---|
| 4.1 | all four hashes unchanged | ✅ §6.1 |
| 4.2 | `sub page 0 free = 3843 B`, `sub page 1 free = 1542 B` printed by `make basic-reloc` | ✅ `__MEAS_SUB_P0_END @ 0x30fd`, `__MEAS_SUB_P1_END @ 0x79fa` |
| 4.3 | scan − label = 0 on both pages, no over-report note | ✅ silent |
| 4.4 | sub **1510 → 1512** spans, 102 seeds, 0 dead (+1 allowlisted) | **1512 / 102 / 0 (+1)** ✅ — both new spans live by fallthrough exactly as reasoned |
| 4.5 | main **1564** spans, **286** seeds, **and the SET unchanged** | **1564 / 286**, and the set diff is `added []  dropped []` ✅ |
| 4.6 | `audit-citations` **706 → 708** | **708**, self-tests 10/10 11/11 12/12 14/14, 4 advisory ✅ |
| 4.7 | `injector-check` **327 → 328** | **328**, 4 exempt, 3 RECORDs, 0 offenders ✅ |
| 4.8 | `preflight-check` **180** spawn sites, **85** exempt | 🔴 **181 / 86**, at `0cbf495` too — the prediction was `grep`-ed from the record, not measured; §6.5 |
| 4.9 | closure `122+4 / 718+15 / `**`522`**`+41` | 🔴 **122+4 / 718+15 / 582+41**, at `0cbf495` too — same cause; §6.5 |
| 4.10 | every emulator gate at its recorded value | `unit-test` **58** ✅, `latch-check` **16/16** ✅, `lnblank REPEAT=2` **539/539** ✅; the rest **DELIBERATELY NOT RUN** — §6.6 |

### 6.3 The knives — 7 of 7 cut, both rounds, and one cut the instrument itself

| # | verdict |
|---|---|
| **K1** | **CUT** — rc **2**, *"build/sub.sym defines no `__MEAS_SUB_P0_END`"*; `make basic-reloc` rc 2. Every named survivor held: `check_reloc.py` still printed **3 B / 194 B** *in the same log*, dead-code rc 0 (sub 1511 spans), the page-1 closure walk rc 0, and `sub.rom` still `01805491…` — deleting a zero-byte label removes no bytes, which is the byte-identity claim proved from the other side |
| **K2a** | **CUT** — sub p0 **3843 → 3827**, exactly **−16**; sub p1 **1542 unchanged** |
| **K2b** | **CUT** — sub p1 **1542 → 1526**, exactly **−16**; sub p0 **3843 unchanged** |
| **K3** | **CUT** — rc **2**, both pages named with the offending byte and address (`0x05 @ 0x30f4`, `0x6f @ 0x78e3`). Both matched pairs pass — §6.4 |
| **K4** | **CUT, and it is the knife §2.4 was written for.** (a) check 2 removed: the all-`$FF` image scores **rc 0** and prints **3843 / 1542**, the correct figures for a ROM with no ROM in it. (b) intact: rc **2** on both anchors. The hole is demonstrated, then closed |
| **K5** | **CUT, and it relocates its own finding** — §6.5 |
| **K6** | **CUT — and it found a defect in the fix** — §6.4 |

#### 6.3.1 🔴 The knife runner reverted the wiring under test, and that read as a MISS

K1's second round reported `make basic-reloc` **rc 0** where the first reported rc 2.
Not a flake and not a tree fault: K3 does `git checkout --force` to reach `b5f4135`,
which reverted the worktree's `Makefile` — including the one line that wires
`check_sub_walls.py` into `basic-reloc` — and the runner's `restore()` put back
`sub.asm` and the tool but **not the Makefile**. Round 2 therefore measured a tree
where the gate was not wired at all, and came back green.

⇒ **A knife aimed at the subject can be silently re-aimed at an unwired gate by the
runner's own cleanup**, and the failure direction is GREEN, which reads as "the
knife missed" ([[knife-runner-false-negatives]], [[knife-aimed-at-the-wrong-gate]]).
Caught by asking why two rounds differed rather than taking the majority; re-run with
the wiring restored and asserted (`grep -c check_sub_walls Makefile` printed per
round), K1 is **rc 2 in both rounds**.

### 6.4 🔴 K6 found a defect in this slice's own instrument

With check 5 neutered, the over-report line printed:

```
⚠️ a trailing-$FF scan reads 1542 B here, -279 B too many:
   the content ends in -279 $FF byte(s). The LABEL is the measurement
```

A **negative** over-report — nonsense rendered as a confident measurement sentence,
on a `scan < free` pair that check 5 normally rejects first. The printer had no
guard of its own: it tested `scan != free`, so any future reorder or weakening of
check 5 would have turned a hard failure into an authoritative-looking line of prose.
That is the [[knife-found-defect-in-own-fix]] shape, and it is the same family as the
defect this whole slice is about — an instrument narrating instead of measuring.

Fixed by splitting the branch: `scan > free` prints the over-report, `scan < free`
prints **`THE INSTRUMENT IS BROKEN`** and returns rc 2. Re-knifed: the neutered-check-5
tool now fails rc 2 on K3's stale pair, **and still passes the healthy pair** — so the
new guard judges rather than simply reddening everything.

**K3's GREEN control is itself a result.** The matched `b5f4135` pair, built with the
landed labels, reads **3852 / 1821** — a third independent instrument (after
D-LFILES's `$FF` scan and its injected labels) agreeing to the byte, and refuting the
recorded 3869 / 1824 for the third time.

### 6.5 🔴 Two of this spec's own predictions were copied figures — and the first diagnosis of WHY was wrong

§4.8 and §4.9 predicted `preflight-check` **180 / 85** and the page-1 closure
**522+41**. Measured: **181 / 86** and **582+41**, at HEAD *and at `0cbf495`*. Neither
gate moved (95 require a guard, 95 guarded, 0 UNGUARDED; abi and page-0 walks
unchanged) — only the numbers I wrote down were wrong.

**The first version of this section blamed the record, and that was wrong.** Both
series were swept the same way §3.1 swept the walls — every commit checked out, built,
and both gates run:

| gate | series | recorded where | verdict |
|---|---|---|---|
| `preflight-check` | 178/85 `4243343`…`121b05b` → 179/85 `76ea851`…`53825bf` → **180/85 `07e9c0a`…`b5f4135`** → **181/86 `0cbf495`** | 178/85 in [`spec-probe-preflight.md`](spec-probe-preflight.md)+[[preflight-slice]]; 180/85 in [`spec-basic-editverb.md`](spec-basic-editverb.md) §6.7 | **every recorded figure is CORRECT at its own commit** |
| `--page1` closure | 515+41 `a191119` → **522+41 `52b2386`…`0b31baa`** → 564+41 `fa0b952`…`b5f4135` → **582+41 `0cbf495`** | 515+41 in [`spec-rom-region-promote-input.md`](spec-rom-region-promote-input.md); 522+41 in all six JUDGE-arc specs + `spec-rom-gate-diskrom.md` + `spec-rom-gate-judge.md` | **every recorded figure is CORRECT at its own commit** |

🎯 **So this is NOT §3.3's defect.** Nothing in the record is stale in the sense the
walls were: no slice wrote a figure it had not measured. D-EDITVERB moved the closure
(522 → **564**, leaving preflight at 180/85) and D-LFILES moved both (→ **181/86**,
→ **582**) — and neither slice recorded either gate at all. **A gap, not an error.**

⇒ **The defect is mine, and it is a different one: I treated the newest RECORDED
figure as the CURRENT baseline.** §1's baseline table should have come from running the
gates at `0cbf495`, which takes seconds; instead two of its rows were `grep`-ed out of
the last spec that happened to mention them, four and two commits stale respectively.
That is a *reading* failure where §3.3 is a *writing* failure, and the two compose:
an unrecorded number and a copied number are indistinguishable to the next slice.

Both corrections point the same way, and it is the one thing this slice actually
builds: **a figure that prints on every build can be neither forgotten nor copied.**
The four walls now do. `preflight-check` and the closure walks already print on every
`make basic-reloc` — they were simply never read off it.

⚠️ Corollary for the next slice: **do not populate a baseline table by `grep`.** Run
the gates. This spec's §1 now carries 181/86 and 582+41 because they were measured
here, not because a document said so.

**And K5 relocates its own finding.** An overrun does not reach check 4: pasmo emits
nothing for a negative `ds`, and `tools/pad_rom.py` refuses the empty image with
*"EMPTY -- the assembler wrote no bytes (check for a negative `ds` count …)"*, so
`make build/sub.rom` fails rc 2 and **no image is produced**. Check 4 is therefore
unreachable from a build; it guards a hand-supplied or hand-edited `.sym`, which is a
smaller claim than §2.5 implied, and it is written down here rather than left as
implied coverage ([[guard-that-cannot-judge-must-say-so]]).

### 6.6 What was NOT run, and why

The eight remaining emulator gates — `lnblank-say-acceptance`, `logicops-acceptance`,
`float-acceptance`, `linemax-acceptance`, `dexp5-pin`, `editverb-acceptance`,
`lptverb-acceptance`, and the two disk gates — were **deliberately not run**.

All four ROM images are byte-identical to `0cbf495` (§6.1), so every one of them would
drive the same machine, bit for bit, as the run that recorded their current values.
They cannot move for a semantic reason; what they can produce is harness variance. The
byte-identity is the stronger control, and it is the same argument
[`rom-region-structure-review.md`](rom-region-structure-review.md) §0 made for its 111
injected labels.

Stated as an omission rather than folded into "corpus green": the gates that read the
**sources** this slice touched all ran — `basic-reloc` (with its eight checks),
`deadcode`, `audit-citations`, `injector-check`, `preflight-check`, `unit-test`,
`latch-check`, and `lnblank-acceptance REPEAT=2` at **539/539**.

### 6.7 The record, corrected

Per §3.5, additions and never substitutions in the two as-built sections:

* [`spec-basic-editverb.md`](spec-basic-editverb.md) §4.2 and §6.7 — 🔴 lines naming
  **1821** and the true **−503**;
* [`spec-basic-lptverb.md`](spec-basic-lptverb.md) §1.2, §4.2 and §6.1 — 🔴 lines
  naming **3852 / 1821** and pointing at §3.3's finding, which that spec's own
  `kwtable` row already contained;
* [`spec-basic-lfiles.md`](spec-basic-lfiles.md) §6.3 and §6.8 — the answer appended
  to the question they filed;
* `MEMORY.md` and [[editverb-slice]] — corrected outright; they carry live guidance,
  not history.

104 of the 112 recorded sites needed no change.

**And one GAP filled rather than corrected** (2026-08-07): §6.5's two figures had no
wrong site to fix — they had no site at all. [`spec-basic-lfiles.md`](spec-basic-lfiles.md)
**§6.1.1** now records the `preflight-check` and three closure-walk figures at
`0cbf495`, measured here and attributed here, marked as *not part of that slice's own
run*. It names the two moves as D-LFILES's own: the page-1 closure **564 → 582** (the
evicted `FILES` walk) and the spawn site **180 → 181**
([`tests/test_wildcard.py:65`](../tests/test_wildcard.py:65), the second `pasmo` call
its §6.6 added). ⚠️ Both of those mechanisms were asserted from plausibility first and
**both were wrong on the first pass** — the spawn site was attributed to the `lfl-`
battery, and the closure delta to a routine set an independent re-walk accounts for
only **17** of **18**. Measured, then written; the residual is stated, not rounded off.

⚠️ **The same gap is still open one and two slices back**: neither
[`spec-basic-lptverb.md`](spec-basic-lptverb.md) (`b5f4135`: closure **564+41**,
preflight **180/85**) nor [`spec-basic-editverb.md`](spec-basic-editverb.md)
(`fa0b952`: closure **564+41**; its preflight 180/85 *is* recorded and correct) carries
the closure figure. Left alone deliberately — `0cbf495` is the baseline the next slice
will read, and filling the two older ones is retro-annotation with no reader.
