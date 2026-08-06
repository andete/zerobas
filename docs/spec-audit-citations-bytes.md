<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-BYTEJUDGE — should the clean-room floor scan for raw opcode BYTES?

Companion to [`spec-audit-citations-gate.md`](spec-audit-citations-gate.md)
(D-CITEJUDGE, the gate's wiring and denominator) and
[`spec-audit-citations-docs.md`](spec-audit-citations-docs.md) (D-DOCJUDGE, the
decoded-**listing** shape = check 5). This one takes the residual D-DOCJUDGE
filed in its §6.5 and `TODO.md`:

> ⚠️ **Raw opcode-BYTE renderings are still uncovered** — `CD 54 54`, `DB A8 C9`,
> and the C-BIOS locator signatures in `probes/lib/latch_check.py`. Check 5 keys
> on the *listing shape*; a hex byte run is a different shape and its
> false-positive surface is UNMEASURED.

**Verdict: the general rule is DECLINED on a proof, not on a statistic** (§2.2);
**one narrow sub-shape is decidable and lands as check 6** (§3.2).

---

## 0. The question this slice was told to answer FIRST

*"Are raw bytes uncovered?"* is a property of the tooling, and
`[[correct-claim-can-be-the-wrong-question]]` says such a property is usually
true and usually not what decides anything. The load-bearing question is:

> **Would a raw-byte rule have caught anything checks 1 and 5 miss, at a
> false-positive cost the tree can carry?**

It has two halves and **they have opposite answers**, which is why this slice is
neither a clean decline nor a clean ship:

| half | measured | §  |
|---|---|---|
| **Recall** — is the residue after checks 1 and 5 empty? | **NO. 20 offender lines; checks 1 and 5 flag 0 of 20.** | §2.1 |
| **Precision** — can any rule that catches them avoid the innocents? | **NO, and provably not: the innocent set carries the offenders' own bytes.** | §2.2 |

The D-DOCJUDGE decline turned on recall (0 on every recorded breach). This one is
the mirror image: recall is *perfect and exclusive* — the class is caught by
nothing else — and the rule dies on precision anyway.

---

## 1. The denominator

### 1.1 The sweep corpus

Check 5's sweep, reused unchanged: **692** first-party text files
(`.md .asm .inc .py .tcl .txt .bas .yml`, minus `build/ scratchpad/ .git/ .claude/
__pycache__/ .vscode/`). This spec adds one file, so the as-built figure is
**693** — stated here because D-DOCJUDGE predicted a count taken *before its own
deliverables existed* and had to correct it.

### 1.2 The labelled corpus — and it has THREE classes, not two

Both remediation commits pair real offenders with hand-reviewed replacements:

* `4c14006` — the 2026-07-04 M20 §11.1 breach (`disk/docs/tier2-m20-spec.md`).
* `e8558c2` — the 2026-07-07 systemic full-verify sweep, 18 files.

Taken together, at `-U10`, excluding `docs/clean-room-audit.md` (the run log,
which only gains text):

| class | lines | what it is |
|---|---:|---|
| **offenders** (removed) | **134** | the sweep judged these forbidden |
| **innocents** (added) | **179** | hand-reviewed replacements, in the tree today |
| **kept context** (unchanged, inside the same hunks) | **984** | 🔴 the sweep *read* these and left them |

⚠️ **The filed figures were 121 / 156.** Those are `e8558c2` alone with blank
lines filtered; both commits together, unfiltered, are 134 / 179. Not a defect in
the filing — but a rule scored against the filed numbers would be scored against
the wrong denominator, so it is restated here.

🔴 **The third class is the one that matters and the filed framing has no name
for it.** A rule that fires on the *innocent* set has a failing control
(`[[control-that-fails-must-be-fixed]]` — that is what killed all four of
D-DOCJUDGE's inline-mnemonic variants). A rule that also fires on lines the human
sweep **deliberately kept, in the very hunks it was editing**, is worse: those are
not lines it failed to reach, they are lines it reached and adjudicated.

### 1.3 The false-positive surface, measured over the live tree

Never measured before this slice. Every variant, over the same 692 files:

| variant | live lines | live files |
|---|---:|---:|
| ≥2 hex pairs, space/comma separated | 1326 | 277 |
| ≥3 hex pairs | 619 | 157 |
| ≥3 pairs, at least one hex letter `A–F` | 445 | 114 |
| ≥3 pairs, at least one **uppercase** hex letter | 393 | 103 |
| ≥4 pairs | 371 | 108 |
| ≥6 pairs | 178 | 72 |
| one run of ≥8 hex characters | 528 | 108 |

For scale: the rule that *did* land in D-DOCJUDGE (check 5, the listing shape)
had **2** hits over the same corpus. The cheapest raw-byte variant is **196×**
noisier than that, and the quietest one that still catches the class is **196×**
as well — the curve is flat because the class and the noise are the same shape.

---

## 2. Falsify by measuring, not by arguing

### 2.1 The residue is NOT empty — checks 1 and 5 score 0 of 20

Locate every offender line in its **pre-remediation** tree (`4c14006^`,
`e8558c2^`), keep the ones carrying a hex-byte run, and run the shipped
`forbidden_hit()` (check 1, with its real 3-line negation window) and
`listing_runs()` (check 5) over the same file contents:

```
offender lines carrying a hex-byte run:   20
  already flagged by CHECK 1 (vocabulary):  0
  already flagged by CHECK 5 (listing):     0
  RESIDUE (neither):                       20
```

**So this is not the vocabulary case.** D-DOCJUDGE declined widening check 1
because its recall on every recorded breach was 0. Here the class is caught by
nothing at all, and one of the 20 sits in `disk/kernel.asm` — a file check 1 has
scanned since day one. If precision were survivable, this rule would be an easy
ship.

### 2.2 🔴 THE PROOF: the innocent set carries the offenders' own bytes

Two of the 179 innocent lines carry a hex-byte run, and 10–16 of the 984 kept
context lines do. That alone is a failing control. But one pair settles it
without any statistics at all:

> `disk/docs/tier2-a3-spec.md:20` — a two-column table row comparing our `$0038`
> vector with the reference machine's. The remediation **kept the row's leading
> `C3 AE DD` = `jp $DDAE` byte-for-byte** and replaced only the parenthetical
> that decoded the target routine's register-save body into mnemonics.

**The hex run is identical on both sides of the edit.** No line-level lexical
rule can fire on the offender and not on its own hand-reviewed replacement,
because on that line the bytes were never the offending element — the decoded
*body* was. This is a proof about the shape of the class, not a threshold that
tuning could rescue.

The same edit is visible from the other side one file over: on
`provider-oracle-scope.md`'s `$F365` row the bytes **were** the offending element
and were removed, while `FF FF FF` on the *same line* was kept. **The 2026-07-07
rubric cuts through the middle of individual lines**, and the two halves are
lexically indistinguishable.

### 2.3 The live tree keeps raw reference-machine bytes ON PURPOSE

15 live lines carry a hex run *and* attribute it to the reference machine on the
same line — `C3 AE DD` (4 sites), `C3 57 DF` (stock's `$F368` jump table),
`95 E5 01 F9 00 02 0F 04` (stock's DPB), `F7 87 10 40 C9`, `D0 C9` (a data
disk's boot stub, in the scanned `disk/init.asm`), `D8 19 3E 40 0A`. All 15 were
read by the 2026-07-07 sweep and kept.

So even a **perfect ours-vs-theirs oracle** — the discriminator a text scanner
cannot have, and the one `spec-audit-citations-docs.md` §2.3 already refuted on
addresses — would fire on all 15 and all 15 are legal.

🔴 **And 2 of the 15 are in the tool's own governance documents** (`TODO.md`'s
entry for this very item, and `spec-audit-citations-docs.md` §6.5). D-DOCJUDGE
found 16 of 26 affirmative hits inside the three documents that define and record
the policy; the same shape recurs here. **A rule for this class reddens on its own
rulebook** — because a rulebook must name what it forbids.

### 2.4 The policy's own discriminator is the PROVENANCE OF THE READING

`docs/allowed-sources.md`'s ✗ list is precise, and the precision is the problem:

> the bytes of any proprietary system binary (reference ROM, MSXDOS.SYS,
> COMMAND.COM) read as anything **other than an oracle** (identical inputs in,
> observed outputs out)

The forbidden thing is not *bytes in a document*. It is **how the bytes were
obtained**. The identical byte string is forbidden when lifted from a ROM code
region and legal when observed through a documented interface — and
`docs/clean-room-audit.md:495` adjudicates exactly that, in the project's own
voice, for a 5-byte hex run:

> *"The `D8 19 3E 40 0A` cycle is observed CONOUT-call/VRAM output, not stock
> code."*

A host-side text scanner has no access to the provenance of a byte. This is
**strictly worse** than the address problem that killed the audit doc's own
follow-on candidate: an address at least *appears in the text* and merely fails
to discriminate; provenance does not appear in the text at all.

### 2.5 And the lexical class cannot even tell hex from decimal

`10, 20, 30, 40` (test line numbers), `12 15 18 19 50 51 53 54` (probe case
indices) and `0: [0, 1], 1: [2, 3, 4]` all match a "run of hex byte pairs",
because every decimal digit is a hex digit. This is why the ≥2-pair variant
reaches 1326 lines. Requiring a hex letter `A–F` removes it (1326 → 445) but
removes genuine all-digit byte runs with it, and 445 is still unusable.

### 2.6 🔴 The filed item's third example is ALREADY covered

The residual names `probes/lib/latch_check.py`'s `SIG`/`SIG2` as uncovered. They
are not:

* the same file's comment block is **already a check-5 finding**, already
  **allowlisted** (`tools/citations-listing-allow.txt`, digest `5565467e6422`)
  with a written reason, and already **filed for a human C-BIOS paper-trail
  confirm** — a standing `- [ ]` item in `TODO.md`;
* `SIG`/`SIG2` are the same window, in the same file, resting on the same
  adjudication.

⇒ the one live artifact the residual pointed at is under review by the machinery
D-DOCJUDGE already built. Four filed claims checked in this slice; see §6.3.

### 2.7 The one sub-shape that IS decidable: the hex-dump ROW

One offender line is not a mnemonic-adjacent annotation but a **dump**: a table
cell holding four space-separated 8-hex-character groups — 16 bytes of the
reference disk ROM's loader, quoted so that the reader could compare them against
our all-zero region. (Described positionally, not quoted:
`[[a-selftest-vector-can-be-the-forbidden-artifact]]` — quoting it here would
reproduce the artifact in a third file, and this check would then find its own
spec.)

That shape — **≥2 consecutive 8-hex-character groups, not all identical** —
measures as follows:

| corpus | hits |
|---|---:|
| live tree, 692 files | **0** |
| labelled offenders (134) | **1** — the genuine breach |
| labelled innocents (179) | **0** |
| labelled kept-context (984) | **0** |

The "not all identical" clause is not fitting: it drops `00000000 00000000
00000000 00000000` (our own *empty* region, annotated as such on the sibling table
row), because a uniform fill carries no information about anyone's code. Without
it the rule scores 2 offenders, one of which is a false positive by construction.

**Walked over all 979 commits** (the house method — `git ls-tree -r` +
`git cat-file --batch`, blob-cached), with the **final** rule, not an earlier
variant:

```
[transition] idx=  0  a44fbdf5  files=[]
[transition] idx=193  1ecf2e35  files=['disk/docs/provider-oracle-scope.md']
[transition] idx=468  e8558c2e  files=[]
```

**One file, ever. Two transitions: red on the exact commit that introduced the
dump, green on the exact commit that remediated it.** Zero hits across the other
977 commits. That is the same evidence profile that made check 5 shippable, at a
smaller N — stated plainly in §3.2 rather than dressed up.

### 2.8 A hand pass over the live tree found no unremediated breach

24 live hex runs sit within ±3 lines of a proprietary-binary mention. Adjudicated
by hand against the 2026-07-07 rubric, all 24 are legal: ours
(`F7 87 10 40 C9`, `C3 51 42`, `C3 FA 41`, our own crunch and GETDPB output),
data layout (DRVTBL, DPB, an FCB filename), a jump **vector** (call-target class),
or an observed value (`D8 3E 40` screen output).

**One is a review candidate, not a finding:** `provider-oracle-scope.md:685`
renders 16 bytes of MSXDOS.SYS's entry-vector header inside a *byte-identical*
oracle claim (our BDOS `$27` load equals the on-disk file). That is the legal
"read as an oracle" form on its face, and the judgement
`docs/clean-room-audit.md` reserves for a human. It is noted for the next paper
trail — **not** turned into a gate finding, because §2.2–§2.4 are exactly the
argument that a tool cannot make this call.

🔴 **And it is the sharpest illustration of the decline.** The one live line worth
a human's attention is lexically indistinguishable from the other 392.

---

## 3. Design

### 3.1 DECLINED: any general raw-opcode-byte rule

Not "deferred", not "too noisy for now" — **declined on §2.2**, which is a proof
that the offender and innocent sets share the deciding feature, and on §2.4,
which locates the real discriminator outside the text.

**What a future slice would have to produce to re-open it.** Not a better
threshold — every threshold is already measured in §1.3. It would need a
discriminator that scores **0 on all three** of:

1. the 179-line innocent replacement corpus,
2. the 984-line kept-context corpus (**this is the new bar** — D-DOCJUDGE's
   inline-form re-open condition names only the replacement corpus, and the kept
   set is both larger and more decisive),
3. the 15 live reference-attributed lines of §2.3,

**while still firing on ≥1 of the 20 residue lines of §2.1.** Since the a3-spec
pair (§2.2) is *byte-identical across the edit*, any such discriminator must read
something other than the line's text — which means it is not this tool.

The honest standing position is the one `docs/clean-room-audit.md` already takes:
**this class's backstop is the human full-verify trail**, exactly as for the
inline decoded form. That is now written down with the measurement behind it
instead of as an unexamined residual.

### 3.2 Check 6 — the hex-dump row

Ships. Scope stated without inflation:

* it detects **a hex-dump row**, not "raw opcode bytes". The check's name, its
  output text and its `TODO.md` entry all say so, because a check named for the
  class would read as coverage the tree does not have;
* **recall against §2.1's residue is 1 of 20 (5 %)** — but that 1 is the most
  severe member: a 16-byte contiguous dump of a proprietary binary is nearer a
  copy than any 3-byte call target is;
* **measured cost is zero**: 0 hits over 692 live files and over 979 commits.

Reuses check 5's sweep (`sweep_files()`, `MIN_SWEEP_FILES`), so the collapsed-glob
floor already covers it. Gating; a finding is exit 1, an instrument fault exit 2.

### 3.3 The self-test vector IS the canary — and it has to be handled

🔴 **This check's positive vector is a problem check 5 did not have.** Check 5's
`LISTING_LINE` is anchored at line start, so a vector written into a Python list
never matches the tool's own source. Check 6 searches *anywhere in a line*
(dumps live inside markdown table cells), so **a synthetic vector in
`tools/audit_citations.py` is a hit on `tools/audit_citations.py`** — the control
becoming the finding, [[a-selftest-vector-can-be-the-forbidden-artifact]] one
level in.

Resolved by making that fact the feature: the synthetic vector is **allowlisted
with a reason** in `tools/citations-dump-allow.txt`, and the allowlist asserts
every entry is **still produced by the sweep**. So check 6 has a permanent live
member, and its green state is never the bare "found nothing" that
`[[deadcode-gate]]` warns about. The vector is invented — no provenance, no
derivation — so writing it down forbids nothing.

Three independent controls, matching D-DOCJUDGE's measured finding that the
self-test and the allowlist each alone catch a blinded sweep:

1. the rule self-test (synthetic positives, real negatives lifted from our own
   honest prose — digests, token tables, decimal case-index lists);
2. the digest-anchored allowlist canary;
3. `MIN_SWEEP_FILES`, shared with check 5.

### 3.4 What does NOT change

Checks 1–5, their scan lists, floors, allowlist and self-tests; the Makefile
wiring; every ROM byte. `docs/clean-room-audit.md` gains the §2.4/§2.8 numbers
next to the sentence that recommended this class be mechanised — the
`[[a-recommendation-in-the-record-is-still-a-claim]]` discipline of writing the
refutation back where the recommendation lives.

---

## 4. Predicted GREEN — fixed BEFORE the change

Exact values. Anything else is a finding.

| # | prediction |
|---|---|
| G1 | `sha256(build/disk.rom)` = `2c630d3d…e33c27`, `sub.rom` = `b2935188…97e5e`, `basic-reloc.rom` = `3f1cd586…594af`, `zerobas-main-eu.rom` = `d061cd58…9e28e` — all four **unchanged** |
| G2 | walls from clean: low **23 B**, page 1 **356 B**, sub p0 **3869 B**, sub p1 **2324 B** |
| G3 | closure walks: abi **122+4**, `--page0` **718+15**, `--page1` **522+41** |
| G4 | dead code: main **1551** spans / **285** seeds → 0; sub **1451** / **102** → 0 (+1 allowlisted). ⚠️ this slice writes prose into `tools/`, an `external_names` root that is read *including comments*; any movement is a finding about my own prose |
| G5 | kwtable identity: **1041 B**, 1 occurrence, 0 in the main image |
| G6 | `audit-citations` per-target files **8 / 107 / 1**; check-1 self-test **10/10**; check-5 listing self-test **11/11**; **7** advisory |
| G7 | check 5: **693** files swept (692 + this spec), **2** allowlisted, 0 findings |
| G8 | check 6: **693** files swept, **1** allowlisted (the synthetic canary), **0** findings |
| G9 | check-6 self-test passes at its full row count; `make audit-citations` exits **0** |
| G10 | corpus (§6.4 list) ALL GREEN, sequential, from the clean tree |

⚠️ **G7/G8 are predicted from the rule as written in §3.2.** If a knife changes
the rule, both are restated, not carried — the D-DOCJUDGE failure mode where a
"1 allowlist entry" prediction was produced by an instrument blind to half its
corpus.

## 5. Predicted RED — the knives

Every knife **asserts it cut** before reading a result
([[knife-aimed-at-the-wrong-gate]]). The restore point is a **scratchpad snapshot
taken before the first cut**, never `git checkout --`
([[knife-cleanup-restores-from-head]]), and the script **refuses to start unless
`make audit-citations` is green**. Every refusal runs **twice**
([[refusal-survives-only-if-the-artifact-does]]).

Per [[a-rule-for-two-corpora-must-be-knifed-in-both]], check 6 claims **repo-wide**
coverage, so it is planted in **every genre it names** — prose, asm comment,
Python comment — not once in the genre that was open while writing it. The
self-test's positive vectors are counted by genre **before** anything is run.

| # | cut | predicted |
|---|---|---|
| K1a | plant a synthetic dump row in a `docs/*.md` prose line | rc **1**, `[DUMP]` names the file |
| K1b | plant the same in an **asm comment** (`sub/beep.asm`) | rc **1** |
| K1c | plant the same in a **Python comment** (`probes/lib/omsx_repl.py`) | rc **1** |
| K1d | control — plant a *uniform-fill* row (all groups identical) | rc **0** |
| K1e | control — plant a 64-char sha256 and a 12-char digest on one line | rc **0** |
| K2a | gut the judgement only: keep emission + call site, make the rule never match | self-test fires → rc **2** |
| K2b | K2a **+ remove the self-test** | canary stops matching → rc **2** |
| K2c | K2a + remove self-test **+ remove the allowlist entry** | 🔴 rc **0**, "clean" — the silent-blind state |
| K3a | break the allowlist digest (one character) | rc **2**, stale entry named |
| K3b | delete `tools/citations-dump-allow.txt` | canary gone → rc **2** |
| K4 | `make basic-reloc` with K1a planted | fails, and fails again on re-run (PHONY) |

🔴 **K2b is predicted rc 2, not rc 0.** D-DOCJUDGE predicted the analogous rows rc
0 and measured rc 2, because the self-test and the canary are *independent*
controls and either alone catches a blinded sweep. Only **K2c**, with both
removed, should produce the silent `rc 0 "clean"`. Predicting it correctly this
time is itself a test of whether that lesson transferred.

---

## 6. As-built — ✅ LANDED 2026-08-06

Shipped: **check 6** (`tools/audit_citations.py`), `tools/citations-dump-allow.txt`,
this spec, the two refutations written back into `docs/clean-room-audit.md`, and
the `TODO.md` record. **Declined and recorded: everything else** (§3.1).

### 6.1 GREEN, scored — 8 of 10 hit, and the miss is one I warned myself about

| # | predicted | measured |
|---|---|---|
| G1 | four ROM hashes unchanged | ✅ all four byte-identical to `2525ddf` |
| G2 | 23 / 356 / 3869 / 2324 B | ✅ exact, from `rm -rf build` |
| G3 | 122+4 / 718+15 / 522+41 | ✅ exact |
| G4 | main 1551/**285**→0, sub 1451/**102**→0 (+1) | ✅ exact — **seed counts did not move** despite ~90 new lines of prose in `tools/` |
| G5 | kwtable 1041 B, 1 occurrence | ✅ exact |
| G6 | 8/107/1 files, self-tests 10/10 + 11/11, 7 advisory | ✅ exact |
| G7 | check 5: **693** swept, 2 allowlisted, 0 findings | 🔴 **694** swept. 2 allowlisted, 0 findings |
| G8 | check 6: **693** swept, 1 allowlisted, 0 findings | 🔴 **694** swept. 1 allowlisted, 0 findings |
| G9 | check-6 self-test passes; `audit-citations` rc 0 | ✅ **12/12**, rc 0 |
| G10 | corpus ALL GREEN | ✅ 20/20 sequential from clean |

🔴 **G7/G8: I predicted 692 + 1 and shipped 692 + 2** — the spec *and*
`citations-dump-allow.txt`, which is a `.txt` and therefore inside `SWEEP_EXTS`.
This is precisely the D-DOCJUDGE failure (a count predicted from before one's own
deliverables exist), repeated **after** writing the warning against it into §1.1
of this document. ⇒ the warning is not enough; **enumerate the files the slice
will add, by extension, and check each against the sweep's own filter** before
writing the number.

### 6.2 RED — 11 knives, each run twice, planted in all three genres

Self-test positive vectors counted by genre **before** running anything: prose 1,
asm comment 1, python comment 1, markdown table cell 1, indented+suffixed 1 — not
five from one genre.

| # | predicted | measured |
|---|---|---|
| K1a prose plant | rc 1 | ✅ 1, 1 |
| K1b **asm comment** plant | rc 1 | ✅ 1, 1 |
| K1c **python comment** plant | rc 1 | ✅ 1, 1 |
| K1d control — uniform fill | rc 0 | ✅ 0, 0 |
| K1e control — sha256 + 12-char digest | rc 0 | ✅ 0, 0 |
| K2a gut the judgement only | rc 2 | ✅ 2, 2 |
| K2b K2a + remove self-test | rc **2** | ✅ 2, 2 |
| K2c K2a + K2b + remove allowlist entry | rc **0**, silent | ✅ 0, 0 |
| K3a break the allowlist digest | rc 2 | ✅ 2, 2 |
| K3b delete the allowlist FILE | rc 2 | 🔴 **rc 1, 1** |
| K4 `make basic-reloc` with K1a planted | fails twice | ✅ make rc 2 both runs, `[DUMP]` named in both logs |

**K2b/K2c came out exactly as predicted**, which is the point: D-DOCJUDGE
predicted the K2b analogue rc 0 and measured rc 2, and that lesson transferred —
the self-test and the canary are *independent* controls, and **K2c, with both
gone, is the only silent state.**

🔴 **K3b is the miss, and the mechanism is worth keeping.** A *missing* allowlist
file is not a *stale entry*: `parse_listing_allow` returns `{}` for a nonexistent
path, so there is nothing to report as stale — and the canary vector, no longer
allowlisted, surfaces as an ordinary `[DUMP]` finding. rc 1, not rc 2. The gate
**still refuses**, in the "tree regressed" disposition rather than "instrument
broken". Left as-is deliberately: it matches check 5's behaviour exactly, and
diverging the two for a disposition label would cost more than it buys. What
matters is the safety property, and it holds — **K2c remains the only way to get
a silent `rc 0`.**

⚠️ Two apparatus notes. The knife script **refused to start** on its first run
(`REFUSING TO START: audit-citations is not green at rest`) — correctly, but for
the wrong reason: `$AU` held `python3 tools/audit_citations.py` and zsh does
**not** word-split an unquoted parameter, so it became one command name → 127
([[zsh-make-var-word-split]]). The refusal did its job on an apparatus fault
instead of a tree fault. And the restore point was a scratchpad snapshot taken
after a green precondition check, never `git checkout --`
([[knife-cleanup-restores-from-head]]).

### 6.3 The filed claims, scored

| filed | measured |
|---|---|
| *"raw opcode-byte renderings are still uncovered"* | **right** — 20 residue lines, checks 1 and 5 score 0 of 20 |
| *"its false-positive surface is UNMEASURED"* | **right, and not load-bearing** — now measured (393–1326), but §2.2's proof settles it without the numbers |
| *"our own ROM's bytes appear throughout our own docs"* | **right, and understated** — the problem is not our bytes but the *reference machine's*, kept on purpose in 15 live lines |
| *"…and the C-BIOS locator signatures in `probes/lib/latch_check.py` (`SIG`/`SIG2`)"* | 🔴 **WRONG** — that file is already an allowlisted check-5 finding with a written reason, already filed for the human C-BIOS confirm. The one live artifact the residual named was already under review |

Arc running total: **seventeen checked — nine wrong, three right-but-misdirected,
five right** ([[filed-justification-is-a-claim]]).

### 6.4 Corpus — ALL GREEN, sequential, from the clean tree

`basic-reloc` · `repack-machine` · `unit-test` · `audit-citations` ·
`preflight-check` · `injector-check` · `latch-check` · `dexp5-pin` ·
`linemax-acceptance` · `lnblank-acceptance REPEAT=2` · `subrom-acceptance` ·
`subrom-inttest` · `graphics-floor-acceptance` · `graphics-acceptance` · `probe` ·
`fat-error-acceptance` · `diskbasic-acceptance` · `bdos-acceptance` ·
`lof-acceptance`.

### 6.5 What this slice did NOT do

* **Did not build a general raw-byte rule** — declined on §2.2's proof, with the
  three-corpus re-open bar in §3.1. The backstop is the human full-verify trail.
* **Did not turn `provider-oracle-scope.md:685` into a finding** (§2.8). It is a
  review candidate for the next human paper trail; §2.2–§2.4 are the argument
  that a tool must not make that call.
* **Did not change the K3b disposition** — see §6.2.
* **Did not revisit** the inline decoded form, the two check-5 allowlist entries
  awaiting a human C-BIOS confirm, or the 7 `[REVIEW]` advisory headers. All three
  remain filed, unchanged.
