<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-DOCJUDGE — should the clean-room floor scan `docs/`?

**Status: SPEC — predicted sets written before any change.**
Slice ID **D-DOCJUDGE**. Baseline `da93f0c` (tree clean, corpus green).

Picked up from `TODO.md` §*Open — standing residuals*:

> ⚠️ **`audit_citations.py` does not scan `docs/`** — and the project's only
> recorded clean-room breach lived there (a hand-decoded Z80 listing, remediated
> at `4c14006`), found by a human paper trail, not by the floor. Narrative prose
> legitimately *discusses* forbidden methods, so the negation-context
> false-positive surface is large and UNMEASURED. Measure it before proposing a
> rule.

Filed by [D-CITEJUDGE](spec-audit-citations-gate.md) §6.5. Per
[[filed-justification-is-a-claim]] every clause is re-measured here before
anything is built. **The scope claim is right, the breach claim is wrong, and the
proposal it implies is DECLINED on measurement** — but the measurement that
declines it also produced a live, unremediated provenance finding and the
instrument that catches it.

---

## 0. The question this slice was told to answer FIRST

Not *"is `docs/` scanned?"* — that is a property of the tooling, checkable in one
reading, and [[correct-claim-can-be-the-wrong-question]] says a property of the
tooling is rarely the load-bearing fact. The question is:

> **Would the current rule have caught the breach if `docs/` had been in scope?**

Everything else is downstream of that. If the quarantined text contains no
forbidden token, then scanning `docs/` does not change the floor's recall on the
only class of breach this project has ever had, and the honest answer is a
decline — no matter how true "docs/ is unscanned" is.

Four more, in the order asked:

1. What is the doc-corpus denominator, and what does the proposed rule cost on it?
2. Is the breach corpus really one incident?
3. If a vocabulary scan is the wrong instrument, what is the right one — and is it
   decidable by a host-side text scanner at all?
4. Does the answer change anything about the files the tool **already** scans?

---

## 1. The denominator

### 1.1 The doc corpus

| directory | `.md` files |
|---|---|
| `docs/` | 189 |
| `disk/docs/` | 72 |
| `tape/docs/` | 9 |
| `basic/docs/` | 8 |
| | **278**, **85 912** lines |

For comparison, checks 1–2 today scan **116** asm/inc files / 56 733 lines. The
proposal is therefore not a widening — it is roughly a **doubling** of the
scanned surface, over text whose genre is discussion rather than assertion.

### 1.2 🔴 What the proposed rule costs: 243 token hits, 26 affirmative, 0 breaches

Check 1's shipped rule (`FORBIDDEN` + the 3-line `NEGATION` window,
post-D-CITEJUDGE, lookbehind included) run over all 278 files:

| | count |
|---|---|
| forbidden-token hits | **243** |
| in a negation/attestation context (pass) | 217 |
| **affirmative — would turn the gate RED** | **26**, in **12** files |
| of those 26 that are an actual provenance breach | **0** |

And the shape of the 26 is the finding, not the number:

| bucket | rows | what it is |
|---|---|---|
| `docs/spec-audit-citations-gate.md` | **8** | the spec **of check 1**, quoting its own four historical false positives verbatim and diffing its own regex |
| `docs/clean-room-audit.md` | **5** | the audit doc **recording what the policy caught** |
| `docs/allowed-sources.md` | **3** | the policy file that **defines the forbidden list** ("the MSX Red Book and any other BIOS/ROM disassembly…") |
| own-code / process narrative | 8 | "copying an element is a byte copy", "byte-copy loops", "disassemble our OWN shifted page-1 region (allowed — our code)", "time-boxed reverse-engineering campaign" |
| tool documentation | 2 | openMSX's `disasm_blob` command reference, and the §8 write-up of the disasm **guard** |

**16 of the 26 are in the three documents that state, implement and record the
policy itself.** A gate that reddens on its own rulebook is not measuring the
tree; and the remaining 10 are the [[reword-the-subject-or-teach-the-rule]] class
again — including two forms the lookbehind cannot reach, because in *"copying an
element is a byte copy"* the word `byte` legitimately begins a word.

⇒ predicted precision of the proposed rule: **0 of 26**, on top of check 1's
measured **0 of 4** over its first 761 commits.

### 1.3 🔴 The premise is wrong: the breach corpus is not one incident, and one of them is not in `docs/`

`docs/clean-room-audit.md`'s run log records **four** provenance events, not one:

| date | where | what |
|---|---|---|
| 2026-06-24 | `disk.asm` §8.37 | a sub-agent derived asm from a disassembled `MSXDOS.SYS` — **asm**, reverted |
| 2026-06-30 | probe output + notes (`971fc78`) | the M12 incident: stock disk-ROM code bytes read and hand-decoded during a CONIN ABI pin |
| 2026-07-04 | `disk/docs/tier2-m20-spec.md` §11.1 (`4c14006`) | a 6-line column listing of the loaded `MSXDOS.SYS` RAM kernel at `$D8AA–$D8BD` |
| **2026-07-07** | **~50 sites** across `disk/*.asm` **and** `disk/docs/*.md` (`e8558c2`) | a **systemic** decoded-stock-code residue, found by the first disk full-verify |

The item names only the third. The fourth is an order of magnitude larger, and it
is the one that settles this slice — because **6 of its ~50 sites were comments in
`disk/init.asm`, `disk/kernel.asm` and `disk/runtime.asm`**, three files that
check 1 *does* scan, and has scanned since the day it was written.

⇒ **this was never a `docs/` scope problem.** Offenders of the identical class sat
inside the denominator and the rule read them as a clean tree. Widening the
denominator cannot fix a rule that cannot see the subject
([[readout-blind-to-its-own-subject]], reached from the opposite side: there the
corpus lost its subject, here the corpus has it and the *rule* is blind).

The audit doc says so itself, twice, in its own voice:

> *"the mechanical scanner (`audit_citations.py`) cannot see decoded-mnemonic prose"*
> *"the forbidden-source scanner does NOT catch decoded-mnemonic prose, so manual
> review is the only backstop for this class"*

and closes with a follow-on candidate, measured in §2.4 below.

---

## 2. Falsify by measuring, not by arguing

The subject is a classifier, so the falsification is a corruption × rule matrix.
Six measurements were taken before any design. The two remediation commits give
something better than planted corruptions: a **labelled corpus of real offenders**
(the text removed) paired with **real innocents** (the hand-reviewed text that
replaced it).

### 2.1 🔴 THE LOAD-BEARING ANSWER: check 1's recall on the breach corpus is 0

Running `forbidden_hit()` — check 1's actual decision function, not a
re-implementation — over each labelled corpus:

| corpus | lines | token hits | **affirmative (RED)** |
|---|---|---|---|
| the 2026-07-04 quarantined listing, verbatim | 6 | **0** | **0** |
| `tier2-m20-spec.md` entire pre-remediation revision | 400 | **0** | **0** |
| `e8558c2`'s removed lines from the **scanned** `disk/*.asm` | 10 | 0 | **0** |
| `e8558c2`'s removed lines from `disk/docs/*.md` | 111 | 2 | **0** |

**Zero.** The 2026-07-04 listing is a column of address + mnemonic; it contains no
`disassembl`, no `byte-cop`, no `reverse-engineer`, no `red-book`. The prose above
it said *"byte-identical ours==stock"* — a phrase check 1 **deliberately exempts**
as the gold-standard clean-room outcome.

And the inversion that settles the question: the **post**-remediation revision is
the one that gains a `disassembl` token (line 355, in the dated clean-room note
explaining what was quarantined). It passes only because the note is written in a
negation context.

> ⇒ **the vocabulary scan is blind to the breach and sees only the remediation.**
> Had `docs/` been in scope on 2026-07-02, the gate would have stayed green for the
> listing's entire 34-commit life and then reported a finding on the fix.

That answers §0. Scanning `docs/` with this rule buys **0 of 4** recall and costs
26 false positives. **DECLINED.**

### 2.2 The other detector shape — measured, and only one variant is decidable

A decoded listing is recognisable as *mnemonic-dense text*, not as a forbidden
word. Two shapes exist in the labelled corpus, and they behave completely
differently.

**Shape A — the INLINE run**, `$0246: LD A,($F340) / AND A / CALL Z,$0317`. Four
narrowings, each scored on recall (the 121 removed lines), on the control (the 156
hand-reviewed replacement lines, which must score **0**), and on the current tree:

| variant | recall | fires on the REPLACEMENT text | current-tree hits |
|---|---|---|---|
| ≥2 operand-bearing mnemonics | 18/121 | **1** | **464** in 192 files |
| ≥2 mnemonics **+** a `$XXXX` address | 17/121 | **1** | **88** in 44 files |
| ≥3 mnemonics | 8/121 | **1** | **98** in 64 files |
| ≥3 mnemonics **+** a `$XXXX` address | 7/121 | **1** | **25** in 17 files |

Every variant fires on the remediated, hand-reviewed text that a full-verify pass
signed off — i.e. **the control fails at every threshold**
([[control-that-fails-must-be-fixed]]: a rule whose control fails is not a rule).
Shape A is **not decidable** by a host-side text scanner. Stated, not worked
around.

**Shape B — the COLUMN LISTING**: consecutive lines of
`<4 hex digits>  <mnemonic> <operands>`. Same measurement:

| | value |
|---|---|
| recall on the 2026-07-04 listing | **6 of 6 lines**, and 0 after remediation |
| fires on any replacement text | **0** |
| hits over **all 690 first-party text files** (234 161 lines) | **2 runs, 6 lines, 2 files** |

Two hits in the whole repository. That is a gate.

### 2.3 🔴 And the audit doc's own follow-on candidate does NOT work

`docs/clean-room-audit.md:298` proposes:

> *"teach `audit_citations.py` a heuristic for 'instruction mnemonic adjacent to a
> non-`$4xxx-$7xxx` address' so this class gets a mechanical floor"*

Implemented literally and measured over the 690 files: **738 hits in 137 files.**
Unusable, and the reason is structural rather than a matter of tuning:

* **the address cannot say whose code it is.** 15 of the 120 addresses on the
  labelled offender lines are **inside** `$4000–$7FFF` — stock's disk ROM occupies
  exactly the window ours does (`$50A9`, `$5454`, `$541D`, `$53A8`). The M12c probe
  guard suppresses by **machine**, not by address, for precisely this reason, and a
  text scanner has no machine to ask.
* conversely most of what lives *outside* that window in our own docs is **ours**
  — page-0 tenants, the sub-ROM, and the published `$F3xx` sysvar area.

⇒ recorded so the next slice does not re-derive it: this is a **recommendation in
the run log that does not survive being measured**, the same shape as
[[filed-justification-is-a-claim]] one level up.

### 2.4 Walk the candidate gate over the whole history — 978 commits

Method as [[citejudge-slice]]: at every commit, the shape-B detector over that
commit's own tree, blob-cached.

```
commits walked: 978     commits RED: 673 (68 %)     distinct files ever flagged: 3
```

68 % red sounds like a nuisance until the transitions are read — there are **four
in 978 commits**:

| # | commit | date | change |
|---|---|---|---|
| 305 | `18116c6` | 06-27 | **+** `tier2-f338-default-spec.md` (3 lines) |
| 367 | `a1cf7ad` | 07-02 | **+** `tier2-m20-spec.md` (6 lines) |
| **401** | **`4c14006`** | **07-04** | **−** `tier2-m20-spec.md` |
| 968 | `07e9c0a` | 08-04 | **+** `probes/lib/omsx_repl.py` (3 lines) |

The middle two are the whole story: the detector goes red on the exact commit that
introduced the recorded breach, and green on the exact commit that remediated it.
**34 commits, no false transitions.** A human whole-target paper trail found it in
two days; this finds it in 0.5 s, on the commit.

The 673 red commits are one file, held open for its entire life — see §2.5.

### 2.5 🔴 THE LIVE FINDING: an unremediated site of the same class, in a file the sweep itself edited

`disk/docs/tier2-f338-default-spec.md:22–24` carries a **3-instruction column
listing of COMMAND.COM's resident startup code at `$C26B`** — a proprietary binary,
✗ per [`allowed-sources.md`](allowed-sources.md), the identical class as the
2026-06-30 M12 incident and the 2026-07-04 §11.1 remediation. Introduced
`18116c6` (2026-06-27); **still present 673 commits later.**

It is not that nobody looked. `e8558c2` — the 2026-07-07 full-verify that swept
~50 sites of this exact class and reported *"fully remediated"* — **edited this
file**, at lines 58–63, removing an inline rendering of **the same instruction
body** from the asm-comment block quoted there. It walked past the full column
listing **36 lines above**, in the same file, in the same pass.

Three whole-target human passes had the file open (2026-06-24 could not — it did
not exist yet; 2026-07-04 and 2026-07-07 did) and none saw it. That is the
argument for a mechanical floor stated as a measurement rather than as a
principle: **the class is one a careful reader misses in the file they are
already editing.**

### 2.6 The second hit adjudicated, and why it is an allowlist entry

`probes/lib/omsx_repl.py:366` renders 3 instructions of **C-BIOS**'s keyboard-buffer
path in a docstring explaining the D-LATCH2 injection window.

C-BIOS is **not** a forbidden source: `allowed-sources.md` grades it **B /
Conditional** — a peer clean-room reimplementation, BSD-2, whose source this
project already patches (`cbios-repack/`). It is not the reference implementation
zerobas reimplements, and the docstring is explicit about the line it is staying on
(*"locating chget in the reference needs a disassembly this project does not do"*).

This is exactly the judgement `docs/clean-room-audit.md` reserves for a human, and
the tool must not make it. It goes to the allowlist **with the reason written
down**, which is what §3.3 makes load-bearing.

---

## 3. Design

### 3.1 DECLINED: extending checks 1–2 to `docs/`

On the measurement in §1.2 and §2.1: **0 of 4 recall on the recorded breach
corpus, 26 affirmative false positives over 278 files, 16 of them inside the three
documents that define and record the policy.**

**What a future slice would have to answer to re-open it.** Not "prose discusses
forbidden methods" — that is granted. It would have to produce a breach, real or
constructed, that (a) a vocabulary scan catches, (b) shape B does not, and (c) is
not simply an author writing the word "disassembly" next to their own confession.
The one recorded doc-resident breach fails (a). Until such a case exists, the
division of labour in [[clean-room-audit-checks]] stands: **the mechanical floor
catches lapses, the human paper trail catches breaches** — and the lapse this
class produces is a *shape*, not a *word*.

Checks 1–2 also keep their asm-only denominator: check 2's per-file attestation
convention is for shipped source, and `.md` files carry no header block.

### 3.2 Check 5 — the decoded-listing floor

A new **gating** check, repo-wide rather than per-target, because §1.3 measured the
class in both asm comments and docs:

```
LISTING_LINE = ^[\s>|*`]*\$?<4 hex digits>[:.]?\s+<Z80 mnemonic>\b
finding      = a run of >= 2 consecutive matching lines
```

* **`>= 2`, not 3.** The threshold is not arbitrary — it is `e8558c2`'s own
  remediation rubric: *"single call/branch **targets** … stay ALLOWED; multi-instruction
  stock routine bodies … are FORBIDDEN"*. Two IS a multi-instruction body. Measured
  cost of 2 over 3: **zero** — the tree contains no 2-line run that is not also a
  3-line run, at any point in 978 commits.
* **Denominator**: every first-party `.md`/`.asm`/`.inc`/`.py`/`.tcl`/`.txt`/`.bas`/`.yml`
  file, excluding `build/`, `scratchpad/`, `.git/`, `.claude/`, `__pycache__/`.
  **690 files today**, verified identical to `git ls-files` (0 difference either
  way) so the sweep cannot silently diverge from what is tracked.
* **A file-count floor**, `MIN_SWEEP_FILES = 600`, exit **2**. Same reason check
  1 has one: a glob that stops matching reads as a cleaner tree.
* **Cost**: 0.33 s to scan 234 161 lines, 0.53 s including the walk. The gate
  currently costs 0.27 s; it will cost under a second.

### 3.3 The allowlist IS the canary, not a suppression list

`tools/citations-listing-allow.txt`, in the shape of `deadcode-allow.txt`
([[deadcode-gate]]: *"an allowlist that must keep matching is a control; one that
only suppresses is rot"*):

```
<relpath>  <sha256[:12] of the run's text>  <reason>
```

* **Content-anchored, not line-anchored.** Line numbers rot; a digest does not.
  Editing the allowed run re-opens it, and a *new* listing elsewhere in the same
  file is still reported — a path-level allowlist would blind the file.
* **A missing reason is a parse error.**
* **Every entry must still be produced by the sweep.** If an allowlisted digest
  stops appearing, that is either a stale entry (delete the line) or a sweep that
  has gone blind — both exit **2**, never a quiet green.

One entry at landing: §2.6's C-BIOS docstring.

### 3.4 The self-test is SYNTHETIC — and it has to be

Check 1's self-test pins its four historical false positives *verbatim*. Check 5
cannot do that: **its true-positive vectors are the forbidden artifact.** Quoting
the 2026-07-04 listing into `tools/` to prove the rule catches it would reproduce
the proprietary listing in a second file and make the tool its own first finding.

So the vectors are **invented** — synthetic address/mnemonic runs with no
provenance at all — plus real negative vectors lifted from our own honest prose.
Misclassification exits **2**. Same disposition rule as check 1: 1 says the tree
regressed, 2 says nothing below it was measured.

⚠️ The same constraint applies to this document: **§2 describes both listings
positionally and never reproduces either.** A spec that quoted its subject would
be the breach.

### 3.5 Remediate §2.5's finding

`disk/docs/tier2-f338-default-spec.md:22–24` is regrounded to behavioural form —
the observed branch condition and its two outcomes, which is what the section
actually rests on (a poke test, already cited two paragraphs below) — following
the M20 §11.1 / `e8558c2` pattern verbatim. The `$C26B` **address** and the
branch **target** stay: those are call/branch-target observations the rubric
allows. Prose only.

Logged in `docs/clean-room-audit.md`'s run log, including the fact that
`e8558c2`'s "fully remediated" verdict was **incomplete**, so the record is not
left overstating itself.

### 3.6 What does NOT change

* **Checks 1–4 keep their rules and their denominators.** §2.1 found no defect in
  check 1's rule; it found the rule aimed at a different class.
* **The advisory check stays advisory** — D-CITEJUDGE §2.5 measured it stable and
  triaged; the residual is already filed.
* **Shape A stays uncovered**, §2.2, stated as a coverage limit rather than
  approximated. The human full-verify remains the only backstop for the inline
  form, exactly as `docs/clean-room-audit.md` says.
* **`.md` files get no attestation requirement** (§3.1).

---

## 4. Predicted GREEN — fixed BEFORE the change

| # | measurement | predicted |
|---|---|---|
| G1 | `python3 tools/audit_citations.py` | **rc 0** |
| G2 | checks 1–2 files scanned | `disk` **8**, `basic` **107**, `tape` **1** — **116**, unchanged |
| G3 | `[FORBIDDEN]` / `[NO-ATTEST]` / `[PRIVATE-REF]` | **0 / 0 / 0** |
| G4 | `[REVIEW]` advisory | **7**, the same 7 files/names |
| G5 | check 1 rule self-test | **10 of 10** |
| G6 | check 5 sweep denominator | **690** files, floor 600 |
| G7 | check 5 self-test | **10 of 10** |
| G8 | `[LISTING]` findings | **0** unallowlisted, **1** allowlisted (`probes/lib/omsx_repl.py`) |
| G9 | check 5 over `da93f0c`'s tree, before §3.5 | **2** runs — the control proving G8's 0 is a remediation, not a blind sweep |
| G10 | `sha256 build/disk.rom` | `2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27` |
| G11 | `sha256 build/sub.rom` | `b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e` |
| G12 | `sha256 build/basic-reloc.rom` | `3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af` |
| G13 | `sha256 build/zerobas-main-eu.rom` | `d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e` |
| G14 | walls, from CLEAN | low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B** |
| G15 | closure walks | abi **122+4**, `--page0` **718+15**, `--page1` **522+41** |
| G16 | dead-code seeds | main **285**, sub **102**; 0 dead both, +1 allowlisted |
| G17 | `kwtable` | **1041 B** |

**G16 is the one to watch**, as in D-CITEJUDGE: `check_dead_code.py`'s
`external_names` roots are `['sub', 'tools']` and it reads **comments**, so the
prose this slice adds to `tools/audit_citations.py` and to the new allowlist can
seed a main-build label. `docs/` and `disk/docs/` cannot. **Any movement in
285/102 is a finding about this slice's own prose.**

🎯 **This slice must be ROM-behaviour-neutral** — it touches one Python tool, one
allowlist, and three prose sites. G10–G13 are the proof; any ROM byte change is a
finding.

---

## 5. Predicted RED — the knives

Each refusal is run **twice** ([[refusal-survives-only-if-the-artifact-does]]).
The knife script snapshots to scratchpad **before** cutting and restores from
there — never `git checkout --` ([[knife-cleanup-restores-from-head]]) — and
**refuses to start unless the subject is green**, so an aborted run cannot freeze
its own damage into the next restore point.

| knife | cut | predicted |
|---|---|---|
| **K1** | plant a synthetic 3-line listing in a `docs/` file | rc **1**, one `[LISTING]` naming that file/line |
| **K1b** | plant the same in a scanned `.asm` **comment** | rc **1** — proves §1.3's real gap is closed, not just the doc half |
| **K1c** | *control* — plant a **single** address+mnemonic line (a branch target: allowed by the rubric) | rc **0** |
| **K1d** | *control* — plant 3 consecutive lines of ordinary prose containing the words `and`, `or`, `set`, `in` | rc **0** |
| **K2** | gut only the judgement (`LISTING_LINE` matches every line), emission and call site intact | self-test fires **rc 2** |
| **K2b** | *same gutting with the check-5 self-test disabled* | predicted rc **0** — a fully gutted rule reading as a clean tree. This is what the self-test buys. |
| **K3** | gut `LISTING_LINE` to match nothing | self-test fires **rc 2**, not a clean rc 0 |
| **K4** | break the sweep glob (point it at a directory that does not exist) | rc **2** on `MIN_SWEEP_FILES`, **not** a clean "0 findings" |
| **K4b** | *same break with `MIN_SWEEP_FILES` zeroed* | predicted rc **0** — 690 fewer files, silently, reported as clean |
| **K5** | corrupt the allowlisted digest so the entry no longer matches any run | rc **2** — the canary; a stale entry and a blind sweep are the same disposition |
| **K6** | remove §3.5's remediation (restore the `$C26B` listing) | rc **1** — proves the remediation is what turned G8 green |
| **K7** | plant K1's offender and run `make basic-reloc` unmodified | build **fails**; run twice (PHONY, so a second `make` re-runs the recipe) |
| **K8** | *control* — same plant with check 5 disabled | `make basic-reloc` **passes** — K7's failure is check 5, not the plant's side effects |

**K2b, K4b and K5 are the ones that matter.** They are the only knives that
distinguish *"the tree is clean"* from *"the instrument went blind"* — and blind
is the state check 1 was in, for this class, for all 978 commits of the repo's
life.

⚠️ **Check that every knife actually CUT** before believing a green
([[knife-aimed-at-the-wrong-gate]]): D-CITEJUDGE's K4 came back green because the
header it gutted attested twice.

---

## 6. As-built — ✅ LANDED 2026-08-06

**ROM-neutral, proved by hash.** All four `build/*.rom` byte-identical to
`da93f0c` from a `rm -rf build` rebuild, re-verified a second time after the
knives:

```
2c630d3dfeec727b5ec87c3c3140cfa5fdedc6b6a144d346467e6142b6e33c27  build/disk.rom
b2935188963eda429d61fc6ded6350a8067f1ccc09b5d4a9edc4713da2697e5e  build/sub.rom
3f1cd5866314270e3ae325b56f8707e62f26b7d65210f1c1d64510b7c48594af  build/basic-reloc.rom
d061cd58ad4cede795221fef1c0b0c9ae2c0d0c7a090f6a2b8fcef1154d9e28e  build/zerobas-main-eu.rom
```

### 6.1 GREEN, scored — 15 of 17 hit, and both misses are findings

| # | predicted | measured |
|---|---|---|
| G1 | rc 0 | **rc 0** |
| G2 | 8 / 107 / 1 files | **8 / 107 / 1** (97 / 181 / 15 provenance-bearing) |
| G3 | 0 / 0 / 0 | **0 / 0 / 0** |
| G4 | 7 `[REVIEW]`, the same 7 | **7, identical files and names** |
| G5 | check 1 self-test 10/10 | **10/10** |
| G6 | **690** files swept | 🔴 **692** — see below |
| G7 | check 5 self-test 10/10 | **11/11** — a vector was added, see below |
| G8 | 0 unallowlisted, **1** allowlisted | 🔴 **0 unallowlisted, 2 allowlisted** — see below |
| G9 | 2 runs over the pre-remediation tree | **2** (`tier2-f338-default-spec.md:22` digest `1f6d05d3a66f`, `omsx_repl.py:366`), measured live at rc 1 before §3.5 |
| G10–G13 | four hashes | **all four identical** |
| G14 | 23 / 356 / 3869 / 2324 | **23 / 356 / 3869 / 2324** (sub walls read off the byte-identical image) |
| G15 | abi 122+4, p0 718+15, p1 522+41 | **122+4, 718+15, 522+41** |
| G16 | main 285 / sub 102 seeds | **1551 spans/285 → 0; 1451 spans/102 → 0 (+1)** |
| G17 | kwtable 1041 B | **1041 B** |

**G16 held.** The prose added to `tools/audit_citations.py` and the whole new
`tools/citations-listing-allow.txt` — both inside `check_dead_code.py`'s
`external_names` roots, both read including comments — seeded nothing.

🔴 **G6 missed for a boring reason worth writing down: 690 was the count *before*
this slice existed.** The sweep is repo-wide, so the spec and the allowlist this
slice writes are themselves inside the denominator. A predicted denominator has to
include the prediction's own deliverables.

🔴 **G8 missed because the prediction was made with the defective instrument.**
"1 allowlisted" was measured with a `LISTING_LINE` whose prefix class had no
comment leaders — see §6.2a. The second site (`probes/lib/latch_check.py:82`) was
*present the whole time* and invisible to the rule that produced the prediction.
⇒ **a predicted set is only as good as the instrument that produced it**; when a
knife changes the rule, every number predicted from the old rule is stale.
G7 moved 10→11 for the same reason: K1b's finding earned a permanent vector.

### 6.2 RED — 14 knives, all as predicted, each run twice

| knife | result |
|---|---|
| **K1** synthetic 3-line listing in `docs/dev-workflow.md` | rc **1**, `[LISTING] docs/dev-workflow.md:289` |
| **K1b** the same in a **scanned** `.asm` comment (`sub/beep.asm`) | rc **1**, `[LISTING] sub/beep.asm:17` — **only after §6.2a's fix** |
| **K1c** *control*, a single address+mnemonic line (a branch target) | rc **0** |
| **K1d** *control*, 3 prose lines using `and`/`or`/`set`/`in`/`ret` | rc **0** |
| **K2** gut the judgement (matches everything) | rc **2**, self-test fires |
| **K2b** same, self-test disabled | rc **2** — the **allowlist canary** catches it |
| **K3** gut it to match nothing | rc **2**, self-test fires |
| **K3b** same, self-test disabled | rc **2** — canary again |
| **K3c** same, **both** controls removed | rc **0**, *"clean"* |
| **K4** break the sweep glob | rc **2**, *"0 file(s), floor 600"* |
| **K4b** same, floor zeroed | rc **2** — canary again |
| **K4c** same, floor zeroed **and** canary emptied | rc **0**, *"clean"* |
| **K5** corrupt the allowlisted digest | rc **2** — the canary, exactly as designed |
| **K6** *control*, restore `da93f0c`'s pre-remediation revision verbatim | rc **1**, `[LISTING] …:22` — proves §3.5's regrounding is what turned it green |
| **K7** plant the offender, `make basic-reloc` | **fails both runs**; PHONY, so a second `make` re-runs and refuses again |
| **K8** *control*, same plant with check 5 gutted | **passes** — K7's failure is check 5, not the plant |

**K3c and K4c are the ones that matter**, and they exist only because the first
run of K2b/K3b/K4b **disagreed with the spec**. §5 predicted rc 0 for
"self-test disabled"; the measurement was rc 2, because the **allowlist canary is
a second, independent control** and either one alone catches a blinded sweep.
Removing both is what produces the silent `rc 0, "clean"` — which is the state
check 1 has been in, for this class, for all 978 commits of the repo's life.
⇒ the spec understated its own instrument; the knives corrected it.

### 6.2a 🔴 K1b came back GREEN, and it was the RULE that was wrong

The first `LISTING_LINE` prefix class was `[\s>|*`]*` — indentation and markdown.
It could not match a line beginning `;`, so **it was blind to a listing in an
`.asm` comment**: precisely the half of the corpus that justified building it
(§1.3 — 6 of the ~50 sites the 2026-07-07 sweep remediated were `disk/*.asm`
comments). K1b planted there and the gate stayed green.

Per [[knife-aimed-at-the-wrong-gate]] the first question is *did the knife cut* —
it had. The rule was wrong. Fixed by adding `;`, `#` and `/` to the prefix class.
Cost over all 692 files: **one additional finding, and it is genuine**
(`probes/lib/latch_check.py:82`, the same C-BIOS window as §2.6, allowlisted with
the same reason). The plant became self-test vector 11.

⇒ **a rule aimed at two corpora must be knifed in both.** The doc half passed on
the first cut and would have shipped a gate that was half-blind, with a spec
claiming repo-wide coverage.

### 6.2b The knife script caught its own drift

`gut_match_all` pasted `LISTING_LINE`'s regex text verbatim into a `.replace()`.
The moment §6.2a changed that regex the replace matched nothing — the exact
[[knife-cleanup-restores-from-head]] family, where the apparatus produces the
reading. It surfaced as an `AssertionError` rather than a green knife **only
because every cut asserts it cut**. Re-anchored on the whole assignment. Two
rules earned their place in the runner: the restore point is a snapshot taken
before the first cut, and the script refuses to start unless the subject is green.

### 6.3 The filed claim, scored

| filed | measured |
|---|---|
| *"`audit_citations.py` does not scan `docs/`"* | **RIGHT**, and **not the load-bearing fact** — the class it was filed for also lives in files the tool *does* scan, where the rule read it as clean. §1.3 |
| *"the project's **only** recorded clean-room breach lived there"* | **WRONG.** Four recorded events, of which ~50 sites on 2026-07-07 dwarf the one named — and 6 of those were in scanned `.asm`. §1.3 |
| *"remediated at `4c14006`, found by a human paper trail, not by the floor"* | **RIGHT**, and it is why the answer is a decline: the floor could not have found it. **0 forbidden tokens** in the quarantined text; the *remediation* is what carries one. §2.1 |
| *"the negation-context false-positive surface is large and UNMEASURED — measure it before proposing a rule"* | **RIGHT, and correct guidance.** Measured: 243 hits, **26 affirmative, 0 breaches**, 16 of the 26 inside the policy's own three documents. §1.2 |

Two right, one right-but-not-load-bearing, one wrong. Running total for this arc:
**thirteen filed justifications checked — eight wrong, two right-but-misdirected,
three right.**

### 6.4 Corpus — ALL GREEN, sequential, from the clean tree

18 of 18, rc 0 each:

`basic-reloc` (23 / 356 / 3869 / 2324; closure 122+4, 718+15, 522+41; dead code
1551/285 → 0 and 1451/102 → 0 (+1); kwtable 1041 B) · `unit-test` ·
`audit-citations` (8/107/1, self-tests 10/10 + 11/11, 692 swept, 2 allowlisted,
7 advisory) · `preflight-check` · `injector-check` · `latch-check` 16/16 ·
`dexp5-pin` 16/16 · `linemax-acceptance` 60/60 · `lnblank-acceptance REPEAT=2`
**536/536, allowlist empty** · `subrom-acceptance` · `subrom-inttest` ·
`graphics-floor-acceptance` · `graphics-acceptance` · `probe` (disk + basic +
tape) · `fat-error-acceptance` 8/8 + directory check over a LIVE FAT layer ·
`diskbasic-acceptance` 34/34 · `bdos-acceptance` 12/12 · `lof-acceptance`
**45 cases, 0 unfiled divergences, 0 oracle drifts, 0 mangled**.

⚠️ **`lof-acceptance` sighting 3 has now failed to occur in SIX consecutive
slices** (D-PINDATA, D-INJSINK, D-ROMJUDGE, D-DSKJUDGE, D-CITEJUDGE, D-DOCJUDGE).
Whole log captured, not tailed.

### 6.5 What this slice did NOT do

* **Did not extend checks 1–2 to `docs/`** — declined on measurement (§3.1), with
  the case a future slice would have to produce to re-open it.
* **Did not cover the inline decoded form** (§2.2) — measured undecidable, stated
  as a coverage limit. This is the one that keeps the human full-verify
  load-bearing.
* **Did not cover raw opcode-byte renderings** (`CD 54 54`, and the C-BIOS
  locator signatures in `probes/lib/latch_check.py`). Same problem as shape A: our
  own ROM's bytes appear in our own docs constantly. Unmeasured; filed.
* **Did not make the C-BIOS judgement** — both allowlist entries are written down
  with their reason and flagged for the next human paper trail, which is where
  `docs/clean-room-audit.md` puts that call.
* **Did not build an advisory allowlist** for the 7 `[REVIEW]` headers — still
  filed, unchanged by this slice.
