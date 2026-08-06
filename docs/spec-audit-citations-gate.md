# D-CITEJUDGE — the clean-room mechanical floor, judged

**Status: SPEC — predicted sets written before any change.**
Slice ID **D-CITEJUDGE**. Baseline `0a9bd89` (tree clean, corpus green).

Picked up from `TODO.md` §*Open — standing residuals*, item 9:

> 🔴 **`make audit-citations` is RED at HEAD, and nothing in the standing corpus
> runs it.**

The filed item carried three claims and named five things to measure. Per
[[filed-justification-is-a-claim]] every one of them is re-measured here before
anything is built. **Two of the three claims are wrong**, and the third is right
for a reason the item did not name.

---

## 0. The question this slice was told to answer FIRST

Not *"is `basic/fat.asm:81` innocent?"* — that is answerable in a minute and
changes nothing. The load-bearing questions, in the order they were asked:

1. **Can the rule tell innocence from evasion, and what does it cost to make it
   able to?** Rewording the sentence silences the gate; that is only right if the
   rule genuinely cannot see the difference.
2. **Is `basic/missing.asm` the only unattested file, and is the attestation
   *absent* or *present in a form the scanner does not match*?** Different fixes.
3. **When did it go red, and what turned it?**
4. **What is the denominator — how many files does it scan, how many does it
   skip, and what is skipped silently?**
5. **Is "advisory" the right call for the 7 `[REVIEW]` headers?**

And the one the item appended: **why is it not in the standing corpus, and is
that reason recorded anywhere?**

---

## 1. The denominator

### 1.1 What check 1 and check 2 actually scan

`TARGETS` at `tools/audit_citations.py:56` is three globs. Counted at `0a9bd89`:

| target | glob | files |
|---|---|---|
| `disk` | `disk/*.asm` + `disk/*.inc` | 7 + 1 = **8** |
| `basic` | `basic/*.asm` + the single hand-listed `basic/sysvars.inc` | 39 + 1 = **40** |
| `tape` | the hand-listed `tape/tape.asm` | **1** |
| | **scanned total** | **49** |

First-party `.asm`/`.inc` in the tree, excluding `build/` and `scratchpad/`:
**130**. Of those, **67 are shipped source that is scanned by nothing**:

| skipped | files | what it is |
|---|---|---|
| `sub/*.asm` | **34** | the entire sub-ROM build — math pack, graphics, string heap, save/load |
| `sub/*.inc` | **3** | `equates.inc`, `basic-resident-abi.inc`, `math-coeffs.inc` |
| `basic/*.inc` (minus `sysvars.inc`) | **30** | the shared bodies assembled into **both** ROMs |
| `probes/**/*.asm` | 14 | harness fixtures — not shipped, but provenance-bearing |

⇒ **the provenance floor covers 49 of 116 shipped first-party asm/inc files —
42 %.** `sub/` — where every derived numeric routine in the project lives — is
outside it completely.

### 1.2 Is the omission deliberate? No — it is temporal, and nothing recorded it

| | commit | date |
|---|---|---|
| tool added | `2e59542` | 2026-06-24 |
| tool last changed | `4c14006` | 2026-07-04 |
| `sub/sub.asm` created | `c224252` | **2026-07-11** |

The sub-ROM did not exist when the tool was last touched. `basic/sysvars.inc` is
in the list because the 2026-06-24 run found a stale citation *in it* — a single
file added by hand after a finding, never generalised to the glob. There is no
note anywhere saying `sub/` is out of scope; it simply arrived after the sweep
stopped being edited.

This is the [[readout-blind-to-its-own-subject]] shape: **the instrument reports
"clean" over a corpus that silently stopped containing the subject.**

### 1.3 The one known clean-room breach was outside the denominator too

The repo's only recorded provenance break — `tier2-m20-spec.md` §11.1 reproducing
a hand-decoded Z80 listing of a proprietary binary — was found by the **human**
paper trail on 2026-07-04 (`4c14006`), in a `docs/` file this tool has never
scanned. Check 1's recall on the only breach in the project's history is **0 of 1**,
because the breach was in a file class outside its denominator.

---

## 2. Falsify by deleting the code under test

The subject here is a **classifier**, so the falsification is a corruption × rule
matrix, not a corrupted artifact. Three measurements were taken before any design.

### 2.1 Walk the gate back over its whole life — 761 commits

Method: a detached worktree; at each commit from `2e59542^..HEAD`, run **that
commit's own tool** against **that commit's own tree**. Faithful, because the tool
changed three times inside the window.

```
commits walked: 761        rc 0: 493        rc 1: 268   (35 % of its life RED)
```

Every transition:

| # | commit | date | findings |
|---|---|---|---|
| 0 | `2e59542` | 06-24 | — green |
| 163 | `a435292` | 07-03 | `FORBIDDEN disk/driver.asm` + `FORBIDDEN disk/kernel.asm` |
| 185 | `4c14006` | 07-04 | green (22 commits red) |
| 289 | `f242fa1` | 07-10 | `NO-ATTEST basic/main-reloc.asm` |
| 301 | `15618da` | 07-10 | green (12 commits red) |
| 339 | `836bfa9` | 07-11 | `NO-ATTEST basic/subromcall.asm` |
| 429 | `3aa26d1` | 07-17 | green (**90 commits red**) |
| **617** | **`6f8ac0f`** | **07-27** | `FORBIDDEN basic/fat.asm:92` |
| 639 | `668aed6` | 07-27 | `+ NO-ATTEST basic/missing.asm:1` |
| 701 | `19e8bfd` | 07-30 | (the `fat.asm` finding moves to line 81) |
| 761 | `0a9bd89` | 08-06 | **still red — 144 consecutive commits, 10 days** |

**The filed claim "last touched at `40647bd`, so this has been red for a while" is
wrong.** `40647bd` (08-02) is merely the last commit that *touched the two files*;
it did not turn anything. The red was turned by **`6f8ac0f` (2026-07-27), `fat:
collapse 13 duplicated tenant shims`** — a slice whose own write-up recorded a
green corpus, because `audit-citations` was not in that corpus. `668aed6`, the
same day, added the second finding.

Note the shape: **five reds, every single one ended by a human noticing.** The
90-commit `subromcall.asm` red is the record.

### 2.2 🔴 Check 1's precision over its whole life: 0 of 4

Every `[FORBIDDEN]` finding the gate has ever produced, read in context:

| commit | line | text | verdict |
|---|---|---|---|
| `a435292` | `disk/driver.asm:510` | "a 65536-**byte copy** that sprayed the whole RAM map" | size qualifier |
| `a435292` | `disk/kernel.asm:1124` | "record/**byte copy** loop (unchanged since M21b)" | granularity qualifier |
| `6f8ac0f` | `basic/fat.asm:92→81` | "an independent 34-**byte copy** of the same body" | size qualifier |
| *(unscanned)* | `sub/fp_sin.asm:182` | "target := source (18-**byte copy**)" | size qualifier |

**Four findings in 761 commits. Four false positives. Zero true positives.** All
four are the same token, `byte[- ]?cop`, matching across the boundary of a
*qualified* `byte`: in `34-byte copy` the word `byte` belongs to the numeral, not
to `copy`.

Meanwhile the other three tokens behave: **65 token hits in the 49 scanned files,
64 in a negation/attestation context, 63 of them `disassembl`.** The negation
window is load-bearing and works.

### 2.3 🔴 And the repo has already paid the reword tax once — for this exact class

`4c14006`'s own commit message, §2:

> *"Mechanical audit floor driven green: two `[FORBIDDEN]` false positives
> reworded ("copy" → "block move" for LDIR/memcpy in our own driver.asm/kernel.asm)"*

That is the "just reword the sentence" fix, applied 2026-07-04. **The class
recurred twice more** — `basic/fat.asm` three weeks later, and `sub/fp_sin.asm`
which is sitting unflagged only because it is outside the denominator. In a
project whose native vocabulary is byte budgets, *"an N-byte copy"* is a phrase
that will keep being written.

⇒ **the filed claim "(i) looks like a false positive" is RIGHT, and its stated
reason is WRONG.** The item says the sentence is innocent because it describes
zerobas's own shims rather than reference material. That distinction —
whose code is being copied — is **semantic and genuinely out of a regex's reach**;
if that were the defect, rewording would be the only fix. It is not the defect.
The defect is **lexical and mechanically decidable**, which is why the rule can be
taught and should be. Same shape as [[correct-claim-can-be-the-wrong-question]],
one level in.

### 2.4 Check 2: `basic/missing.asm` — absent, not unmatched, and never present

`grep -i` for the whole attestation vocabulary over all 591 lines of
`basic/missing.asm`: **zero hits.** Not "present in a form the scanner misses" —
absent. And absent since birth: the header at `668aed6` (the file's first commit)
has no attestation either.

It is the **only** one of the 39 `basic/*.asm` without one; the other 38 all
carry a header attestation, in six different phrasings the scanner accepts.

**Found in passing, and it is doc debt of its own:** `19e8bfd` (*S3: retire the
lean cart's 284 gates*) mangled the header block. The 2026-07-27 text read

```
; ⚠️ REPACK-ONLY, deliberately (S-MC-5). The whole file is behind one
; `IF ROM_BASE < $4000`, so the lean 16 KB cart assembles NOTHING from it and
; stays byte-identical -- LEAN_SHA256 does not move. ...
```

and today reads *"The whole file is behind one"* followed by a different sentence,
plus *"was inline in page 1, where the / kwtable is a sub.rom tenant"*. Two
sentences were truncated mid-clause by a text edit that nothing checked.

### 2.4b 🔴 A SECOND rule defect of the same shape — found by writing the fix

Found while writing §3.4's attestations, not before: **9 of the 23 files the
widened denominator exposed already carry a properly worded `CLEAN-ROOM:`
attestation** — and were reported as having none.

`HEADER_BLOCK_LINES = 45` is a fixed window. These nine attest at lines **46,
51, 56, 58, 59, 63, 64, 78** — all inside their own header comment block, all
past the window. Headers longer than 45 lines are ordinary in this tree; the
longest of the nine has a 153-line header.

| file | attests at line |
|---|---|
| `basic/randio-body.inc`, `sub/lineno.asm` | 46 |
| `sub/bload.asm` | 51 |
| `sub/fatprim.asm` | 56 |
| `sub/save.asm` | 58 |
| `basic/sprtrap-body.inc` | 59 |
| `sub/errtrap.asm` | 63 |
| `sub/lineedit.asm` | 64 |
| `sub/fp_rnd.asm` | 78 |

Same shape as §2.2, one check over: **an arbitrary mechanical approximation
firing on honest source.** The docstring has always said the attestation must be
*"in its header block"*; 45 was an approximation of "header block", and the
approximation is what failed. Measuring the block exactly costs one loop and
removes **9 of the 24** findings without editing a single file.

⇒ and it changes the §3.4 verdict: **15 attestations to write, not 24.** Nine of
what looked like a provenance gap was an instrument artefact. Had they been
"fixed" by writing a second attestation into each file, the gate would have gone
green over nine files that were already compliant, and the instrument's real
defect would have been paid for in prose — the §2.3 mistake, repeated.

### 2.5 The advisory half — measured, and it is NOT rot

7 `[REVIEW]` headers today. Ran the tool at `4c14006` in the walk worktree:
**the same 7 headers, same files, same names**, only the line numbers moved. And
they were triaged — `docs/clean-room-audit.md:381` records
*"7 genuine advisory headers remain (structural headers whose bodies carry full
citations — judged individually, all acceptable)"*, dated 2026-07-04.

⇒ this is **not** a [[guard-that-cannot-judge-must-say-so]] situation. The check
says exactly what it is, its output is stable across 575 commits, and a human made
the judgement it declines to make. **Advisory is the right call and stays.** §3.6
records the one residual risk and why it is not closed here.

### 2.6 Why nothing runs it — the reason IS recorded, and the record is false

The filed item says *"the reason it is not there is not recorded anywhere."*
**Wrong — it is recorded twice, identically**, at `Makefile:1600` and
`docs/clean-room-audit.md:114`:

> *"run it on demand / in CI so the citation scaffolding cannot silently lapse"*

Both clauses fail:

* **"in CI"** — `.github/workflows/ci.yml` exists. It runs `make build/basic.rom
  disk`, a host-tooling smoke import, and `make unit-test`. **It does not run
  `audit-citations`.** And it is `workflow_dispatch:` only — the `push`/
  `pull_request` triggers are commented out, deliberately, because Actions minutes
  are metered on a private repo. So even the CI that exists never fires by itself.
* **"on demand"** — measured in §2.1: red for 268 of 761 commits, and every green
  return came from a human happening to run it.

⇒ the ninth filed justification checked in this arc, and the ninth to be wrong.
The gate's cadence was written down as a **habit**, and a habit is not a control.

**Cost of running it:** `0.27 s` wall, pure `python3`, read-only, no pasmo, no
emulator, no reference ROMs. It is by orders of magnitude the cheapest gate in the
repo — cheaper than the `make` invocation that would carry it.

---

## 3. Design

### 3.1 Check 1: teach the rule (do NOT reword the sentence)

```python
-    r"disassembl|byte[- ]?cop|reverse[- ]?engineer|red[- ]?book", re.I,
+    r"disassembl|(?<![\w/-])byte[- ]?cop|reverse[- ]?engineer|red[- ]?book", re.I,
```

One lookbehind. It says: **`byte` must begin a word.** When something binds to the
front of it — `34-byte`, `65536-byte`, `18-byte`, `record/byte` — `byte` is a unit
of size or granularity, and `copy` is the ordinary English noun. When nothing
does — `byte-copy`, `byte copy`, `bytecopied` — it is the compound that names the
forbidden derivation method.

Measured against the whole tree (130 files):

| | token hits | affirmative (RED) |
|---|---|---|
| old pattern | 99 | **2** (`basic/fat.asm:81`, `sub/fp_sin.asm:182`) |
| new pattern | 96 | **0** |

The three lost hits are exactly the three size-qualified forms present today; the
63 `disassembl` hits and their negation contexts are untouched.

**Stated coverage limit, before running.** The lookbehind does not make this rule
evasion-proof and is not meant to: *"an 8-byte copy of the CF-3300's DPB"* is a
genuine byte-copy that it will not flag. No keyword scan resists an author who
simply omits the word — the tool's own docstring says so, and that is the
[[clean-room-audit-checks]] division of labour: **the mechanical floor catches
lapses, the human paper trail catches breaches.** What the change buys is that the
floor stops firing on the phrase this project cannot stop writing.

### 3.2 Check 1 gains a permanent self-test — the control, wired in

A regex whose green state is *"found nothing affirmative"* is exactly the shape
[[deadcode-gate]] says needs a canary, not just a falsification row. So the rule's
decision function gets an embedded table that must keep classifying correctly:
the five genuine-derivation forms, the **four historical false positives** from
§2.2 verbatim, and `byte-identical` (the legitimate oracle outcome). A
misclassification is **rc 2**, not rc 1 — the instrument is broken, and nothing
below it was measured ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]'s
two-disposition rule).

This is also what stops §3.1 from being a one-off: the four lines that have ever
falsely reddened this gate are now permanent test vectors.

### 3.3 The denominator is closed, and stated in the output

* `basic` target becomes `basic/*.asm` + **`basic/*.inc`** + **`sub/*.asm`** +
  **`sub/*.inc`** — the whole shipped BASIC deliverable, main ROM and sub-ROM.
  `sub/` belongs to `basic` because that is what it is: the BASIC sub-ROM.
* check 4 (private-reference) additionally scans `probes/**/*.asm`. Those are
  fixtures, not shipped source, so they get the provenance-bearing check and not
  the attestation check. Measured cost today: **0 findings**.
* the tool **prints its denominator** — `== basic == (107 files)` — and enforces a
  floor per target (`disk` ≥ 8, `basic` ≥ 100, `tape` ≥ 1). A glob that stops
  matching currently reads as a cleaner tree; with the floor it is **rc 2**.

Measured cost of closing it: **23 `[NO-ATTEST]` + 1 `[FORBIDDEN]`**. The
`[FORBIDDEN]` is `sub/fp_sin.asm:182`, cleared by §3.1. The 23 attestations are
written in §3.4.

### 3.3b Check 2: measure the header block, do not approximate it

`HEADER_BLOCK_LINES = 45` is replaced by `header_block()`, which returns the
contiguous comment run that follows the copyright/SPDX preamble — the thing the
docstring already claimed to check. Widening a window can only *remove* findings,
never add one, so this cannot mask a regression it would otherwise have caught;
what it removes is the 9 false ones in §2.4b. K4 (§5) is the control that proves
check 2 still fires with the wider window.

### 3.4 The 15 attestations

`basic/missing.asm` (the filed gap) plus the 14 that survive §2.4b's window fix:
8 under `sub/`, 6 under `basic/*.inc`. **Two of the 15 are in GENERATED files**
(`sub/basic-resident-abi.inc`, `sub/math-coeffs.inc`) and are therefore written
into their generators, `tools/gen_resident_abi.py` and `tools/gen_math_coeffs.py`
— editing the `.inc` would be undone by the next `make`
([[a-generated-input-needs-its-own-pin]]).

⚠️ **An attestation is a claim, so none of these is invented.** Measured first:
**every one of the headers already states its basis in substance** — a
`spec-*.md §` pointer, "own design", "black-box", "VG-8020-measured", "never the
MSX ROM's own coefficients" — and fails only because the scanner's vocabulary does
not contain those words. The attestation is a **restatement of what the file
already says**, verifiable against its own header. The one exception is
`basic/sv-tputw.inc` (a twelve-instruction little-endian word emitter over the
documented `TAPOUT` BIOS entry), whose basis is readable off the body itself.

`basic/missing.asm` also gets the two sentences `19e8bfd` truncated (§2.4)
repaired. Comment-only.

### 3.5 Wiring: the habit becomes a control

1. **`Makefile`** — `python3 tools/audit_citations.py` becomes the last step of
   the `basic-reloc` PHONY recipe, beside `check_dead_code.py`, for the reason
   that target already carries `deadcode`: it is the target every slice runs, and
   0.27 s is free. Unscoped, so a disk or tape slice is covered too.
2. **`.github/workflows/ci.yml`** — its own step on both runners, before the unit
   tests. Pure `python3`; no new dependency on either platform.
3. **docs** — `docs/clean-room-audit.md` and `Makefile`'s comment stop saying
   *"on demand / in CI"*, which was false in both clauses (§2.6), and say where it
   actually runs. `docs/dev-workflow.md:72` already calls a clean run the floor;
   it gains the pointer to where the floor is enforced.

### 3.6 What does NOT change, and why

* **The advisory check stays advisory** (§2.5): triaged, stable at the same 7
  headers for 575 commits, and honest about what it cannot judge. The residual
  risk is that a *new* advisory header lands unnoticed in a 7-line list nobody
  diffs. Closing that means a second allowlist-with-reasons file in the
  `deadcode-allow.txt` style — the right shape, but it needs 7 written
  justifications and this slice already writes 24 attestations. **Filed, with the
  stability measurement that would justify it.**
* **The negation window stays a 3-line `NEGATION.search`.** It is loose — "this is
  NOT the fast path; derived by disassembly of the reference" would pass — but
  that is the evasion axis, where no keyword scan holds, and it is doing its job
  on 63 hits per run.
* **`docs/` is still not scanned by checks 1–2** even though §1.3's breach lived
  there. Prose narrative legitimately *discusses* forbidden methods at length;
  scanning it means a large negation-context false-positive surface. Out of scope
  here and worth its own measurement.

---

## 4. Predicted GREEN — fixed BEFORE the change

| # | measurement | predicted |
|---|---|---|
| G1 | `python3 tools/audit_citations.py` | **rc 0** |
| G2 | files scanned | `disk` **8**, `basic` **107**, `tape` **1** — total **116** |
| G3 | `[FORBIDDEN]` findings | **0** (95 token hits, all in a negation context) |
| G4 | `[NO-ATTEST]` findings | **0** |
| G5 | `[PRIVATE-REF]` findings | **0** |
| G6 | `[REVIEW]` advisory | **7**, the same 7 files/names as §2.5 |
| G7 | rule self-test | 10 of 10 |
| G8 | `sha256 build/disk.rom` | `2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27` |
| G9 | `sha256 build/sub.rom` | `b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e` |
| G10 | `sha256 build/basic-reloc.rom` | `3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af` |
| G11 | `sha256 build/zerobas-main-eu.rom` | `d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e` |
| G12 | walls, from CLEAN | low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B** |
| G13 | closure walks | abi **122+4**, `--page0` **718+15**, `--page1` **522+41** |
| G14 | dead-code seeds | main **285**, sub **102**; 0 dead both, +1 allowlisted |
| G15 | `kwtable` | **1041 B** |

**G14 is the one to watch.** `check_dead_code.py`'s `external_names` roots are
`['sub', 'tools']` and it reads **comments too** — so the prose added to
`tools/audit_citations.py` in §3.1–§3.3 can seed a main-build label, and the
attestations added to 15 `sub/` files can seed either build. Editing
`basic/*.asm` cannot (`basic/` is not a root). **Any movement in 285/102 is a
finding about this slice's own prose**, per the standing residual.

---

## 5. Predicted RED — the knives

Each refusal is run **twice** ([[refusal-survives-only-if-the-artifact-does]]).

| knife | cut | predicted |
|---|---|---|
| **K1** | plant a genuine offender (`; byte-copied from the reference ROM listing`) in a scanned `sub/` file | rc **1**, one `[FORBIDDEN]` naming that file/line |
| **K1c** | *control* — plant `; an independent 34-byte copy of the same body` in the same place | rc **0** |
| **K2** | gut only the judgement: `NEGATION` → matches everything, emission and call site intact | K1's planted line **passes**, and the self-test fires **rc 2** |
| **K3** | gut `FORBIDDEN` → matches nothing | self-test fires **rc 2**, not a clean rc 0 |
| **K4** | delete the attestation line from one newly-scanned `sub/` file | rc **1**, `[NO-ATTEST]` naming it — proves the widened denominator is live, not decorative |
| **K5** | break the `sub/` glob (point it at a directory that does not exist) | rc **2** on the file-count floor, **not** a clean "0 findings" |
| **K6** | revert `basic-reloc`'s new step and re-run `make basic-reloc` with a planted offender | build **passes** — the control proving K7 cut |
| **K7** | plant the same offender and run `make basic-reloc` unmodified | build **fails**; run twice |

K5 and K3 are the two that matter most: they are the only knives that can tell
"the tree is clean" from "the instrument went blind", which is the failure mode
this gate spent 90 commits in.

---

## 6. As-built — ✅ LANDED 2026-08-06

**ROM-neutral, proved by hash.** All four `build/*.rom` byte-identical to
`0a9bd89` from a `rm -rf build` rebuild:

```
2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27  build/disk.rom
b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e  build/sub.rom
3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af  build/basic-reloc.rom
d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e  build/zerobas-main-eu.rom
```

### 6.1 GREEN, scored — every §4 prediction hit exactly

| # | predicted | measured |
|---|---|---|
| G1 | rc 0 | **rc 0** |
| G2 | 8 / 107 / 1 files | **8 / 107 / 1** (97 / 181 / 15 provenance-bearing) |
| G3 | 0 `[FORBIDDEN]` | **0** |
| G4 | 0 `[NO-ATTEST]` | **0** |
| G5 | 0 `[PRIVATE-REF]` | **0** |
| G6 | 7 `[REVIEW]`, the same 7 | **7, identical files and names** |
| G7 | self-test 10/10 | **10/10** |
| G8–G11 | four hashes | **all four identical** |
| G12 | low 23 / page 1 356 / sub p0 3869 / sub p1 2324 | **23 / 356 / 3869 / 2324** |
| G13 | abi 122+4, p0 718+15, p1 522+41 | **122+4, 718+15, 522+41** |
| G14 | main 285 / sub 102 seeds, 0 dead (+1) | **1551 spans/285 → 0; 1451 spans/102 → 0 (+1)** |
| G15 | kwtable 1041 B | **1041 B** |

**G14 is the one that had to be watched, and it did not move.** The prose added to
`tools/audit_citations.py`, `tools/gen_math_coeffs.py` and `tools/gen_resident_abi.py`
— all three inside `check_dead_code.py`'s `external_names` roots, all read
including comments — seeded nothing new, and neither did the eight new `sub/`
attestations.

### 6.2 RED, and what each knife found

Every refusal run twice; every RED paired with a GREEN control.

| knife | result |
|---|---|
| **K1** plant `; byte-copied from the reference ROM listing` in `sub/beep.asm` | rc **1**, `[FORBIDDEN] sub/beep.asm:17`, both runs — and it proves the widened denominator is live: that file was scanned by nothing before this slice |
| **K1c** *control*, `; an independent 34-byte copy of the same body`, same file, same place | rc **0**, both runs |
| **K2** gut only the judgement (`NEGATION` matches everything), emission and call site intact | rc **2**, self-test fires, both runs |
| **K2b** *same gutting with the self-test disabled* | rc **0** — the planted offender passes and a fully-gutted rule reads as a clean tree. This is what the self-test buys. |
| **K3** gut `FORBIDDEN` to match nothing | rc **2**, self-test fires, both runs |
| **K4** remove `sub/fatprim.asm`'s attestation | rc **1**, `[NO-ATTEST]`, both runs — see 6.2a |
| **K5** break the `sub/` glob | rc **2**, *"basic: 70 file(s), floor 100 — a glob stopped matching"*, both runs |
| **K5b** *same break with `MIN_FILES` zeroed* | rc **0** — 37 fewer files silently, reported as clean |
| **K7** plant the offender, `make basic-reloc` | **fails both runs** (`Error 1`); `basic-reloc` is PHONY, so a second `make` re-runs the whole recipe and refuses again |
| **K6** *control*, same plant with the new Makefile step removed | **passes** — K7's failure is the new step, not the plant's side effects |

**K2b and K5b are the two that matter.** Without the self-test and the file-count
floor, both ways of blinding this gate produce **exit 0 and the word "clean"** —
which is the state it was actually in for the 575 commits `sub/` sat outside it.

### 6.2a 🔴 K4 came back GREEN first, and the knife had not cut

The first K4 removed every line containing `CLEAN-ROOM` from `sub/fatprim.asm` —
one line — and the gate stayed green. Before concluding anything about check 2,
check the knife cut ([[knife-aimed-at-the-wrong-gate]]): it had not. That header
carries the attestation vocabulary **twice**, at line 56 (`CLEAN-ROOM: original
code … own-design`) and again at line 61 (`… provenance … No reference-ROM
disassembly`). The knife removed one sentence, not the attestation. Re-aimed at
every attestation-bearing line in the header block, it cuts cleanly: 2 lines
removed, rc **1**, both runs, and the restored file is rc 0.

### 6.2b 🔴 A knife's CLEANUP destroyed the slice's own uncommitted work

The first knife script used `git checkout -- <file>` to undo each plant. `git
checkout --` restores from **HEAD**, not from the pre-knife state — so it silently
reverted every uncommitted edit this slice had made to those files, including all
of `tools/audit_citations.py`, the tool under test. K3, K4 and K5 then ran against
HEAD's *old* tool and reported its old behaviour; K1c's control failed for a
reason that had nothing to do with the knife. Nothing in the output said so: the
findings printed were plausible, and three of them named a real line.

Then the second-order version: two aborted re-runs left plants in the tree, and
the next run's `cp`-to-scratchpad **snapshotted the polluted tree** and restored
*that*. Three copies of the plant accumulated, and K1c failed again.

⇒ two rules, both now in the script: **a knife's restore point is a snapshot taken
before the knife, never `git checkout`**; and **a knife script must refuse to run
if its subject is not green before it starts**, because otherwise it freezes the
previous run's damage into its own restore point.

### 6.3 The four filed claims, scored

| filed | measured |
|---|---|
| *"`basic/fat.asm:81` looks like a false positive"* | **RIGHT, wrong reason.** Not "own code vs reference material" (semantic, out of a regex's reach) but `34-byte \| copy` — a lexical boundary a lookbehind decides. §2.2 |
| *"`basic/missing.asm` is a real gap"* | **RIGHT.** Absent, not unmatched, and absent since the file's first commit. §2.4 |
| *"has been red for a while … last touched `40647bd`"* | **WRONG.** Turned by `6f8ac0f` on 2026-07-27, 144 commits ago; `40647bd` turned nothing. §2.1 |
| *"the reason it is not in the corpus is not recorded anywhere"* | **WRONG.** Recorded twice — *"on demand / in CI"* — and false in both clauses. §2.6 |

Two of four wrong, and the two that were right were right for reasons that would
have produced the wrong fix. Running total for this arc: **nine filed
justifications checked, seven wrong, one right-but-misdirected, one right.**

### 6.4 Corpus — ALL GREEN, sequential, from the clean tree

18 of 18, rc 0 each:

`basic-reloc` (23 / 356 / 3869 / 2324; closure 122+4, 718+15, 522+41; dead code
1551/285 → 0 and 1451/102 → 0 (+1); kwtable 1041 B; **audit-citations now runs
inside it**) · `unit-test` · `audit-citations` (8/107/1, self-test 10/10, 7
advisory) · `preflight-check` (UNGUARDED 0) · `injector-check` · `latch-check`
16/16 · `dexp5-pin` 16/16 · `linemax-acceptance` 60/60 ·
`lnblank-acceptance REPEAT=2` **536/536, allowlist empty** · `subrom-acceptance` ·
`subrom-inttest` (JIFFY delta 28, in 1..64) · `graphics-floor-acceptance`
(read-back mismatches 0) · `graphics-acceptance` · `probe` (disk + basic + tape) ·
`fat-error-acceptance` 8/8 + directory check, **over a LIVE FAT layer** (D-DSKJUDGE's
precondition) · `diskbasic-acceptance` 34/34 · `bdos-acceptance` 12/12 ·
`lof-acceptance` **45 cases, 0 unfiled divergences, 0 oracle drifts, 0 mangled**.

⚠️ **`lof-acceptance` sighting 3 has now failed to occur in FIVE consecutive
slices** (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE). Whole log
captured (`> file 2>&1`), not tailed.

### 6.5 What this slice did NOT do

* **Did not scan `docs/`** — where the project's only actual clean-room breach
  lived (§1.3). Narrative prose legitimately discusses forbidden methods, so the
  negation-context false-positive surface there is large and unmeasured. Filed.
* **Did not build an advisory allowlist** — §2.5 measured the advisory set stable
  and triaged; the residual (a *new* advisory header landing unnoticed) is filed
  with the stability measurement that would justify closing it.
* **Did not touch the negation window** (§3.6).
